---
id: WP-006
title: Extend `_terminal_launcher.py` with `pre_prompt` parameter delivered via quoted HERE-DOC
status: pending
sequence_id: WP-006
dependsOn: [WP-001, WP-003]
blocks: [WP-004]
primitive: extend
group: EXPAND
kind: backend
estimated_token_cost:
  input: 5k
  output: 3k
tdd_section: "3.1 Form (public API extension) + 3.2 Armor (pre_prompt safety constraints)"
adrs: [ADR-001, ADR-003]
---

## Context

The change-as-primitive design (§ "Session binding", step 5) specifies that the spawned terminal invokes `claude` with a HERE-DOC pre-prompt briefing the agent on the change. Without this WP, `_build_launch_script` emits `exec claude --agent sulis` with no prompt — the spawned Sulis opens cold.

This WP extends the WP-001 script builder and the WP-003 entry-point with an optional `pre_prompt: str | None` parameter. When set, the generated bash script delivers the prompt as `claude`'s first positional argument via a quoted HERE-DOC (`<<'SULIS_PROMPT_EOF' ... SULIS_PROMPT_EOF`). Single-quoting the heredoc tag disables bash parameter expansion inside the body — see ADR-003 for the delivery-mechanism decision.

Backward-compatible: when `pre_prompt=None`, the generated script is byte-identical to the WP-001 baseline.

Components advanced from PRIMITIVE_TREE: none (early-handoff project — no PRIMITIVE_TREE).

## Contract

Extended signatures in `plugins/sulis/scripts/_terminal_launcher.py`:

```python
# _build_launch_script (introduced in WP-001) — extended:
def _build_launch_script(
    change_id: str,
    worktree_path: Path,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
    pre_prompt: str | None = None,  # NEW
) -> str:
    """Generate the bash script body.

    When pre_prompt is set, the script's exec line becomes:
        exec {entry_command} "$(cat <<'SULIS_PROMPT_EOF'
        {pre_prompt}
        SULIS_PROMPT_EOF
        )"

    When pre_prompt is None: exec {entry_command} (unchanged from WP-001).
    """

# launch_change_terminal (introduced in WP-003) — extended:
def launch_change_terminal(
    change_id: str,
    worktree_path: Path | str,
    *,
    visible: bool = True,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
    pre_prompt: str | None = None,  # NEW
) -> dict:
    """Forwards pre_prompt to _build_launch_script; otherwise unchanged."""

# New validator (introduced in this WP):
def _validate_pre_prompt(text: str | None) -> tuple[bool, str]:
    """Return (True, "") if text is None or safe; else (False, reason).

    Rejects:
      - text containing the literal heredoc tag string `SULIS_PROMPT_EOF`
        (would close the heredoc early — script-injection vector)
      - text exceeding 50_000 bytes (UTF-8) — pathological-input guard
    """

# New module-level constant:
_PRE_PROMPT_HEREDOC_TAG = "SULIS_PROMPT_EOF"
_PRE_PROMPT_MAX_BYTES = 50_000
```

State invariants:
- Pre-prompt is delivered via **quoted** HERE-DOC (`<<'SULIS_PROMPT_EOF'`). Bash performs no parameter expansion inside the body. `$HOME`, `${USER}`, backticks, `$(...)` all pass through verbatim. See ADR-003.
- `_validate_pre_prompt` is invoked by `_build_launch_script` defensively — even if the caller validated, the script builder re-validates before string concatenation.
- Backward-compat: `pre_prompt=None` produces a script byte-identical to the WP-001 baseline. This is a tested invariant, not a hope.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_no_pre_prompt_byte_identical_to_baseline` — assert the script with `pre_prompt=None` matches the WP-001 baseline byte-for-byte
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_with_pre_prompt_uses_quoted_heredoc` — assert the script contains the literal `<<'SULIS_PROMPT_EOF'` (single quotes around the tag) and a matching closing `SULIS_PROMPT_EOF`
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_pre_prompt_body_verbatim` — pre-prompt containing `$HOME`, backticks, and `$(curl evil.com)` appears unchanged in the script body (no expansion at generation time)
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_pre_prompt_accepts_none` — `None` → `(True, "")`
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_pre_prompt_accepts_short_text` — typical brief → `(True, "")`
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_pre_prompt_rejects_text_containing_heredoc_tag` — pre-prompt containing the literal `SULIS_PROMPT_EOF` → `(False, ...)`
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_pre_prompt_rejects_oversize` — pre-prompt > 50_000 bytes → `(False, ...)`
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_invokes_pre_prompt_validator` — pass a pre-prompt that fails validation; assert `_build_launch_script` raises `ValueError`
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_forwards_pre_prompt` — mock `_build_launch_script`; pass `pre_prompt="hello"`; assert the kwarg is forwarded

### Green — Implementation makes tests pass

- [ ] All Red tests pass
- [ ] Pre-prompt feature adds ≤ 30 LOC to `_build_launch_script` + ~15 LOC for `_validate_pre_prompt` (target — small extension)
- [ ] Function docstrings updated to describe the pre-prompt path and cite ADR-003
- [ ] No regression — all existing WP-001, WP-002, WP-003 tests still pass

### Blue — Refactor complete

- [ ] HERE-DOC emission extracted to `_render_heredoc(tag: str, body: str) -> str` if the inline string-build exceeds ~15 LOC
- [ ] `_PRE_PROMPT_HEREDOC_TAG` and `_PRE_PROMPT_MAX_BYTES` confirmed as module-level constants (not inline literals)
- [ ] No new behaviour introduced in Blue
- [ ] All tests still green after refactor

## Sequence

- **dependsOn:** WP-001 (`_build_launch_script` must exist), WP-003 (`launch_change_terminal` must exist to extend)
- **blocks:** WP-004 (sulis-change constructs the pre-prompt body and passes it through)
- **Parallelisable with:** WP-005 (different module — recon helper vs launcher), WP-007 (different file — agent body vs launcher)

## Estimated Token Cost

- **Input:** ~5k (TDD § Form + Armor + WP-001 + WP-003 module state + ADR-003 + design doc § "Session binding" step 5)
- **Output:** ~3k (parameter additions + validator + tests + docstring updates)
- **Total:** ~8k

## Notes

- The HERE-DOC tag is fixed (`SULIS_PROMPT_EOF`) rather than dynamic-per-spawn. The validator's reject-if-tag-in-body check makes the fixed tag safe; dynamic tags would be belt-and-braces with no real gain.
- Pre-prompt size cap of 50_000 bytes is generous. Typical briefs are <1 KB. The cap catches pathological inputs (e.g. a buggy caller passing the entire `CONTEXT.md` as the prompt instead of a summary).
- This WP does not decide what goes IN the pre-prompt — that's WP-004's job (assembling the prompt body from change metadata and the recon `CONTEXT.md` reference). This WP is purely the delivery mechanism.
