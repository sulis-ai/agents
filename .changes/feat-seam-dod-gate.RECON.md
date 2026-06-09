# Recon — feat-seam-dod-gate (CH-01KTP7)

Stage 0 completed at: 2026-06-09T13:07:23Z

Marker file: its existence signals `/sulis:recon` ran for this change, so
stage-inference can distinguish "post-recon" from "pre-spawn stub only".

## What's already here (recon findings)

- **This is fix "A" of a 4-change methodology program** (sibling tasks #96/#97;
  upstream substrate #98). The durable baton is `.changes/feat-seam-dod-gate.HANDOFF.md`
  — read it first.
- **Upstream substrate SHIPPED** (PR #259, commit e4cb9a09): the headless scenario
  runner is tiered (scripted vs agent-step), isolated (reset→process→env ladder),
  and carries an equality|property verdict-invariant evaluated over the REAL saved
  record → observed | blocked. This verdict is the field the seam-close gate reads.
- **Scripted-tier drivers are live** (`_scenario_dispatch.py`: http_call, subprocess,
  browser) and produce a real saved record. The runner the gate calls
  (`sulis-verify-acceptance`) wraps this today.
- **Known stub boundary**: the agent-step tier's EXECUTION (browser-MCP / live
  subagent dispatch) is deferred to #92 (`agent-step-execution-mcp`). Declared,
  not executed — such seams return blocked/deferred, which observed-or-blocked
  correctly treats as "not done".
- **Acceptance fires too late today**: only at SHIP (gate 4.8 in
  `skills/change/SKILL.md`, via `sulis-verify-acceptance`). The change re-times this
  to seam-close.
- **No seam-close gate exists yet** in run-wp / run-all — confirmed absent. This is
  new gate logic, not a modification. Natural hook: run-wp Step 7 completion /
  run-all integration-WP completion of a seam-spanning WP.
- **Seam definition** lives in `CONTRACT_FIRST_STANDARD.md` (producer/consumer;
  contract WP first, parallel per-kind, integration last). Seam-close = integration point.

## Standing repo condition (not a blocker)

- Arrival check: `main` does NOT require the branch checks (this repo is on a plan
  without branch protection → branch-CI is advisory, not blocking). "Done" later
  must be grounded in the gate that actually blocks, not advisory CI.

## Open question for /sulis:specify (resolve FIRST)

- **Do enumerated Scenarios tile the seam set 1:1?** If yes → the gate's unit is the
  Scenario id. If no → the unit drops to the seam / contract-WP boundary and keys off
  the CONTRACT_FIRST seam boundary, not a Scenario id. This determines the gate's
  trigger shape.

See `plugins/sulis/agents/sulis.md` "Change context" section for stage-inference rules.
