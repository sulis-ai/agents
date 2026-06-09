# ADR-004 — Login-expired pause→notify→resume reuses ADE ADR-002 resume and the existing message surface

- **Status:** accepted
- **Date:** 2026-06-08
- **Change:** CH-01KTMK · automation-reliability-recovery
- **Deciders:** SEA

## Context

For a login-expired stoppage the layer must: pause the in-flight run (not
fail it), emit a notification carrying a re-login link, and **resume from
where it paused** after re-auth — without losing the run's place. The spec
mandates: reuse ADE ADR-002's resume path (do not invent a parallel
resume); ride the platform's existing message/event surface for the
notification (no new screen, no new error stream); persist *through* the
existing store (no new durable store).

The existing facts:

- **Resume already exists, twice.** ADE ADR-002 defines the cockpit
  `SessionBridge` resolve-then-deliver resume (resume from the persisted
  transcript, re-run an incomplete step, never fabricate completion). The
  session-manager has the lower-level half: `LifecycleManager` restarts a
  dead process reusing the **same key + same log**, with resume honoured
  iff `adapter.capabilities.supports_resume` and a `resume_ref` exists
  (`manager._respawn` → `Session.replace_process`). Both share one rule:
  **restart-is-not-a-new-key** — the conversation/log survives.
- **The log is the persistence.** Paused-run state is *the existing event
  log plus the persisted transcript* the resume path already reads. There
  is nothing new to store.
- **The state machine** has no "paused" state today; it has READY /
  EXECUTING / ERROR / DEAD / TERMINATED_* / PERMANENTLY_DISABLED.

## Decision

**Model login-expired as a pause that surfaces an `error` Event
(`NOT_AUTHORIZED`) into the existing log, freezes recovery for that
session until a re-auth confirmation arrives, then resumes via the
*existing* resume path — `supports_resume` + the same-key/same-log
restart that `LifecycleManager`/`_respawn` already implement (the
session-manager half of ADE ADR-002).** No parallel resume, no new store,
no new surface.

Flow (all observable in the existing stream):

1. Classifier → `LOGIN_EXPIRED` (ADR-003).
2. RecoveryDriver appends an `error` Event with the existing
   `NOT_AUTHORIZED` code and a message carrying the re-login link obtained
   from `adapter.reauth()`. **This Event is the notification** — it rides
   the message/event surface the cockpit already renders (ADE ADR-005,
   ADR-003: the chat/event stream is the one coherent surface). The
   operator sees "login expired — re-login here" through the same channel
   they already read; no new screen is designed (spec non-goal honoured).
3. The driver **pauses** the run: it stops the retry loop for this session
   (it is *not* a transient blip — burning the budget would be wrong) and
   waits on a re-auth confirmation signal. The one-in-flight slot is
   released normally by the failed turn (existing semantics untouched);
   the *run* is paused at the driver level, not the lifecycle level.
4. On re-auth confirmation (the `reauth()` ticket completing), the driver
   **resumes** using the existing path: the next turn re-opens/continues
   the same-key session with `resume_ref` set, so the agent wakes with
   full memory and **re-runs the incomplete step** rather than reporting
   it done (ADE ADR-002 / FR-26 / NFR-REL-04 — no fabricated completion).
5. A resume after re-auth emits a `result`/`chunk` stream exactly as a
   normal turn; the run continues from its place.

**Pause representation.** Rather than add a new `SessionState` (which
would touch the state machine the spec says not to disturb), pause is a
**driver-level** condition: the session sits in its normal post-error
state while the driver holds it out of the retry loop pending re-auth.
This keeps the enforced state machine (`state.py`) and turn-complete
semantics byte-unchanged (acceptance) — the pause is in the Armor layer
around the lifecycle (ADR-001), consistent with "around not inside".

## Alternatives considered

- **Add a `PAUSED` state to the session state machine (rejected).**
  Touches `state.py`'s single-source-of-legality map and risks the
  "must-not-change turn-complete / one-in-flight" guarantee. The pause is
  a recovery-layer concern (how long the *driver* waits before the next
  turn), not a lifecycle-legality concern. Keeping it in the driver
  honours ADR-001's "around not inside".
- **Invent a new resume mechanism for the paused run (rejected, spec
  forbids).** The same-key/same-log restart with `resume_ref` (the
  session-manager half of ADE ADR-002) already does exactly "wake with
  full memory, re-run the incomplete step". Reusing it is the only
  sanctioned path; a parallel resume would risk fabricated completion the
  existing path is specifically designed to avoid.
- **A new durable record of paused runs (rejected, non-goal).** The
  event log + persisted transcript already *are* the paused state — they
  survive across the re-auth wait because the session/key persists (and
  the daemon persists across windows per `DAEMON_CONTRACT.md`). No second
  store.
- **A dedicated re-login notification channel/screen (rejected,
  non-goal).** The notification is an `error` Event on the existing stream
  carrying the link; the cockpit's one coherent surface (ADE ADR-005)
  renders it. Designing a new surface is explicitly out of scope.

## Consequences

- The notification is an `error` Event with code `NOT_AUTHORIZED` plus a
  re-login link in its message/payload — no new Event kind, no new code,
  no new stream (ADR-003 + spec).
- Resume reuses `capabilities.supports_resume` + `resume_ref` +
  same-key/same-log restart — the existing path; the driver triggers it,
  it does not reimplement it.
- The re-auth confirmation is the `reauth()` ticket completing (ADR-003);
  how the operator completes re-login (clicking the link) is the
  platform's existing surface, outside this layer.
- No fabricated completion: resume hands the restored transcript to the
  agent and lets it re-run the incomplete step (ADE ADR-002 discipline,
  inherited not reimplemented).
- The state machine, turn-complete, and one-in-flight slot are unchanged
  (acceptance).
