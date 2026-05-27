---
id: WP-006
title: Extend `_terminal_launcher.py` to support a HERE-DOC pre-prompt delivered to `claude --agent sulis`
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
tdd_section: "3.1 Form (entry_command extension) + 3.2 Armor (pre_prompt safety)"
adrs: [ADR-001]
---

## Context

Per the change-as-primitive design doc § "Session binding mechanics":

> 5. New terminal `cd`s into the change worktree, sets `SULIS_CHANGE_ID={ulid}` env var, invokes `claude` with a HERE-DOC pre-prompt:
> ```
> You are Sulis, focused on change CH-01HQ8X: "fix the auth bug".
> Working directory is the change worktree.
> Context recon is at ~/.sulis/changes/01HQ8X.../CONTEXT.md.
> Current stage: Specify. Suggest: /sulis:specify
> ```

Without the pre-prompt, the spawned `claude --agent sulis` session opens cold — the founder has to manually re-introduce the change to it. The pre-prompt makes the spawn feel "the change is already focused" (the design doc's stated UX).

This WP extends WP-001's `_build_launch_script` + WP-003's `launch_change_terminal` to accept an optional `pre_prompt: str | None` parameter. When set, the generated bash script delivers the prompt as the first positional argument to `claude` (or via stdin).

## Contract

```python
# Extended signature in _build_launch_script (WP-001):

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

    The HERE-DOC delimiter SULIS_PROMPT_EOF is quoted (single-quotes around
    the heredoc tag) so that bash performs no parameter expansion inside the
    prompt body — prevents accidental $-injection from prompt content.

    When pre_prompt is None: exec {entry_command} (unchanged from WP-001).
    """

# Extended signature in launch_change_terminal (WP-003):

def launch_change_terminal(
    change_id: str,
    worktree_path: Path | str,
    *,
    visible: bool = True,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
    pre_prompt: str | None = None,  # NEW
) -> dict:
    """Now forwards pre_prompt to _build_launch_script."""
```

State invariants:
- Pre-prompt is delivered via quoted HERE-DOC (`'SULIS_PROMPT_EOF'` — single quotes) so bash performs NO parameter expansion. No accidental `$VAR` substitution inside the prompt body.
- Pre-prompt is NOT validated by regex — it's free-form text that becomes a user message to Claude. But it IS run through a basic length check (reject > 50KB to prevent runaway prompts) and a check that it does NOT contain the literal string `SULIS_PROMPT_EOF` (which would close the heredoc early).
- Backward-compat: when `pre_prompt=None`, the generated script is byte-identical to the WP-001 baseline.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_no_pre_prompt_unchanged` — assert script with `pre_prompt=None` matches WP-001 baseline byte-for-byte
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_with_pre_prompt_uses_quoted_heredoc` — assert script contains `<<'SULIS_PROMPT_EOF'` (with quotes around the tag)
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_with_pre_prompt_inserts_body_verbatim` — pre_prompt with `$HOME` inside it appears verbatim in the script (no expansion)
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_rejects_oversize_pre_prompt` — pre_prompt > 50KB raises ValueError
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_rejects_pre_prompt_containing_heredoc_tag` — pre_prompt containing literal `SULIS_PROMPT_EOF` raises ValueError
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_forwards_pre_prompt` — mock `_build_launch_script`; assert pre_prompt kwarg forwarded

### Green — Implementation makes tests pass

- [ ] All Red tests pass
- [ ] Pre-prompt feature adds ≤ 30 LOC to `_build_launch_script` (target — small extension)
- [ ] Function docstring updated to describe the pre-prompt path
- [ ] No regression — all existing WP-001 + WP-003 tests still pass

### Blue — Refactor complete

- [ ] Pre-prompt validation extracted to `_validate_pre_prompt(text) -> tuple[bool, str]` if the inline checks grow past ~10 LOC
- [ ] HERE-DOC tag (`SULIS_PROMPT_EOF`) extracted to module-level constant (`_PRE_PROMPT_HEREDOC_TAG`) — readability + single-source-of-truth
- [ ] No new behaviour introduced in Blue

## Sequence

- **dependsOn:** WP-001 (`_build_launch_script` must exist), WP-003 (`launch_change_terminal` must exist)
- **blocks:** WP-004 (sulis-change constructs the pre_prompt and passes it via the integration)
- **Parallelisable with:** WP-005 (different concern — recon vs prompt delivery), WP-007 (different file)

## Estimated Token Cost

- **Input:** ~5k (TDD + WP-001 + WP-003 module state + design doc Session binding section quoting the pre-prompt shape)
- **Output:** ~3k (the parameter additions + tests + docstring updates)
- **Total:** ~8k

## Notes

- Why quoted HERE-DOC (`<<'SULIS_PROMPT_EOF'`)? Bash interprets `<<EOF` as expand-vars + interpret-backticks inside the body. `<<'EOF'` (with quotes around the tag) disables both. We want disabled — the prompt body must not be re-interpreted by the shell.
- The heredoc tag could be made unique-per-spawn (e.g. `SULIS_PROMPT_${change_id}_EOF`) but that's belt-and-braces. Single-tag with a literal-check is simpler and equally safe.
- Why not `claude --prompt "..."` flag? Claude Code's CLI accepts the prompt as the first positional argument; `--prompt` isn't a documented flag. The `$(cat <<'EOF' ... EOF)` substitution puts the prompt body in argv[1] cleanly.
- Pre-prompt size cap of 50KB is generous — typical prompts are < 1KB. The cap exists to catch pathological inputs (e.g., a buggy caller passing the entire `CONTEXT.md` file as prompt instead of a summary).
