# Work Packages — automation-reliability-recovery

> **Change:** CH-01KTMK · `feat` · change_id `01KTMKAZDV03Z12AT0VAH5BH3T`
> **Source:** `.architecture/automation-reliability-recovery/TDD.md` (status: designed)
> **Kind:** all `backend` except WP-001 (`contract`). `founder_facing: false`.
> **Decomposition:** contract-first (CONTRACT_FIRST WP-08.5) — the data
> contract WP comes first; the classifier, policy, and adapter-seam consumers
> depend on it and build in parallel.
>
> Derived file — do not hand-edit.

## ▶ Ready to start (4)

- **WP-001** — Reliability-layer data contract: RecoveryClass + RetryPolicy shape   (contract, 2h)
- **WP-002** — Provider-neutral classifier: EventError → RecoveryClass             (backend, 3h) └─ dependsOn WP-001
- **WP-003** — Retry policy: RetryPolicy + next_delay backoff curve                (backend, 3h) └─ dependsOn WP-001
- **WP-004** — Adapter seam extension: classify_failure + reauth on the Protocol   (backend, 3h) └─ dependsOn WP-001

> WP-001 is the only thing truly ready *now*. The moment it merges, **WP-002,
> WP-003, WP-004 all unblock at once and run fully in parallel** (three
> independent consumers of the contract — no cross-dependency between them).

## ⏸ Blocked — unblock as dependencies close (4)

- **WP-005** — RecoveryDriver: retry / abandon / pause→resume                      (backend, 8h) └─ waiting on WP-002, WP-003, WP-004
- **WP-006** — Claude provider detection + re-auth                                 (backend, 4h) └─ waiting on WP-004
- **WP-007** — Manager wiring: construct driver + error-observation hook           (backend, 4h) └─ waiting on WP-005, WP-006
- **WP-008** — Observability + end-to-end recovery integration test                (backend, 4h) └─ waiting on WP-007

## 🔄 In progress (0)
## 💤 Sleeping (0)
## ✅ Done — awaiting loop-close (0)
## 🔒 Closed (0)

---

## Dependency graph

```
                 WP-001  (contract — RecoveryClass + RetryPolicy shape)
                /   |   \
               /    |    \
          WP-002  WP-003  WP-004        ← parallel after WP-001
        (classifier)(policy)(adapter seam)
               \    |      |  \
                \   |      |   \
                 \  |      |    WP-006  (Claude detection + reauth) ← parallel with WP-005
                  \ |      |   /          (only needs WP-004)
                   WP-005 ─┘  /
              (RecoveryDriver — needs classifier + policy + adapter seam)
                       \     /
                        WP-007  (manager wiring + hook)
                          |
                        WP-008  (observability / e2e integration test)
```

## Critical path

`WP-001 → {WP-004} → WP-006` and `WP-001 → {WP-002, WP-003, WP-004} → WP-005`
both feed **WP-007 → WP-008**. The longest chain is
**WP-001 → WP-002/003/004 → WP-005 → WP-007 → WP-008** ≈ 2 + 3 + 8 + 4 + 4 =
**21h of sequential work** if a single engineer runs it; with the parallel
fan-out after WP-001 the wall-clock floor is lower (WP-006 runs alongside
WP-005, the three contract consumers run together).

## Parallelism summary

| Wave | WPs runnable together | Gate to enter |
|---|---|---|
| 1 | WP-001 | — |
| 2 | WP-002, WP-003, WP-004 | WP-001 merged |
| 3 | WP-005, WP-006 | WP-005 ← {002,003,004}; WP-006 ← {004} |
| 4 | WP-007 | WP-005 + WP-006 merged |
| 5 | WP-008 | WP-007 merged |

## Verification frontmatter shapes (verification-standard ADR-003)

- **Concrete** (`adapter: backend` + named `artifact:`): WP-001..008 — every WP
  ships its own test the moment it lands.
- **Deferred** (`deferred-to-follow-on: live-reauth-resume-claude`): the **real**
  login-expiry → re-auth → resume round-trip against a live `claude` with a
  genuinely expired credential. Manual, on the founder machine — cannot
  bootstrap in CI (ARCH.yaml `deferred_needs`; TDD §4.3). WP-006 and WP-008
  cover the *logic* concretely against the fake ticket; only the live
  round-trip is deferred.

## Notes on test paths

The TDD's Verification Plan names test artifacts under a `tests/session_manager/`
path; the **real** repo convention is `plugins/sulis/scripts/tests/{unit,integration}/test_session_manager_*.py`
(confirmed against the existing suite — `test_session_manager_core.py`,
`test_session_manager_contract.py`, `test_session_manager_host.py`). The WP
`artifact:` fields use the real convention so the executor can pin them in CI.
This is a path concretion, not a design change.

All eight WPs are `EXPAND-Create` / additive `EXPAND-Extend` / `REINFORCE-Test`
— none is a REORGANISE-Refactor, so none carries a characterisation test in Red
(TDD §5; EP-07). The regression guard for the one live-file change (WP-007
`manager.py`) is the existing session-manager suite staying green.
