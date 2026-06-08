---
id: WP-005
title: Session state machine + restart-on-death + resume-as-capability
kind: backend
primitive: EXPAND-Create
group: expand
status: ready
dependsOn: [WP-004]
estimated_token_cost: { input: ~16k, output: ~13k }
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/integration/test_session_restart_resume.py"
---

## Context

Contract §2.7 (resume-as-capability + the internal state machine). This is the
**Armor** primitive for process lifecycle: the manager owns the state machine
(consumers never touch it), restarts a dead process, and resumes prior context
*only where the provider's capability allows* — with an honest `resumed` flag
(mirrors the cockpit's FR-26 honesty: never synthesise continuity a provider
can't give).

Adapted from AE `claude_session.py` `SessionState` + `attempt_recovery`, re-shaped
onto the keyed event-log model and given the tests AE never had (ADR-001).

Module: `plugins/sulis/scripts/_session_manager/lifecycle.py`, attaching to the
`_on_process_death` hook WP-004 exposes. State enum in `_session_manager/state.py`.

## Contract

State machine exactly per §2.7:

```
INITIALIZING → READY → EXECUTING → READY            (normal turn cycle)
                 │         ├→ ERROR → attempt_recovery → READY | TERMINATED_*
                 │         ├→ TERMINATED_TIMEOUT       (WP-007)
                 │         └→ TERMINATED_RUNAWAY       (WP-007)
                 └→ DEAD → restart-on-death (+resume) → INITIALIZING
                              └→ PERMANENTLY_DISABLED  (recovery exhausted)
```

- **restart-on-death:** process exits unexpectedly → manager restarts it; the
  **same key, same event log continues** (restart is not a new key). Where
  `adapter.capabilities.supports_resume`, the restart resumes from transcript so
  the conversation survives the crash.
- **resume-as-capability (§2.7):** on first `open`, resume from `spec.resume_ref`
  iff `capabilities.supports_resume`. Otherwise start fresh; `Session.resumed`
  is `False` and the consumer is told honestly.
- **recovery budget:** a finite restart budget per session; exhaustion →
  `PERMANENTLY_DISABLED`; subsequent `send` → `ExpectedError("SESSION_DISABLED")`.
- A death mid-turn surfaces an `error` Event into the log before/around the
  restart (so a `read(follow=True)` sees the failure, then the continuation).

## Definition of Done

### Red (failing tests first)
Integration tests with a **real child process the test can kill** (e.g. a scripted
python child that emits NDJSON then can be SIGKILLed on cue). No mocked death.
- `test_open_resumes_when_capability_true` — adapter with `supports_resume=True` + `resume_ref` → `Session.resumed is True`, resume flag in argv.
- `test_open_starts_fresh_when_capability_false` — adapter with `supports_resume=False` + `resume_ref` set → starts fresh, `Session.resumed is False` (honest, §2.7).
- `test_open_no_resume_ref_starts_fresh` — no `resume_ref` → fresh, `resumed False`.
- `test_process_death_restarts_same_key_same_log` — kill the child mid-session; manager restarts; the **log offset keeps climbing** (not reset); a `read(since=0)` still has the pre-death events (proves §2.7 restart-is-not-new-key).
- `test_death_mid_turn_surfaces_error_then_continues` — kill mid-turn; an `error` Event appears in the log, then the restarted turn/continuation (proves the §2.7 death+restart stub scenario, contract §2.10 #6).
- `test_restart_resumes_context_when_capable` — after restart with a resume-capable adapter, the resumed process is spawned with the resume flag.
- `test_recovery_budget_exhaustion_disables` — force N consecutive deaths past budget → state `PERMANENTLY_DISABLED`; next `send` → `SESSION_DISABLED`.
- `test_state_transitions_follow_machine` — assert the legal transitions; an illegal transition is rejected (the machine is enforced, not advisory).

### Green
- Implement the state enum + a transition guard (explicit allowed-transitions map
  — boring, no implicit state). Wire `_on_process_death` to: detect → DEAD →
  restart (resume if capable) → INITIALIZING → READY, decrementing the budget.
- Honest `resumed` set at first `open` from `capabilities.supports_resume AND resume_ref`.

### Blue (refactor)
- The transition-guard map is the single source of legality — confirm WP-007 adds
  its TERMINATED_* transitions to the same map, not a parallel one.
- Dead-process *detection* consumes WP-004's `is_alive(session)` primitive
  directly — do not re-implement the poll here. This WP owns *recovery*
  (DEAD → restart → resume); WP-004 owns *liveness*; WP-006 owns the
  *maintenance tick* that calls liveness and fires `_on_process_death`.

## Notes
- §2.7 names AE `is_healthy`/`attempt_recovery` as the adapted source — adapt the
  mechanism, add the tests.
- Liveness detection (`is_alive`) is owned and exposed by WP-004 (it backs
  `health`/`status`); this WP consumes it. No shared-primitive handshake with
  WP-006 is needed — both consume the same WP-004 primitive.
