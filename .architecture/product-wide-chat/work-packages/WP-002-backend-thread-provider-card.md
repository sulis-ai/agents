---
id: WP-002
title: Backend — per-product thread keying, provider-on-open, chat→card wiring
kind: backend
primitive: Create
group: expand
status: pending
dependsOn: [WP-001]
blocks: [WP-004]
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/_session_manager/tests/test_chat_scope_store.py::test_two_scopes_two_threads"
estimated_token_cost: "input: ~35k / output: ~14k"
source: tdd:product-wide-chat#2.2
---

# WP-002 — Backend: thread keying + provider-on-open + chat→card

## Context

TDD §2.2, ADR-002, ADR-003, ADR-004. Implements the server side of the seam against the
WP-001 contract. **Overwhelmingly composition** — reuses `LocalThreadStore`, the daemon
provider registry, and the `start-from-intent` orchestrator. New code is a scope resolver,
a provider resolver, and route handlers.

## Contract

- **Thread keying (ADR-002):** `resolve_chat_thread(chat_scope) -> LocalThreadStore` rooted
  at `~/.sulis/chat/{chat_scope}/threads/`, reusing the shipped record shapes + append-only
  invariants. Provider remembered per scope via `participant_context.provider` (no schema
  fork). `chat_scope` validated through the existing `validate_store_id`.
- **Provider-on-open (ADR-003):** widen `resolveChange`/`StartProductionServerOptions`
  (`apps/cockpit/server/index.ts:275`) from the `{provider:"pty"}` literal to a per-scope
  resolver: picked provider → else remembered → else `pty`. The choice flows through the
  existing `SessionSpec.provider` → daemon `_adapters.get` path (unchanged downstream).
- **Routes (against WP-001 contract):** `GET /api/chat/:scope/thread`,
  `POST /api/chat/:scope/message` (SSE), `PUT /api/chat/:scope/provider` (AI-03: persists
  the choice, returns `applied:"new-work"`, does NOT re-home a live run).
- **Chat→card (ADR-004):** the chat message route, on a "start work" intent, drives the
  REUSED `start-from-intent` propose→confirm; no new creation path, no second confirm gate.

## Definition of Done

**Red**
- [ ] `test_chat_scope_store.py::test_two_scopes_two_threads` — two scopes write to two
      thread directories; `get_messages` returns each scope's own history; **no blend**.
      Characterisation test on the new root resolver; fails before the resolver exists.
- [ ] `test_provider_on_open.py` — opening with `provider:"agy"` selects the agy adapter,
      `"pty"` selects Claude, unknown → `pty` fallback (uses the daemon registry / fake-child
      seam `SULIS_DAEMON_PTY_CHILD`). Fails while the provider is hardcoded.
- [ ] `chatRoutes.test.ts` — `PUT /provider` persists per scope and returns
      `applied:"new-work"`; a running session is NOT re-homed (asserts the live session keeps
      its provider).

**Green**
- [ ] `resolve_chat_thread` + chat-scoped store root implemented; provider stamped in
      `participant_context`.
- [ ] `resolveChange` widened to the per-scope provider resolver; `index.ts:275` literal gone.
- [ ] The three routes land, wired against the WP-001 shared types; chat→card delegates to
      `start-from-intent`.
- [ ] All Red tests green.

**Blue**
- [ ] No fork of the thread-store contract — only the root resolver + key are new; record
      shapes and invariants reused verbatim.
- [ ] Provider resolution is one function with explicit fallback order (boring, no implicit
      magic); `UNKNOWN_PROVIDER` remains the daemon backstop.
- [ ] No new external call without the existing timeout/CB the daemon + store already enforce.

## Acceptance Evidence

- Branch: wp/create-product-wide-chat/wp-002-backend-thread-provider-card (deleted post-merge)
- Completed: `2026-06-25T22:16:59Z` (Step 12 by calling session)
