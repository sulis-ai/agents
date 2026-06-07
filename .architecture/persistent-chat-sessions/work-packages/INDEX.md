# Work Packages — persistent-chat-sessions · Phase 1

> **Change:** CH-01KTAD · persistent-chat-sessions
> **Source design:** [`../contracts/SESSION_MANAGER_CONTRACT.md`](../contracts/SESSION_MANAGER_CONTRACT.md) · [`../adrs/ADR-001-provider-neutral-foundation-session-manager.md`](../adrs/ADR-001-provider-neutral-foundation-session-manager.md)
> **Effective primitive:** CREATE (a new provider-neutral foundation capability), not a refactor of the cockpit bridge.
> **Tier (right-sizing):** M — sFPC ≈ 11 (3 ILF + 1 EIF + 7 ops), ASR ≈ 10. Single bounded module; no existing coverage to reference, so Form/Armor/Proof each get full treatment.

---

## Module home (decided, justified)

The manager lives as a **subpackage** at `plugins/sulis/scripts/_session_manager/`,
mirroring the existing `_discovery/` foundation subpackage (`__init__.py` +
focused sub-modules, tests under `plugins/sulis/scripts/tests/`, imported via
the package name with `_SCRIPTS_DIR` on `sys.path` per `tests/conftest.py`).
This is the repo's established convention for a multi-file Python foundation
capability (CP-01 priority 0 — internal prior art). The CLI driver lands as
`plugins/sulis/scripts/sulis_session.py`, mirroring the existing
`sulis_list_changes.py` entrypoint convention.

The dunder-prefix (`_session_manager`) marks it as foundation-internal, exactly
as `_discovery`, `_canonical_drift` do. Public surface is the `SessionManager`
class and the `ProviderAdapter` Protocol re-exported from the package
`__init__.py`.

---

## Dependency graph

```
WP-001  event-log + cursor semantics        (Form spine — depends on nothing)
   │
   ├──▶ WP-002  event vocabulary types        (Form — depends on nothing; can run parallel to WP-001)
   │
WP-003  ProviderAdapter Protocol + Claude adapter   (Form seam — depends on WP-002)
   │
WP-004  SessionManager core surface (open/send/read/health/status/close,
   │            single warm process, one-in-flight queue)   (depends on WP-001, WP-002, WP-003)
   │
   ├──▶ WP-005  state machine + restart-on-death + resume-as-capability  (Armor — depends on WP-004)
   ├──▶ WP-006  idle-eviction + LRU memory-cap + dead-process detection   (Armor — depends on WP-004)
   └──▶ WP-007  runaway / timeout guards + error-event surfacing          (Armor — depends on WP-004, WP-005)
            │
WP-008  contract-stub fixtures + contract-test harness   (Proof — depends on WP-003; tests grow as WP-004..007 land)
   │
WP-009  minimal real CLI driver + observed-done gate      (observability cap — depends on WP-004; full set when WP-005..007 land)
```

### Parallelisable vs sequential

| Wave | Runs in parallel | Gate before next wave |
|---|---|---|
| 1 | **WP-001**, **WP-002** | both green (the Form spine + types) |
| 2 | **WP-003** | green (the only Form seam; needs WP-002 types) |
| 3 | **WP-004** | green (the core surface; needs 001/002/003) |
| 4 | **WP-005**, **WP-006**, **WP-007** in parallel | all three green (independent Armor primitives over the same core; 007 wants 005's state machine but can stub it) |
| 5 | **WP-008**, **WP-009** in parallel | both green — **WP-009 is the observed-done gate for the whole phase** |

WP-005/006/007 touch the same `SessionManager` but in **separate concerns**
(lifecycle/recovery vs eviction vs guards); they are written as separate
collaborators the manager composes, so they merge without conflict if each
keeps to its own module file. If the executor finds they fight over the same
maintenance loop, serialise 006 after 005.

**Liveness ownership (decomposition fork resolved):** the `is_alive(session)`
liveness primitive is **owned and exposed by WP-004** — it backs `health(key)`
and `status()`, so it is intrinsically a WP-004 concern, not a shared primitive
discovered later. WP-005 (restart-on-death detection) and WP-006 (dead-process
detection in the maintenance tick) both **consume** `is_alive` from WP-004
unchanged. There is no separate liveness WP (no WP-004b), and there is no
"whoever lands first owns it" handshake between 005 and 006 — both depend on
WP-004 already, so the wave-4 parallelism (WP-005 ∥ WP-006 ∥ WP-007) is
preserved with no shared-primitive coordination.

---

## WP list

| WP | Purpose (one line) | `kind:` | Primitive | Depends on |
|---|---|---|---|---|
| [WP-001](WP-001-event-log-cursor.md) | Append-only, offset-addressed per-session event log with `since`/`follow`/history + `OFFSET_EVICTED` | backend | EXPAND-Create | — |
| [WP-002](WP-002-event-vocabulary.md) | Shared provider-neutral event types (`chunk`/`tool_use`/`result`/`error`) + three-category errors | backend | EXPAND-Create | — |
| [WP-003](WP-003-provider-adapter-claude.md) | `ProviderAdapter` Protocol + Claude adapter #1 (spawn_argv/encode/decode/turn_complete/capabilities) | backend | EXPAND-Create | WP-002 |
| [WP-004](WP-004-manager-core-surface.md) | `SessionManager` six-method surface; warm process per key; one-in-flight FIFO queue; decoupled send/read | backend | EXPAND-Create | WP-001, WP-002, WP-003 |
| [WP-005](WP-005-state-machine-restart-resume.md) | Session state machine + restart-on-death + resume-as-capability (honest `resumed`) | backend | EXPAND-Create | WP-004 |
| [WP-006](WP-006-eviction-memory-cap.md) | Idle-eviction + LRU memory-cap + dead-process detection (maintenance loop) | backend | EXPAND-Create | WP-004 |
| [WP-007](WP-007-runaway-timeout-guards.md) | Runaway / timeout turn guards → terminal states + surfaced `error` events | backend | EXPAND-Create | WP-004, WP-005 |
| [WP-008](WP-008-contract-stubs-harness.md) | The §2.10 recorded-NDJSON stub set + Python contract-test harness | backend | REINFORCE-Test | WP-003 |
| [WP-009](WP-009-cli-driver-observed-done.md) | Minimal real CLI driver (open→send→read --follow→close vs real `claude`) — the observed-done gate | backend | EXPAND-Create | WP-004 |

---

## Phase 2 — deferred (captured, NOT decomposed now)

Per the founder's phasing decision (Working Set log, 2026-06-05T12:24:53Z):
**Phase 1 = the in-process core + CLI driver only.** The following are real,
designed, and out of Phase-1 scope — they are not lost, they are the next slice:

- **The Unix-domain-socket NDJSON server** (the cross-process binding) —
  contract §2.8.1/§2.8.2. The in-process library binding (this phase) is the
  prerequisite; the socket server wraps the same `SessionManager` instance.
- **The cockpit migration** — `SessionBridge.ts` production adapter changes
  from "spawn `claude` directly" to a socket client; `runSessionBridgeContract`
  runs against it; binding guard + in-flight lock compose (contract §2.8.3).
- **Consequence acknowledged:** the cockpit chat keeps its 40–60s per-message
  lag until Phase 2 lands. Phase 1 delivers the foundation and proves it
  end-to-end via the CLI, but does not touch the cockpit.

The interface (contract §2.8) is locked for both, so Phase 2 is additive — no
re-design of Phase-1 artifacts.

### Decided-by-default tuning (applied in Phase-1 WPs; do not re-open)

- **Log retention** = retain the whole live session (WP-001). `OFFSET_EVICTED`
  exists but is not hit under the default; it is proven via a forced-cap test.
- **Memory cap** = derive from host RAM with a conservative floor (WP-006).
- **Socket path / lifecycle** = Phase 2 concern.

---

## Verification posture (verification-by-design)

- WP-001..007 ship their own unit + integration tests in Red (real threaded
  in-process behaviour, no mocks of the manager's own state — MEA-09).
- WP-008 holds the **contract** stubs that prove the §2.10 scenarios against the
  real manager; it is the cross-WP conformance gate.
- WP-009 is the **observed-done** gate: the phase is not done when units are
  green — it is done when a human (or CI driving real `claude`) has watched
  `open → send → read --follow → close` stream a live turn end-to-end. That
  observation is the phase-exit evidence.
