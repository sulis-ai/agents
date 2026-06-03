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
- `lifecyclerun` v1.0.0 → **2.2.0** — RE-VENDORED (WP-002) in lockstep with the
  emitter. This is the BREAKING `step_name` (free string) → required `step`
  (a `dna:step:<ulid>` ref) swap from DR-009, PLUS the DR-013 optional fields
  (`run_id`/`deterministic`/`inputs_ref`/`outputs_ref`) and the optional
  `for_project` ref (the `for_project` mint, DR-032). The re-vendor and the
  emitter migration (`_lifecyclerun_emission` + the three `_brain_emit_helper`
  lifecycle helpers + the `sulis-emit-lifecyclerun` CLI default path) land in
  **one atomic change** (ADR-004), so no instance is ever emitted in a shape the
  vendored schema rejects. The per-run specificity the old `step_name` string
  carried now lives in `run_id`; there is no `step_label` and no `used` field
  (both rejected upstream — DR-013). The three lifecycle Step ULIDs the `step`
  ref points at are authored once in
  `plugins/sulis/instances/lifecycle-steps/steps.jsonld` (WP-001).
- `product` v1.0.0 → **1.1.0** and `opportunity` v2.0.0 → **2.1.0** —
  RE-VENDORED (WP-008) to consume the upstream-minted `wasGeneratedBy`
  provenance edge (the `wasGeneratedBy` mint, DR-031). Each gains an optional
  `wasGeneratedBy → dna:entity:lifecyclerun` edge at card `0..1`, modelled
  exactly like the five existing producers (Component/Release/Metric/
  TestResult/PostMortem) via the `prov_constraints` mechanism — **not** a
  snake_case wire field, no `@context` map, no `_predicate_map` edit (the
  `prov:wasGeneratedBy` predicate already exists). The edge lives in the
  **triples manifest**, not the JSON-Schema body, so the vendored schema
  re-vendor is the `$id` bump only (the vendored tree is schema-only — triples
  are not vendored for any entity). The `0..1` cardinality (vs the producers'
  `1..1`) keeps pre-bump instances valid — a zero-migration additive MINOR.
  **`project` is excluded** — it is a `prov:Plan` (an Entity→Activity edge is a
  type violation), so it stays at v1.0.0, untouched. `wasRevisionOf` appears
  nowhere (ADR-002).

**Still to catch up (breaking / structural — deliberately NOT bundled):**
the 10 foundation-mirror entities the PD source now carries (the mirror-surface
reconciliation). Tracked, not done here.

Distribution mechanism (vendoring) is intentional first-slice pragmatism. A
published package or git-submodule is the right longer-term answer; track that
as a follow-on when more entities are wired.
