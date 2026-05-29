---
# Identity (WP-01)
id: WP-005
title: "Visual contract — the founder-facing CONTRACT.html full-picture default view (real-token mockup)"
kind: contract
contract_type: visual
# primitive: EXPAND-Create — net-new design artifact (real-token mockup); the done-oracle for the renderer
primitive: Create
group: expand
source: feature
change_id: 01KSSV19SFWBJM01BM2XP6CZZ0
parent_phase: cockpit-contract-preview

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: low

acceptance_criteria:
  - "A real-token mockup of the CONTRACT.html full-picture default view exists at `.architecture/cockpit-contract-preview/mockups/CONTRACT-walkthrough.mockup.html`, showing a TWO-AREA example (a 'Platforms' area + a 'Notifications' area; ADR-006) with the 'areas covered' overview and one grouped block per area."
  - "Within each area the mockup shows the full default register (TDD §4.5): what-it-does with the readable action description PAIRED with the actual operation identifier; the readable permission line + 'Who can do this' line + the actual permission code paired with the meaning; sign-in + background flags; form fields (a labelled field, a validation rule, a human-labelled enum, a show-when field); the languages line; entities + lifecycle; business rules; a workflow journey; what-each-action-changes; the enriched retirement badge (sunset + replacement); the errors surface; and the collapsed 'show technical detail' toggle (ADR-002 Rev 6)."
  - "Tokens are real (UXD-14): the mockup renders against the cockpit's real design tokens, design-time WCAG AA holds, no hardcoded values stand in for tokens."
  - "Founder sign-off recorded: signed_off_at + provenance: production-approved (UXD-14 / WP-08.5 done-gate)."

test_plan:
  unit: []
  integration:
    - "Visual review of the rendered mockup against the cockpit token set (design-time WCAG AA)."
  verification:
    - "Founder sign-off on the rendered mockup (the done-oracle for a visual contract)."
verification_gates: [contract]

# Lineage (WP-06)
derived_from:
  - finding: "TDD §4.5 (visual-contract gate, UXD-14) + ADR-002 (full-picture default view + Rev 5/6 permission + identifier pairing) + ADR-006 (area grouping)"
    found_in: .architecture/cockpit-contract-preview/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: blueprint-run/2026-05-29
  agent: sulis-engineering-architect
addresses_findings:
  - "feature::cockpit-contract-preview::visual-contract-default-view"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
# status: done — the founder has SIGNED OFF the visual contract (2026-05-29)
status: done
dependsOn: []

# Visual-contract sign-off (UXD-14 / WP-08.5 — the done-gate for a kind:contract visual WP)
mockup: .architecture/cockpit-contract-preview/mockups/CONTRACT-walkthrough.mockup.html
signed_off_at: 2026-05-29
provenance: production-approved

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  N/A — a design artifact. Superseded only by a re-signed mockup if the
  default-view design changes.
---

# Visual contract — the CONTRACT.html full-picture default view

## Why

The CONTRACT.html default view is a **user-facing surface** (the founder reads it
to judge the work). Per UXD-14 / WORK_PACKAGE WP-08.5, a user-facing seam needs a
**visual contract**, signed off before any frontend builds against it. This WP is
that contract: the real-token mockup the renderer (WP-001) must produce and the
cockpit wiring (WP-003) declares against.

## What it specifies (TDD §4.5)

The mockup at `mockups/CONTRACT-walkthrough.mockup.html` shows a **two-area**
example (ADR-006) — "Platforms" + "Notifications" — with:

- the **"areas covered" overview** at the top, then one grouped block per area;
- within each area, the full default register: readable action description
  **paired with the actual operation identifier**; the **readable permission
  line** (meaning) + **"Who can do this"** + the **actual permission code** paired
  with the meaning (ADR-002 Rev 6); the **sign-in + background** flags; the
  **form fields** a user fills in (a labelled field, a validation rule, a
  human-labelled enum, a show-when field); the **languages** line; **entities +
  lifecycle**; **business rules**; a **workflow journey**;
  **what-each-action-changes**; the **enriched retirement badge** (sunset +
  replacement); the **errors** surface; and the **collapsed technical toggle**.

The **auto-trim** behaviour (sections present only when the spec carries them)
and the **single-area-no-heading** behaviour are proven by the WP-001 unit tests,
**not** by the mockup.

## Status

**SIGNED OFF by the founder on 2026-05-29** (`signed_off_at` +
`provenance: production-approved`). This unblocks WP-001 (the renderer produces
this view) and WP-003 (the frontend declares `visual_contract: WP-005` against
it). Per WP-08.5 the done-gate for a visual contract is founder sign-off — met.

## Rollback

A design artifact. Re-sign only if the default-view design changes.
