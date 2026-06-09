"""Shared reliability-contract fixtures (WP-001 — CF-04 examples).

This module encodes the two example tables from
``.architecture/automation-reliability-recovery/contracts/\
reliability-layer.contract.md`` as plain Python data structures:

- :data:`CLASSIFICATION_TRUTH_TABLE` — the classifier truth table (13 rows:
  9 provider-neutral defaults + 1 adapter-hint-wins + 3 raw-Claude hint rows),
  incl. the unknown-code → dead-end fall-through (CF-04's non-happy case).
- :data:`NEXT_DELAY_STUBS` — the 4-row backoff-ceiling stub table for the
  ``DEFAULT_RETRY_POLICY`` curve, incl. the budget-exhausted → ``None`` row.

It is the **one source of truth** the downstream WP test suites consume: the
classifier suite (WP-002) asserts its real ``classify`` against
``CLASSIFICATION_TRUTH_TABLE``; the policy suite (WP-003) asserts its real
``next_delay`` against ``NEXT_DELAY_STUBS``. Pinning the examples once keeps
the verdict vocabulary from being re-spelled on either side of the seam
(CF-11), and is the "≥1 consumer fixture generated from the contract" gate
(WP-001 contract gate).

The classification codes reference the *existing* ``events.py`` constants
(``NOT_AUTHORIZED`` etc.) — never a redeclared copy. The raw-Claude rows
carry the provider's raw status string as ``code`` (``"401"``, ``"429"``,
``"400"``) together with the adapter hint that wins for them; those are the
cases the shared classifier cannot interpret without the provider hint.
"""

from __future__ import annotations

from dataclasses import dataclass

from _session_manager import events as ev
from _session_manager.classifier import RecoveryClass


@dataclass(frozen=True)
class ClassificationCase:
    """One row of the classifier truth table.

    ``category`` is the ``events.py`` ``ErrorCategory`` (or the literal
    ``"any"`` for the adapter-hint-wins row, where the category is irrelevant
    because the hint decides). ``code`` is an ``events.py`` code constant for
    the neutral rows, or the provider's raw status string for the raw-Claude
    hint rows. ``adapter_hint`` is the per-provider detection hint
    (``None`` ⇒ defer to the neutral category default). ``expected`` is the
    contracted verdict.
    """

    category: str
    code: str
    adapter_hint: RecoveryClass | None
    expected: RecoveryClass
    rationale: str


@dataclass(frozen=True)
class NextDelayCase:
    """One row of the backoff stub table.

    ``expected_ceiling`` is the jitter-free per-attempt ceiling
    (``min(max_delay, base * multiplier**attempt)``) the full-jitter
    ``next_delay`` samples within, or ``None`` on budget exhaustion.
    """

    attempt: int
    elapsed_seconds: float
    expected_ceiling: float | None
    note: str


# ── the classification truth table (contract §"truth table") ─────────────

CLASSIFICATION_TRUTH_TABLE: tuple[ClassificationCase, ...] = (
    # Provider-neutral rows (no adapter hint) — the category default.
    ClassificationCase(
        "protocol",
        ev.SOCKET_CLOSED,
        None,
        RecoveryClass.TRANSIENT_BLIP,
        "transport wobble; ProtocolError doc says retry-with-backoff",
    ),
    ClassificationCase(
        "protocol",
        ev.STDIN_BROKEN,
        None,
        RecoveryClass.TRANSIENT_BLIP,
        "transport; retryable",
    ),
    ClassificationCase(
        "protocol",
        ev.SPAWN_FAILED,
        None,
        RecoveryClass.TRANSIENT_BLIP,
        "transport; retryable",
    ),
    ClassificationCase(
        "expected",
        ev.NOT_AUTHORIZED,
        None,
        RecoveryClass.LOGIN_EXPIRED,
        "the one neutral expected code with login meaning",
    ),
    ClassificationCase(
        "expected",
        ev.CWD_NOT_FOUND,
        None,
        RecoveryClass.DEAD_END,
        "deterministic decline; retry repeats it",
    ),
    ClassificationCase(
        "expected",
        ev.UNKNOWN_PROVIDER,
        None,
        RecoveryClass.DEAD_END,
        "deterministic decline",
    ),
    ClassificationCase(
        "expected",
        ev.NO_SESSION,
        None,
        RecoveryClass.DEAD_END,
        "deterministic decline",
    ),
    ClassificationCase(
        "internal",
        ev.DECODE_FAILED,
        None,
        RecoveryClass.DEAD_END,
        "a bug; model says log+escalate, don't retry",
    ),
    ClassificationCase(
        "internal",
        ev.LOG_CORRUPT,
        None,
        RecoveryClass.DEAD_END,
        "a bug; don't retry",
    ),
    # Adapter-hint-wins row — the provider knows better; category irrelevant.
    ClassificationCase(
        "any",
        ev.SOCKET_CLOSED,
        RecoveryClass.TRANSIENT_BLIP,
        RecoveryClass.TRANSIENT_BLIP,
        "adapter hint wins (provider knows better)",
    ),
    # Raw-Claude rows — the shared layer cannot interpret these codes; the
    # provider's classify_failure hint is what drives the verdict.
    ClassificationCase(
        "expected",
        "401",
        RecoveryClass.LOGIN_EXPIRED,
        RecoveryClass.LOGIN_EXPIRED,
        "Claude classify_failure maps 401/403 -> login",
    ),
    ClassificationCase(
        "expected",
        "429",
        RecoveryClass.TRANSIENT_BLIP,
        RecoveryClass.TRANSIENT_BLIP,
        "Claude maps 429 -> rate-limit blip",
    ),
    ClassificationCase(
        "expected",
        "400",
        RecoveryClass.DEAD_END,
        RecoveryClass.DEAD_END,
        "Claude maps bad-request -> dead-end",
    ),
)


# ── the 4-row next_delay stub table (contract, DEFAULT_RETRY_POLICY) ───────
# policy: base=1, max=60, mult=2, budget=720, full jitter.

NEXT_DELAY_STUBS: tuple[NextDelayCase, ...] = (
    NextDelayCase(0, 0.0, 1.0, "first step, full jitter: min(60, 1*2**0)=1"),
    NextDelayCase(3, 10.0, 8.0, "min(60, 1*2**3)=8"),
    NextDelayCase(10, 700.0, 60.0, "capped at max_delay"),
    NextDelayCase(0, 720.0, None, "budget exhausted -> reclassify dead-end"),
)
