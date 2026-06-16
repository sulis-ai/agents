# Cockpit Board Refresh — Handover

> This spec was written **after** the design went straight to a build plan, to fill the
> skipped requirements pass. It is the input the existing plan
> (`.architecture/cockpit-board-refresh/`) should be **revised off**.

## What this spec adds that the design + plan didn't have

1. **The unknown / degraded states** (the sharpest gap). The signed-off design drew only
   the healthy ends — On/Off track, Working/Live/Idle. This spec specifies what the card
   shows when there is **no signal**:
   - **Health unknown** (FR-31) — a fresh Recon change with no tests and no artifacts must
     read as honestly unknown, not falsely "On track".
   - **Liveness unknown** (FR-41) — a missing/malformed session record must render a
     distinct unknown probe shape, not a confident "Idle".
   - **No recency** (FR-42) — `lastActivityAt === null` must omit the time, not show "now".
2. **Never-throw / never-500 degradation as a MUST** (BR-11 / NFR-DEGRADE-1), with the
   partial-enrichment, poll-failure, and gone-worktree paths specified (EF-2/3/5).
3. **A grounded existing-vs-gap map** ([`EXISTING_VS_GAP.md`](EXISTING_VS_GAP.md)) — and the
   build-state correction that the plan's WP-001/002/003 **have not actually landed in this
   worktree yet**, so the whole GAP column is real net-new work.
4. **Verifiable scenarios** ([`SCENARIOS.md`](SCENARIOS.md), S-1..S-31) including a dedicated
   block for the unknown/degraded states and the misuse cases — the testable-state intake.
5. **Defensible NFR thresholds** ([`NFR.md`](NFR.md)) the plan referenced abstractly:
   board first-paint, lane scale, enrichment cost, the AA/3:1 contrast + 44px + tablist
   accessibility gates, and the single-poll preservation.

## Reading order

1. [`SRD.md`](SRD.md) — journeys, use cases, the single-foot-verdict rule, health/liveness
   derivation, alternate + error flows, the unknown states.
2. [`EXISTING_VS_GAP.md`](EXISTING_VS_GAP.md) — what to reuse vs build.
3. [`SCENARIOS.md`](SCENARIOS.md) — the driven, observable pass conditions.
4. [`NFR.md`](NFR.md) and [`MISUSE_CASES.md`](MISUSE_CASES.md).
5. [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) — six founder-owned calls, each with a default.

## How the plan should change

- **Add WP coverage for the unknown states.** WP-002 (server health) must emit an `unknown`
  health; WP-005 (card) and the liveness-probe rework must render health-unknown,
  liveness-unknown, and no-recency. Today's WPs only describe the healthy ends.
- **Make the never-500 degradation an explicit DoD** on WP-002 (it's noted in TDD A-1 but
  not a per-WP acceptance criterion).
- **Seed the bootstrap fixture** with the unknown/degraded changes (per the SRD Verification
  Plan) so S-16..S-23 are drivable from zero.
- **Carry the six open decisions** into the WPs as parameters with the recommended defaults.

## Next step

Revise the build plan against this spec:

```
/sulis:plan-work .specifications/cockpit-board-refresh/
```

(or hand `.specifications/cockpit-board-refresh/` to the architecture pass to reconcile the
existing TDD/WPs with the unknown-state + degradation requirements). The design contract is
unchanged and still authoritative for the visual end-state; this spec adds the behavioural
states the visuals didn't cover.
</content>
