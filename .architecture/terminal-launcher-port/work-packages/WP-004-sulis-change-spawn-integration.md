---
id: WP-004
title: Wire `--spawn` into `sulis-change start` — composes recon, pre-prompt, and `launch_change_terminal`
status: pending
sequence_id: WP-004
dependsOn: [WP-003, WP-005, WP-006]
blocks: []
primitive: extend
group: EXPAND
kind: backend
estimated_token_cost:
  input: 5k
  output: 3k
tdd_section: "3.1 Form (composition root — sulis-change as caller)"
adrs: [ADR-001, ADR-003]
---

## Context

The terminal WP — composes the launcher mechanism (WP-001/WP-002/WP-003), the recon writer (WP-005), and the pre-prompt delivery mechanism (WP-006) into the `sulis-change start` CLI behind a `--spawn` flag.

After this WP lands, `sulis-change start --slug X --primitive Y --spawn` performs:

1. Existing change-creation work (branch, worktree, metadata) — unchanged
2. Synchronous `write_change_context(...)` — produces `~/.sulis/changes/{change_id}/CONTEXT.md` (WP-005)
3. Builds the pre-prompt body from change metadata + a reference to the recon path
4. Invokes `launch_change_terminal(..., pre_prompt=...)` (WP-003 + WP-006)
5. Emits the structured JSON output augmented with `spawn_result`

The pre-prompt body is constructed **here** in `sulis-change`, not in the launcher. The launcher delivers; this WP authors. That separation keeps the launcher free of Sulis-specific copy.

Also ships the v0.43.0 version bump that releases Phase 5 #5 to the marketplace, plus the manual smoke-test scaffolds for the end-to-end spawn path.

Components advanced from PRIMITIVE_TREE: none (early-handoff project — no PRIMITIVE_TREE).

## Contract

Modifications in `plugins/sulis/scripts/sulis-change`:

```python
# 1. New argparse flag on the `start` subcommand:
p_start.add_argument(
    "--spawn", action="store_true",
    help="After creating the change branch + worktree + metadata, write "
         "the recon CONTEXT.md and spawn a new terminal in the worktree "
         "with SULIS_CHANGE_ID set, running `claude --agent sulis` with "
         "a HERE-DOC pre-prompt briefing the agent on the change. "
         "Default off. See plugins/sulis/docs/change-as-primitive-design.md "
         "§ Session binding.",
)

# 2. In cmd_start, after write_change_metadata(...) succeeds:
from _change_context import write_change_context

context_path = write_change_context(
    change_id=change_id,
    metadata=metadata,
    repo_root=repo_root,
)

spawn_result: dict | None = None
if args.spawn:
    from _terminal_launcher import launch_change_terminal
    pre_prompt = _build_change_pre_prompt(
        change_id=change_id,
        handle=handle,
        slug=slug,
        intent=metadata.get("intent", ""),
        primitive=metadata.get("primitive", ""),
        context_md_path=context_path,
    )
    spawn_result = launch_change_terminal(
        change_id=change_id,
        worktree_path=worktree_dest,
        visible=True,
        pre_prompt=pre_prompt,
    )

# 3. The JSON output includes context_path always; spawn_result only when --spawn was set:
emit_ok(data={
    "change_id": change_id,
    "handle": handle,
    "branch": branch,
    "context_md_path": str(context_path),
    "spawn_result": spawn_result,  # None when --spawn absent
    ...,  # existing fields
})

# 4. New private helper in sulis-change (or pushed into _change_context.py at impl
#    time — implementer's call, both are valid):
def _build_change_pre_prompt(
    change_id: str, handle: str, slug: str,
    intent: str, primitive: str, context_md_path: Path,
) -> str:
    """Assemble the HERE-DOC body briefing Sulis on the change.

    Shape (per design doc § Session binding step 5):
        You are Sulis, focused on change {handle}: "{intent}".
        Working directory is the change worktree.
        Context recon is at {context_md_path}.
        Primitive: {primitive}. Suggested next step: see CONTEXT.md.
    """
```

State invariants:
- `--spawn` defaults to **False** (backward-compat — the pre-Phase-5 flow continues to work unchanged).
- The recon write (`write_change_context`) is **unconditional** — even without `--spawn`, the recon runs and `context_md_path` is in the JSON output. (Cheap, useful artefact; nothing downstream is harmed.)
- Spawn failure does **not** unwind the change-creation work. The branch, worktree, metadata, and recon are committed; only the terminal spawn failed. The structured JSON surfaces the failure via `spawn_result.status == "failed"`; the founder can fall back to `cd worktree && claude --agent sulis`.
- The pre-prompt body never embeds secrets — it includes only the change identity (id, handle, slug, intent, primitive) and the absolute path to the recon file. Reading the file is the spawned Claude's job.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_sulis_change.py::test_cmd_start_always_writes_recon` — recon runs whether or not `--spawn` is set; JSON output contains `context_md_path`
- [ ] `tests/unit/test_sulis_change.py::test_cmd_start_default_no_spawn` — `--spawn` absent → no `launch_change_terminal` call (mock the import); `spawn_result` is `None` in JSON
- [ ] `tests/unit/test_sulis_change.py::test_cmd_start_with_spawn_invokes_launcher` — `--spawn` set → mock returns spawned dict; JSON `spawn_result.status == "spawned"`
- [ ] `tests/unit/test_sulis_change.py::test_cmd_start_with_spawn_passes_pre_prompt` — mock `launch_change_terminal`; assert it was called with `pre_prompt=<non-empty str>` and the pre-prompt body contains the handle and the context_md_path
- [ ] `tests/unit/test_sulis_change.py::test_cmd_start_recon_runs_before_spawn` — mock both `write_change_context` and `launch_change_terminal`; assert call order is recon-then-spawn
- [ ] `tests/unit/test_sulis_change.py::test_cmd_start_with_spawn_failure_still_emits_ok` — mock launcher returns `{"status": "failed", ...}`; `sulis-change` still exits 0; JSON includes the failed `spawn_result`
- [ ] `tests/unit/test_sulis_change.py::test_build_change_pre_prompt_includes_handle_and_intent` — assert the produced string contains the handle and intent literally
- [ ] `tests/unit/test_sulis_change.py::test_build_change_pre_prompt_does_not_contain_heredoc_tag` — defensive: the assembled body never contains `SULIS_PROMPT_EOF` (would break WP-006's validator)
- [ ] `tests/manual/smoke_sulis_change_start_spawn.md` — documented end-to-end procedure: run `sulis-change start --slug X --primitive create --intent "..." --spawn` on macOS and Linux; verify new terminal opens, CONTEXT.md is referenced, Sulis greets in change-context mode (composes with WP-007)

### Green — Implementation makes tests pass

- [ ] All Red tests pass
- [ ] Argparse flag wired with the documented help text
- [ ] `cmd_start` modifications stay minimal — recon call ≤ 5 LOC, spawn block ≤ 15 LOC, output augmentation ≤ 5 LOC
- [ ] `_build_change_pre_prompt` ≤ 30 LOC (target — simple string assembly)
- [ ] Manual smoke-test doc covers macOS and Linux walkthroughs with expected JSON shape
- [ ] `plugins/sulis/.claude-plugin/plugin.json` version bumped to v0.43.0
- [ ] `.claude-plugin/marketplace.json` sulis version and metadata version bumped
- [ ] `plugins/sulis/CHANGELOG.md` v0.43.0 entry naming Phase 5 #5 — terminal-launcher-port — and citing WPs 001..007

### Blue — Refactor complete

- [ ] If the `if args.spawn:` block grew past ~20 LOC, extract to `_invoke_terminal_spawn(change_id, metadata, context_path, worktree_dest) -> dict`
- [ ] `_build_change_pre_prompt` consider moving to `_change_context.py` (cohesion with recon) if `sulis-change` is gaining other unrelated helpers — judgment call at impl time
- [ ] No new behaviour introduced in Blue
- [ ] All existing `sulis-change` tests still pass (regression check)

## Sequence

- **dependsOn:** WP-003 (`launch_change_terminal` exists), WP-005 (`write_change_context` exists), WP-006 (`pre_prompt` parameter supported)
- **blocks:** none (this is the terminal WP)
- **Parallelisable with:** none — composes three upstreams; runs last

## Estimated Token Cost

- **Input:** ~5k (TDD § Form composition root + sulis-change current `cmd_start` shape + WP-003 + WP-005 + WP-006 contracts)
- **Output:** ~3k (argparse + cmd_start modification + `_build_change_pre_prompt` + tests + manual smoke doc + CHANGELOG)
- **Total:** ~8k

## Notes

- `--spawn` default-off is deliberate for v0.43.0. The capability ships behind an explicit flag so (a) the existing test suite and manual workflows continue to pass without behaviour change; (b) founders opt in incrementally; (c) if spawn breaks on a fresh OS variant, the founder falls back to `cd worktree && claude --agent sulis` without losing the change. v0.44.0 may flip the default once the manual smoke confirms cross-platform stability.
- The pre-prompt body is **assembled here**, not in the launcher. Keeps the launcher free of Sulis-specific copy and keeps the prompt a literal-string concern co-located with where the change metadata is already in hand.
- The recon write is unconditional even without `--spawn`. Cost is small (three git subprocess calls, single Markdown file). Benefit: any future `/sulis:change focus` or `/sulis:changes` skill that wants to peek at the change's context has the artefact already on disk.
