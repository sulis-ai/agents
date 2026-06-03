---
id: WP-002
title: Add compose_requirement_from_idea pure transform
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-002
dependsOn: []
blocks: [WP-004]
estimated_token_cost:
  input: 6k
  output: 2k
tdd_section: Form — Component inventory (compose_requirement_from_idea)
adrs: [ADR-005, ADR-003]
primitive: extend
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_requirement_from_idea.py::test_source_is_real_opportunity_ref
---

## Context

Advances the **Capture path** machinery (TDD Form: component inventory row
`compose_requirement_from_idea`). Adds a single-idea compose function to
`_requirement_emission.py`, sibling to `compose_requirements_from_srd`. Per
ADR-005, this closes the synthetic-placeholder loop the from-SRD requirement
path documents: that path emits a *synthetic* Opportunity ref because
Opportunity emission "didn't exist yet." It exists now (WP-001), so the
single-idea Requirement's `source` is a **real** Opportunity id the
orchestrator just emitted — never synthetic. EXPAND-Extend on a domain-owned
module; not a wrapper.

Reuse mandate (CP-01..05): the `_deterministic_ulid_from` helper and the
`_flatten` discipline already in `_requirement_emission.py` are reused
unchanged. The output dict shape is identical to the from-SRD path's
per-requirement dict (validates against the same vendored
`product-development/requirement.schema.json`).

## Contract

```python
# plugins/sulis/scripts/_requirement_emission.py  (this WP adds, alongside compose_requirements_from_srd)

def compose_requirement_from_idea(
    *,
    statement: str,              # the "what" — the requirement text
    source: str,                 # dna:opportunity:<ulid> — REAL, never synthetic (ADR-005)
    seed: str,                   # stable seed → deterministic ULID (NFR-04)
    priority: str = "must",
    acceptance_criteria: list[str] | None = None,
) -> dict:
    """Pure transform: idea fields → single Requirement entity dict. No I/O.

    ID = dna:requirement:<_deterministic_ulid_from(f"requirement-from-idea:{seed}")>.
    state defaults to "draft" (captured-and-set-aside lives as draft, per SRD grounding).
    """
```

Contract invariants:
- **Pure** — no I/O. Same inputs → identical dict incl. id.
- **`source` is passed through verbatim** — the compose fn does not mint a synthetic Opportunity ref; the caller (WP-004) supplies a real one. If `source` does not match `^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$`, raise `ValueError` (fail loud, never emit a dangling ref).
- **Deterministic id** — `dna:requirement:` + `_deterministic_ulid_from("requirement-from-idea:" + seed)`; distinct namespace from the from-SRD path.
- **Defaults** — `state="draft"`, `priority="must"`, `verification_method="test"` matching the from-SRD defaults; `acceptance_criteria=None` ⇒ a single honest placeholder criterion (mirror existing convention) or omitted per schema, whichever keeps `unevaluatedProperties:false` clean.
- The from-SRD path (`compose_requirements_from_srd`) is **untouched**.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_requirement_from_idea.py::test_compose_is_pure_and_deterministic` — two identical calls → identical dict incl. id; no file touched.
- [ ] `tests/unit/test_requirement_from_idea.py::test_source_is_real_opportunity_ref` — given a real opportunity id, the dict's `source` equals it verbatim.
- [ ] `tests/unit/test_requirement_from_idea.py::test_rejects_malformed_source` — a non-`dna:opportunity:` source raises `ValueError` (no dangling-ref emission).
- [ ] `tests/unit/test_requirement_from_idea.py::test_output_validates_against_vendored_schema` — dict passes `jsonschema` against the real vendored requirement schema.
- [ ] `tests/unit/test_requirement_from_idea.py::test_state_defaults_draft` — default state is `draft`.

### Green — Implementation makes tests pass
- [ ] All Red tests pass.
- [ ] `_deterministic_ulid_from` + `_flatten` reused unchanged.
- [ ] Boring code: explicit kwargs, no metaprogramming, no module-level state.
- [ ] `compose_requirements_from_srd` tests still green (regression).

### Blue — Refactor complete
- [ ] If from-SRD and from-idea share single-requirement dict-assembly, extract a private `_requirement_dict(...)` builder both call.
- [ ] No new behaviour introduced in Blue.
- [ ] All tests green after refactor.

## Sequence
- **dependsOn:** — (pure addition)
- **blocks:** WP-004 (orchestrator calls this compose fn)
- **Parallelisable with:** WP-001, WP-007

## Estimated Token Cost
- **Input:** ~6k
- **Output:** ~2k
- **Total:** ~8k

## Notes
- The `source` validation is the load-bearing line: it is the code-level enforcement of "no orphan requirements" — the requirement physically cannot be composed without a real opportunity ref.

## Acceptance Evidence

- Branch: feat/wp-002-compose-requirement-from-idea (deleted post-merge)
- Completed: `2026-06-03T08:12:40Z` (Step 12 by calling session)
