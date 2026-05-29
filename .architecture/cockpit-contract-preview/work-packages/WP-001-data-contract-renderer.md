---
# Identity (WP-01)
id: WP-001
title: "wpx-render-contract — render a change's data contract into a founder-legible CONTRACT.html (keystone)"
kind: backend
# primitive: EXPAND-Create — net-new wpx subtool; Sulis owns the interface
primitive: Create
group: expand
source: feature
change_id: 01KSSV19SFWBJM01BM2XP6CZZ0
parent_phase: cockpit-contract-preview

# Scope (WP-02..04)
atomic_branch: yes
estimate: large
blast_radius: low
keystone: yes                          # test-first; everything else builds on the artifacts this produces

acceptance_criteria:
  - "`wpx render-contract --worktree <path> [--out <path>]` writes a self-contained CONTRACT.html + a manifest JSON into the worktree, emitting the standard emit_ok JSON on stdout (exit 0)."
  - "ServiceSpec-first precedence holds: a worktree with both a ServiceSpec JSON-LD and an OpenAPI doc renders the ServiceSpec; OpenAPI-only renders the OpenAPI fallback; neither renders a raw-contract + plain note; none of these throws (ADR-005/003)."
  - "Fixture-A rich, MULTI-AREA test passes all of TDD §4.1 assertions 0–14 (area grouping + 'areas covered' overview; operation identifier paired with readable action; readable permission line + 'Who can do this' + actual permission code in the default view; form-fields projection with labels/placeholders/validation/human-enum-labels/show-when; entities + lifecycle chain; constraints as business rules; languages line; workflows as journeys; what-each-action-changes; background flag; walkthrough; example; errors; retirement badge with sunset + replacement; technical detail behind the toggle)."
  - "Fixture-B minimal SINGLE-AREA test passes TDD §4.1 assertions 15–18 (what-it-does + example present; entities/lifecycle/rules/journeys/state-effects/languages/background/retirement sections ABSENT with NO empty heading; plain input renders as basic fields with no rich chrome; single-area renders ungrouped with no area heading and no overview)."
  - "OpenAPI-fallback + degradation tests pass per TDD §4.2 (graceful degradation: richer sections absent, no empty headings; tag-grouping when tags present, single ungrouped block when absent; two-contracts render both in precedence order; no-contract renders raw + note)."

test_plan:
  unit:
    - "plugins/sulis/scripts/tests/unit/test_wpx_render_contract.py::test_fixtureA_multi_area_full_picture  (TDD §4.1 assertions 0–14)"
    - "plugins/sulis/scripts/tests/unit/test_wpx_render_contract.py::test_fixtureB_minimal_single_area_autohide  (TDD §4.1 assertions 15–18)"
    - "plugins/sulis/scripts/tests/unit/test_wpx_render_contract.py::test_openapi_fallback_degrades_gracefully  (TDD §4.2)"
    - "plugins/sulis/scripts/tests/unit/test_wpx_render_contract.py::test_openapi_tag_grouping_and_no_tag_single_block  (TDD §4.2)"
    - "plugins/sulis/scripts/tests/unit/test_wpx_render_contract.py::test_two_contracts_precedence_order  (TDD §4.2)"
    - "plugins/sulis/scripts/tests/unit/test_wpx_render_contract.py::test_no_contract_raw_plus_note  (TDD §4.2)"
  integration:
    - "plugins/sulis/scripts/tests/integration/test_wpx_render_contract_cli.py::test_cli_emits_ok_and_writes_artifacts"
  verification:
    - "branch-ci workflow green on the WP branch"
verification_gates: [unit, integration, smoke]

# Lineage (WP-06 — PROV-O-aligned)
derived_from:
  - finding: "TDD §2.3 (renderer internal seams) + §4.1/§4.2 (keystone + fallback tests); ADR-001/002/003/005/006"
    found_in: .architecture/cockpit-contract-preview/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-05-29
  agent: sulis-engineering-architect
addresses_findings:
  - "feature::cockpit-contract-preview::data-contract-renderer"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
# dependsOn: visual contract (WP-005, default-view layout) signed off; renderer produces what it specifies
dependsOn: [WP-005]

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Pure additive: a new wpx subtool + its tests + fixtures. Remove the
  wpx-render-contract script, its dispatcher registration, and the test dir.
  No data migration, no change to existing steps or the cockpit.
---

# wpx-render-contract — the data-contract renderer (keystone, test-first)

## Why

The data contract is produced at design time but is an inert file in a worktree.
The founder needs to *see* it — before dispatch (a review gate) and again while
testing. This step renders any change's contract into a founder-legible
`CONTRACT.html`, derived **entirely** from the contract's own fields so it cannot
drift from what is built (ADR-002/003/005). This is the keystone: WP-002 (UI
renderer) sits beside it, and WP-003 (cockpit wiring) + WP-004 (recreate) serve
the artifacts it produces.

## What changes (Form — where it lives)

- NEW `plugins/sulis/scripts/wpx-render-contract` — a stdlib-only Python step
  built on `_wpxlib.py` (`add_common_args`, `emit_ok`/`emit_error`), matching the
  `wpx-worktree` / `wpx-pipeline` shape (ADR-001).
- Registered as a subtool of the `wpx` dispatcher (`plugins/sulis/scripts/wpx`).
- NEW `plugins/sulis/scripts/tests/unit/test_wpx_render_contract.py` + fixtures
  + `tests/integration/test_wpx_render_contract_cli.py`.

The step's only inputs are a **worktree path** and (optionally) an output path.
It never hard-wires a change (ADR-003): it **discovers** the contract(s) inside
the worktree by convention-glob + content sniff, in ServiceSpec → OpenAPI → raw
precedence (ADR-005).

## How (internal seams — TDD §2.3)

Two front-ends feed one format-agnostic `ContractModel`:

- `locate_contracts(worktree)` → ordered `[(Path, Format)]`
- `parse_servicespec(path)` → `ContractModel` (PRIMARY)
- `parse_openapi(path)` → `ContractModel` (SECONDARY)
- then the format-agnostic builders: `build_form_fields`, `derive_auth_flags`,
  `enrich_permission`, `derive_retirement`, `derive_languages`,
  `build_walkthrough`, `build_entity_views`, `build_workflow_views`,
  `build_state_effects`, `derive_areas`, `render_technical`, `compose_html`.

**Defensive field-by-field reads (load-bearing, TDD §2.3).** The platform's
`ServiceSpec.to_jsonld()` emits some fields and not others (e.g. `lifecycle` as a
flat `list[str]`; `leadsTo`/`stateEffects` may be absent from the serialiser even
when the schema defines them; `async`/`i18n` reliably present; `deprecated`/
`sunsetDate`/`replacementOperation` only when set). Every accessor reads
defensively — missing key → that detail simply absent. This is why **auto-trim is
mandatory, not cosmetic**.

**Default view = the full picture, auto-trimmed (ADR-002, binding founder
decision).** Above the "show technical detail" toggle: what-it-does (readable
action + paired actual operation identifier), readable permission line + "Who can
do this" + paired actual permission code, sign-in/background/retirement flags,
form fields (labels/placeholders/input types/grouping/validation/human enum
labels/show-when), languages, entities + lifecycle states, business rules,
journeys, what-each-action-changes, worked example, errors. Each section renders
**only if the spec carries content** (no empty headings).

**Area grouping (ADR-006).** `derive_areas` attributes each element to a service
area; >1 area → "areas covered" overview + one grouped block per area; ==1 →
ungrouped, no heading, no overview. OpenAPI fallback groups by tag.

**Technical toggle holds:** rateLimits, idempotent flag, bindings, raw
input/output JSON schemas, error relatedDocs, full ServiceSpec JSON-LD / Redoc.
The actual permission code + operation identifier are NOT toggle-only (ADR-002
Rev 6) — they appear in the default view paired with their readable forms.

**Events are out of scope** (not carried by the ServiceSpec contract; ADR-005).

## Armor

- Any subprocess (Redoc CLI for the OpenAPI technical render) uses an argv array,
  `shell=false`, and a bounded timeout — matching `wpx-worktree`'s `_run`.
- Spec discovery + artifact writes stay inside the resolved worktree root (reject
  traversal shapes). No network on the hot path; no secrets; no PII.
- Observability: the step emits the standard wpx JSON result (what was produced).

## Tests (Proof — the keystone Red comes first; WPB-08 outside-in)

Write both fixtures + assertions, see them fail, **then** build the renderer.

- **Fixture A — rich, MULTI-AREA** ServiceSpec (two areas, e.g. "Platforms" +
  "Notifications"), shaped per `core/service/types.py` `ServiceSpec.to_jsonld()`:
  ≥3 operations (one `async`, one `deprecated` with `sunsetDate` +
  `replacementOperation`); top-level `permissions` definitions; ≥1 entity with
  rich `properties` (label+placeholder+group; validation; an enum with
  `x-enum-labels`; an `x-visibility` show-when), multi-state `lifecycle`, ≥1
  `constraint`; ≥1 operation `input` with form metadata; ≥1 `workflow`;
  multi-locale `supported_locales`. Asserts TDD §4.1 (0–14).
- **Fixture B — minimal, SINGLE-AREA** ServiceSpec: one operation, plain typed
  input/output, no form metadata, single locale, no entities/workflows/state.
  Asserts TDD §4.1 (15–18): auto-trim + no empty headings + single-area
  ungrouped.
- **OpenAPI-fallback + degradation** (TDD §4.2): graceful degradation with no
  empty headings; tag-grouping vs single-block; two-contracts precedence;
  no-contract raw + note.

## Rollback

Remove the new script, its dispatcher registration, and the test dir. Pure
additive — no existing step or cockpit code changes.
