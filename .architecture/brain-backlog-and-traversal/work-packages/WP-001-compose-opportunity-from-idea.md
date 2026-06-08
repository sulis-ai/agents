---
id: WP-001
title: Add compose_opportunity_from_idea pure transform
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-001
dependsOn: []
blocks: [WP-004]
estimated_token_cost:
  input: 6k
  output: 2k
tdd_section: Form — Component inventory (compose_opportunity_from_idea)
adrs: [ADR-005, ADR-003]
primitive: extend
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_opportunity_from_idea.py::test_compose_is_pure_and_deterministic
---

## Context

This WP advances the **Capture path** machinery (TDD Form: component
inventory row `compose_opportunity_from_idea`). It adds a single-idea
compose function to the existing `_opportunity_emission.py` module, a
sibling to the already-present `compose_opportunity_from_srd`. Per ADR-005,
capture has no source document — it has a why-string typed in conversation —
so the from-SRD parser would have nothing to parse. The boring move is to
feed the *same* persistence and ID-derivation discipline a different front
end, not to fabricate a throwaway SRD. This is EXPAND-Extend: a new sibling
function at an existing extension point in a domain-owned module — not a
wrapper.

Reuse mandate (CP-01..05): the Crockford-base32 `_deterministic_ulid_from`
helper already in `_opportunity_emission.py` is reused unchanged; the dict
shape produced must be byte-identical to what `compose_opportunity_from_srd`
produces for the same fields (so it validates against the same vendored
`product-development/opportunity.schema.json`).

## Contract

```python
# plugins/sulis/scripts/_opportunity_emission.py  (this WP adds, alongside compose_opportunity_from_srd)

def compose_opportunity_from_idea(
    *,
    job_statement: str,
    for_product: str,          # dna:product:<ulid> — the rooting product ref
    seed: str,                 # stable seed → deterministic ULID (NFR-04)
    state: str = "hypothesis", # quick path default; analyst sets validated/defined on full path
    evidence: str | None = None,
    impact: str | None = None,
) -> dict:
    """Pure transform: idea fields → Opportunity entity dict. No I/O.

    ID = dna:opportunity:<_deterministic_ulid_from(f"opportunity-from-idea:{seed}")>.
    Optional fields (evidence/impact) are omitted from the dict when None,
    keeping unevaluatedProperties:false clean (ADR-005 consequence).
    """
```

Contract invariants:
- **Pure** — no filesystem, no network, no `repo.save`. Same inputs → identical dict, including the id.
- **Deterministic id** — `dna:opportunity:` + `_deterministic_ulid_from("opportunity-from-idea:" + seed)`. Distinct namespace prefix from the from-SRD path so the two never collide on the same string.
- **Schema-clean** — output validates against the vendored opportunity schema with `unevaluatedProperties:false`; `None`-valued optional fields are absent keys, not `null`.
- **`job_statement`** is flattened to a single line (mirror `_opportunity_emission`'s existing flatten discipline).
- The from-SRD path (`compose_opportunity_from_srd`) is **untouched**.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_opportunity_from_idea.py::test_compose_is_pure_and_deterministic` — two calls with identical kwargs return identical dicts incl. id; no file touched.
- [ ] `tests/unit/test_opportunity_from_idea.py::test_id_namespace_distinct_from_srd` — same string fed as `seed` and as an SRD path yields different ULIDs (namespace prefix differs).
- [ ] `tests/unit/test_opportunity_from_idea.py::test_output_validates_against_vendored_schema` — composed dict passes `jsonschema` against `product-development/opportunity.schema.json` (real vendored schema, no mock).
- [ ] `tests/unit/test_opportunity_from_idea.py::test_optional_fields_omitted_when_none` — `evidence=None`/`impact=None` ⇒ keys absent (unevaluatedProperties clean).
- [ ] `tests/unit/test_opportunity_from_idea.py::test_state_defaults_hypothesis` — default state is `hypothesis`; explicit `validated` honoured.

### Green — Implementation makes tests pass
- [ ] All Red tests pass.
- [ ] `_deterministic_ulid_from` reused unchanged (no second copy of the helper).
- [ ] Boring code: explicit kwargs, no `**kwargs`, no reflection, no module-level mutable state.
- [ ] `compose_opportunity_from_srd` tests still green (regression).

### Blue — Refactor complete
- [ ] If `compose_opportunity_from_srd` and `compose_opportunity_from_idea` share dict-assembly logic, extract a private `_opportunity_dict(...)` builder both call — single home for the field/default shape.
- [ ] No new behaviour introduced in Blue.
- [ ] All tests green after refactor.

## Sequence
- **dependsOn:** — (pure addition to an existing module)
- **blocks:** WP-004 (the orchestrator calls this compose fn)
- **Parallelisable with:** WP-002, WP-007 (different functions / modules)

## Estimated Token Cost
- **Input:** ~6k (this WP + the `_opportunity_emission.py` head)
- **Output:** ~2k (one function + one test file)
- **Total:** ~8k

## Notes
- Per ADR-005, optional `evidence`/`impact` stay unset on the quick path; the analyst (ADR-004) populates them on the full path. Keep them optional.

## Acceptance Evidence

- Branch: feat/wp-001-compose-opportunity-from-idea (deleted post-merge)
- Completed: `2026-06-03T08:12:40Z` (Step 12 by calling session)
