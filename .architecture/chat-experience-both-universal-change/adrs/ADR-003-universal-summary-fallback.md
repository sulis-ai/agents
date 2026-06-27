# ADR-003 — The universal chat uses the first-sentences summary fallback; it does not get a new product-scoped summary endpoint

> Status: accepted · 2026-06-27 · Change CH-9642DA · Tier S
> Decision owner: engineering-architect · Scope: Form, scope boundary

## Context

The in-change `TurnCard` shows a generated 2–3 sentence Haiku summary, fetched
by `useTurnSummaries(changeId)` from `GET /api/changes/:id/turn-summaries`. That
endpoint is **change-scoped** — keyed by change id. The universal chat is
**product-scoped** (`ProductChatDock` → `useProductChat(scope)`); there is no
change id, and no product-scoped summary endpoint exists.

`TurnCard` already handles a missing summary gracefully: `summary` is optional,
and the card falls back to `firstSentences(turn.said, 3)` when no generated
summary is present (`shared/groupTurns.ts`). The spec is explicit:

> No change to the summary-generation engine itself — the universal chat reuses
> the same summaries the in-change chat already produces.

## Decision

**The universal chat renders `TurnCard` with no `summary` prop, so each card
shows the built-in first-sentences fallback. We do not build a product-scoped
summary endpoint in this change.**

This honours the spec's non-goal ("no change to the summary-generation engine")
and the convention-preference rule (reuse the existing graceful-degradation path
the card already ships). The universal chat still gets the exact card *shape*
the founder asked for — summary lead, "show the full reply" toggle, folded
steps, markdown rendering — with the fallback summary as the lead. Where the
in-change chat later backfills a generated summary, the universal chat shows the
honest first-few-sentences condensation, which is the same fallback the
in-change chat itself shows before its Haiku summary lands.

## Consequences

- No server change, no new query, no new wire type — the change stays a
  pure-client frontend change (confirms Tier S).
- `ProductChat` passes `<TurnCard turn={item} />` with neither `summary` nor
  `generating` — the card's existing fallback does the rest.
- Acceptance bullet "an agent reply appears as a summary card … not a raw wall
  of text" is satisfied by the fallback lead + the progressive-disclosure
  toggle; the bullet does not require a *generated* summary specifically.
- **Follow-on (out of scope, recorded):** if product-scoped generated summaries
  are wanted later, that is a new change — a product-scoped summaries endpoint +
  a `useProductTurnSummaries` hook, wired into the same `summary` prop. Need
  identifier: `summary-endpoint-product-scope`.
