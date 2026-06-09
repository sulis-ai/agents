# ADR-002 — The retry budget is an injected policy value object (persistent default, configurable later)

- **Status:** accepted
- **Date:** 2026-06-08
- **Change:** CH-01KTMK · automation-reliability-recovery
- **Deciders:** SEA (founder decision pre-made: policy = persistent)

## Context

The one founder decision already made: the retry/give-up policy is
**persistent** — exponential backoff with jitter, capped at a ~10–15-minute
total budget, after which a transient-blip is reclassified dead-end and
abandoned. The standing requirement: *structure the budget so it can later
become a per-run / per-provider setting without a redesign — don't hardcode
it unreachably.*

The codebase already shows the boring convention for exactly this: the
manager takes tuning values (`recovery_budget`, `idle_timeout`,
`memory_cap`, `turn_timeout`) as constructor kwargs with module-level
`DEFAULT_*` constants (`DEFAULT_RECOVERY_BUDGET = 3`,
`DEFAULT_TURN_TIMEOUT_SECONDS`), injected at the composition root. That is
the pattern to follow — not a new config system.

## Decision

**Represent the retry policy as a frozen `RetryPolicy` value object with a
module-level `DEFAULT_RETRY_POLICY` constant, injected into the
`RecoveryDriver` at construction — the same convention the manager already
uses for `recovery_budget` and the turn guards.** Backoff is the
established convention (CP-01): exponential base with full jitter, bounded
by a total wall-clock budget.

```
@dataclass(frozen=True)
class RetryPolicy:
    base_delay_seconds: float       # first backoff step
    max_delay_seconds: float        # per-step ceiling
    multiplier: float               # exponential base (e.g. 2.0)
    jitter: Literal["full", "none"] # full jitter (AWS convention), default "full"
    total_budget_seconds: float     # the ~10–15-min cap; exhaustion → dead-end

DEFAULT_RETRY_POLICY = RetryPolicy(
    base_delay_seconds=1.0, max_delay_seconds=60.0, multiplier=2.0,
    jitter="full", total_budget_seconds=720.0,   # 12 min — mid ~10–15
)
```

- **The budget is wall-clock, not attempt-count.** "~10–15 min total
  budget" is a time cap; attempts stop when the *next* backoff would push
  cumulative elapsed past `total_budget_seconds`. On exhaustion the driver
  reclassifies the run dead-end and abandons it with a typed, observable
  `error` Event (acceptance).
- **Full jitter** (the AWS Architecture Blog convention, CP-01): the actual
  sleep is `random_between(0, min(max_delay, base * multiplier**attempt))`.
  Boring and well-understood; prevents thundering-herd on a shared
  provider outage.
- **Made configurable later with zero redesign.** The driver reads its
  policy from the injected value object. To make it per-run or
  per-provider later, the composition root selects which `RetryPolicy` to
  inject (e.g. keyed by provider name, or carried on the `SessionSpec`) —
  the driver's contract does not change. The default constant is the
  *fallback*, not a hardcoded literal in the retry loop.

## Alternatives considered

- **Hardcode the numbers in the retry loop (rejected).** Directly violates
  the founder's "don't hardcode it unreachably" — making it per-run later
  would mean editing the loop. The value object externalises every knob.
- **A new config file / settings store (rejected).** No-new-store
  non-goal; over-engineered for one policy object. The injected-kwarg +
  `DEFAULT_*` convention already in `manager.py` is the established local
  pattern (CP-01 priority 0: internal prior art).
- **Attempt-count budget instead of time budget (rejected).** The founder
  decision is explicitly a *time* budget (~10–15 min). A fixed attempt
  count under exponential backoff gives an unpredictable wall-clock
  ceiling; the time budget is what "persistent for ~10–15 min" means.
- **Decorrelated jitter vs full jitter (full chosen).** Both are
  established AWS conventions. Full jitter is the simpler, more widely-
  cited default (CP-04: prefer the older/more boring). Decorrelated is a
  later tuning knob the value object can express without redesign.

## Consequences

- New: `RetryPolicy` frozen dataclass + `DEFAULT_RETRY_POLICY` constant,
  living with the `RecoveryDriver` (`recovery.py`).
- The driver takes `retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY` —
  mirrors `recovery_budget` injection. Tests inject a tiny-budget policy +
  a fake clock for deterministic, sleep-free verification (the maintenance
  tests' precedent).
- The path to per-run/per-provider is a composition-root selection, not a
  driver change — the redesign-free requirement is satisfied structurally.
- The wall-clock budget needs an injectable clock (a `now()` callable) so
  the budget test is deterministic; the driver takes `clock=time.monotonic`
  by default, a fake in tests (no real sleeping in CI).
