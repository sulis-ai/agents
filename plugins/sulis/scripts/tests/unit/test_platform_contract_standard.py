"""Structural verification for WP-001 (platform-contract-standard change).

WP-001 authors the keystone artifact: the **fourth design-stage contract
standard** at
``plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md``. It is
prose, not code — so the failing-first (RED) cycle pins the documented
invariants on the live file as structural assertions, exactly as the sibling
``test_verification_questions_standard.py`` does for its standard.

Per the WP Contract (`Definition of Done > Red`), the standard MUST:

  1. Exist at the canonical path fixed by ADR-002 / TDD §Canonical
     Identifiers.
  2. Declare the severity convention (a MUST / SHOULD / MAY block).
  3. Cite all three sibling standards by filename (FR-016):
     ``CONTRACT_FIRST_STANDARD.md``, ``UX_VISUAL_DESIGN_STANDARD.md``,
     ``SERVICE_SPECIFICATION.md``.
  4. Reproduce the claim-entry schema — the keys ``inferred:``,
     ``load_bearing:`` and ``probe-result:`` must all be present (FR-004).
  5. Carry the four conformance invariants the ``contract`` adapter checks.
  6. Contain requirement IDs ``PC-01`` .. ``PC-08`` (one per Armor control
     A-1..A-8).
  7. State the faithful-generation-harness as the mandated production
     mechanism (FR-003 / ADR-004).
  8. State the gate boundary — write/deploy hard, read-only soft (ADR-001).
  9. Name the canonical storage path for contracts (ADR-002).
  10. Carry a freshness staleness constant (the 180-day threshold; ADR-003).
  11. Cross-reference the relevant ADRs and the triggering incident (#137).
  12. Read cleanly in founder English — no obvious internal-jargon leaks in
      the prose.

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this test
file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_CANONICAL = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "references"
    / "standards"
    / "PLATFORM_CONTRACT_STANDARD.md"
)

# The three sibling standards the Relationship section MUST name (FR-016).
# Cited by filename so a reviewer can navigate the four-contracts family.
_REQUIRED_SIBLING_FILES = (
    "CONTRACT_FIRST_STANDARD.md",
    "UX_VISUAL_DESIGN_STANDARD.md",
    "SERVICE_SPECIFICATION.md",
)

# The claim-entry schema keys that distinguish this schema from any other
# YAML block. All three MUST appear (FR-004). These are the load-bearing
# fields every downstream WP conforms to.
_REQUIRED_SCHEMA_KEYS = (
    "inferred:",
    "load_bearing:",
    "probe-result:",
)

# The eight numbered requirements, one per Armor control A-1..A-8.
_REQUIRED_PC_IDS = tuple(f"PC-0{n}" for n in range(1, 9))

# ADRs this standard is authored against (WP frontmatter `adrs:` +
# the gate/freshness/storage ADRs it must point at so a reader can chase
# the decision rationale).
_REQUIRED_ADR_REFS = (
    "ADR-001",
    "ADR-002",
    "ADR-003",
    "ADR-004",
    "ADR-005",
)

# Read-aloud test (FE-03): obvious internal-vocabulary leaks. Conservative —
# catches accidental copy-paste of executor / facilitation terminology into
# the prose. "load-bearing" is permitted here because it is a genuine term of
# art in this standard's harness-binding section (and is hyphenated, not the
# bare noun the FE check polices); the schema key `load_bearing:` is also
# legitimately present.
_FORBIDDEN_JARGON = (
    "OODA",
    "five whys",
    "scope-guard",
    "facilitation",
)


@pytest.fixture(scope="module")
def standard_text() -> str:
    """Read the canonical standard once per test module."""
    if not _CANONICAL.exists():
        pytest.fail(
            f"PLATFORM_CONTRACT_STANDARD.md missing at {_CANONICAL}. "
            "WP-001 authors this file; the structural assertions cannot run "
            "until it exists."
        )
    return _CANONICAL.read_text(encoding="utf-8")


def test_standard_exists() -> None:
    """The standard lives at the path fixed by ADR-002 / TDD §Canonical
    Identifiers."""
    assert _CANONICAL.exists(), (
        f"Standard missing at {_CANONICAL} "
        "(per ADR-002 — canonical storage convention)."
    )


def test_declares_severity_convention(standard_text: str) -> None:
    """The standard declares its MUST / SHOULD / MAY severity block (per
    repo CLAUDE.md, mirroring the sibling standards)."""
    assert re.search(
        r"##\s+Severity convention",
        standard_text,
        re.IGNORECASE,
    ), "Expected a `## Severity convention` heading."
    for token in ("MUST", "SHOULD", "MAY"):
        assert re.search(rf"\b{token}\b", standard_text), (
            f"Expected the severity token `{token}` in the convention block."
        )


def test_cites_three_sibling_standards(standard_text: str) -> None:
    """Relationship-to-siblings section names all three siblings by filename
    (FR-016 — the four-contracts family)."""
    for sibling in _REQUIRED_SIBLING_FILES:
        assert sibling in standard_text, (
            f"Expected the standard to cite sibling `{sibling}` by filename "
            "(FR-016 relationship-to-existing-standards section)."
        )


def test_contains_claim_entry_schema(standard_text: str) -> None:
    """The claim-entry schema (FR-004) is reproduced — the three
    distinguishing keys must all be present."""
    for key in _REQUIRED_SCHEMA_KEYS:
        assert key in standard_text, (
            f"Expected claim-entry schema key `{key}` "
            "(FR-004 — the canonical identifier every downstream WP "
            "conforms to)."
        )


def test_contains_conformance_invariants(standard_text: str) -> None:
    """The four conformance invariants the `contract` adapter checks are
    stated (TDD §Canonical Identifiers lines 41-44)."""
    # inferred:false ⇒ source+quote+retrieval-date; inferred:true ⇒ no
    # fabricated source; load_bearing:true ⇒ probe+probe-result;
    # probe-result:confirmed ⇒ probe-evidence. We assert the discriminating
    # tokens are present (the source+quote+retrieval-date triple, and the
    # probe-evidence requirement).
    for token in ("retrieval-date", "quote", "probe-evidence"):
        assert token in standard_text, (
            f"Expected conformance-invariant token `{token}` in the schema section."
        )


def test_contains_pc_requirement_ids(standard_text: str) -> None:
    """Requirement IDs PC-01..PC-08, one per Armor control A-1..A-8."""
    for pc in _REQUIRED_PC_IDS:
        assert pc in standard_text, (
            f"Expected requirement ID `{pc}` (mirrors the sibling-standard "
            "numbered-requirement convention; one per Armor control)."
        )


def test_states_harness_as_mandated_mechanism(standard_text: str) -> None:
    """The standard mandates the faithful-generation-harness as the
    production mechanism (FR-003 / ADR-004)."""
    assert "faithful-generation-harness" in standard_text, (
        "Expected the standard to name `faithful-generation-harness` as the "
        "mandated production mechanism (FR-003 / ADR-004)."
    )
    assert "execute-workflow" in standard_text, (
        "Expected the standard to name the `execute-workflow` dispatch path (ADR-004)."
    )


def test_states_gate_boundary(standard_text: str) -> None:
    """The gate posture is stated: write/deploy hard, read-only soft
    (ADR-001)."""
    lowered = standard_text.lower()
    assert "write" in lowered and "deploy" in lowered, (
        "Expected the gate section to name the write/deploy hard-gate class."
    )
    assert "read-only" in lowered, (
        "Expected the gate section to name the read-only soft-recommend "
        "class (ADR-001)."
    )


def test_names_storage_path(standard_text: str) -> None:
    """The canonical contract storage path is named (ADR-002)."""
    assert "plugins/sulis/references/platform-contracts/" in standard_text, (
        "Expected the storage-path convention "
        "`plugins/sulis/references/platform-contracts/<platform>.md` "
        "(ADR-002)."
    )


def test_names_staleness_threshold(standard_text: str) -> None:
    """The freshness staleness constant (180 days) is named (ADR-003)."""
    assert re.search(r"\b180\b", standard_text), (
        "Expected the 180-day staleness threshold named constant (ADR-003)."
    )


def test_cites_required_adrs(standard_text: str) -> None:
    """Cross-references resolve to the design's ADRs so a reviewer can chase
    context."""
    for adr in _REQUIRED_ADR_REFS:
        assert adr in standard_text, (
            f"Expected cross-reference to {adr} in the standard."
        )


def test_cites_triggering_incident(standard_text: str) -> None:
    """The provenance section cites the triggering incident (#137 — the
    reusable-workflow-location flaw)."""
    assert "#137" in standard_text, (
        "Expected the standard to cite issue #137 (the triggering "
        "reusable-workflow incident) in its provenance section."
    )


def test_no_obvious_operator_jargon(standard_text: str) -> None:
    """Read-aloud test (FE-03) — flag obvious internal-vocabulary leaks."""
    leaks: list[str] = []
    for term in _FORBIDDEN_JARGON:
        if re.search(rf"\b{re.escape(term)}\b", standard_text, re.IGNORECASE):
            leaks.append(term)
    assert not leaks, (
        f"Found internal-jargon terms in the standard text: {leaks}. "
        "Rephrase in plain English (FE-03)."
    )
