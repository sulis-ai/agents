# Recon — create-brain-backlog-and-traversal

Stage 0 completed at: 2026-06-03T05:55:48Z

This marker file's existence indicates that `/sulis:recon` has been run
for this change. The spawned Sulis's stage-inference uses this file to
distinguish "post-recon" from "pre-spawn stub only".

## What's already here (recon findings)

CAPTURE PATH:
- sulis-emit-requirements + sulis-emit-opportunity + sulis-emit-product all
  exist and work — but EVERY one is SRD-shaped (`--from-srd <path>`, parses
  a full SRD markdown). There is no single-idea intake.
- Only plugins/sulis/skills/specify/SKILL.md (deep mode) calls any emitter,
  and only sulis-emit-requirements. opportunity + product are orphaned.
- The real gap: a scoped-out idea has no lightweight intake. The emit logic
  lives in _requirement_emission.emit_requirements_from_srd /
  _opportunity_emission.emit_opportunity_from_srd — both SRD-coupled.

TRAVERSE PATH:
- plugins/sulis/scripts/_brain_query.py (read seam) + sulis-brain-query (CLI)
  exist. CLI modes: --list, --by-id, --verifying, --passing-verifying.
- _brain_query.py HAS where_field_equals / find_requirements but the CLI does
  NOT expose a state filter (--state proposed) or a --requirements convenience.
- NOTHING in skills/ or agents/ calls the query seam. Confirmed orphaned.

STORE:
- .brain/instances/product-development exists with design/ decision/
  lifecyclerun/ subdirs. No requirement/ or opportunity/ subdir yet — nothing
  has been captured into those types in this repo.

SCOPE BOUNDARIES (from brief, confirmed):
- Single-repo .brain/instances is the right home now (Product/Opportunity
  cross-repo home is Platform-tier, deferred).
- EVOLUTION / bitemporal history (#67) stays OUT of this change.
