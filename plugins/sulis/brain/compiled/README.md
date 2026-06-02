# Brain compiled artifacts (vendored)

These JSON Schemas and triple manifests are **compiled outputs** from the
`dna-runner` in the `sulis-ai/plugins` repo (specifically
`.specifications/business-dna/tools/dna-runner/`). They define the wire-shape
of Brain entities the marketplace persists.

**Do not edit these files directly.** They are vendored copies; regenerate from
upstream when the entity ontology bumps. Source ontology:
`sulis-ai/plugins/.specifications/business-dna/exemplars/{domain}.entities.jsonld`.

Currently mirrored at the ontology's **v0.5.0** for product-development —
**except** `scenario`, `testrun`, and `testresult`, which are surgically
vendored from source **v0.9.0** (DR-028: the `Scenario` entity + its
`of_scenario`/`scenario` re-point). These three are additive and standalone
(no `$id` pins, only optional fields added), so the mixed-version vendor is
safe. The full v0.5.0 → v0.9.0 catch-up (11 new entities + 4 versions of
drift) is a separate, deliberate integration — tracked, not bundled here.

Distribution mechanism (vendoring) is intentional first-slice pragmatism. A
published package or git-submodule is the right longer-term answer; track that
as a follow-on when more entities are wired.
