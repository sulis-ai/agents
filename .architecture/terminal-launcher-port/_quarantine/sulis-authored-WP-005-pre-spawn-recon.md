---
id: WP-005
title: Pre-spawn reconnaissance — write `CONTEXT.md` for the change before terminal opens
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
tdd_section: "3.1 Form (composition root — sulis-change as caller) + Phase 5 integration"
adrs: [ADR-001]
---

## Context

Per the change-as-primitive design doc § "Session binding mechanics":

> 2. Run recon synchronously; write `CONTEXT.md` to both locations

The pre-spawn recon gathers situational awareness for the change and writes it to `~/.sulis/changes/{change_id}/CONTEXT.md`. The spawned Claude session reads this file (via the HERE-DOC pre-prompt from WP-006) to greet the founder with focused context.

Without this WP, the spawned Sulis greets the founder cold — no knowledge of the change's primitive, slug, base branch state, or what's already in flight. The HERE-DOC pre-prompt in WP-006 references this file; without it, the pre-prompt's `Context recon is at ~/.sulis/changes/{change_id}/CONTEXT.md` line points at nothing.

This WP is **independent of the launcher module** (WP-001 through WP-003). It modifies `sulis-change` (the CLI) to gather + write the recon BEFORE `launch_change_terminal` is called.

## Contract

```python
# New function in _wpxlib.py (or new module _change_recon.py — choose at impl time):

def write_change_context(
    change_id: str,
    metadata: dict,
    repo_root: Path,
) -> Path:
    """Gather pre-spawn recon and write CONTEXT.md.

    Writes to ~/.sulis/changes/{change_id}/CONTEXT.md.

    Recon content:
        - Change metadata: change_id, handle, slug, primitive, branch
        - Git state at change start: HEAD SHA, base SHA, ahead/behind dev
        - Working-tree snapshot: file count, recent commits (last 5 on dev)
        - Hints for the spawned Sulis session: suggested next stage based
          on primitive (e.g. "create" → "start with /sulis:specify"; "fix" →
          "start with /sulis:analyse-codebase to locate the bug")

    Returns:
        Path to the written CONTEXT.md (absolute).
    """
```

```python
# Modified in sulis-change `cmd_start` (existing function):
# After write_change_metadata(...) succeeds, BEFORE the optional --spawn:

context_path = write_change_context(
    change_id=change_id,
    metadata=metadata,
    repo_root=repo_root,
)

# Then if --spawn: launch_change_terminal(...) is called separately
```

State invariants:
- `CONTEXT.md` is written synchronously before `cmd_start` returns. Spawn waits for it.
- The file is human-readable Markdown — operators can `cat ~/.sulis/changes/{change_id}/CONTEXT.md` to see what Sulis sees.
- Recon never modifies the repo. Pure-read git operations only.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_change_recon.py::test_write_change_context_creates_file_at_expected_path`
- [ ] `tests/unit/test_change_recon.py::test_write_change_context_includes_change_metadata` — assert change_id, handle, slug, primitive all present in the rendered markdown
- [ ] `tests/unit/test_change_recon.py::test_write_change_context_includes_git_state` — mock `_run` to return a known HEAD SHA + base SHA; assert they appear in the output
- [ ] `tests/unit/test_change_recon.py::test_write_change_context_includes_primitive_hint` — for primitive="create", assert hint mentions `/sulis:specify`; for primitive="fix", assert hint mentions `/sulis:analyse-codebase`
- [ ] `tests/unit/test_change_recon.py::test_write_change_context_returns_absolute_path`
- [ ] `tests/unit/test_sulis_change.py::test_cmd_start_calls_recon_before_spawn` — mock both `write_change_context` + `launch_change_terminal`; assert the call order

### Green — Implementation makes tests pass

- [ ] All Red tests pass
- [ ] `write_change_context` ≤ 80 LOC (target — small surface)
- [ ] Recon does not modify the repo (assert via `git status` snapshot before/after in an integration smoke)
- [ ] Hints map covers all 22 change primitives + 3 Conventional Commits fallbacks (defensive default for unknown: "start with /sulis:status")

### Blue — Refactor complete

- [ ] Primitive → hint map extracted to module-level constant `_CHANGE_PRIMITIVE_HINTS: dict[str, str]`
- [ ] Git-state gathering helpers (HEAD SHA, base SHA, ahead/behind) extracted as private helpers if the inline subprocess calls exceed ~15 LOC
- [ ] No new behaviour introduced in Blue

## Sequence

- **dependsOn:** none (uses existing _wpxlib helpers like `_run`, `_gh_ref_sha`)
- **blocks:** WP-004 (sulis-change calls write_change_context before launch_change_terminal)
- **Parallelisable with:** WP-001, WP-002, WP-003, WP-007 (different files / different module)

## Estimated Token Cost

- **Input:** ~4k (design doc Session binding section + existing _wpxlib patterns + sulis-change cmd_start current shape)
- **Output:** ~3k (write_change_context function + tests + hints map)
- **Total:** ~7k

## Notes

- `~/.sulis/changes/{change_id}/CONTEXT.md` will co-exist with the launch.sh + session.json from WP-003. All three are per-change local artifacts; the directory's purpose is "everything for this change that lives locally + ephemerally".
- Per the design doc, CONTEXT.md should ALSO be committed to `.architecture/{project}/changes/{ulid}/CONTEXT.md` — defer that to a Phase 5.x follow-up. Local-only is sufficient for v0.43.0.
- The "hints" map is opinionated but lightweight. If a primitive doesn't have a strong canonical next-step (e.g., `chore`), default to "start with `/sulis:status`".
