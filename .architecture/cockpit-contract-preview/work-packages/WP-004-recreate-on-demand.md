---
# Identity (WP-01)
id: WP-004
title: "Recreate-on-demand — re-materialise a shipped change's worktree from shipped_sha before rendering"
kind: backend
# primitive: EXPAND-Compose — composes the shipped `sulis-change recreate` behind a serving seam
primitive: Compose
group: expand
source: feature
change_id: 01KSSV19SFWBJM01BM2XP6CZZ0
parent_phase: cockpit-contract-preview

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: low

acceptance_criteria:
  - "Given a change record whose worktree is absent but which is recreatable (branch present or shipped_sha pinned), the serving path re-materialises the worktree by spawning the shipped `sulis-change recreate --handle <handle>` (argv array, shell=false, bounded timeout) before rendering — transparently to the founder (ADR-004)."
  - "Three states are distinguished and handled: (a) worktree present → render directly; (b) absent-but-recreatable → recreate then render; (c) absent-and-not-recreatable (legacy, no shipped_sha) → typed failure → cockpit degrades to 'couldn't reach this shipped change's contracts', never hangs (TDD §3 bounded recreate)."
  - "recreate is idempotent: an already-present worktree is a no-op success (reuses cmd_recreate's existing behaviour — not re-implemented)."

test_plan:
  unit:
    - "apps/cockpit/server/tests/recreate-on-demand.test.ts::test_recreatable_invokes_recreate_then_renders  (recreate stubbed via fake)"
    - "apps/cockpit/server/tests/recreate-on-demand.test.ts::test_present_skips_recreate"
    - "apps/cockpit/server/tests/recreate-on-demand.test.ts::test_not_recreatable_returns_typed_note"
  integration:
    - "apps/cockpit/server/tests/recreate-on-demand.test.ts::test_recreate_timeout_degrades_not_hangs"
  verification:
    - "branch-ci workflow green on the WP branch"
verification_gates: [unit, integration, smoke]

# Lineage (WP-06)
derived_from:
  - finding: "TDD §3 (bounded recreate) + §5 (on-demand timing); ADR-004 recreate-on-demand via sulis-change recreate (#56)"
    found_in: .architecture/cockpit-contract-preview/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-05-29
  agent: sulis-engineering-architect
addresses_findings:
  - "feature::cockpit-contract-preview::recreate-on-demand"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
# dependsOn: composes the shipped `sulis-change recreate`; can build against a fake recreate seam
dependsOn: []

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Remove the recreate-on-demand helper + its tests. The serving path falls back
  to "worktree present → render; absent → note". No change to `sulis-change
  recreate` (composed, not modified).
---

# Recreate-on-demand for shipped changes

## Why

A shipped change's worktree is removed by the #56 tidy step, but its branch +
record (with a pinned `shipped_sha`) are kept. To render contracts for a tidied
change, the worktree must be re-materialised first — transparently, so the
founder never navigates a worktree (TDD §5 on-demand timing).

## What changes (Form)

- NEW recreate-on-demand helper consumed by the serving path (WP-003), in
  `apps/cockpit/server/` (likely beside `_worktree.ts`). It composes the
  already-shipped `sulis-change recreate` CLI (ADR-004 — reuse, EP-03/CP-01), it
  does **not** re-implement worktree materialisation (`cmd_recreate`).
- A `FakeChangeStoreReader`-style fake recreate seam so tests use a real adapter
  shape, not ad-hoc mocks (MEA-09 / WPB-03 in-memory-first).
- NEW `apps/cockpit/server/tests/recreate-on-demand.test.ts`.

## How (Armor — bounded + typed failure)

- Resolve the change generically via the existing `ChangeStoreReader` port
  (`worktreePath`, `branch`, `shipped_sha`) — no hard-wiring (ADR-003).
- Three states (ADR-004 consequence):
  - **present** → render directly (no recreate).
  - **absent-but-recreatable** → `spawn("sulis-change", ["recreate", "--handle",
    handle], {shell:false, timeout})`, then render. Idempotent: already-present →
    no-op success.
  - **absent-and-not-recreatable** → typed failure; the cockpit degrades to a
    plain "couldn't reach this shipped change's contracts" note rather than
    hanging a request.
- The recreate spawn follows the cockpit's spawn-not-exec + bounded-timeout
  discipline (the `SulisChangeStoreReader` / `wpx-worktree` pattern). The cockpit
  stays read-only: recreate is a separate explicitly-invoked step, not in-process
  server generation.

## Tests (Proof)

Route/seam tests (the existing supertest + fake-adapter pattern, TDD §4.3):
recreatable → recreate invoked (stubbed via the fake) then served; present →
recreate skipped; not-recreatable → typed note; recreate timeout → degrades, does
not hang.

## Rollback

Remove the helper + tests; serving path falls back to present-or-note. No change
to `sulis-change recreate`.
