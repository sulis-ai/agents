---
founder_facing: false
---
# Spec — Provider-neutral reliability layer for unattended automation

**Change:** CH-01KTMK · feat
**Opportunity:** dna:opportunity:RD0MNJ3JHSER2SZVA4WA5B9PKT
**Critical-thinking trace:** 01KTMJGQF2QEDZB7026AN3CZW1

## Intent

When unattended automation hits a transient API failure today, the session
simply stops — a human has to notice and restart it. This change adds a
reliability layer that keeps unattended runs alive across the failures that
are survivable, fails cleanly on the ones that aren't, and pauses-then-resumes
across an expired login. It is **provider-neutral**: the classification and
recovery logic is shared, and only thin per-provider detection + re-auth lives
behind the existing session-manager adapter seam.

The layer observes the session manager's existing structured error stream
(`_session_manager/events.py` — `Event` kind="error", `EventError`, the
`ErrorCategory` model and error-code constants) and classifies each stoppage
into one of three recovery classes:

| Class | What it means | What the layer does |
|---|---|---|
| **transient-blip** | A momentary, self-clearing failure (rate-limit, brief network/API wobble, socket reset) | Retry with exponential backoff + jitter, up to a ~10–15 min budget, then escalate to dead-end |
| **dead-end** | An unrecoverable failure (bad request, unknown provider, cwd missing, decode failure, retry budget exhausted) | Abandon the run cleanly with a typed, observable failure |
| **login-expired** | Provider auth has lapsed (maps to the existing `NOT_AUTHORIZED` signal) | Pause the run, notify with a re-login link, and resume from where it paused once re-auth succeeds |

## Scope

- A shared, provider-neutral **classifier** that maps an observed error event
  to one of the three recovery classes.
- A **retry policy**: exponential backoff with jitter, capped at a
  ~10–15-minute total budget (the agreed "persistent" default), after which a
  transient-blip is reclassified dead-end and abandoned.
- A **pause / resume** path for login-expired: pause the in-flight run, emit a
  notification carrying a re-login link, and resume the paused run after
  re-auth without losing the run's place.
- A **thin per-provider seam** behind the existing `ProviderAdapter`
  (`_session_manager/adapter.py`): per-provider *detection* (which raw failure
  is a login-expiry vs a transient blip vs a dead-end) and *re-auth* trigger.
  Implement the **Claude** provider now (existing `adapters/claude.py` /
  `adapters/claude_pty.py`); keep the seam provider-neutral so a second
  provider needs only a new thin adapter, not changes to the shared layer.
- Observe the **existing** structured error stream — do not invent a new error
  channel.

## Non-goals

- **No new durable store.** Durable storage of paused-run state / messages
  defers to the platform's existing messages store. We persist *through* it,
  not alongside it.
- **No new error stream.** We consume the session manager's existing event
  model; we don't add a parallel one.
- **No new notification surface.** The re-login notification rides the
  platform's existing message/event surfacing; this change emits the
  notification, it does not design a new screen for it.
- **No multi-provider implementation beyond the seam.** Only Claude is wired
  now; other providers are a future thin-adapter add, out of scope here.
- **No change to what counts as "turn complete"** or the one-in-flight slot
  semantics — the layer sits around the existing lifecycle, not inside it.

## Acceptance

- A simulated transient failure (e.g. rate-limit / socket reset) on an
  unattended run is retried with exponential backoff and the run **survives**
  once the underlying condition clears — no human restart.
- A transient failure that never clears is retried until the ~10–15 min budget
  is exhausted, then **abandoned as a dead-end** with a typed, observable
  failure event (not a silent hang).
- A dead-end failure (e.g. bad request / unknown provider / cwd missing) is
  **abandoned immediately** without burning the retry budget.
- An expired login is detected, the run is **paused** (not failed), a
  notification carrying a re-login link is emitted, and after re-auth the run
  **resumes from where it paused**.
- Every classification and recovery action is **observable in the existing
  error/event stream** — a later reviewer can see why a run was retried,
  abandoned, or paused.
- The classifier + retry policy are **provider-neutral** (covered by tests
  that don't depend on the Claude adapter); only detection + re-auth are
  exercised per-provider.

## Constraints

- Build behind the **existing** `ProviderAdapter` seam
  (`_session_manager/adapter.py` + `adapters/`); do not fork or widen it more
  than the thin detection + re-auth additions require.
- Consume the **existing** event model in `_session_manager/events.py`
  (reuse the error-code constants and `ErrorCategory`; login-expiry maps to
  `NOT_AUTHORIZED`). Add a new error/recovery code only where no existing one
  fits, following the file's stated convention.
- Backoff uses the **established convention**: exponential backoff with jitter,
  bounded retries, capped total budget (CP-01 — boring and well-understood).
- Conform to the autonomous-delivery-environment design already in the repo
  (`.architecture/autonomous-delivery-environment/` — TDD, ADRs, contracts);
  respect ADR-002 (session-bridge resume/spawn) for the resume path.
- The retry budget is a **persistent ~10–15 min default**; structure it so it
  can later become a per-run / per-provider setting without a redesign.
- Must not change existing turn-complete semantics or the one-in-flight slot.

## Notes

- `founder_facing: false` — this is a backend reliability layer. The
  login-expired notification surfaces to the operator, but via the platform's
  existing message surface; no new user-facing screen is designed here.
- Linked opportunity / critical-thinking trace are recorded for provenance;
  they were authored in the founder's session context (not present in this
  repo's brain store).
