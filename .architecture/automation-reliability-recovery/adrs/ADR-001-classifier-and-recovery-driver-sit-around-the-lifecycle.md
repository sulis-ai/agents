# ADR-001 — The classifier + recovery driver sit *around* the lifecycle, not inside it

- **Status:** accepted
- **Date:** 2026-06-08
- **Change:** CH-01KTMK · automation-reliability-recovery
- **Deciders:** SEA

## Context

The spec adds a reliability layer that observes the session manager's
structured error stream (`events.py`) and reacts to a stopped turn:
retry a transient blip, abandon a dead-end, pause/resume a login-expiry.
The question is **where** this logic attaches relative to the existing
`SessionManager` / `Session` / `LifecycleManager`.

The constraint (spec) is loud: *"the reliability layer sits AROUND the
lifecycle, not inside it"* and *"must not change existing turn-complete
semantics or the one-in-flight slot"*. There is already a precedent in
the codebase for exactly this shape: `lifecycle.py`'s `LifecycleManager`
handles **process death** by attaching to the manager's no-op
`_on_process_death` hook — recovery logic injected with the two
capabilities it needs (spawn-fresh, append-event), owning recovery while
the manager keeps owning the registry and the six-method surface.

## Decision

**Introduce a `RecoveryDriver` that mirrors `LifecycleManager`'s
around-the-core shape: it is the Armor primitive for *turn-level API
failure* exactly as `LifecycleManager` is the Armor primitive for
*process death*.** It attaches to the manager through the same kind of
injected-capability hook, observing each `error`-kind `Event` as it lands
in the log and driving recovery without touching `Session.submit`, the
FIFO queue, or `turn_complete`.

Concretely, the layer is three pieces with dependencies pointing inward:

```
events.py (Form invariant — unchanged)
   ▲
classifier.py   (pure domain: EventError → RecoveryClass; NO adapter dep)
   ▲
recovery.py     (RecoveryDriver: observes error events, applies policy,
                 drives retry / abandon / pause→resume via injected
                 manager capabilities — same shape as LifecycleManager)
   ▲
manager.py      (composition root — wires the driver to a hook, as it
                 already wires LifecycleManager to _on_process_death)
```

- **Classifier** is pure: `(category, code)` + an optional per-provider
  detection hint → one of three `RecoveryClass` values. It depends on
  `events.py` only (provider-neutral, ADR-003).
- **RecoveryDriver** consumes the manager's existing primitives — `read`
  (to observe the error), `send` (to re-submit a transient blip), the
  resume path (ADR-002 of ADE, reused for login-expired), and
  `log.append` (to surface every recovery action as an Event). It owns
  *recovery*; the manager keeps owning the lifecycle.
- **The hook.** The manager already exposes `_on_process_death`,
  `_maintenance_tick`, `_guard` as attach seams "so the wave-4 Armor WPs
  attach without editing the core flow". The recovery driver attaches at
  the **error-event observation seam** (a turn ending in an `error` Event
  that is not a process death) — the same architectural slot, a sibling
  to the death hook.

## Alternatives considered

- **Inline the retry inside `Session.submit` / the stdin pump
  (rejected).** Puts recovery policy in the hottest, most concurrency-
  sensitive code in the system, directly violating the spec's "around
  not inside" and "must not change one-in-flight semantics". The pump's
  job is to drain one turn; making it also own backoff timers and
  re-classification would tangle two concerns and make the policy
  untestable without a live subprocess.
- **A new top-level orchestrator that wraps `SessionManager`
  (rejected).** That is a SUBSTITUTE-Wrap over internal code — a
  Band-Aid wrapper the change-primitive walk forbids (step 4: REORGANISE
  before WRAP-over-internal). The manager already *has* the extension
  seams; using them is EXPAND-Create against an existing extension point,
  not a wrap.
- **Fold recovery into the existing `LifecycleManager` (rejected).**
  Process-death recovery and API-failure recovery are different triggers
  (EOF on a dead process vs an `error` Event on a live one) with
  different policies (immediate respawn within a small integer budget vs
  exponential backoff within a time budget). Merging them would overload
  one class with two state machines. They are siblings, not one thing —
  kept as separate modules attaching at separate seams.

## Consequences

- New files: `classifier.py` (pure), `recovery.py` (`RecoveryDriver` +
  the policy value object from ADR-002). The manager gains a wiring line
  and a hook, exactly as it gained one for `LifecycleManager`.
- The existing turn-complete / one-in-flight / state-machine code is
  **untouched** (acceptance: must-not-change). The driver's retry is a
  *new `send`*, which the FIFO queue already serialises — so a retry is
  just another turn, never a second in-flight turn.
- Every recovery action is an Event in the existing log (no new stream,
  ADR-004), so a later reviewer sees why a run was retried / abandoned /
  paused — straight from `read(follow=True)`.
- The around-the-core shape means a second provider needs no change here:
  the driver is provider-neutral (ADR-003); only the adapter's detection
  hint differs.
