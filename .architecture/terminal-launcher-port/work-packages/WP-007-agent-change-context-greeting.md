---
id: WP-007
title: Extend Sulis agent body to recognise `SULIS_CHANGE_ID` and greet in change-context mode
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
tdd_section: "3.1 Form (session-bound Sulis behaviour) — composition with WP-005 + WP-006"
adrs: []
---

## Context

The spawned terminal sets `SULIS_CHANGE_ID={ulid}` (WP-003) and delivers a pre-prompt briefing the agent on the change (WP-006). The agent body at `plugins/sulis/agents/sulis.md` currently has no instructions for handling either. Without this WP:

- The pre-prompt arrives but the agent has no protocol to verify it against the env var
- The recon `CONTEXT.md` (written by WP-005) is never read by the agent
- The founder gets a default Sulis greeting rather than a change-focused one

This WP adds a new section to the Sulis agent body — *"Change context (when `SULIS_CHANGE_ID` is set)"* — that codifies session-start behaviour:

1. On first response, check `SULIS_CHANGE_ID` via `Bash`
2. If set, resolve the change manifest via `_wpxlib.resolve_current_change()` (shipped at Phase 5 #2)
3. Read `~/.sulis/changes/{change_id}/CONTEXT.md` if present (written by WP-005)
4. Greet the founder with change context, surfacing the recon's suggested next step
5. Stale-env handling: if the env var is set but no matching change exists, surface honestly and offer three paths (continue change-less, start new change, list in-flight changes)

**Pure markdown change.** No Python, no test runner, no new imports. Verification is manual smoke (three documented scenarios).

Components advanced from PRIMITIVE_TREE: none (early-handoff project — no PRIMITIVE_TREE).

## Contract

New section inserted into `plugins/sulis/agents/sulis.md`, placed after *Identity* / *Required reading* / *Workflow* and before per-phase content (logical grouping with session-start behaviours):

```markdown
## Change context (when `SULIS_CHANGE_ID` is set)

When a session starts and `SULIS_CHANGE_ID` is present in the environment,
you are bound to a specific change. Your first response MUST:

1. **Verify the binding.** Run:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'plugins/sulis/scripts')
   from _wpxlib import resolve_current_change
   import json
   c = resolve_current_change()
   print(json.dumps(c) if c else 'null')
   "
   ```
   Returns the change manifest dict or `null` if the env var is set but no
   matching change branch exists.

2. **Read the recon.** If `~/.sulis/changes/{change_id}/CONTEXT.md` exists,
   read it. It contains change identity, git state, and a suggested next
   step.

3. **Greet in change-context mode.** Example:

   > *"I see you're focused on change CH-01KSG1: 'fix the auth bug' (a
   > 'fix' primitive). The recon flagged 12 files in the auth flow worth
   > looking at first. Suggested next step: `/sulis:analyse-codebase` to
   > narrow down where the bug actually lives.
   >
   > Or tell me what you've already tried — I can route from there."*

4. **Downstream dispatch carries the change_id.** Specialist invocations
   (requirements-analyst, engineering-architect, executor) receive
   `change_id` in their context. Per WORK_PACKAGE_STANDARD v1.1.0, any
   WPs created during this session carry `change_id` in frontmatter.

### When `SULIS_CHANGE_ID` resolves to null

The env var is set but no matching change branch exists. Typical cause:
the founder switched git branches; the shell still has the old value.
Surface honestly:

> *"Your shell has `SULIS_CHANGE_ID={value}` but I can't find a matching
> change branch. Either the change was finished and cleaned up, or you're
> in the wrong terminal. Three options:
> 1. Continue in change-less mode (treat this like a normal Sulis session)
> 2. Help you start a new change with `/sulis:change start`
> 3. Show in-flight changes with `/sulis:changes` (when that ships)"*

### When `SULIS_CHANGE_ID` is unset

No special behaviour. Proceed with normal Sulis greeting and journey
routing per existing convention.
```

State invariants:
- Section placement is **after** the existing top-of-agent identity blocks and **before** the phase-specific content. This puts session-start behaviour next to the agent's other startup rules.
- The new section does not rewrite or replace any existing content. It is purely additive.
- Sulis already has `Bash` tool permission (`tools: "*"` per its frontmatter) — no permission change needed.

## Definition of Done

### Red — Failing tests written

Agent-body changes are not unit-testable in the conventional sense. The "test" is the agent producing the expected behaviour in a real session. Three manual smoke procedures document the expected paths:

- [ ] `tests/manual/smoke_sulis_change_id_resolves.md` — procedure: set `SULIS_CHANGE_ID` to a valid existing ULID; run `claude --agent sulis "Hi"`; verify the greeting includes change identity + suggested next step from the recon
- [ ] `tests/manual/smoke_sulis_change_id_stale.md` — procedure: set `SULIS_CHANGE_ID` to a non-existent ULID; run `claude --agent sulis "Hi"`; verify the agent surfaces the stale-env case with the three options
- [ ] `tests/manual/smoke_sulis_change_id_unset.md` — procedure: unset `SULIS_CHANGE_ID`; run `claude --agent sulis "Hi"`; verify the agent uses the default greeting (no regression)

### Green — Implementation makes tests pass

- [ ] New section *"Change context (when `SULIS_CHANGE_ID` is set)"* inserted at the documented position in `plugins/sulis/agents/sulis.md`
- [ ] All three manual smoke procedures documented and runnable (a founder following the doc could verify)
- [ ] The existing add-agent v0.1.0 verification report for Sulis (`plugins/sulis/agents/sulis.VERIFICATION_REPORT.md`) still passes — Coaching Delivery / Tone Conformance / Register Switch unchanged
- [ ] Section length ≤ 80 lines (the longest section currently in `sulis.md` is comparable; this fits proportionally)

### Blue — Refactor complete

- [ ] If the three branch states (resolves / stale / unset) grew past ~80 lines combined, collapse the "When stale" + "When unset" tails into a single decision-tree paragraph
- [ ] Cross-references to other skills (`/sulis:analyse-codebase`, `/sulis:change start`, `/sulis:changes`) point at real skill names — no dead links
- [ ] No new behaviour introduced in Blue

## Sequence

- **dependsOn:** none (uses already-shipped `_wpxlib.resolve_current_change` from Phase 5 #2)
- **blocks:** none (the agent will recognise change context once landed, but nothing else in this WP set requires it to be done first)
- **Parallelisable with:** ALL other WPs in this set (different file; no Python or test interaction)

## Estimated Token Cost

- **Input:** ~4k (current Sulis agent body + Phase 5 #2 `resolve_current_change` API + design doc § "Session binding")
- **Output:** ~2k (the new markdown section ~70 lines + 3 manual smoke procedures ~30 lines each)
- **Total:** ~6k

## Notes

- This WP does not trigger a re-run of `sulis:add-agent`'s 5-gate methodology. It is an additive section that extends the existing agent's responsibilities, not a re-author. Per add-agent's deepening mode: *"Gate 3 EXTENDS the existing agent.md (does not rewrite); preserves existing dispatch trigger if it still routes correctly."*
- After this WP lands, the spawned Sulis session has **two independent paths** into change context: (a) the HERE-DOC pre-prompt from WP-006 brief, (b) the agent's own `SULIS_CHANGE_ID` check at session start. Both arrive at the same greeting; the pre-prompt is the priming, the env-var check is the verification. Robust by construction.
