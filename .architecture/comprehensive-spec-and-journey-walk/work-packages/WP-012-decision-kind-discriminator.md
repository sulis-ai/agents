---
id: WP-012
title: Add the ADR/BDR kind discriminator and fix the multi-decision id collision
status: pending
sequence_id: WP-012
dependsOn: [WP-001]
blocks: []
estimated_token_cost:
  input: 7k
  output: 5k
tdd_section: 7.4 (decision.schema.json + _decision_emission.py + sulis-emit-decision) + 9.1 (migration)
adrs: [ADR-006]
primitive: extend
group: expand
kind: backend
verification:
  adapter: methodology
  artifact: tests/methodology/test_bdr_distinct_from_adr.py::test_emit_bdr_carries_kind_bdr
---

## Context

The `decision` brain schema has no `kind`/`category` field — there is no way to
distinguish a technical ADR from a business BDR (FR-17). ADR-006 adds
`kind ∈ {adr, bdr}` as a discriminator on the existing `decision` entity (not a
new entity type). The emitter (`_decision_emission.py` + `sulis-emit-decision`)
gains `--kind` / infers from the source dir. The design flagged a multi-decision
`@id` collision — this WP fixes it in the same change (the two are coupled: both
touch the decision emission path). Migration is additive-optional: absent `kind`
reads as `adr`, so existing `decision/*.jsonld` need no rewrite (§9.1). Ships the
SC-17 driver scripts (`_drive_decisions.py`, `_assert_bdr_adr.py`).

Advances DESIGN.md §6.5 hop T11 (GAP → WP, Phase 3) and the §7.4
`decision.schema.json + _decision_emission.py + sulis-emit-decision` "Modify"
row.

## Contract

```text
# plugins/sulis/brain/compiled/product-development/decision.schema.json (this WP modifies)
#   Add: "kind": { "enum": ["adr", "bdr"], "default": "adr" }  (additive-optional)
# plugins/sulis/scripts/_decision_emission.py (this WP modifies)
#   Accept --kind; infer from --from-adr / --from-bdr source dir; fix the
#   multi-decision @id collision (each emitted decision gets a distinct @id).
# plugins/sulis/scripts/sulis-emit-decision (this WP modifies)
#   Surface --kind / --from-bdr.

# plugins/sulis/scripts/_drive_decisions.py  (this WP creates) — drives an emit of a BDR + an ADR
# plugins/sulis/scripts/_assert_bdr_adr.py    (this WP creates) — exit 0 iff the BDR is kind:bdr and distinct from the ADR (SC-17)
```

Invariants:
- Additive-optional: a `decision` with no `kind` reads as `adr` (§9.1) — no
  backfill required, existing instances unaffected.
- Each emitted decision in a multi-decision run gets a distinct `@id` (the
  collision fix) — no two decisions share an id.
- `MalformedDecisionDoc` ⇒ rejected at write, no partial persistence (existing
  behaviour preserved).

## Definition of Done

### Red — Failing tests written
- [ ] `tests/methodology/test_bdr_distinct_from_adr.py::test_emit_bdr_carries_kind_bdr` — emit a BDR ⇒ `kind: bdr`, distinct from an emitted ADR (SC-17).
- [ ] `tests/methodology/test_bdr_distinct_from_adr.py::test_absent_kind_reads_as_adr` — an existing decision with no `kind` reads `adr` (migration §9.1).
- [ ] `test_decision_emission.py::test_multi_decision_emit_no_id_collision` — emitting ≥2 decisions in one run ⇒ distinct `@id`s (the collision fix).

### Green — Implementation makes tests pass
- [ ] `decision.schema.json` carries `kind` (enum, default `adr`).
- [ ] `_decision_emission.py` accepts `--kind`, infers from source, mints distinct `@id`s.
- [ ] `sulis-emit-decision` surfaces `--kind`/`--from-bdr`.
- [ ] `_drive_decisions.py` + `_assert_bdr_adr.py` exist and pass.

### Blue — Refactor complete
- [ ] The `@id` minting logic is a single helper (no per-call-site id generation that could re-collide).
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** WP-001 (the fixture-change harness the decision-emit driver reuses for setup)
- **blocks:** none (terminal P3 WP)
- **Parallelisable with:** WP-011 (template side — different file scope)

## Estimated Token Cost

- **Input:** ~7k (this WP + the schema + the emitter + the collision context)
- **Output:** ~5k (schema + emitter edits + two scripts + tests)
- **Total:** ~12k

## Notes

- ADR-006: a `kind` on the existing entity, not a new entity type. The vendored
  compiled schema is the one to edit (`brain/compiled/...`).
- The `@id` collision fix is bundled here per the design's explicit instruction
  ("AND fix the multi-decision @id collision the design flagged, same WP") — the
  two changes share the emission path, so splitting would create a merge seam on
  the same file.
