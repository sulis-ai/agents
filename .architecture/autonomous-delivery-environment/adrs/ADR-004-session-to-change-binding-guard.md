# ADR-004 — Positive session-to-change binding before any delivery

- **Status:** accepted
- **Date:** 2026-06-03
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA

## Context

The single most dangerous failure for a multi-change cockpit is delivering
the founder's message to the **wrong change's** agent — corrupting an
unrelated piece of work. FR-21, FR-N2, NFR-SEC-02, and NFR-SEC-06 all
converge on one rule: a message reaches a session **only** if the server
can *positively prove* that session belongs to the named change — for a
live, resumed, **or** freshly-spawned session alike.

The existing `locateTranscripts` already has the right instinct: it
verifies a transcript's `cwd` field equals the worktree path rather than
trusting the directory-name mangle (MVP ADR-004 — "the symptom is 'no
transcripts found' rather than 'the wrong thread's chat rendered'").

## Decision

**Make session-to-change binding a positive check that fails closed, run
at the relay seam before any process start or prompt delivery.** The guard
proves the resolved session is bound to the named change by an
identity it carries, not by position or convenience:

- the session record (`session.json`) carries `change_id`; the resolved
  session's `change_id` MUST equal the requested change id; and
- the session's worktree/`cwd` MUST equal the named change's
  `worktreePath` (the same `cwd`-equality failsafe `locateTranscripts`
  uses).

If either cannot be positively confirmed → refuse with
`SESSION_CHANGE_MISMATCH`, **zero bytes delivered**, no process touched.
The guard applies identically to live / resumed / spawned (NFR-SEC-02),
and runs **before** resume/spawn acts, so the resume/spawn itself can only
ever act on the targeted change's session (NFR-SEC-06, FR-N2).

## Alternatives considered

- **Trust the directory-name mangle / lookup table (rejected).** A mangle
  collision or a stale table would mis-route silently — the exact failure
  this guard exists to make impossible. Fail-closed on a carried identity
  is the safe default.
- **Check after delivery (rejected).** Too late; bytes already sent to the
  wrong agent. The check is a precondition, not a validation.
- **Reuse only liveness as the proof (rejected).** Liveness proves a pid
  exists, not that it is *this change's* session. Binding needs identity,
  not existence.

## Consequences

- A new typed error `SESSION_CHANGE_MISMATCH` joins the existing envelope
  (alongside `SESSION_BUSY`, `SESSION_UNREACHABLE`).
- The guard is a small pure function over (requested change record,
  resolved session record) — unit-testable without a live agent, and the
  recorded-bridge fixture exercises it for resumed and spawned sessions
  (NFR-SEC-02 acceptance: A-request → B-session ⇒ mismatch, zero bytes).
- The guard composes with the one-in-flight lock (ADR-001) and the
  read-only gate (ADR-003): bind, then lock, then act, then stream.
