---
id: WP-005
title: Write `~/.sulis/changes/{change_id}/CONTEXT.md` synchronously before terminal spawn
status: pending
sequence_id: WP-005
dependsOn: []
blocks: [WP-004]
primitive: extend
group: EXPAND
kind: backend
estimated_token_cost:
  input: 4k
  output: 3k
tdd_section: "3.1 Form (composition root — sulis-change as caller)"
adrs: [ADR-001]
---

## Context

The change-as-primitive design (§ "Session binding — how a terminal stays bound to its change", step 2) requires recon to run synchronously before the new terminal is spawned. The output is `~/.sulis/changes/{change_id}/CONTEXT.md` — a Markdown brief that the spawned Sulis session reads via the pre-prompt (WP-006) and via direct file read on session start (WP-007).

Without this WP, the file referenced by the pre-prompt doesn't exist; the spawned Sulis opens cold; the founder-UX described in the design doc doesn't land.

**Independent of the launcher module.** This WP modifies `sulis-change start` (the CLI). It does not touch `_terminal_launcher.py`.

Components advanced from PRIMITIVE_TREE: none (early-handoff project — no PRIMITIVE_TREE).

## Contract

New module `plugins/sulis/scripts/_change_context.py` (separate from `_wpxlib.py` to keep `_wpxlib`'s growth bounded — see ADR-002 note about future `lib/` split):

```python
# plugins/sulis/scripts/_change_context.py — created in this WP

from pathlib import Path

# Module-level constant — opinionated next-step hint per primitive.
# Used by the rendered CONTEXT.md to suggest where the founder goes next.
_PRIMITIVE_NEXT_STEP_HINTS: dict[str, str] = {
    "create":   "start with `/sulis:specify` to capture what you want to build",
    "fix":      "start with `/sulis:analyse-codebase` to locate the bug",
    "refactor": "start with `/sulis:analyse-codebase` to scope the structural change",
    # ... covers all 22 change primitives + 3 Conventional Commits fallbacks
    # Defensive default for unknown primitive: "start with `/sulis:status`"
}

def write_change_context(
    change_id: str,
    metadata: dict,
    repo_root: Path,
) -> Path:
    """Gather pre-spawn context and write it to ~/.sulis/changes/{change_id}/CONTEXT.md.

    Sections produced in the rendered markdown:
      - Change identity: change_id, handle, slug, primitive, branch
      - Git state at spawn: HEAD SHA, base SHA, ahead/behind dev counts
      - Working-tree snapshot: file count, last 5 commits on dev
      - Suggested next step: looked up from _PRIMITIVE_NEXT_STEP_HINTS

    Pure-read: never modifies the repo. Subprocess calls are git-status,
    git-rev-parse, git-log only.

    Returns:
        Absolute path to the written CONTEXT.md.
    """
```

Wired into `sulis-change cmd_start` (existing function in `plugins/sulis/scripts/sulis-change`), called after `write_change_metadata(...)` succeeds and before any `--spawn` work:

```python
# In sulis-change cmd_start — added in this WP:
from _change_context import write_change_context

context_path = write_change_context(
    change_id=change_id,
    metadata=metadata,
    repo_root=repo_root,
)
# WP-004 will later read this path back when constructing the pre-prompt.
```

State invariants:
- The write is **synchronous and blocking**. `cmd_start` does not return until `CONTEXT.md` is on disk.
- The function never modifies the repo. Static-analysis-friendly: only `git rev-parse`, `git log`, `git status --porcelain` subprocess calls.
- `~/.sulis/changes/{change_id}/` directory is created if absent (`mkdir -p` semantics).
- File is human-readable Markdown — `cat ~/.sulis/changes/{change_id}/CONTEXT.md` is a supported debugging move.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_change_context.py::test_write_change_context_creates_file_at_expected_path`
- [ ] `tests/unit/test_change_context.py::test_write_change_context_returns_absolute_path`
- [ ] `tests/unit/test_change_context.py::test_write_change_context_includes_change_identity` — assert change_id, handle, slug, primitive, branch all present in the rendered markdown
- [ ] `tests/unit/test_change_context.py::test_write_change_context_includes_git_state` — mock the git subprocess helpers to return a known HEAD SHA + base SHA + ahead/behind tuple; assert all appear in the output
- [ ] `tests/unit/test_change_context.py::test_write_change_context_includes_next_step_hint_for_create` — primitive=`create` → hint mentions `/sulis:specify`
- [ ] `tests/unit/test_change_context.py::test_write_change_context_includes_next_step_hint_for_fix` — primitive=`fix` → hint mentions `/sulis:analyse-codebase`
- [ ] `tests/unit/test_change_context.py::test_write_change_context_defaults_hint_for_unknown_primitive` — primitive=`weirdo` → hint mentions `/sulis:status`
- [ ] `tests/unit/test_change_context.py::test_write_change_context_does_not_modify_repo` — capture `git status --porcelain` before and after; assert identical
- [ ] `tests/unit/test_change_context.py::test_write_change_context_creates_parent_dir_if_absent` — uses tmp HOME via `monkeypatch.setenv("HOME", ...)`

### Green — Implementation makes tests pass

- [ ] All Red tests pass
- [ ] `write_change_context` ≤ 80 LOC (target — single-purpose function)
- [ ] `_PRIMITIVE_NEXT_STEP_HINTS` covers all 22 change primitives plus the 3 Conventional Commits fallbacks (`docs`, `chore`, `test`) — defensive default for anything else: `"start with /sulis:status"`
- [ ] Implementation follows `references/boring-code.md` — explicit types, stdlib only, no metaprogramming
- [ ] Module docstring cites the change-as-primitive design doc § "Session binding"

### Blue — Refactor complete

- [ ] Git-state gathering extracted to private helpers (`_head_sha`, `_base_sha`, `_ahead_behind`) if the inline subprocess block exceeds ~15 LOC
- [ ] Rendered-markdown template extracted to a `_render_context_md(...)` helper if the inline `.format()` block exceeds ~20 LOC
- [ ] No new behaviour introduced in Blue
- [ ] All tests still green after refactor

## Sequence

- **dependsOn:** none (uses already-shipped `_wpxlib` subprocess helpers like `_run`)
- **blocks:** WP-004 (sulis-change wiring composes recon + pre-prompt + spawn)
- **Parallelisable with:** WP-001, WP-002, WP-003, WP-006, WP-007 (different file; no Python dependency on launcher module)

## Estimated Token Cost

- **Input:** ~4k (design doc § "Session binding" + existing `_wpxlib` subprocess patterns + sulis-change `cmd_start` current shape)
- **Output:** ~3k (`_change_context.py` ~100 LOC + tests ~120 LOC)
- **Total:** ~7k

## Notes

- The committed copy at `.architecture/{project}/changes/{ulid}/CONTEXT.md` (per design doc step 2 — "write CONTEXT.md to both locations") is deferred. v0.43.0 ships the local-only write because the committed-copy path adds repo-write semantics + ADR weight that isn't needed for the spawn UX itself. Tracked as a follow-up.
- The next-step hint is opinionated but cheap. If a primitive doesn't have a strong canonical next step (e.g. `chore`), the default points the founder at `/sulis:status` — never silent, never wrong.
- Performance bound (per NFR-3 `spawn-time < 2s`): the recon's three git subprocess calls together should complete well under 500ms on a normal-sized repo. If a future repo trips this, the bound becomes a real test, not a Note.
