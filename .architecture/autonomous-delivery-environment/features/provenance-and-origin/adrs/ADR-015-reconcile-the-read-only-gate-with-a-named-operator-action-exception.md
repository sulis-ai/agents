# ADR-015 — Reconcile the read-only gate with a named operator-action exception

- **Status:** accepted (mechanism); **founder confirmation requested** on keep-with-exception vs remove-the-feature
- **Date:** 2026-06-05
- **Change:** CH-01KT50 · feature: provenance-and-origin
- **Deciders:** SEA

## Context

The read-only gate (`apps/cockpit/scripts/check-read-only.sh` +
`read-only-inventory.test.ts`) is the cockpit's load-bearing safety guarantee
(ADR-003). **It is currently RED on this branch** — four violations the feature
set inherits and must reconcile to ship green:

1. `server/routes/advanced.ts` — two `router.post` (`/reveal`, `/processes/:pid/stop`) → gate rule 5.
2. `server/lib/changeAdvanced.ts` — `process.kill(pid,"SIGTERM")` + `"SIGKILL")` → gate rule 4 (non-zero signal).
3. `server/lib/turnSummaries.ts` — `writeFile` (summary cache) → gate rule 1.
4. `server/lib/turnSummaries.ts` — `spawn("claude",…)` (the Haiku summariser) → gate rule 2b.

These are **pre-existing** (tasks #21/#22 + the turnSummaries pair), introduced
by earlier work, not by this feature set — but a feature set cannot ship green
on top of a red gate.

## Decision

**Keep the gate; add path-scoped, named exceptions with recorded rationale —
the same audited-exception discipline ADR-003 already uses for the chat
relay/bridge.** A new exception class **operator-action** is added:

| File | Exception | Rationale (recorded in the gate's `--explain`) |
|---|---|---|
| `server/routes/advanced.ts` | allow its two POST routes | Deliberate, founder-initiated OS-side operator actions (reveal a folder; stop a process the founder started). Not data writes; not a session start. |
| `server/lib/changeAdvanced.ts` | allow the non-zero `process.kill` | The **one** place a founder-initiated "stop this process" lives. Liveness stays signal-0 everywhere else. |
| `server/lib/turnSummaries.ts` | allow the `writeFile` (cache) + `spawn("claude")` | The write is a derived, throwaway summary cache (not change/worktree data); the spawn is a neutral-cwd Haiku summariser (no project context, no session, no commit). Pre-dates this set. |

Every exception is **by path + rule**, not a blanket waiver: any *other* file
that sprouts a write, a non-zero signal, a process start, or a POST still fails
the gate. `read-only-inventory.test.ts` + `check-read-only-script.test.ts` gain
parallel assertions that **exactly** these files are exception-listed.

## Why keep-with-exception is the convention

ADR-003 already established that the right move is to **narrow the allow-list,
not remove the gate** — the value is that the *one* exception is named and
audited and everything else still fails. The operator-action exception extends
that precedent rather than inventing a new posture. Removing the gate (or
blanket-waiving `server/`) would let any future route gain a write undetected —
the exact regression the gate exists to prevent.

## Alternatives considered

- **Remove "stop a process" from the cockpit entirely (the founder alternative).**
  More conservative — the cockpit would have no non-zero signal anywhere, and
  `/reveal` could become a GET (it's idempotent). Costs the founder a feature
  they already have (stop a process you started). Offered as the alternative in
  TDD §10.2.
- **Blanket "writes allowed in `server/`" waiver (rejected).** Defeats the gate;
  ADR-003 already rejected this for the same reason.
- **Refactor `turnSummaries` to not write/spawn (rejected as out-of-scope here).**
  The cache + neutral-cwd spawn are deliberate performance fixes (chat-B2); a
  rewrite is a separate piece of work, not a hardening exception. The exception
  records them as audited.

## Consequences

- The gate goes **green** after WP-P00 (the first WP); the feature set ships on
  a clean gate.
- The gate's `--explain` documents each operator-action + summary-cache
  exception. The cockpit stays *provably* read-only everywhere except the named,
  audited operator-action seam and the derived summary cache.
- This closes tasks #21 (the QueryClientProvider test wrap is folded into
  WP-P00's test fixes) and #22 (the advanced-view gate tension).
