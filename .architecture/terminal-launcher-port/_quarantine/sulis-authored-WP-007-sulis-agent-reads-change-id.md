---
id: WP-007
title: Update Sulis agent body to read `SULIS_CHANGE_ID` at session start + greet with change context
status: pending
sequence_id: WP-007
dependsOn: []
blocks: []
primitive: extend
group: EXPAND
kind: docs
estimated_token_cost:
  input: 4k
  output: 2k
tdd_section: "3.1 Form (session-bound Sulis behaviour) + Phase 5/6 integration"
adrs: []
---

## Context

The spawned terminal sets `SULIS_CHANGE_ID={ulid}` (per WP-003) and the HERE-DOC pre-prompt (per WP-006) tells the agent it's focused on a specific change. But the agent body at `plugins/sulis/agents/sulis.md` doesn't currently know what to do with that env var. Result: even with WP-001..WP-006 landed, the spawned Sulis would receive the pre-prompt but have no instructions to verify it against `SULIS_CHANGE_ID` or to read `~/.sulis/changes/{change_id}/CONTEXT.md` for the recon.

This WP adds a new section to the Sulis agent body — "Change context (when SULIS_CHANGE_ID is set)" — that codifies the session-bound behaviour:

1. On first response in a session, check `SULIS_CHANGE_ID` via `Bash`
2. If set, resolve the change manifest via `_wpxlib.resolve_current_change()` (already shipped at Phase 5 #2)
3. Read `~/.sulis/changes/{change_id}/CONTEXT.md` if present
4. Greet the founder with the change context — "I see you're in change CH-X: '{intent}'. Recon shows {summary}. Want me to walk you through the next step?"

This is a **pure agent-body modification** — no Python code, no test changes. It modifies markdown in `plugins/sulis/agents/sulis.md`.

## Contract

New section inserted into `plugins/sulis/agents/sulis.md`, structured as below:

```markdown
## Change context (when SULIS_CHANGE_ID is set — Phase 5 / Phase 6 integration)

When a session starts and `SULIS_CHANGE_ID` is in the environment, you are
bound to a specific change. Your first response MUST:

1. **Verify the binding.** Run:
   ```bash
   python3 -c "
   import sys
   sys.path.insert(0, 'plugins/sulis/scripts')
   from _wpxlib import resolve_current_change
   import json
   c = resolve_current_change()
   print(json.dumps(c) if c else 'null')
   "
   ```
   This returns the change manifest (dict with change_id, handle, slug,
   primitive, branch, worktree_path) or `null` if the env var is set but
   no matching change branch exists.

2. **Read the recon** at `~/.sulis/changes/{change_id}/CONTEXT.md` if it
   exists. This is the pre-spawn reconnaissance written by `sulis-change start`.

3. **Greet the founder in change-context mode**, e.g.:

   > *"I see you're focused on change CH-01KSG1: 'fix the auth bug' (a
   > 'fix' primitive). The recon found 12 files in the auth flow that match
   > common bug-shape patterns. Suggested next step: `/sulis:analyse-codebase`
   > to narrow down where the bug actually lives.
   >
   > Or: tell me what you've already tried — I can route from there."*

4. **All subsequent dispatch routes through the change.** Specialist
   invocations (requirements-analyst, engineering-architect, executor) get
   the change_id passed in their context. Per WORK_PACKAGE_STANDARD v1.1.0,
   any WPs created during this session carry the change_id in frontmatter.

### When SULIS_CHANGE_ID resolves to null

Means the env var is set but no matching change branch was found. This is
a stale env-var scenario (typical cause: founder switched git branches but
the shell still has the old SULIS_CHANGE_ID). Surface honestly:

> *"Your shell has `SULIS_CHANGE_ID=01KSG1TD2CEZ63G5BJ7C3HDCZD` but I can't
> find a matching change branch. Either the change was finished + cleaned
> up, or you're in the wrong terminal. Want me to:
> 1. Continue in change-less mode (treat this like a normal sulis session)
> 2. Help you start a new change
> 3. Show you the in-flight changes via `/sulis:changes` (when that lands)"*

### When SULIS_CHANGE_ID is unset

No special behaviour — proceed with normal Sulis greeting + journey routing
per existing convention.
```

## Definition of Done

### Red — Failing tests written

Per the eight-standards rubric, agent-body changes don't have unit tests in the conventional sense — the "test" is the agent producing the expected behaviour in a real session. Three smoke tests document the expected paths:

- [ ] `tests/manual/smoke_sulis_change_context.md` — manual procedure: set `SULIS_CHANGE_ID` to a valid ULID, run `claude --agent sulis "Hi"`, verify the greeting includes change context
- [ ] `tests/manual/smoke_sulis_change_id_stale.md` — manual procedure: set `SULIS_CHANGE_ID` to a non-existent ULID, verify the agent surfaces the stale-env case honestly
- [ ] `tests/manual/smoke_sulis_no_change_id.md` — manual procedure: unset `SULIS_CHANGE_ID`, verify the agent uses default greeting (no regression)

### Green — Implementation makes tests pass

- [ ] New section "Change context (when SULIS_CHANGE_ID is set — Phase 5 / Phase 6 integration)" inserted into `plugins/sulis/agents/sulis.md`
- [ ] Section is placed AFTER the existing "Identity" / "Required reading" / "Workflow" sections, BEFORE the per-phase content (logical grouping with session-start behaviours)
- [ ] Manual smoke-test docs written
- [ ] Sulis agent body still passes its existing add-agent v0.1.0 verification (Coaching Delivery / Tone Conformance / Register Switch — see plugins/sulis/agents/sulis.VERIFICATION_REPORT.md)

### Blue — Refactor complete

- [ ] If the new section grew past ~80 lines, extract the "When SULIS_CHANGE_ID is set" + "When stale" + "When unset" triad into a single decision-tree paragraph
- [ ] Cross-references to existing skills (`/sulis:analyse-codebase`, etc.) verified — no dead links
- [ ] No new behaviour introduced in Blue

## Sequence

- **dependsOn:** none (uses already-shipped Phase 5 #2 `resolve_current_change` helper)
- **blocks:** none — this WP adds value alongside WP-004 but doesn't block it
- **Parallelisable with:** ALL other WPs in this set (different file, no Python dependency on launcher)

## Estimated Token Cost

- **Input:** ~4k (current Sulis agent body sections + Phase 5 #2 helper docs + design doc Session binding flow)
- **Output:** ~2k (the new markdown section ~80 lines + 3 manual smoke docs ~30 lines each)
- **Total:** ~6k

## Notes

- This WP shouldn't trigger a re-run of `sulis:add-agent`'s 5-gate methodology — it's an additive section that extends the existing agent's responsibilities, not a re-author. Per add-agent's deepening mode: "Gate 3 EXTENDS the existing agent.md (does not rewrite); preserves existing dispatch trigger if it still routes correctly". OK as-is.
- The agent body says to invoke `Bash` and `python3 -c "..."`. This means Sulis needs `Bash` tool permission (which it has — `tools: "*"` per its frontmatter).
- After this WP lands, the founder's `claude --agent sulis` invocation (whether spawned by `sulis-change start --spawn` or run manually) will recognize change context whenever `SULIS_CHANGE_ID` is set. The HERE-DOC pre-prompt from WP-006 becomes a redundant safety net (Sulis would figure out the context from the env var alone) rather than the primary mechanism — but both together gives the most robust UX.
