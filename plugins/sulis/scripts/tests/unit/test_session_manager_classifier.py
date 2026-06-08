"""WP-002 — tests for the provider-neutral classifier.

Contract: ``.architecture/automation-reliability-recovery/contracts/\
reliability-layer.contract.md`` (the classification truth table) + ADR-003
(classification is provider-neutral; detection is a thin adapter hint).

``classify(error, adapter_hint) -> RecoveryClass`` is the producer in the
WP-001 contract seam: it maps an observed :class:`~_session_manager.events.\
EventError` to exactly one :class:`~_session_manager.classifier.RecoveryClass`,
using the per-provider hint when present and the neutral category default
otherwise. It is **pure and total** — every ``(category, code, hint)`` triple
yields a class; an unrecognised future code falls through to the category
default (dead-end, the safe direction) and never raises.

Verification posture (MEA-09 / contract CF-07): the truth table is asserted
against the *real* ``events.py`` ``EventError`` value objects — no mocks of the
value objects, and no fake classifier. The rows come from the single shared
fixture (``_recovery_contract_fixtures``) so the verdict vocabulary is never
re-spelled (CF-11).

The provider-neutral guarantee (ADR-003) is made mechanical by
``test_no_adapter_import``: the classifier module's source must not import the
adapter layer — the ``"401"`` magic-string interpretation lives in the Claude
adapter (WP-006), never in the shared classifier.
"""

from __future__ import annotations

import pytest

from _session_manager import events as ev
from _session_manager.classifier import RecoveryClass, classify

from tests.unit._recovery_contract_fixtures import (
    CLASSIFICATION_TRUTH_TABLE,
    ClassificationCase,
)


def _event_error(case: ClassificationCase) -> ev.EventError:
    """Build a real ``events.py`` ``EventError`` from a truth-table row.

    The fixture's ``"any"`` category (the adapter-hint-wins row, where the
    category is irrelevant because the hint decides) is materialised as a
    concrete valid category so we exercise the *real* frozen value object — the
    hint, not the category, drives that row's verdict.
    """
    category = "protocol" if case.category == "any" else case.category
    return ev.EventError(category=category, code=case.code, message=case.rationale)


# ── the contract truth table, against real events.py value objects ────────


@pytest.mark.parametrize(
    "case",
    CLASSIFICATION_TRUTH_TABLE,
    ids=[
        f"{c.category}/{c.code}/hint={c.adapter_hint}"
        for c in CLASSIFICATION_TRUTH_TABLE
    ],
)
def test_truth_table(case: ClassificationCase) -> None:
    """Every contracted row classifies to its contracted verdict — driven
    against the real ``EventError`` value object (no mocks)."""
    error = _event_error(case)
    assert classify(error, case.adapter_hint) is case.expected


# ── totality: unknown code with no hint → category default (never raises) ──


def test_unknown_code_falls_through_to_dead_end() -> None:
    """CF-04 non-happy case: an unrecognised future ``(category, code)`` with
    no adapter hint falls through to the neutral category default rather than
    crashing. The function is total and never raises.

    - unknown ``expected`` code → DEAD_END (safe: don't retry a decline)
    - unknown ``internal`` code → DEAD_END (safe: a bug; log + escalate)
    - unknown ``protocol`` code → TRANSIENT_BLIP (transport wobble; retry)
    """
    unknown_expected = ev.EventError(
        category="expected", code="SOME_FUTURE_DECLINE", message="not yet known"
    )
    assert classify(unknown_expected, None) is RecoveryClass.DEAD_END

    unknown_internal = ev.EventError(
        category="internal", code="SOME_FUTURE_BUG", message="not yet known"
    )
    assert classify(unknown_internal, None) is RecoveryClass.DEAD_END

    unknown_protocol = ev.EventError(
        category="protocol", code="SOME_FUTURE_TRANSPORT", message="not yet known"
    )
    assert classify(unknown_protocol, None) is RecoveryClass.TRANSIENT_BLIP


# ── adapter hint wins (provider knows better) ─────────────────────────────


def test_adapter_hint_wins() -> None:
    """When the provider supplies a hint, the hint is the verdict regardless of
    the neutral category default (ADR-003). An ``expected`` error that the
    neutral default would call DEAD_END becomes TRANSIENT_BLIP when the adapter
    hints so (the raw-Claude ``429`` case)."""
    rate_limit = ev.EventError(category="expected", code="429", message="rate limited")
    assert (
        classify(rate_limit, RecoveryClass.TRANSIENT_BLIP)
        is RecoveryClass.TRANSIENT_BLIP
    )

    # And the hint can override what would otherwise be a login verdict.
    not_authorized = ev.EventError(
        category="expected", code=ev.NOT_AUTHORIZED, message="auth"
    )
    assert classify(not_authorized, RecoveryClass.DEAD_END) is RecoveryClass.DEAD_END


# ── provider-neutrality, made mechanical (ADR-003) ────────────────────────


def test_no_adapter_import() -> None:
    """The classifier module must not *import* the adapter layer —
    classification policy is provider-neutral (ADR-003); the only place a
    provider's raw vocabulary (``"401"`` etc.) is interpreted is the adapter's
    ``classify_failure`` (WP-006). Asserted by parsing the module's actual
    import statements (not docstring prose, which may legitimately *mention*
    the adapter for context) so the guarantee can't silently regress."""
    import ast
    import inspect

    import _session_manager.classifier as classifier_module

    tree = ast.parse(inspect.getsource(classifier_module))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)

    offending = [m for m in imported_modules if "adapter" in m.lower()]
    assert not offending, (
        "classifier.py must not import the adapter layer — classification is "
        f"provider-neutral (ADR-003); offending imports: {offending}"
    )
