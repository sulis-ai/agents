---
id: WP-013
title: Point living-entity emit base_dir at the central ~/.sulis/instances/{tenant_id}/ home and prove cross-repo Tenant read
status: pending
kind: backend
primitive: reuse
group: REUSE
change_id: CH-01KT61
sequence_id: WP-013
dependsOn: [WP-002, WP-009, WP-010]
blocks: [WP-014, WP-016]
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: Form #7, #8; Armor §Central-home write durability; Proof §Central-home read/write test, §Cross-repo Tenant read test
adrs: [ADR-005]
verification:
  adapter: backend
  artifact: tests/unit/test_central_tenant_home.py::test_round_trip_central_home
---

## Context

Build-order piece 5 (ADR-005 — **reuse, not build**). The cross-repo Platform
home is the EXISTING `LocalFileEntityAdapter` pointed at the EXISTING
`~/.sulis/instances/{tenant_id}/` convention. This WP wires the living-entity emit
`base_dir` at that central Tenant home and proves a cross-repo Tenant read — every
open-window Product/Opportunity for one Tenant, read from the central home, across
repos. No new module, no new adapter (SQLite deferred to a later change behind the
same port).

The Tenant ULID is the **existing deterministic derivation** in
`_tenant_emission.py` — `_deterministic_ulid_from("tenant-name:{name}")` →
`dna:tenant:<26-Crockford>` — reused as-is. The path convention
`~/.sulis/instances/{tenant_id}/` is documented in that module's docstring
(lines 5–7). This change is the "follow-up slice" that docstring promised.

# canonical-source: plugins/sulis/scripts/_tenant_emission.py — Tenant-ULID derivation + ~/.sulis/instances/{tenant_id}/ convention (module docstring lines 5-7, _deterministic_ulid_from lines 41-49, seed "tenant-name:" line 83)

## Contract

### Files modified

```
plugins/sulis/scripts/<living-entity emit wiring — the base_dir resolution point>
plugins/sulis/scripts/_brain_query.py    # find_current_for_tenant over the central home
```

### Surface

```python
def central_tenant_home(tenant_id: str) -> Path:
    """~/.sulis/instances/{tenant_id}/ — the cross-repo Platform home.
    tenant_id is the existing deterministic dna:tenant:<ulid> (reused, not minted)."""

def find_current_for_tenant(
    *,
    tenant_id: str,
    entity_type: str,
) -> list[dict]:
    """Every open-window entity of entity_type for tenant_id, read from the
    central home via the existing iter_entities walk."""
```

Reuses: `LocalFileEntityAdapter(base_dir=central_tenant_home(...))`, the existing
`iter_entities` walk, the existing `_atomic_write` durability. No new persistence
or query code beyond pointing `base_dir` and adding the Tenant-scoped read.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_central_tenant_home.py::test_round_trip_central_home` — save a living-entity version to a temp `~/.sulis/instances/{tenant_id}/`-shaped base_dir via the existing adapter; read it back
- [ ] `tests/unit/test_central_tenant_home.py::test_cross_repo_tenant_read` — versions written "from two repos" (two base_dir writes under one Tenant home) are both returned by `find_current_for_tenant`; a single repo-local tree read cannot return both (asserts the central home is the reason it works)
- [ ] `tests/unit/test_central_tenant_home.py::test_atomic_write_durable` — a half-written file is never visible (tmp-then-rename); a committed window survives
- [ ] `tests/unit/test_central_tenant_home.py::test_tenant_ulid_reuses_existing_derivation` — the Tenant ULID equals `_deterministic_ulid_from("tenant-name:<name>")` byte-exact (no new mint)
- [ ] `tests/unit/test_central_tenant_home.py::test_only_open_windows_returned` — closed windows excluded from `find_current_for_tenant`

### Green — Implementation makes tests pass

- [ ] `central_tenant_home(tenant_id)` resolves `~/.sulis/instances/{tenant_id}/`
- [ ] Living-entity emit `base_dir` points there (reusing `LocalFileEntityAdapter`)
- [ ] `find_current_for_tenant` reads the central home via existing `iter_entities`

### Blue — Refactor complete

- [ ] **No new adapter class, no new query adapter** (ADR-005 — reuse proven by the absence of new persistence code)
- [ ] Tenant ULID derivation is imported from `_tenant_emission.py`, not re-implemented
- [ ] The same `iter_entities` serves repo-local and central home (relocation is behaviour-preserving — parity)

## Sequence

- **dependsOn:** WP-009 (the central home stores the *windows* evolve produces; the window contract must exist first — ADR-005 build-order note); WP-002 and WP-010 (peer-collision serialisation — WP-013 edits `_brain_emit_helper.py` after WP-002's Step-resolution edit to that same file, and `_brain_query.py` after WP-010's `read_as_of` edit, so no two WPs modify either shared file in parallel — P6)
- **blocks:** WP-014 (the reconciled Project home is whichever adapter the port has — the central-home wiring must exist); WP-016 (peer-collision serialisation on `_brain_emit_helper.py` — WP-016's change-start `for_project` edit lands after WP-013's `base_dir` edit to the same file, P6)

## Estimated Token Cost

- **Input:** ~4k (`_tenant_emission.py` + `_entity_adapter_local.py` + `_brain_query.py` + ADR-005)
- **Output:** ~4k
- **Total:** ~8k

## Notes

- `reuse` primitive (top of the change-primitive decision priority). The proof
  that this is reuse, not build: the Blue gate asserts **no new persistence code**.
- Central-home write durability (Armor) is the file adapter's existing
  `_atomic_write` — inherited, not re-implemented. SQLite WAL durability is
  deferred with the SQLite swap.
