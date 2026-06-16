# ADR-002 — Surface attention + health by enriching the existing board feed, not a new endpoint

> **Status:** accepted
> **Date:** 2026-06-09
> **Deciders:** SEA (from the signed-off design)

## Context

The redesigned card needs three reads per change that aren't on the board feed
(`GET /api/changes`) today:

1. **"Waiting on you"** — the `needsAttention()` verdict (`{ flagged, reason }`).
   The logic already exists in `server/lib/needsAttention.ts`, but it rides
   `ChangeStatus` (the *per-change* status endpoint), not the board's `Change`
   list.
2. **Change-health** — the new On/Off-track verdict (ADR-001).
3. **Liveness "working" sub-state** — splitting the binary `running` into
   *working* (live + actively moving) vs *live* (open but quiet), plus a
   last-activity timestamp for the relative time.

The board renders all of these **per card, for every card at once**. Today the
feed (`server/routes/changes.ts`) shapes each record via `toWireChange(record,
liveness)`.

## Decision

**Enrich the existing `GET /api/changes` feed.** Each row gains:

- `needsAttention: { flagged, reason }` — reusing `needsAttention()` verbatim.
- `health: { state, reason }` — from the new `computeHealth()` (ADR-001).
- `liveness` stays the discriminated union but gains a `lastActivityAt` field;
  the *working* vs *live* split is derived client-side (or server-side) from
  `lastActivityAt` recency, not a new liveness variant.

No new endpoint. The wire `Change` type (`shared/api-types.ts`) gains the
fields; producer (`changes.ts` via `toWireChange`) and consumers (`ChangeCard`,
`StageColumn`, the mobile switcher counts) import them verbatim (CF-02).

## Why (Convention Preference)

- **One read, one feed (CP-01 — internal prior art).** The board already makes
  exactly one list call and polls it every 10s (ADR-007's single permitted
  polling exception). Adding a second per-card endpoint would mean N+1 calls or
  a second poll — strictly worse than widening the one feed already in flight.
- **Reuse the verdict, don't re-detect (EP-03).** `needsAttention()` is the
  single source of truth; the search path (WP-006) already reuses it. The board
  feed becomes a third caller of the same pure function — no parallel logic.
- **The contract is the single source of truth (CF-02).** Widening the `Change`
  shape in `shared/api-types.ts` keeps producer and every consumer symmetric.

## Consequences

- `toWireChange` (and the search shaping path, which reuses it) must gather the
  same attention + health + last-activity signals the status route gathers.
  That means the feed handler now reads, per record, the cheap signals
  `needsAttention` needs (an open-blocker probe + the last transcript turn
  shape) — the same reads the status route already does, lifted onto the list.
- **Performance note (Armor):** the feed already does a per-record `await
  probeLiveness(...)` inside `Promise.all`. The added reads (open-blocker
  filesystem probe, last-turn shape) follow the same best-effort, read-only,
  never-throw discipline as `detectOpenBlocker`. The list is bounded by the
  in-flight change count (small); no pagination pressure. If the per-record
  fan-out ever grows costly, that is a separate optimisation WP — not a reason
  to split the endpoint now.
- Idle-but-fine stays **not flagged** (FR-12) — the enrichment changes *where*
  the verdict is surfaced, never the verdict itself.

## Alternatives rejected

- **A new `GET /api/changes/health` (or `/attention`) batch endpoint.**
  Rejected: a second list call + a second poll for data the board needs
  in lockstep with the change list. N+1 or dual-poll for no benefit.
- **Per-card client calls to the existing `/status` endpoint.** Rejected:
  classic N+1 — one request per visible card, every 10s.
- **Compute health/attention client-side.** Rejected: rigor-for-stage and
  open-blocker reads are filesystem reads the client cannot and must not do;
  the verdict must be honestly server-derived (no client invention).
