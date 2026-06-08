---
id: WP-002
title: Surgically re-vendor canonical LifecycleRun v2.1.0 + migrate the emitter core (compose + helper) in ONE atomic lockstep WP
status: pending
kind: contract
primitive: substitute-strangle
group: SUBSTITUTE
change_id: CH-01KT61
sequence_id: WP-002
dependsOn: [WP-001]
blocks: [WP-005, WP-006, WP-007, WP-008, WP-013, WP-016]
composite_of: [revendor-schema, migrate-_lifecyclerun_emission, migrate-_brain_emit_helper]
removal_plan:
  deprecated_surface: "the v1.0.0 `step_name` property + any transitional name→Step string-resolution path"
  target: "the v1 `step_name` field is removed in this re-vendor (clean break to canonical v2.1.0); the deprecated `--step-name` CLI alias is introduced in WP-005 and removed in the next minor after downstream consumers migrate (tracked there)"
estimated_token_cost:
  input: 5k
  output: 5k
tdd_section: Form #3; Canonical Identifiers — Schema versions + name→Step-ULID map; ADR-001, ADR-004
adrs: [ADR-001, ADR-004]
verification:
  adapter: backend
  artifact: tests/unit/test_lifecyclerun_schema_v2.py::test_revendored_schema_matches_canonical
---

## Context

The PROV spine (build-order piece 1). **LifecycleRun v2.1.0 is ALREADY MINTED
upstream** (DR-009 did `step_name`→`step` as v2.0.0; DR-013 added
`run_id`/`deterministic`/`inputs_ref`/`outputs_ref` as v2.1.0). The action is a
**surgical re-vendor** of the canonical compiled schema, **lockstep/atomic with
the emitter-core migration** — one WP, never a loose schema commit (ADR-004 +
the `plugins/sulis/brain/compiled/README.md` lockstep mandate).

This WP **absorbs three previously-separate moves** (old WP-002 schema-author,
old WP-003 `_lifecyclerun_emission`, old WP-004 `_brain_emit_helper`) into one
atomic slice, because any commit ordering between them leaves a window where the
vendored schema and the emitter disagree and **every emit reject-on-invalids**.
The CLI (WP-005) and the instance migration (WP-006) follow as separate WPs once
this consistent core lands.

**Correction baked in:** there is **no `step_label` field and no `used` field on
the LifecycleRun** — both were invented by an earlier draft, both are absent from
canonical v2.1.0, and DR-013 already rejected payload-on-the-run-record. The
re-vendored schema is byte-faithful to canonical v2.1.0; per-run specificity is
carried by the existing canonical `run_id` field.

# canonical-source: TDD.md §Canonical Identifiers — Schema versions + name→Step-ULID map

## Contract

### Files modified / created

```
plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json   # RE-VENDOR: copy canonical compiled v2.1.0 over the vendored v1.0.0
plugins/sulis/scripts/_lifecyclerun_emission.py                            # compose_lifecyclerun: `step` ref (NOT step_name); ID seed from step+timestamp
plugins/sulis/scripts/_brain_emit_helper.py                               # 3 helpers resolve a Step ULID for `step` via the name→Step-ULID map
```

### Step 1 — Re-vendor the canonical compiled v2.1.0 schema

Copy `.specifications/business-dna/compiled/schemas/product-development/lifecyclerun.schema.json`
(the canonical compiled v2.1.0) over the vendored copy. The canonical compiled
output already carries the vendored envelope fields (`sys_status`,
`valid_from`/`valid_to`/`confidence`), so this is a clean drop-in (diff confirms
only `step_name`→`step` + the four DR-013 optional fields change). **Surgical
single-file re-vendor** respecting the README's intentional mixed-version vendor —
NOT the wholesale `sync-from-canonical.sh` (which targets the separate sulis-brain
plugin in the dna repo).

| Field | vendored v1.0.0 | re-vendored v2.1.0 (canonical) |
|---|---|---|
| `step_name` | required string | **removed** |
| `step` | — | **required** ref `^dna:(step):[0-9A-HJKMNP-TV-Z]{26}$` |
| `run_id` | — | optional string (DR-013) |
| `deterministic` | — | optional boolean (DR-013) |
| `inputs_ref` | — | optional string `x-sensitive` (DR-013) |
| `outputs_ref` | — | optional string `x-sensitive` (DR-013) |
| `$id` | `…/lifecyclerun/1.0.0` | `…/lifecyclerun/2.1.0` |

**No `step_label`. No `used`.**

### Step 2 — `compose_lifecyclerun` (`_lifecyclerun_emission.py`)

```python
def compose_lifecyclerun(
    *,
    step: str,                       # was step_name; now a resolved dna:step:<ulid> ref
    outcome: str,
    at: str | None = None,
    by_actor: str = "",
    run_id: str | None = None,       # per-run trace grouping (canonical v2.1.0) — carries the old per-run specificity
) -> dict:
    ...
    run = {
        "id": "dna:lifecyclerun:" + _ulid(f"lcrun:{step}:{timestamp}:{by_actor}"),
        "step": step,                # required ref; reject if not ^dna:step:<26>$
        "at": timestamp,
        "outcome": outcome,
        "sys_status": "active",
        # run_id emitted only when provided (unevaluatedProperties:false clean)
    }
```

### Step 3 — `_brain_emit_helper.py` (the 3 LifecycleRun helpers)

```python
_NAME_TO_STEP_ULID = {
    "change-started": "dna:step:01KT61X5ST01CHANGESTART00A",
    "change-shipped": "dna:step:01KT61X5ST02CHANGESH1PP00A",
}
_UNCLASSIFIED_STEP = "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"

def _resolve_step(name: str) -> str:
    """Return a canonical Step ULID for a known name; else the unclassified Step.
    The per-run specificity that used to be smuggled into the step_name string
    is carried by run_id, NOT a step_label (which does not exist)."""
```

- `emit_change_started_event` → `step=_resolve_step("change-started")`
- `emit_change_shipped_event`  → `step=_resolve_step("change-shipped")`
- `emit_lifecycle_step_event(step_name=...)` → `step=_resolve_step(step_name)`;
  the original free string, when needed for trace grouping, goes to `run_id`.

All ULIDs are the WP-001 authored values (single source of truth; no inline mint).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_lifecyclerun_schema_v2.py::test_revendored_schema_matches_canonical` — the vendored file is byte-equal (modulo whitespace) to the canonical compiled v2.1.0 schema
- [ ] `::test_schema_id_is_2_1_0` — `$id` ends `/lifecyclerun/2.1.0`
- [ ] `::test_v2_requires_step_ref` — a doc with `step` validates; one with `step_name` and no `step` is rejected
- [ ] `::test_no_step_label_field` — the schema has NO `step_label` property
- [ ] `::test_no_used_field` — the schema has NO `used` property
- [ ] `::test_dr013_optional_fields_present` — `run_id`/`deterministic`/`inputs_ref`/`outputs_ref` all present, all optional
- [ ] `tests/unit/test_lifecyclerun_emission_v2.py::test_compose_emits_step_ref` — output has `step`, no `step_name`, no `step_label`
- [ ] `::test_compose_rejects_non_step_ref`
- [ ] `::test_run_id_emitted_when_provided`
- [ ] `::test_output_validates_against_revendored_v2`
- [ ] `tests/unit/test_brain_emit_helper_step_resolution.py::test_change_started_resolves_to_canonical_step`
- [ ] `::test_change_shipped_resolves_to_canonical_step`
- [ ] `::test_unknown_name_resolves_to_unclassified`
- [ ] `::test_map_ulids_match_canonical` — the 3 ULIDs byte-exact vs TDD §Canonical Identifiers
- [ ] `::test_emitted_run_validates_v2`
- [ ] `tests/integration/test_emit_lifecyclerun_lockstep.py::test_schema_and_emitter_agree` — a helper-emitted run validates against the re-vendored schema in one pass (proves no reject-on-invalid window)

### Green — Implementation makes tests pass

- [ ] Canonical compiled v2.1.0 re-vendored over the v1.0.0 copy (surgical, single file)
- [ ] `compose_lifecyclerun` rewritten: `step` ref, ID seed from `step`, `run_id` optional; no `step_name`, no `step_label`, no `used`
- [ ] 3 helpers resolve `step` via `_resolve_step`; graceful-degradation discipline unchanged (still `dict | None`)

### Blue — Refactor complete

- [ ] No `step_name`, `step_label`, or `used` anywhere in the emitter core or schema
- [ ] One `_resolve_step` (EP-03) — no duplicate maps across the helpers
- [ ] Re-vendored schema is byte-faithful to canonical (drift detector parity, WP-007, reads this)
- [ ] Operator-facing log lines stay plain-English (FE-01..FE-10)

## Sequence

- **dependsOn:** WP-001 (the Step ULIDs the `step` ref + resolution map point at)
- **blocks:** WP-005 (CLI shares `_resolve_step` + targets the re-vendored schema), WP-006 (migration re-validates against the re-vendored schema + reuses `_resolve_step`), WP-007 (drift parity reads the re-vendored schema), WP-008 (the prov edge points at the re-vendored LifecycleRun ref shape), WP-013 (the `_brain_emit_helper.py` base_dir edit follows WP-002's Step-resolution edit), WP-016 (the v2.2.0 `for_project` increment re-vendors over this WP's v2.1.0 file + extends its compose/emit helpers — ADR-007)
- **Lockstep (ADR-004 + README mandate):** the re-vendor (step 1) and the emitter-core migration (steps 2–3) are atomic in this one WP — no intermediate commit where schema and emitter disagree.

## Estimated Token Cost

- **Input:** ~5k (canonical compiled schema + 2 emitter modules + ADR-004)
- **Output:** ~5k (re-vendor + 2 module rewrites + tests)
- **Total:** ~10k

## Notes

- `substitute-strangle`: a breaking required-field swap (`step_name`→`step`) with
  a recorded `removal_plan`. The re-vendor is the schema side; the composer +
  helper are the call-site side; they are ONE removal, atomic (ADR-004 "no commit
  leaves schema and emitters disagreeing"; README "migrated in lockstep").
- `composite_of` records the three absorbed moves (old WP-002/003/004) so the
  executor sees the slice's internal ordering without four separate files.
- The wholesale `sync-from-canonical.sh` is NOT used here — it targets the
  separate sulis-brain plugin and would overwrite the marketplace's intentional
  mixed-version vendor (ADR-004).
