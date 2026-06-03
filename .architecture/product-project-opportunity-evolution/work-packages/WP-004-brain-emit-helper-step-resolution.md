---
id: WP-004
title: Resolve Step refs in the 3 _brain_emit_helper LifecycleRun helpers via the name→Step-ULID map
status: pending
kind: backend
primitive: substitute-strangle
group: SUBSTITUTE
change_id: CH-01KT61
sequence_id: WP-004
dependsOn: [WP-001, WP-003]
blocks: [WP-005, WP-013]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form #3; Canonical Identifiers — name→Step-ULID map; ADR-004 §Step-ref resolution
adrs: [ADR-001, ADR-004]
verification:
  adapter: backend
  artifact: tests/unit/test_brain_emit_helper_step_resolution.py::test_change_started_resolves_to_canonical_step
---

## Context

The three LifecycleRun helpers in `plugins/sulis/scripts/_brain_emit_helper.py`
today pass `step_name=f"change-started:{primitive}:{slug}"` strings. Under v2
they resolve a **Step ref** and move the per-run `{primitive}:{slug}` detail to
`step_label` (ADR-001/004):

- `emit_change_started_event` → `step = <change-started ULID>`
- `emit_change_shipped_event` → `step = <change-shipped ULID>`
- `emit_lifecycle_step_event(step_name=...)` (general) → resolves the free string
  via a **name→Step-ULID map** (known prefixes `change-started`/`change-shipped`);
  unknown names → `unclassified-lifecycle-step` ULID, original string preserved in
  `step_label`.

The map is the single source of truth for the events-known-name split (TDD
§Canonical Identifiers); it keys on the canonical Step names authored in WP-001.

# canonical-source: TDD.md §Canonical Identifiers — name→Step-ULID map

## Contract

### Files modified

```
plugins/sulis/scripts/_brain_emit_helper.py
```

### The resolution map (single source of truth)

```python
_NAME_TO_STEP_ULID = {
    "change-started": "dna:step:01KT61X5ST01CHANGESTART00A",
    "change-shipped": "dna:step:01KT61X5ST02CHANGESH1PP00A",
}
_UNCLASSIFIED_STEP = "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"

def _resolve_step(step_name: str) -> tuple[str, str]:
    """Return (step_ref, step_label). Known prefix → its ULID; else unclassified.
    step_label preserves the original free string in all cases."""
```

All three ULIDs sourced from `TDD.md §Canonical Identifiers` (= WP-001's authored
values). Helpers call the WP-003 `compose_lifecyclerun(step=..., step_label=...)`.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_brain_emit_helper_step_resolution.py::test_change_started_resolves_to_canonical_step`
- [ ] `tests/unit/test_brain_emit_helper_step_resolution.py::test_change_shipped_resolves_to_canonical_step`
- [ ] `tests/unit/test_brain_emit_helper_step_resolution.py::test_unknown_name_resolves_to_unclassified`
- [ ] `tests/unit/test_brain_emit_helper_step_resolution.py::test_step_label_preserves_original_string` — `change-started:feat:my-slug` survives in `step_label`
- [ ] `tests/unit/test_brain_emit_helper_step_resolution.py::test_map_ulids_match_canonical` — the 3 ULIDs byte-exact vs TDD §Canonical Identifiers
- [ ] `tests/unit/test_brain_emit_helper_step_resolution.py::test_emitted_run_validates_v2`

### Green — Implementation makes tests pass

- [ ] `_NAME_TO_STEP_ULID` + `_UNCLASSIFIED_STEP` + `_resolve_step` added
- [ ] 3 helpers updated to resolve `step` + pass `step_label`; graceful-degradation discipline unchanged (still return `dict | None`)

### Blue — Refactor complete

- [ ] One resolution function, not three copies of the mapping logic (EP-03)
- [ ] Map ULIDs are the literal WP-001 values (no re-derivation)
- [ ] Operator-facing log lines stay plain-English (FE-01..FE-10) — no internal IDs in stderr

## Sequence

- **dependsOn:** WP-001 (Step ULIDs), WP-003 (`compose_lifecyclerun` v2 signature)
- **blocks:** WP-005 (CLI shares the same `_resolve_step` for `--step-name` deprecated-alias mapping); WP-013 (peer-collision serialisation — WP-013's `_brain_emit_helper.py` base_dir edit lands after this WP's Step-resolution edit to the same file)

## Estimated Token Cost

- **Input:** ~3k (existing helper + ADR-004 + canonical map)
- **Output:** ~3k
- **Total:** ~6k

## Notes

- `substitute-strangle` (call-site side of the breaking swap). Graceful
  degradation is inherited, not re-implemented — the host operation never fails
  on emission failure (reused discipline).
