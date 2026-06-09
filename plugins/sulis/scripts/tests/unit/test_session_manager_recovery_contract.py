"""WP-001 — tests for the reliability-layer data contract.

Contract: ``.architecture/automation-reliability-recovery/contracts/\
reliability-layer.contract.md`` + ADR-002 (RetryPolicy), ADR-003
(RecoveryClass + provider-neutral classification), ADR-004 (login-expired
re-auth ticket).

This is the producer/consumer seam at the heart of the reliability layer
(CONTRACT_FIRST CF-01): the classifier (WP-002) produces a ``RecoveryClass``
verdict; the recovery driver (WP-005) consumes it; the policy (WP-003)
produces a backoff delay. Pinning the vocabulary + value-object shapes here
lets every downstream WP be built and tested in parallel against one agreed
source — the verdict words are never re-spelled on either side (CF-11).

The contract's truth table (the classification examples, incl. the
unknown-code → dead-end fall-through) and the ``next_delay`` stub table live
in a single shared fixture module (``_recovery_contract_fixtures``) that the
classifier (WP-002) and policy (WP-003) test suites both import — one source
of truth for the examples (CF-04 happy + error + empty cases).

Verification posture: real value objects, no mocks — the contract is the
typed shapes themselves, asserted against the *existing* ``events.py`` value
objects (not re-declared codes).
"""

from __future__ import annotations

import dataclasses

import pytest

from _session_manager import (
    DEFAULT_RETRY_POLICY,
    ReauthTicket,
    RecoveryClass,
    RetryPolicy,
)
from _session_manager import events as ev
from _session_manager.recovery import next_delay_ceiling

from tests.unit._recovery_contract_fixtures import (
    CLASSIFICATION_TRUTH_TABLE,
    NEXT_DELAY_STUBS,
    ClassificationCase,
    NextDelayCase,
)


# ── RecoveryClass enum (ADR-003) ──────────────────────────────────────────


def test_recovery_class_values():
    """The neutral vocabulary is exactly the three contracted members."""
    assert {member.name for member in RecoveryClass} == {
        "TRANSIENT_BLIP",
        "DEAD_END",
        "LOGIN_EXPIRED",
    }
    # Members are referenceable as symbols (a typo becomes AttributeError).
    assert RecoveryClass.TRANSIENT_BLIP is not RecoveryClass.DEAD_END
    assert RecoveryClass.LOGIN_EXPIRED is not RecoveryClass.TRANSIENT_BLIP


def test_recovery_class_importable_from_package_and_classifier():
    """The vocabulary lives in classifier.py (ADR-003) and re-exports from
    the package so callers import from the package, not the sub-module."""
    from _session_manager.classifier import RecoveryClass as FromModule

    assert FromModule is RecoveryClass


# ── RetryPolicy + DEFAULT_RETRY_POLICY (ADR-002) ──────────────────────────


def test_retry_policy_is_frozen_dataclass_with_contracted_fields():
    """The six contracted knobs, frozen so the injected policy can't drift
    under the driver. ``max_lifetime_retries`` (CH-01KTMK hardening FIX 2) is the
    absolute, turn-clear-proof retry ceiling — a defaulted sixth knob added
    backward-compatibly alongside the original five."""
    assert dataclasses.is_dataclass(RetryPolicy)
    field_names = {f.name for f in dataclasses.fields(RetryPolicy)}
    assert field_names == {
        "base_delay_seconds",
        "max_delay_seconds",
        "multiplier",
        "jitter",
        "total_budget_seconds",
        "max_lifetime_retries",
    }
    # The new knob is DEFAULTED so existing constructions (the original five
    # positional/keyword knobs) keep working without passing it — backward
    # compatible (CH-01KTMK FIX 2 constraint).
    five_knob = RetryPolicy(
        base_delay_seconds=1.0,
        max_delay_seconds=60.0,
        multiplier=2.0,
        jitter="full",
        total_budget_seconds=720.0,
    )
    assert five_knob.max_lifetime_retries >= 1
    # Frozen: assignment raises.
    policy = RetryPolicy(
        base_delay_seconds=1.0,
        max_delay_seconds=60.0,
        multiplier=2.0,
        jitter="full",
        total_budget_seconds=720.0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.base_delay_seconds = 2.0  # type: ignore[misc]


def test_default_retry_policy_constants():
    """The ADR-002 defaults: base=1, max=60, mult=2, full jitter, 12-min
    budget (mid ~10-15)."""
    assert DEFAULT_RETRY_POLICY.base_delay_seconds == 1.0
    assert DEFAULT_RETRY_POLICY.max_delay_seconds == 60.0
    assert DEFAULT_RETRY_POLICY.multiplier == 2.0
    assert DEFAULT_RETRY_POLICY.jitter == "full"
    assert DEFAULT_RETRY_POLICY.total_budget_seconds == 720.0
    # CH-01KTMK FIX 2: the absolute lifetime retry ceiling — generous for
    # legitimate use, finite for a pathological alternating provider.
    assert DEFAULT_RETRY_POLICY.max_lifetime_retries == 200


# ── ReauthTicket value object (ADR-003/004) ───────────────────────────────


def test_reauth_ticket_shape():
    """The ticket carries the re-login link the notification surfaces plus a
    completion handle the driver waits on (ADR-003/004)."""
    assert dataclasses.is_dataclass(ReauthTicket)
    field_names = {f.name for f in dataclasses.fields(ReauthTicket)}
    assert field_names == {"relogin_link", "completion_handle"}

    ticket = ReauthTicket(
        relogin_link="https://example.test/relogin?token=abc",
        completion_handle="reauth-1",
    )
    assert ticket.relogin_link == "https://example.test/relogin?token=abc"
    assert ticket.completion_handle == "reauth-1"
    # Frozen value object.
    with pytest.raises(dataclasses.FrozenInstanceError):
        ticket.relogin_link = "x"  # type: ignore[misc]


# ── No new error code introduced (ADR-003 / contract) ─────────────────────


def test_vocabulary_does_not_redeclare_event_codes():
    """The reliability vocabulary references the existing events.py code
    constants; it must not redeclare any of them (ADR-003 — NOT_AUTHORIZED
    already carries login-expiry)."""
    import _session_manager.classifier as classifier
    import _session_manager.recovery as recovery

    event_codes = {
        ev.SPAWN_FAILED,
        ev.STDIN_BROKEN,
        ev.SOCKET_CLOSED,
        ev.NO_SESSION,
        ev.UNKNOWN_PROVIDER,
        ev.CWD_NOT_FOUND,
        ev.NOT_AUTHORIZED,
        ev.DECODE_FAILED,
        ev.LOG_CORRUPT,
    }
    for module in (classifier, recovery):
        for code in event_codes:
            # A module-level *assignment* of the same name to the same string
            # would be a redeclaration. The constant may appear in a fixture's
            # data, but the production modules must not own a new binding.
            owned = module.__dict__.get(code)
            assert owned is None or owned is getattr(ev, code, None), (
                f"{module.__name__} redeclares error code {code!r}; "
                "it must reference events.py, not own a copy"
            )


# ── Shared truth-table fixture (CF-04) ────────────────────────────────────


def test_truth_table_uses_real_event_codes_and_categories():
    """Every classification row is built from the *existing* events.py codes
    and the existing three-category vocabulary — not magic strings the shared
    layer invents (the raw-Claude rows are the provider-hint cases, where the
    hint, not the code, drives the verdict)."""
    valid_categories = {"protocol", "expected", "internal"}
    valid_verdicts = set(RecoveryClass)
    # The contract's truth table has 13 data rows (9 provider-neutral defaults
    # + 1 adapter-hint-wins + 3 raw-Claude hint rows). The WP prose rounds this
    # to "the 12-row truth table"; the contract document is authoritative.
    assert len(CLASSIFICATION_TRUTH_TABLE) == 13
    for case in CLASSIFICATION_TRUTH_TABLE:
        assert isinstance(case, ClassificationCase)
        assert case.category in valid_categories or case.category == "any"
        assert case.expected in valid_verdicts
        if case.adapter_hint is not None:
            assert case.adapter_hint in valid_verdicts


def test_truth_table_includes_unknown_code_dead_end_fall_through():
    """CF-04 non-happy case: the safe direction. Every neutral-default row
    (no adapter hint) that is not protocol-transient or NOT_AUTHORIZED-login
    classifies dead-end — including the deterministic-decline expected codes
    and the internal bugs."""
    neutral = [c for c in CLASSIFICATION_TRUTH_TABLE if c.adapter_hint is None]
    # protocol → transient-blip
    for c in (c for c in neutral if c.category == "protocol"):
        assert c.expected is RecoveryClass.TRANSIENT_BLIP
    # internal → dead-end (a bug; do not retry)
    for c in (c for c in neutral if c.category == "internal"):
        assert c.expected is RecoveryClass.DEAD_END
    # expected → dead-end EXCEPT NOT_AUTHORIZED → login-expired
    for c in (c for c in neutral if c.category == "expected"):
        if c.code == ev.NOT_AUTHORIZED:
            assert c.expected is RecoveryClass.LOGIN_EXPIRED
        else:
            assert c.expected is RecoveryClass.DEAD_END


def test_truth_table_adapter_hint_wins():
    """When the provider supplies a hint, the hint is the verdict (provider
    knows better) — the contract's 'adapter hint wins' row + the raw-Claude
    rows."""
    hinted = [c for c in CLASSIFICATION_TRUTH_TABLE if c.adapter_hint is not None]
    assert hinted, "truth table must include adapter-hint cases"
    for case in hinted:
        assert case.expected is case.adapter_hint


def test_next_delay_stub_table():
    """The backoff curve's contracted examples (ADR-002, full jitter): each
    step's ceiling is min(max_delay, base * multiplier**attempt); budget
    exhaustion yields None. The shared stub table is what WP-003 asserts the
    real next_delay against."""
    policy = DEFAULT_RETRY_POLICY
    assert len(NEXT_DELAY_STUBS) == 4
    for case in NEXT_DELAY_STUBS:
        assert isinstance(case, NextDelayCase)
        ceiling = next_delay_ceiling(case.attempt, case.elapsed_seconds, policy)
        if case.expected_ceiling is None:
            # Budget exhausted → the curve must signal None.
            assert ceiling is None
        else:
            assert ceiling == pytest.approx(case.expected_ceiling)
