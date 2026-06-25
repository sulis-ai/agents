# Work Packages — Antigravity (`agy`) provider adapter (CH-M7WSQ4)

One atomic WP: the adapter, its additive registration, and its tests ship together.
The registration is inert without the adapter; the tests are the WP's own Red/Green
gates — not separable work. Deliberately not over-decomposed (tier S).

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Interactive agy pty adapter + additive provider registration | Create | done | — | — |

## Extra detail (non-canonical second table)

| ID | Group | Source TDD | Platform Contract | ADRs | Verification |
|---|---|---|---|---|---|
| WP-001 | expand | §Form/§Armor/§Proof | PC-001 | ADR-001/002/003 | concrete: `tests/unit/test_agy_pty_adapter.py`; deferred: `agy-real-session-driver-google` |
