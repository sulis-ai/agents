---
id: ADR-002
title: Per-product conversation history — key the thread by product, one thread per product
status: accepted
date: 2026-06-25
change: CH-G3Y4RM
---

# ADR-002 — Per-product thread keying in the durable store

## Context

The shipped thread store (`LocalThreadStore`, `thread_store_local.py` + `thread_contract.py`) is constructed **per `change_id`**, with **one thread per change** — the thread id IS the session key IS the change id (`manager.py:744`; ADR-004 in the store's own lineage). Root on disk: `~/.sulis/changes/{change_id}/threads/{thread_id}.{thread,memory,messages}.json[l]`.

The spec requires **one conversation per product**, persisted, never blended; switching products swaps the thread. The store has no product dimension today. `ThreadMemoryContent.participant_context` is an open-ended dict already documented as the slot for "Sulis-specific context (bound change_id, provider identity)".

The "All products" overview and "Unassigned" triage are distinct conversations, not blends of per-product history.

## Decision

**Introduce a product-scoped thread key and persist one thread per product scope.** The chat thread is keyed by a stable `chat_scope` derived from the product scope:

- a real product → `product:{productId}`
- "All products" → `product:__all__` (the overview chat)
- "Unassigned" → reserved `product:__unassigned__` (the triage chat — Phase 2, key reserved now so the store layout doesn't fork later)

The thread is persisted at a **chat-scoped store root** parallel to the existing change-scoped root: `~/.sulis/chat/{chat_scope}/threads/` — reusing the existing `LocalThreadStore` record shapes (`Thread`, `ThreadMessage`, `ThreadMemory`) and append-only invariants verbatim. `validate_store_id` already accepts `[A-Za-z0-9_-]+`; the scope ids are validated through it.

The **chosen agent (provider) is remembered per product** by stamping `participant_context.provider` on the thread's `ThreadMemory` — no contract fork; this is the documented additive slot.

## Why this lead

- **Reuse the record shapes and invariants** (append-only, secret-scrub-on-write, offset ordering) rather than inventing a parallel store (EP-03). Only the *root resolver* and the *key* are new.
- **One thread per scope** matches the ChatGPT-Projects / Slack-channel pattern in the inspiration probe: separate history per context, switching swaps, never blends.
- **`participant_context` for provider** keeps the agent choice durable per product with zero schema change.

## Alternatives rejected

- **Reuse the change-scoped root (`~/.sulis/changes/{change_id}/`).** Rejected: a product chat is not bound to a single change; the change-scoped root would force an artificial change id and would blend chat with one change's transcript.
- **Add a `product_id` column/field to `Thread` and keep one global thread.** Rejected: a single thread filtered by product is exactly the "blended firehose" the spec and CL-02 forbid; filtering is not separation.
- **A new bespoke per-product store.** Rejected: the shipped `LocalThreadStore` already gives durable, append-only, secret-scrubbed persistence — re-implementing it is wasted work and a second source of truth.

## Consequences

- The backend gains a `resolve_chat_thread(chat_scope)` entry that constructs/reads the scope's thread via `LocalThreadStore` rooted at the chat root.
- Switching products on the client swaps the `chat_scope` → the dock reads that scope's thread; histories are physically separate directories, so blending is impossible by construction.
- The contract WP (see ADR-003 sibling) defines `chat_scope` as the wire key the client sends and the server resolves.
- Phase-2 "Unassigned" triage chat slots in at `product:__unassigned__` with no store migration.
