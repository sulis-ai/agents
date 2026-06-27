---
id: WP-001
title: Chat parity + status-line visual contract (founder sign-off gate)
kind: frontend
status: done
change: CH-9642DA
primitive: REINFORCE-Document
group: reinforce
dependsOn: []
estimated_token_cost: "input: ~2k / output: ~1k"
signed_off_at: "2026-06-27"
provenance: production-approved
verification:
  na: true
  justification: "Visual contract is a design-time sign-off artifact, not shipped code; its 'test' is founder approval of the signed contract + mockup. The frontend #45/UXD-14 gate requires every implementation WP point back to it."
source: spec:chat-experience-both-universal-change#45 / UXD-14
---

# WP-001 — Chat parity + status-line visual contract (sign-off gate)

## Context

TDD §1 + the signed visual contract
`contracts/visual/chat-both-status.contract.md` (mockup
`chat-both-status.html`). This is a **user-facing frontend surface**, so the
#45 / UXD-14 gate applies: the founder signs off on *how it looks* before any
implementation WP touches the components. The contract is **already signed**
(`signed_off_at: 2026-06-27`, `provenance: production-approved` — "Let's press
ahead with that design and approach").

## The contract (what the founder approved)

Turn-summary cards in the universal chat (reusing the signed chat-B2 card),
markdown + code rendered in both chats through the one safe renderer, and the
conversation-anchored working↔finished status line sharing one
mutually-exclusive slot with the suggestion chips — plus the bottom-dock
de-collision fix. Tokens lifted verbatim from `tokens.css` v4.2.0; WCAG AA
decided at design time.

## Definition of Done (sign-off, not code)

- [x] Founder viewed the signed contract + mockup (light + dark) and approved.
- [x] Sign-off recorded (`signed_off_at` + `provenance: production-approved`).
- [x] Every implementation WP below carries `dependsOn: [WP-001]` so the
      frontend gate is satisfied.

## Downstream (gated by this contract)

WP-002 (shared `ChatStatusLine`), WP-003 (universal turn-card parity),
WP-004 (Composer status line + de-collision), WP-005 (dock status line),
WP-006 (no-raw-colours coverage extension).
