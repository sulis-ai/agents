---
# Identity (WP-01)
id: WP-003
title: "Cockpit wiring — per-change 'open data contract / open UI' links, rendered at the review gate + on demand"
kind: frontend
# primitive: EXPAND-Create — net-new GET endpoints + client link components on the existing cockpit
primitive: Create
group: expand
source: feature
change_id: 01KSSV19SFWBJM01BM2XP6CZZ0
parent_phase: cockpit-contract-preview

# Scope (WP-02..04)
atomic_branch: yes
estimate: large
blast_radius: medium

acceptance_criteria:
  - "Each in-flight change in the cockpit surfaces its OWN 'open data contract' and 'open UI' affordances, resolved entirely via the existing `ChangeStoreReader` port + `requireChange`/`resolveWorktreeRoot` — generic, never hard-wired to a change (ADR-003)."
  - "Two new GET-only server endpoints serve the rendered CONTRACT.html + UI.html (read-only inventory invariant preserved: only `router.get`; the read-only test still passes). Rendering/recreate are steps, not in-process server work (ADR-001/004)."
  - "Design-time (pre-dispatch review gate): after decompose, before run-all dispatch, the in-flight change's CONTRACT.html + UI.html are rendered so the founder can eyeball them before anything is built on the contract (TDD §5)."
  - "On-demand: the per-change links render (or re-render) the artifacts when the founder clicks, recreating a tidied worktree first if needed (consumes WP-004) — the founder never navigates a worktree."
  - "The shipped CONTRACT.html default-view render matches the signed-off visual contract (WP-005); a change with no UI contract shows 'no UI contract for this change', not a broken link."
  - "Loading / error / empty states for both link surfaces (WPF-05): rendering-in-progress, recreate-failed/not-recreatable note, no-contract note. WCAG AA gated (jest-axe per component, Playwright-axe per page; WPF-06)."

test_plan:
  unit:
    - "apps/cockpit/server/tests/routes.contract.test.ts::test_get_data_contract_served_when_present"
    - "apps/cockpit/server/tests/routes.contract.test.ts::test_get_ui_contract_none_returns_note_not_broken_link"
    - "apps/cockpit/server/tests/routes.contract.test.ts::test_read_only_invariant_preserved_get_only"
    - "apps/cockpit/client/src/tests/contract-links.test.tsx::test_each_change_links_to_its_own_contracts (jest-axe)"
    - "apps/cockpit/client/src/tests/contract-links.test.tsx::test_loading_error_empty_states (jest-axe)"
  integration:
    - "apps/cockpit/server/tests/app.integration.test.ts::test_contract_endpoints_mounted_and_reachable"
    - "apps/cockpit/client/src/tests/contract-preview.e2e.spec.ts (Playwright + Playwright-axe — open a change, open its data contract + UI)"
  verification:
    - "branch-ci workflow green on the WP branch"
    - "Anti-hard-wiring acceptance walk (see Release acceptance below) — release gate, ADR-003 / TDD §4.4"
verification_gates: [unit, integration, e2e, a11y, perf]

# Visual contract (WPF-11 / WP-08.5 — REQUIRED for a user-facing frontend WP)
visual_contract: WP-005                 # the signed-off CONTRACT.html default view

# Lineage (WP-06)
derived_from:
  - finding: "TDD §2.1/§2.3 (cockpit endpoints + client affordances), §3 (read-only invariant), §5 (review-gate + on-demand timing); ADR-001/003/004; WPF-12 (agentic AI surface)"
    found_in: .architecture/cockpit-contract-preview/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-05-29
  agent: sulis-engineering-architect
addresses_findings:
  - "feature::cockpit-contract-preview::cockpit-wiring"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
# dependsOn: serves WP-001/002 output; uses WP-004 recreate; declares WP-005 visual contract
dependsOn: [WP-001, WP-002, WP-004, WP-005]

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Remove the two GET endpoints + their mounting, the client link components, and
  the design-time render hook. Pure additive to the cockpit; the read-only
  invariant and existing routes are untouched. No data migration.
---

# Cockpit wiring — links + review-gate timing

## Why

WP-001 and WP-002 produce inert HTML in a worktree. The founder reaches them
through the cockpit: per-change "open data contract / open UI" links, rendered at
the pre-dispatch review gate and again on demand. This is the surface that makes
the rendered contracts a defect-prevention review gate rather than buried files.

## What changes (Form)

- **Server (Node/Express, `apps/cockpit/server/`):** two NEW GET-only endpoints
  extending the existing router table in `app.ts`, mirroring the
  `routes/file.ts` shape (`router.get`, `requireChange`, `resolveWorktreeRoot`,
  `safeJoin`). They serve the rendered `CONTRACT.html` + `UI.html` for a change
  resolved by `:id`. NEW `routes/contract.ts`; mounted in `app.ts`.
- **Client (React, `apps/cockpit/client/src/`):** per-change "open data contract
  / open UI" affordances on the existing change surfaces (`Dashboard` /
  `ThreadView`), with loading/error/empty states and `shared/api-types.ts` wire
  types.
- **Design-time hook:** after `decompose`, before `run-all` dispatch, render the
  in-flight change's artifacts (invokes WP-001 + WP-002 steps) so the founder
  reviews before build.
- **On-demand:** the link handler renders/re-renders, recreating a tidied
  worktree first via WP-004 if needed.

## How (the data seam — CONTRACT_FIRST)

The producer/consumer seam here is **Python step (WP-001/002) → Node server
(this WP)**, meeting at the **rendered artifact files + the manifest** in the
worktree. The server consumes that manifest (which records `data_contract` +
`ui_contract: present|none`) and serves the files — it does not parse contracts
itself (keeps the cockpit read-only; ADR-001). The server builds against a
manifest fixture (the contract mock) so it can proceed in parallel with WP-001/002
(CF-05). The **visual** contract is WP-005 (signed off); this WP declares
`visual_contract: WP-005` and `dependsOn` it (WPF-11 / WP-08.5).

## Armor

- Read-only invariant: only `router.get`; the existing read-only inventory test
  must still pass. Recreate (WP-004) is a separate spawned step with a bounded
  timeout, not in-process server generation.
- Path safety: reuse `safeJoin` / `resolveWorktreeRoot`; reject traversal shapes.

## Agentic-interface (WPF-12, AI surface — the cockpit)

Outcomes deliver in a purpose-built UI (the rendered contract view), not a chat
transcript; honest-confidence (the "this contract carries less guidance" /
"no UI contract" notes are surfaced plainly, not hidden).

## Tests (Proof — outside-in, WPF-10)

- Server route tests (supertest, TDD §4.3): artifact-present → served;
  ui-none → note not broken link; read-only invariant preserved.
- Client component tests (RTL + jest-axe): each change links to its OWN
  contracts; loading/error/empty states.
- E2E (Playwright + Playwright-axe): open a change, open its data contract + UI.

## Release acceptance (anti-hard-wiring — release gate, ADR-003 / TDD §4.4) — MUST

**Open the cockpit, walk EVERY in-flight change, confirm each surfaces its OWN
data + UI contracts.** This is an explicit release-acceptance step, not a
single-change smoke test. It is the trust property of the whole feature and the
proof that resolution is generic (no change is hard-wired).

## Rollback

Remove the endpoints + mounting, the client components, and the design-time hook.
Pure additive; read-only invariant and existing routes untouched.
