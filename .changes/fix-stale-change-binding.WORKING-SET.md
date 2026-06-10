# Working Set — fix-stale-change-binding

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Newly-spawned change session inherits a stale SULIS_CHANGE_ID from the cockpit service env, binding the window to the WRONG change. Two-layer fix: (1) launcher unsets+exports so the new id is authoritative on claude's process; (2) agent body trusts the worktree manifest over a disagreeing env.

## 2. Current best solution  (→ Design)
_(not yet established)_

## 3. Decisions in flight  (→ Decision; status: proposed)
_(none yet — one entry per non-trivial choice being weighed: the choice, options
considered, rejected alternatives + rationale, status proposed→accepted on lock)_

## 4. Open questions / unknowns
_(none yet — the live "what we still don't know" parking lot)_

## 5. Rejected so far  (→ Decision.rejected_alternatives)
_(none yet — paths tried and abandoned, **with the why**)_

## 6. Working log  (append-only)
- 2026-06-10T07:01:42Z — Working Set created.
- 2026-06-10T07:01:42Z — LIVE REPRO at binding: worktree manifest=CH-RDJ8SD (fix-stale-change-binding) but env SULIS_CHANGE_ID=01KTR381 → resolve_current_change() returns CH-5DMB1N (unique-wp-ids). Trusting worktree per Layer-2 discipline.
