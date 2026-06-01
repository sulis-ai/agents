"""Behavioural verification for the P-VER rubric harness (WP-007).

WP-002 extended ``decompose-validation-rubric.md`` to v0.3.0 with Phase 9
(eight failure-mode checks 9.01..9.08 + a grandfather sub-phase). The
rubric ships as prose; this WP authors the smallest harness that
applies those checks to synthetic SRD/TDD/WP artifacts plus the 12
fixtures (8 fail + 4 pass) that prove each check fires for exactly the
intended failure mode.

The harness module is ``plugins/sulis/scripts/_p_ver_rubric.py``
(stdlib-only, no PyYAML dependency for the front-matter parse — the
fixtures use the trivial subset the rubric needs). The fixtures live
under ``tests/unit/fixtures/p_ver/`` and each one is the smallest
synthetic file that triggers exactly one of the eight failure modes
(or none, for the pass fixtures).

Per WP Definition of Done:

* Red:  test_all_failure_modes_and_passes parametrised over all 12
        fixtures asserts the expected verdict + failure-mode check ID.
* Red:  test_idempotent runs P-VER twice over the same pass fixture
        and asserts byte-identical verdicts.
* Blue: the 2-consumer threshold did NOT fire on the harness internals
        (``_verification_plan_body``, ``_extract_front_matter``, and
        ``_parse_flat_yaml`` are already the shared primitives). A
        ``fixture_helpers.py`` build-helper module was considered and
        deliberately skipped: fixtures are test DATA, hand-written
        for ``cat``-readability per Blue D-o-D bullet 2. Polish added
        instead: ``test_every_fixture_has_top_line_intent_comment``
        enforces Blue D-o-D bullet 3 (intent-line discoverability).

Stdlib + pytest only, Python 3.11+. Paths resolve relative to this
file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _p_ver_rubric import run_p_ver  # noqa: E402 — path-insert above

_FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "p_ver"


# ---------------------------------------------------------------------------
# Fixture expectations table
# ---------------------------------------------------------------------------
#
# Each entry: (fixture_dir_name, expected_verdict, expected_failed_check).
# expected_failed_check is None for PASS / PASS_GRANDFATHERED verdicts.
#
# The 12 fixtures cover the eight failure modes (9.01..9.08) once each
# plus four PASS shapes (P-A through P-D per TDD Proof test class 2).

_FIXTURE_EXPECTATIONS = (
    # 8 failure-mode fixtures (one per check 9.01..9.08)
    ("fail_01_section_missing", "FAIL", "9.01"),
    ("fail_02_placeholder_content", "FAIL", "9.02"),
    ("fail_03_na_without_justification", "FAIL", "9.03"),
    ("fail_04_hallucinated_infrastructure", "FAIL", "9.04"),
    ("fail_05_unmapped_kind", "FAIL", "9.05"),
    ("fail_06_no_canonical_citation", "FAIL", "9.06"),
    ("fail_07_wp_missing_verification_field", "FAIL", "9.07"),
    ("fail_08_adapter_mismatch", "FAIL", "9.08"),
    # 4 PASS fixtures (one per common kind)
    ("pass_a_complete_methodology", "PASS", None),
    ("pass_b_complete_backend", "PASS", None),
    ("pass_c_complete_infrastructure", "PASS", None),
    ("pass_d_complete_documentation", "PASS", None),
)


@pytest.mark.parametrize(
    "fixture_name,expected_verdict,expected_check",
    _FIXTURE_EXPECTATIONS,
    ids=[t[0] for t in _FIXTURE_EXPECTATIONS],
)
def test_all_failure_modes_and_passes(
    fixture_name: str,
    expected_verdict: str,
    expected_check: str | None,
) -> None:
    """Per-fixture verdict assertion.

    For each fixture directory, invoke ``run_p_ver`` against it. The
    eight FAIL fixtures must each produce verdict ``FAIL`` with the
    matching ``failed_check`` ID. The four PASS fixtures must produce
    verdict ``PASS`` with no failed check.

    Failure output is debuggable per Blue D-o-D: the rubric verdict +
    expected verdict + actual failed-check ID surface in the assert.
    """
    fixture_dir = _FIXTURES_ROOT / fixture_name
    assert fixture_dir.exists(), (
        f"Fixture directory missing: {fixture_dir}. WP-007 Green "
        f"creates every fixture under {_FIXTURES_ROOT}."
    )

    verdict = run_p_ver(fixture_dir)

    assert verdict.verdict == expected_verdict, (
        f"Fixture {fixture_name!r}: expected verdict "
        f"{expected_verdict!r}, got {verdict.verdict!r}. "
        f"Failed check: {verdict.failed_check!r}. "
        f"Message: {verdict.message!r}."
    )
    assert verdict.failed_check == expected_check, (
        f"Fixture {fixture_name!r}: expected failed_check "
        f"{expected_check!r}, got {verdict.failed_check!r}. "
        f"Full message: {verdict.message!r}."
    )


def test_idempotent_pass_fixture() -> None:
    """Idempotency — TDD Proof test class 4.

    Running P-VER twice over the same pass fixture must produce a
    verdict that compares byte-identical: same verdict, same failed
    check, same message. No hidden state in the rubric harness.
    """
    fixture_dir = _FIXTURES_ROOT / "pass_a_complete_methodology"
    first = run_p_ver(fixture_dir)
    second = run_p_ver(fixture_dir)

    assert first.verdict == second.verdict, (
        f"Non-idempotent verdict: first={first.verdict!r}, second={second.verdict!r}."
    )
    assert first.failed_check == second.failed_check, (
        f"Non-idempotent failed_check: first={first.failed_check!r}, "
        f"second={second.failed_check!r}."
    )
    assert first.message == second.message, (
        f"Non-idempotent message: first={first.message!r}, second={second.message!r}."
    )


def test_idempotent_fail_fixture() -> None:
    """Idempotency on a FAIL fixture — the same fixture must produce
    the same failure mode + message on repeated runs (no hidden state,
    no randomised check ordering)."""
    fixture_dir = _FIXTURES_ROOT / "fail_02_placeholder_content"
    first = run_p_ver(fixture_dir)
    second = run_p_ver(fixture_dir)

    assert first.verdict == second.verdict == "FAIL"
    assert first.failed_check == second.failed_check == "9.02"
    assert first.message == second.message


def test_every_fixture_has_top_line_intent_comment() -> None:
    """Blue D-o-D bullet 3 — each fixture's primary artifact carries a
    top-line HTML comment describing what failure mode it triggers.
    Discoverable by ``head -1`` from the command line."""
    for fixture_name, *_rest in _FIXTURE_EXPECTATIONS:
        fixture_dir = _FIXTURES_ROOT / fixture_name
        # The intent comment lives in the SRD or (for fail_07/fail_08)
        # the WP file. Pick whichever exists.
        primary = fixture_dir / "SRD.md"
        if not primary.exists():
            for wp in fixture_dir.glob("WP-*.md"):
                primary = wp
                break
        assert primary.exists(), (
            f"Fixture {fixture_name!r} has no primary SRD/WP artifact."
        )
        first_line = primary.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("<!--") and "fixture" in first_line, (
            f"Fixture {fixture_name!r} primary artifact "
            f"({primary.name}) must start with an HTML-comment line "
            f"containing 'fixture' describing its intent. Got: "
            f"{first_line!r}"
        )


def test_grandfather_verdict_skips_checks() -> None:
    """A change whose ``started_at`` precedes the rubric's
    ``verification_required_from`` constant returns
    ``PASS_GRANDFATHERED`` and runs no further checks (ADR-002 +
    ADR-006). The fixture deliberately omits a Verification Plan
    section — under normal scoring this would FAIL 9.01, but the
    grandfather sub-phase short-circuits."""
    fixture_dir = _FIXTURES_ROOT / "pass_e_grandfathered_change"
    verdict = run_p_ver(fixture_dir)
    assert verdict.verdict == "PASS_GRANDFATHERED", (
        f"Grandfathered fixture should short-circuit to "
        f"PASS_GRANDFATHERED, got {verdict.verdict!r}."
    )
    assert verdict.failed_check is None
