---
# Identity (WP-01)
id: WP-002
title: "UI-contract renderer — render a change's visual contract to UI.html, or emit-nothing-with-note"
kind: backend
# primitive: EXPAND-Create — net-new wpx render-ui path (reuses design-system VIEWER inside)
primitive: Create
group: expand
source: feature
change_id: 01KSSV19SFWBJM01BM2XP6CZZ0
parent_phase: cockpit-contract-preview

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: low

acceptance_criteria:
  - "For a change with a visual contract / tokens in its worktree, the step produces UI.html by reusing the design-system skill's VIEWER generation pointed at that contract; UI.html is self-contained."
  - "For a change with NO visual contract (non-user-facing), the step emits NOTHING for UI.html and records `ui_contract: \"none\"` (with a human note) in the manifest — never a broken link or an exception (TDD §2.4)."
  - "The step shares the wpx shape with WP-001 (argv, emit_ok/emit_error, worktree-only inputs, no hard-wired change — ADR-001/003): `wpx render-ui --worktree <path>` (or a render-contract subcommand)."
  - "Generic per-change resolution: the visual contract is discovered inside the worktree by convention, never by a fixed filename for one change (ADR-003)."

test_plan:
  unit:
    - "plugins/sulis/scripts/tests/unit/test_wpx_render_ui.py::test_renders_viewer_when_visual_contract_present"
    - "plugins/sulis/scripts/tests/unit/test_wpx_render_ui.py::test_emits_none_with_note_when_no_visual_contract"
  integration:
    - "plugins/sulis/scripts/tests/integration/test_wpx_render_ui_cli.py::test_cli_emits_ok_and_manifest_records_ui_state"
  verification:
    - "branch-ci workflow green on the WP branch"
verification_gates: [unit, integration, smoke]

# Lineage (WP-06)
derived_from:
  - finding: "TDD §2.4 (UI renderer reuses design-system VIEWER; emit-nothing-with-note); ADR-001/003"
    found_in: .architecture/cockpit-contract-preview/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-05-29
  agent: sulis-engineering-architect
addresses_findings:
  - "feature::cockpit-contract-preview::ui-contract-renderer"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
# dependsOn: independent of WP-001; both produce artifacts the cockpit later serves
dependsOn: []

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Pure additive: a new wpx render-ui path + tests. Remove it. No change to the
  design-system skill (reused, not modified) and no cockpit change.
---

# UI-contract renderer (reuses the design-system VIEWER)

## Why

The change's visual / UI contract is as inert as the data contract. The founder
should see the rendered UI alongside the rendered data contract. The
design-system skill already generates a self-contained VIEWER from a design
source — reuse it (EP-03), don't rebuild it.

## What changes (Form)

- NEW `wpx render-ui` path (a sibling step or a `wpx-render-contract`
  subcommand) in `plugins/sulis/scripts/`, same wpx shape as WP-001 (ADR-001).
- Reuses the **design-system skill's VIEWER** generation pointed at the change's
  visual contract / tokens located in the worktree; emits `UI.html`.
- Writes `ui_contract` state into the shared manifest (`"present"` with the path,
  or `"none"` with a note).
- NEW tests + fixtures under `plugins/sulis/scripts/tests/`.

## How

- Discover the visual contract inside the worktree by convention (ADR-003 —
  generic, never a fixed filename for one change).
- Present → invoke the design-system VIEWER generation, write `UI.html`.
- Absent → write nothing for `UI.html`; record `ui_contract: "none"` + a plain
  note in the manifest, so WP-003's cockpit shows "no UI contract for this
  change" rather than a broken link (TDD §2.4).

## Armor

- Same spawn/timeout discipline as WP-001 if the VIEWER generation shells out.
- Writes stay inside the resolved worktree root; no network on the hot path.

## Tests (Proof)

- Fixture worktree **with** a visual contract → `UI.html` produced, manifest
  records `present`.
- Fixture worktree **without** a visual contract → no `UI.html`, manifest records
  `none` + note, no exception (the TDD §4.2 "no visual contract" case).

## Rollback

Remove the render-ui path + tests. Pure additive.
