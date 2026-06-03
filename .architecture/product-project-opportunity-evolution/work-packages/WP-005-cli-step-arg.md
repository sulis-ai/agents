---
id: WP-005
title: Migrate sulis-emit-lifecyclerun CLI to --step with --step-name as a deprecated alias
status: pending
kind: backend
primitive: substitute-strangle
group: SUBSTITUTE
change_id: CH-01KT61
sequence_id: WP-005
dependsOn: [WP-002]
blocks: []
removal_plan:
  deprecated_surface: "the `--step-name` CLI flag (alias)"
  target: "removed in the next minor after downstream consumers migrate; tracked as a follow-on, kept this change for one-release back-compat"
estimated_token_cost:
  input: 2k
  output: 2k
tdd_section: Form #3; ADR-004 §Lockstep ordering step 5
adrs: [ADR-004]
verification:
  adapter: backend
  artifact: tests/unit/test_emit_lifecyclerun_cli_v2.py::test_step_flag_resolves
---

## Context

The `sulis-emit-lifecyclerun` CLI today exposes `--step-name`. Under v2 it
exposes `--step` (which resolves to a canonical Step ref via WP-002's
`_resolve_step`), and keeps `--step-name` only as a **deprecated alias** that
resolves the legacy string to a Step ref (unknown → `unclassified-lifecycle-step`)
and, where trace grouping is needed, carries the original string in the canonical
`run_id` field — **not** a `step_label` (which does not exist in canonical
v2.1.0). Kept for one release of consumer back-compat, then removed per
`removal_plan`.

# canonical-source: TDD.md §Canonical Identifiers — name→Step-ULID map

## Contract

### Files modified

```
plugins/sulis/scripts/sulis-emit-lifecyclerun
```

### CLI surface

| Flag | Behaviour |
|---|---|
| `--step <name-or-ref>` | resolves via `_resolve_step` → canonical Step ULID; the primary path |
| `--step-name <string>` | **deprecated alias**: emits a deprecation notice to stderr, resolves the string via `_resolve_step` (→ `unclassified-lifecycle-step` if unknown); the original string is carried in `run_id` when trace grouping is needed (NOT a `step_label`) |

Mutually exclusive: passing both is an error. Calls WP-002's `compose_lifecyclerun`.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_emit_lifecyclerun_cli_v2.py::test_step_flag_resolves` — `--step change-started` → canonical ULID in output
- [ ] `tests/unit/test_emit_lifecyclerun_cli_v2.py::test_step_name_alias_warns_and_resolves` — `--step-name foo` emits deprecation notice, resolves to unclassified; output carries NO `step_label` field
- [ ] `tests/unit/test_emit_lifecyclerun_cli_v2.py::test_both_flags_is_error`
- [ ] `tests/unit/test_emit_lifecyclerun_cli_v2.py::test_output_validates_v2`

### Green — Implementation makes tests pass

- [ ] `--step` added; `--step-name` kept as deprecated alias per Contract
- [ ] Deprecation notice is plain-English to stderr (FE-01..FE-10)

### Blue — Refactor complete

- [ ] CLI shares WP-002's `_resolve_step` — no second copy of the map
- [ ] `--help` text documents `--step` as primary, `--step-name` as deprecated

## Sequence

- **dependsOn:** WP-002 (the atomic re-vendor+emitter-core WP — `compose_lifecyclerun` v2 signature + `_resolve_step` + map all land there)
- **blocks:** — (leaf of the emitter cluster)

## Estimated Token Cost

- **Input:** ~2k
- **Output:** ~2k
- **Total:** ~4k

## Notes

- The `removal_plan` records the deprecated `--step-name` deletion (No-Band-Aid:
  the alias is transitional within the strangle, with a recorded target).
