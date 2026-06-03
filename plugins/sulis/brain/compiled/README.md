# Brain compiled artifacts (vendored)

These JSON Schemas and triple manifests are **compiled outputs** from the
`dna-runner` in the `sulis-ai/plugins` repo (specifically
`.specifications/business-dna/tools/dna-runner/`). They define the wire-shape
of Brain entities the marketplace persists.

**Do not edit these files directly.** They are vendored copies; regenerate from
upstream when the entity ontology bumps. Source ontology:
`sulis-ai/plugins/.specifications/business-dna/exemplars/{domain}.entities.jsonld`.

Currently mirrored at the ontology's **v0.5.0** for product-development, with
these entities surgically vendored from source **v0.9.0** (each additive +
standalone — only optional fields added, no `$id`-breaking change — so the
mixed-version vendor is safe):

- `scenario` + `testrun`/`testresult` re-point (DR-028 — the `Scenario` entity).
- `requirement` + `decision` — gain the bitemporal fields (`valid_from`/
  `valid_to`/`confidence`), so the living entities can hold version history.
  This is the data-shape foundation for change-as-transaction / evolution.

**`brand-identity`** is vendored from sulis-brain **v0.15.0** (DR-030 — the
domain's first compiled entities). Three schemas, vendored flat as
`compiled/brand-identity/{entity}.schema.json` (matching foundation +
product-development — schemas only; triples are not vendored here):

- `brand` — the upstream identity anchor (id + name + `belongs_to_tenant` +
  the discovery-lifecycle `state` + the nine soft element_schema_v0.3 elements:
  voice/values/positioning/audience/offering/lexicon/claims/visual-identity/
  distinctive-assets). schema.org `Brand`.
- `design-system` — the realized W3C-DTCG token + asset artifact;
  `realizes_identity → brand` (required, minItems 1); `tokens` is a DTCG object
  OR a URI string; WCAG pairs; three-axis lifecycle. The `ux-designer` agent
  emits one when it establishes a design language, and reads it when one exists.
- `tenant` — the foundation mirror (so `Brand.belongs_to_tenant` resolves).

**Still to catch up (breaking / structural — deliberately NOT bundled):**
`lifecyclerun` v1.0.0 → **2.1.0** is BREAKING (`step_name` → required `step`
ref) and needs the emitter (`_brain_emit_helper`) migrated in lockstep — that's
the "LifecycleRun-as-transaction-node" change, coupled + needing a modelling
call. Plus the 10 foundation-mirror entities the PD source now carries (the
mirror-surface reconciliation). Tracked, not done here.

Distribution mechanism (vendoring) is intentional first-slice pragmatism. A
published package or git-submodule is the right longer-term answer; track that
as a follow-on when more entities are wired.
