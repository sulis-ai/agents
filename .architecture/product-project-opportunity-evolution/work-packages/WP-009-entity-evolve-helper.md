---
id: WP-009
title: Build _entity_evolve helper — close/open-window + was_generated_by + _LIVING_ENTITY_TYPES guard
status: pending
kind: backend
primitive: create
group: GENERATE
change_id: CH-01KT61
sequence_id: WP-009
dependsOn: [WP-008]
blocks: [WP-010, WP-011, WP-012, WP-013]
estimated_token_cost:
  input: 4k
  output: 5k
tdd_section: Form #5; Armor §Window invariants, §Append-only guard, §PROV write discipline; Proof §Evolve characterisation test, §Append-only guard test
adrs: [ADR-002, ADR-003]
verification:
  adapter: backend
  artifact: tests/unit/test_entity_evolve.py::test_close_open_window
---

## Context

The shared evolve primitive (ADR-003), the heart of build-order piece 3. A new
module `_entity_evolve.py` sits **above** the `EntityRepository` port (so it works
unchanged against either the repo-local file adapter or the central Tenant home —
ADR-005). `evolve_entity(...)`:

1. reads the current open window for `(type, id)` via the port;
2. closes it (sets `valid_to`) and opens a new window (`valid_from` ==
   prior `valid_to`, `+ confidence + sys_status + was_generated_by`);
3. persists BOTH via the file adapter as a single-file history-envelope rewrite
   (ADR-003 — one atomic envelope write, no instant with two open windows);
4. a byte-identical re-emit is a **no-op** (opens no window — idempotent);
5. refuses any type not on the `_LIVING_ENTITY_TYPES` allowlist (Product /
   Opportunity / Project) — Decision / LifecycleRun stay append-only.

Per ADR-002, `_entity_evolve` is the **single writer** of `was_generated_by`.

**This is EXPAND-Create, not a Wrap** (TDD §Ports & Adapters vs Wrappers): a new
helper above the port the domain owns — not a band-aid over internal code.

## Contract

### Files created

```
plugins/sulis/scripts/_entity_evolve.py
```

### Signatures

```python
_LIVING_ENTITY_TYPES: frozenset[str] = frozenset({"product", "opportunity", "project"})

def evolve_entity(
    *,
    repo: EntityRepository,        # the port — file adapter, repo-local OR central home
    entity_type: str,
    entity_id: str,
    new_fields: dict,              # the changed attributes for the new window
    was_generated_by: str,         # the dna:lifecyclerun:<ulid> that produced this version
    at: str | None = None,
) -> dict | None:
    """Close the prior window, open a new one with was_generated_by; persist both
    atomically. No-op (returns None) when new window is byte-identical to current.
    Raises if entity_type not in _LIVING_ENTITY_TYPES."""
```

Reuses the existing `EntityRepository` port (`save`/`find_by_id`/`validate`) and
the file adapter's `_atomic_write` discipline — no new persistence code.

# canonical-source: TDD.md §Form #5 — _entity_evolve helper

## Definition of Done

### Red — Failing tests written (characterisation of the evolve contract)

- [ ] `tests/unit/test_entity_evolve.py::test_first_emission_opens_one_window`
- [ ] `tests/unit/test_entity_evolve.py::test_close_open_window` — second emission closes prior (`valid_to` set) + opens new with `was_generated_by`; windows abut exactly (prior `valid_to` == new `valid_from`)
- [ ] `tests/unit/test_entity_evolve.py::test_noop_idempotent` — byte-identical re-emit opens no new window
- [ ] `tests/unit/test_entity_evolve.py::test_refuses_event_entity` — `entity_type="decision"` and `="lifecyclerun"` both raise
- [ ] `tests/unit/test_entity_evolve.py::test_writes_was_generated_by` — new window carries a valid `dna:lifecyclerun:<ulid>` ref
- [ ] `tests/unit/test_entity_evolve.py::test_no_two_open_windows` — at no instant does one entity have two `valid_to IS NULL` windows
- [ ] `tests/unit/test_entity_evolve.py::test_runs_against_real_temp_adapter` — exercised against a real temp-dir file adapter (no mock, MEA-09)

### Green — Implementation makes tests pass

- [ ] `_entity_evolve.py` authored per Contract — close/open-window, no-op detection, allowlist guard, single `was_generated_by` writer
- [ ] Window pair materialised via the file adapter's existing atomic-write envelope

### Blue — Refactor complete

- [ ] Sits above the port — zero adapter-specific branches (works against any `EntityRepository`)
- [ ] `_LIVING_ENTITY_TYPES` is the single guard; no per-emitter type checks elsewhere
- [ ] Reuses `_atomic_write` / port `save` — no duplicate persistence logic

## Sequence

- **dependsOn:** WP-008 (it writes `was_generated_by`, so the field must exist in the grammar)
- **blocks:** WP-010 (as-of read pairs with the windows this writes), WP-011 (apply-evolve characterisation test exercises this), WP-012 (the emitters call `evolve_entity` directly), WP-013 (central home stores the windows this produces)

## Estimated Token Cost

- **Input:** ~4k (port + file adapter + ADR-003)
- **Output:** ~5k (helper + characterisation tests)
- **Total:** ~9k

## Notes

- Window invariants + append-only guard + single-PROV-writer (Armor) are all
  enforced *here* — this is the one place those guarantees live.
- ADR-003 OAQ-1 (SQLite row-based window materialisation) is deferred with the
  SQLite swap (ADR-005); this WP is file-adapter-envelope only.
