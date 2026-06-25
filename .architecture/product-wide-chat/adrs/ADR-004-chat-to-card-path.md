---
id: ADR-004
title: Chat → card — reuse start-from-intent; overview chat collects product before filing
status: accepted
date: 2026-06-25
change: CH-G3Y4RM
---

# ADR-004 — The chat→card creation path

## Context

When a per-product conversation means "do some work", the spec requires a **confirm gate (AI-03)** then a **change card on that product's board**, clickable through to the change. The "All products" overview chat must **ask which product** before filing.

The cockpit already has a confirm-gated, product-scoped change-create flow: **`start-from-intent`** (`POST /api/changes/start-from-intent`, two-phase `propose`→`confirm`). `StartFromIntentRequest` carries `{ phase, productId, intent, kind }`; the proposal returns a `confirmToken`; confirming returns a full `Change` (with `changeId`, `branch`, `stage:"recon"`). The client hook `useStartFromIntent({productId})` exposes `propose/confirm/reset`. Product scope is supplied **at creation time** via `productId`; the board then shows the card because the change's resolving Project belongs to that Product (`productScope.ts`). Cards navigate via `<Link to={/c/:changeId}>`.

## Decision

**Chat→card reuses `start-from-intent` verbatim as the creation path; the chat is the surface that gathers `intent` + (for the overview chat) `productId`, then drives the existing propose→confirm lifecycle.**

- **Per-product chat:** the active product's id is already known (the dock's `chat_scope`), so the chat calls `propose(intent)` with that `productId`, shows the proposal, and on the AI-03 confirm calls `confirm()`. The returned `Change` surfaces as a card on that product's board (server-side scope, no client filtering needed).
- **Overview chat ("All products"):** `productId` is null, so before `propose` the chat **asks which product** the new work belongs to (a required disambiguation step using the same `ProductControl` menu idiom), then proceeds exactly as above with the chosen `productId`. It never files a card without a product.
- The confirm gate is the existing `confirmGate.ts` propose→confirm verdict — chat does **not** invent a second gate.
- Clicking the surfaced card navigates to `/c/:changeId` (existing `ChangeCard` Link), focusing the change.

## Why this lead

- **`start-from-intent` already is the confirm-gated chat→card flow** with product scoping built in (EP-03: reuse, don't rebuild). It is deliberately a deterministic server action (not an agent turn) — the right primitive for "create a card".
- **Product-at-creation-time** means the card lands on the right board with zero extra wiring; the board's existing server-side scope (`productScope.ts`) does the rest.
- **The overview-chat "ask which product"** is a thin pre-step (one menu), not a new creation path — keeping a single change-create flow (one source of truth).

## Alternatives rejected

- **A bespoke chat→card endpoint.** Rejected: duplicates `start-from-intent`'s propose/confirm/product-resolve logic — two sources of truth for change creation, and loses the confirm gate the orchestrator already enforces.
- **Create the card unscoped, then assign product via `assignChangeProduct`.** Rejected: a two-step create-then-assign races the board render (card briefly appears on the wrong/no board) and is unnecessary — `start-from-intent` takes `productId` up front.
- **Let the agent turn create the card.** Rejected: change-creation is deterministic by design (the WP-010 lesson encoded in `SulisChangeStarter`); an agent-authored create would be non-deterministic and unconfirmable.

## Consequences

- The chat dock embeds the `useStartFromIntent` lifecycle (propose/confirm/reset) and renders the proposal + confirm using the existing `StartFromIntent` confirm UI pattern.
- The overview chat gains a required "which product?" disambiguation before `propose`; the per-product chat skips it (product already known).
- On `started`, the card appears on the target product's board via existing scope; the chat shows a plain-language activity line ("Started X — it's on the {Product} board now") and a link.
- No change to the board's scoping logic or the data model (a spec non-goal is preserved).
