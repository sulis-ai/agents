# Working Set — feat-seam-dod-gate

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Re-time real-data Scenario acceptance (observed-or-blocked) from ship-stage to seam-close, so an un-driven seam between two pieces of work is caught when cheap to fix, not after merge. Consumes the shipped verdict-invariant substrate (#259).

## 2. Current best solution  (→ Design)
A seam-close gate in the build loop (run-wp / run-all) that fires when a
contract-first seam closes (producer+consumer both done, or integration/composite
WP completes). It drives the real-data Scenario acceptance for that seam via the
existing `sulis-verify-acceptance` runner (wrapping the shipped #259 substrate) and
reads the equality|property verdict-invariant over the REAL saved record →
observed | blocked. Blocked halts seam-close as "not done", surfaced in founder
English (which seam, what wasn't driven). Ship-stage gate 4.8 stays as a backstop.

## 3. Decisions in flight  (→ Decision; status: accepted)
- **Gate trigger unit = the seam (contract-WP boundary), NOT the Scenario.**
  status: accepted. Resolved by examining the code at recon (handoff's #1
  "resolve-first" uncertainty). At a closing seam, drive the Scenarios that
  verify the requirements the seam's two sides implement.
- **A closing seam with no covering Scenario → blocked.** status: accepted.
  Its real-data behaviour was never driven (observed-or-blocked).
- **Agent-step-tier seams report blocked until #92 lands.** status: accepted.
  Correct behaviour, not a bug; escapable via the existing --allow-deferred flag.
- **Keep the ship-stage drive (gate 4.8) as a backstop; don't remove it.**
  status: accepted. Defence in depth — the new gate moves the *primary* catch
  earlier, it doesn't replace ship.

## 4. Open questions / unknowns
- Exact mechanism by which the gate maps a closing seam → the requirements its
  WPs implement → the covering Scenarios. (Design-stage detail; principle is set.)
- Precise hook point in run-wp Step 7 vs run-all integration-WP completion.
  (Design-stage; recon confirmed no seam-close gate exists today.)

## 5. Rejected so far  (→ Decision.rejected_alternatives)
- **Gate unit = the Scenario id** (handoff's branch-1) — REJECTED: Scenarios key
  to requirements/journeys and do not tile seams 1:1 (verified in the code at
  recon), so a Scenario-keyed trigger can't reliably fire per-seam.
- **Replace the ship-stage gate entirely** — REJECTED: leaves a hole if the
  seam-close gate is bypassed; defence-in-depth keeps both.

## 6. Working log  (append-only)
- 2026-06-09T13:07:30Z — Working Set created.
- 2026-06-09T13:10:43Z — Specify (standard): gate unit resolved = seam not Scenario (Scenarios don't tile seams 1:1, verified in code). SPEC.md written, 6 test-first acceptance criteria.
- 2026-06-09T13:35:45Z — Design complete: TDD + 5 ADRs + 6 WPs (2 parallel tracks: code WP-001..004, standards WP-005..006). Hook = wpx-step12 done-transition. Open Qs resolved: rely on journey-filtered fallback (no implements: backfill); brain-evidence as already-driven signal. Rubric PASS.
- 2026-06-09T14:34:06Z — Implement complete: all 6 WPs merged to change branch (37b092ac). Two test-first pairs (WP-001/002 gate module, WP-003/004 wiring+docs) landed sequentially; standards track (WP-005/006) parallel. Full tests/unit/ suite green (2338 passed), compileall + routing-coverage + change-branch branch-ci all green. Ready for Review stage.
