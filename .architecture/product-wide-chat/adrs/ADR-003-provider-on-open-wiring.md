---
id: ADR-003
title: Provider-on-open — the agent picker drives the daemon provider seam, not the Claude-only relay
status: accepted
date: 2026-06-25
change: CH-G3Y4RM
---

# ADR-003 — Provider-on-open: which seam the agent picker drives

## Context

The cockpit hardcodes the provider in **one** place: `apps/cockpit/server/index.ts:275` — `return { provider: "pty", cwd: record.worktreePath }` inside `resolveChange`. This flows: `resolveChange` → `TerminalSidecar.ts` injects it into `params.spec` → daemon → `SessionManager.open(key, spec)` → `self._adapters.get(spec.provider)` (`manager.py:341`). The daemon already registers `"pty"` = Claude, `"agy"`/`"antigravity"` = Antigravity (`session_manager_daemon.py:636-641`). The agy adapter is on main.

Critically, there are **two session systems**:
- the **daemon/pty** path — provider-aware (`SessionSpec.provider`), the only seam where `agy` can be selected;
- the **chat relay** (`POST /api/changes/:id/chat` → `StreamJsonSessionBridge`) — a separate headless `claude` subprocess with **no provider concept at all**.

The spec requires the picker to select `pty`(Claude)/`agy`(Antigravity) for the product's chat — so the picker must drive a provider-aware seam.

## Decision

**The per-product chat session opens on the provider-aware daemon/pty path, and the agent picker's choice is threaded through `resolveChange` (replacing the `"pty"` literal) into `SessionSpec.provider`.**

Concretely:
- The client sends the chosen provider (`pty` | `agy`) with the session-open request, scoped to the active `chat_scope` (ADR-002).
- `resolveChange` (and the `StartProductionServerOptions`/sidecar plumbing it sits in) is widened from returning a literal `{provider:"pty"}` to returning the **provider resolved for the active chat scope**: the picker's choice if set, else the scope's remembered `participant_context.provider`, else the safe default `pty`.
- Unknown/absent provider falls back to `pty` (Claude) — the daemon already raises `UNKNOWN_PROVIDER` for a bad key, so the client never sends a free-form string; it sends one of the two registered keys.
- **Guarded mid-run switch (AI-03):** switching the provider while a session is running is a confirm gate; the switch applies to **new work** (a new session open on the new provider), never silently re-homes a live run. Honest active-agent identity (AI-07): the composer foot names the *actually running* provider, not the picked-but-not-yet-applied one.

## Why this lead

- **The daemon/pty path is the only provider-aware seam.** Selecting `agy` is impossible on the `StreamJsonSessionBridge` relay without inventing a provider concept there — extending the seam that already has one is the boring choice (CP-01, EP-03).
- **One literal to replace** (`index.ts:275`) plus its option plumbing — a surgical change, not a rewrite.
- **Default-to-`pty`** preserves today's behaviour for any scope with no remembered choice, so the change is additive.

## Alternatives rejected

- **Add a provider concept to the `StreamJsonSessionBridge` chat relay.** Rejected: that's a second provider-selection mechanism (two sources of truth) and a larger change than threading the existing `SessionSpec.provider`; the daemon already does provider selection correctly.
- **Keep `pty` hardcoded and branch in the client.** Rejected: the client cannot spawn `agy`; provider selection is a server/daemon responsibility. A client-side branch would be a lie about what's running (violates AI-07 honest identity).
- **Switch the live session in place on agent change.** Rejected: AI-03 — re-homing a running agent mid-turn is unsafe and dishonest; the guard applies the choice to new work.

## Consequences

- `StartProductionServerOptions` / `resolveChange` signature widens to carry a per-scope provider resolver; `TerminalSidecar` plumbing unchanged (it already forwards `spec.provider`).
- The honest active-agent badge in the composer foot reflects the **running** provider (sourced from the live session), reusing the LiveTerminal honest-status idiom (status by glyph+word, not colour).
- The mid-run switch reuses the cockpit's existing propose→confirm gate idiom (`confirmGate.ts`) for the AI-03 guard.
- Chaos/contract test: opening a scope with `provider:"agy"` must spawn the agy adapter; with `provider:"pty"` the Claude adapter; an unknown key falls back to `pty` (never errors the user).
