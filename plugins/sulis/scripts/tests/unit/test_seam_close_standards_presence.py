"""Standards-presence tests for the seam-close DoD gate (CH-01KTP7).

The seam-close gate re-times the real-data acceptance drive from the ship
stage to seam-close. That timing rule is codified in the standards prose so
humans + agents read it at session start; these structural assertions pin the
documented invariants on the live standards files, exactly as the sibling
``test_platform_contract_standard.py`` does for its standard.

WP-005 authors this file and the ``CF-12`` presence assertion. WP-006 appends
one further assertion (``test_work_package_standard_seam_close_dod``) for the
WORK_PACKAGE_STANDARD.md amendment — the file is shaped so that append is a
clean addition at the tail.

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this test
file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

from pathlib import Path

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_STANDARDS = _REPO_ROOT / "plugins" / "sulis" / "references" / "standards"
_CONTRACT_FIRST = _STANDARDS / "CONTRACT_FIRST_STANDARD.md"
_WORK_PACKAGE = _STANDARDS / "WORK_PACKAGE_STANDARD.md"


def _contract_first_text() -> str:
    assert _CONTRACT_FIRST.is_file(), f"missing {_CONTRACT_FIRST}"
    return _CONTRACT_FIRST.read_text(encoding="utf-8")


def _work_package_text() -> str:
    assert _WORK_PACKAGE.is_file(), f"missing {_WORK_PACKAGE}"
    return _WORK_PACKAGE.read_text(encoding="utf-8")


def test_contract_first_standard_has_cf12() -> None:
    """CF-12 — seam-close timing rule is present, MUST, with the no-covering-
    Scenario-blocks clause and the CF-07/ship-backstop relationship.

    CF-07 says *what* "done at the seam" means; CF-12 adds *when* it is driven
    (seam-close, not ship). The rule MUST exist, carry MUST severity, name the
    seam-close timing, distinguish the no-covering-Scenario case as blocked,
    and anchor to CF-07 with the ship gate as the backstop (ADR-002).
    """
    text = _contract_first_text()

    # The rule exists under its own heading at the same depth as its peers.
    assert "### CF-12" in text, (
        "CONTRACT_FIRST_STANDARD.md must declare a CF-12 requirement "
        "(### CF-12 …) for the seam-close DoD timing rule"
    )

    # Locate the CF-12 section so the clause assertions are scoped to it
    # (and don't accidentally match earlier CF-NN prose).
    cf12_start = text.index("### CF-12")
    cf12 = text[cf12_start:]

    # MUST severity — this is a blocking rule, not a SHOULD.
    assert "MUST" in cf12, "CF-12 must carry MUST severity"

    # The timing rule: driven at seam-close, not deferred to ship.
    lowered = cf12.lower()
    assert "seam-close" in lowered or "seam close" in lowered, (
        "CF-12 must state the seam-close timing"
    )
    assert "ship" in lowered, (
        "CF-12 must contrast seam-close timing against the ship stage"
    )

    # The no-covering-Scenario-blocks clause (ADR-005): a seam with no covering
    # Scenario is blocked, not silently passed.
    assert "no covering scenario" in lowered, (
        "CF-12 must state that a seam with no covering Scenario is blocked "
        "(not silently passed)"
    )
    assert "blocked" in lowered, (
        "CF-12 must state the no-covering-Scenario / undriven seam is blocked"
    )

    # Anchored to CF-07 (the 'what') with the ship gate named as the backstop
    # (ADR-002) so the timing relationship is explicit.
    assert "CF-07" in cf12, (
        "CF-12 must cross-reference CF-07 (the seam-done definition it re-times)"
    )
    assert "observed-or-blocked" in lowered, (
        "CF-12 must name the observed-or-blocked Definition-of-Done discipline"
    )


def test_work_package_standard_seam_close_dod() -> None:
    """WORK_PACKAGE_STANDARD.md carries the seam-close DoD wording **and** the
    contract-WP ``implements:`` SHOULD clause (the requirement bridge, ADR-004).

    Two additive amendments land here (WP-006):

    1. The seam-close DoD wording — a seam-spanning (``kind: contract`` /
       integration ``kind: composite``) WP is not ``done`` until the seam-close
       gate reports ``observed``, or a conscious ``--allow-deferred`` was
       recorded; a seam with no covering Scenario (or one needing a tier not yet
       live) is blocked. It cross-references CF-12 (the timing rule it enforces).
    2. The contract-WP ``implements:`` field — a ``kind: contract`` WP SHOULD
       carry ``implements: [dna:requirement:…]`` so the seam-close gate resolves
       the seam to its covering Scenarios directly, with a journey-filtered
       fallback when absent.
    """
    text = _work_package_text()
    lowered = text.lower()

    # --- Amendment 1: the seam-close DoD wording ---------------------------
    assert "seam-close" in lowered, (
        "WORK_PACKAGE_STANDARD.md must state the seam-close DoD timing"
    )
    assert "observed" in lowered, (
        "the seam-close DoD wording must name the `observed` verdict the gate "
        "must report before a seam-spanning WP is done"
    )
    assert "--allow-deferred" in text, (
        "the seam-close DoD wording must name the conscious --allow-deferred "
        "escape hatch"
    )
    assert "no covering scenario" in lowered, (
        "the seam-close DoD wording must state that a seam with no covering "
        "Scenario is blocked (not silently passed)"
    )
    assert "blocked" in lowered, (
        "the seam-close DoD wording must state the no-covering-Scenario / "
        "tier-not-live seam is blocked"
    )
    # Cross-references the timing rule it enforces (CF-12 by id).
    assert "CF-12" in text, (
        "the seam-close DoD wording must cross-reference CF-12 (the timing rule "
        "it enforces)"
    )

    # --- Amendment 2: the contract-WP `implements:` SHOULD clause -----------
    assert "implements:" in text, (
        "WORK_PACKAGE_STANDARD.md must document the contract-WP `implements:` "
        "field (the requirement bridge, ADR-004)"
    )
    assert "dna:requirement" in lowered, (
        "the `implements:` clause must name the `dna:requirement:…` ids the "
        "seam satisfies"
    )
    # SHOULD, not MUST — the journey-filtered fallback keeps legacy WPs working.
    assert "SHOULD" in text, (
        "the `implements:` clause must be SHOULD strength (the journey-filtered "
        "fallback keeps older WPs working)"
    )
    assert "fallback" in lowered, (
        "the `implements:` clause must name the journey-filtered fallback used "
        "when the field is absent"
    )
    assert "ADR-004" in text, (
        "the `implements:` clause must anchor to ADR-004 (the requirement-bridge "
        "decision it implements)"
    )
