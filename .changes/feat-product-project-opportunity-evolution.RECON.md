# Recon — feat-product-project-opportunity-evolution

Stage 0 completed at: 2026-06-03T06:10:34Z

This marker's existence indicates `/sulis:recon` has been run for this change.
The spawned Sulis's stage-inference uses this file to distinguish "post-recon"
from "pre-spawn stub only".

## Verified against code on this branch (base main @ 50eb6d0)

- LifecycleRun schema = v1.0.0 with `step_name` string (NOT a Step ref). A
  v2.1.0 migration making it a required `step` ref is BREAKING. CONFIRMED.
  (plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json)
- Bitemporal fields (valid_from/valid_to/confidence/sys_status) EXIST on all
  ~26 living-entity schemas; NO emitter writes history. Evolution is OFF for
  everyone. CONFIRMED (_brain_emit_helper.py + _*_emission.py write current
  snapshots only; zero PROV writes).
- PROV vocabulary is ABSENT entirely — no wasGeneratedBy/used/wasRevisionOf in
  any schema or emission code. Adding PROV is greenfield, not "use existing
  grammar". (refinement of the brain-consult assumption)
- Product/Opportunity emit to repo-local .brain/instances/... (single-repo
  home) — ALREADY IN MAIN (CH-01KSWZ #118). No central Platform store exists
  yet; multi-repo shared-brain is a modelling decision, not a thing to wire to.
- Project is minted to .sulis/projects/<slug>.jsonld by /sulis:discover-project
  (minter.py:93), NOT .brain/instances — the real inconsistency to reconcile.
  Project schema:5 states the multi-repo case; belongs_to_product_ref is a
  plain string; depends_on/consumed_by are the inter-repo edges. CONFIRMED.

## Coordination (no duplication-in-flight)

- change/create-brain-backlog-and-traversal (CH-01KT60) sits AT main — branched,
  no unique commits yet.
- change/refactor-living-emitters-write-history is a STALE pointer at the
  docs-only commit 3da681c (the plugin-evolution thread design), already merged
  into main. No implementation in flight.
- Relevant design docs landed on main and MUST be read at specify/design:
  docs/plugin-evolution-context-brief.md, docs/sulis-distribution-and-deployment-design.md,
  docs/trunk-based-release-workflow-remodel.md, docs/claude-code-plugin-distribution-brief.md

## Arrival check

RC-01 flags default branch = main (expected dev) — STALE for this repo: it
moved to trunk-based (main) per the release-train re-model. Not a blocker here.
