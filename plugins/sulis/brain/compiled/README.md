# Brain compiled artifacts (vendored)

These JSON Schemas and triple manifests are **compiled outputs** from the
`dna-runner` in the `sulis-ai/plugins` repo (specifically
`.specifications/business-dna/tools/dna-runner/`). They define the wire-shape
of Brain entities the marketplace persists.

**Do not edit these files directly.** They are vendored copies; regenerate from
upstream when the entity ontology bumps. Source ontology:
`sulis-ai/plugins/.specifications/business-dna/exemplars/{domain}.entities.jsonld`.

Currently mirrored at the ontology's **v0.5.0** for product-development.

Distribution mechanism (vendoring) is intentional first-slice pragmatism. A
published package or git-submodule is the right longer-term answer; track that
as a follow-on when more entities are wired.
