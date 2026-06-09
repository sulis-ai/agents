"""WP-003 — tests for the ``next_delay`` full-jitter backoff curve.

Contract: ``.architecture/automation-reliability-recovery/contracts/\
reliability-layer.contract.md`` (``next_delay`` stub table) + ADR-002 (the
injected ``RetryPolicy`` value object, full-jitter exponential backoff,
wall-clock budget).

``next_delay`` is a **pure function** (the second producer in the WP-001
contract, parallel to and independent of the classifier): given an attempt
index, the cumulative elapsed wall-clock seconds, and the injected policy, it
returns the jittered delay before the next attempt — or ``None`` when the next
attempt would push cumulative elapsed past ``policy.total_budget_seconds``
(budget exhausted → the driver reclassifies ``TRANSIENT_BLIP`` → ``DEAD_END``).

Full jitter (the AWS convention, CP-01):
``random_between(0, min(max_delay, base * multiplier ** attempt))`` — the
upper bound is exactly the jitter-free ceiling WP-001 already pins as
``next_delay_ceiling`` (one source of truth for the curve; the contract's stub
table asserts against it).

Verification posture (ADR-002 + WP prose): the RNG is **injectable** so the
tests seed it for repeatable delays; the clock is **not** this function's
concern (``elapsed_seconds`` is passed in by the driver). **No real
``time.sleep`` is reachable** — the function is pure arithmetic over an
injected ``rng`` callable. The stub-table rows are consumed from the shared
``_recovery_contract_fixtures.NEXT_DELAY_STUBS`` (CF-04 one source of truth),
so the bounds the policy is asserted against are the same examples the WP-001
contract test pins.
"""

from __future__ import annotations

import random

import pytest

from _session_manager import DEFAULT_RETRY_POLICY, RetryPolicy, next_delay

from tests.unit._recovery_contract_fixtures import NEXT_DELAY_STUBS, NextDelayCase


# ── full-jitter bounds at the contracted attempts (stub table) ────────────


@pytest.mark.parametrize(
    "case",
    [c for c in NEXT_DELAY_STUBS if c.expected_ceiling is not None],
    ids=lambda c: f"attempt={c.attempt},elapsed={c.elapsed_seconds}",
)
def test_jitter_bounds_at_attempts(case: NextDelayCase):
    """For every non-exhausted stub row, ``next_delay`` returns a float in
    ``[0, ceiling]`` where ``ceiling = min(max_delay, base*mult**attempt)`` —
    attempts 0 → [0,1], 3 → [0,8], 10 → [0,60]. Full jitter samples the whole
    band, so we sweep many seeds and assert every draw stays in bounds and the
    band is actually exercised (min near 0, max near the ceiling)."""
    assert case.expected_ceiling is not None  # narrows for the type checker
    ceiling = case.expected_ceiling
    draws: list[float] = []
    for seed in range(500):
        rng = random.Random(seed).random
        delay = next_delay(
            case.attempt,
            case.elapsed_seconds,
            DEFAULT_RETRY_POLICY,
            rng=rng,
        )
        assert delay is not None
        assert isinstance(delay, float)
        assert 0.0 <= delay <= ceiling, (
            f"attempt={case.attempt}: delay {delay} outside [0, {ceiling}]"
        )
        draws.append(delay)
    # Full jitter means the band is genuinely sampled, not pinned to one end.
    assert min(draws) < ceiling * 0.1
    assert max(draws) > ceiling * 0.9


# ── budget exhaustion → None (the give-up signal) ─────────────────────────


def test_budget_exhaustion_returns_none():
    """When ``elapsed_seconds`` has reached the wall-clock budget, the next
    attempt is over-budget and ``next_delay`` returns ``None`` — the driver's
    signal to reclassify ``TRANSIENT_BLIP`` → ``DEAD_END`` and abandon (the
    contract's ``elapsed 720 → None`` row)."""
    exhausted = next(c for c in NEXT_DELAY_STUBS if c.expected_ceiling is None)
    result = next_delay(
        exhausted.attempt,
        exhausted.elapsed_seconds,
        DEFAULT_RETRY_POLICY,
        rng=random.Random(0).random,
    )
    assert result is None

    # Past the budget is also None (the budget is a wall-clock cap, not a
    # single point), and exactly at the budget is None (the *next* attempt
    # would exceed it).
    assert (
        next_delay(0, 720.0, DEFAULT_RETRY_POLICY, rng=random.Random(0).random) is None
    )
    assert (
        next_delay(5, 10_000.0, DEFAULT_RETRY_POLICY, rng=random.Random(0).random)
        is None
    )


# ── determinism under a fixed seed; no real sleeping ──────────────────────


def test_seeded_rng_deterministic():
    """A seeded RNG produces repeatable delays — same seed, same delay — so
    the backoff curve is fully testable without any real ``time.sleep``
    (ADR-002: tests inject the RNG; the clock is the driver's concern)."""
    delay_a = next_delay(3, 10.0, DEFAULT_RETRY_POLICY, rng=random.Random(42).random)
    delay_b = next_delay(3, 10.0, DEFAULT_RETRY_POLICY, rng=random.Random(42).random)
    assert delay_a == delay_b

    # A different seed gives a different draw (the jitter is real, not a stub).
    delay_c = next_delay(3, 10.0, DEFAULT_RETRY_POLICY, rng=random.Random(7).random)
    assert delay_c != delay_a

    # The injected rng is what's sampled: a fake returning a constant fraction
    # yields exactly fraction * ceiling — proving the jitter is
    # random_between(0, ceiling) and nothing sleeps.
    def half() -> float:
        return 0.5

    # attempt 3 ceiling = min(60, 1*2**3) = 8 → 0.5 * 8 = 4.0
    assert next_delay(3, 10.0, DEFAULT_RETRY_POLICY, rng=half) == pytest.approx(4.0)

    def zero() -> float:
        return 0.0

    assert next_delay(3, 10.0, DEFAULT_RETRY_POLICY, rng=zero) == 0.0


def test_default_rng_is_module_random_when_unset():
    """The RNG defaults to ``random.random`` (the boring default, CP-01) so
    callers that don't care about determinism get real jitter without wiring
    anything — only the tests inject a seeded source."""
    # Called with no rng kwarg: still in bounds for the first step (ceiling 1).
    for _ in range(200):
        delay = next_delay(0, 0.0, DEFAULT_RETRY_POLICY)
        assert delay is not None
        assert 0.0 <= delay <= 1.0


def test_custom_policy_band_is_respected():
    """A non-default injected policy is honoured (the policy is the source of
    the curve, not a literal in the function) — a tiny-budget, tiny-ceiling
    policy bounds the draw accordingly."""
    tiny = RetryPolicy(
        base_delay_seconds=0.5,
        max_delay_seconds=4.0,
        multiplier=2.0,
        jitter="full",
        total_budget_seconds=30.0,
    )
    # attempt 2 ceiling = min(4, 0.5*2**2) = min(4, 2) = 2.0
    for seed in range(200):
        delay = next_delay(2, 5.0, tiny, rng=random.Random(seed).random)
        assert delay is not None
        assert 0.0 <= delay <= 2.0
    # over the tiny budget → None
    assert next_delay(0, 30.0, tiny) is None
