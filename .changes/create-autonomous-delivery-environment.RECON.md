# Recon — create-autonomous-delivery-environment

Stage 0 completed at: 2026-06-02T20:24:04Z

## What's already here (lay of the land)

This is the Sulis marketplace repo itself — mature, deeply documented. No
separate context index needed.

### The change has two interwoven goals (primary = the dogfood)
1. **PRIMARY** — first real end-to-end road-test of the testable-state
   scenario loop shipped in sulis v0.90.0 (PR #154): drive THIS change
   through /sulis:specify (author plain-English verification journey ->
   emit Scenario+Workflow+IDEF0 Steps to the brain) -> /sulis:draft-architecture
   (resolve Scenario.exercises placeholder -> real Design) -> implement ->
   /sulis:verify-acceptance --scenario <id> (run straight from the graph).
2. The vehicle — a thin, shippable cockpit slice. Thin enough to ship AND
   verify through the new loop.

### The scenario loop already EXISTS (#154 merged)
Per the design doc (scenario-authoring-source-design.md), the genuinely-open
work it named — founder-facing authoring intake in /sulis:specify, the graph
emit, bundle-from-graph — is what #154 shipped. So our job is to ROAD-TEST
it with a real change, not build it. Watch for friction in the
specify->author->emit->resolve->run flow and capture lessons.

### Prior cockpit thinking on disk (read at specify time, don't rebuild)
- .changes/create-cockpit-mvp.SPEC.md — read-only cockpit MVP (dashboard,
  sidebar, per-thread transcript, file browser, read-only viewer, diff,
  copy-path). Lives at apps/cockpit/.
- .changes/cockpit-contract-preview.SPEC.md — "see the contracts before you
  go" preview (CONTRACT.html via Redoc, UI.html via design-system VIEWER).
  Founder-legible-first dual-register decisions recorded.

The thin slice for THIS change should be ONE small, real, shippable cockpit
capability we can write a plain-English verification journey for and run
through the scenario loop. Scope decided with the founder in /sulis:specify.

## Friction finding (capture as lesson candidate)
- Arrival check (RC-01) expects default branch `dev`; repo just moved to
  trunk-based releases on `main` (recent commit: "re-model release-train
  Workflow to trunk-based"). The RC-01 expectation is now stale. NOT a
  blocker for this change; flag for a standards/arrival-check follow-up.

## Suggested next step
/sulis:specify — scope the thin slice + author the plain-English verification
journey (the dogfood entry point).
