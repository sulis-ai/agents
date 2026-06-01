"""Structural verification for WP-001 (verification-by-design change).

WP-001 authors the canonical 20-question verification reference standard
at ``plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md``. This
module is the RED-phase verification: the standard has no runtime tests
(docs prose), so the failing-first cycle pins the documented invariants
on the live file as structural assertions.

Per the WP Contract (`Definition of Done > Red`), the file MUST:

  1. Exist at the canonical path fixed by ADR-004.
  2. Carry a ``version: 1.0.0`` field and an ``active`` status in the
     header front matter.
  3. Contain twenty questions, numbered ``Q1.`` through ``Q20.``, split
     into three labelled groups (Foundational / Per-integration /
     Per-kind verification adapter).
  4. Carry the seven-row kind-to-adapter table from ADR-007, with rows
     for ``methodology``, ``backend``, ``frontend``, ``async``,
     ``infrastructure``, ``documentation``, and ``contract``.
  5. Include the canonical HTML-comment annotation shape consumers cite
     in their own artifacts (per MUC-003 defence).
  6. Cross-reference the relevant ADRs (ADR-001, ADR-003, ADR-004,
     ADR-006, ADR-007) and the SRD's FR-006 / FR-007.
  7. Read cleanly in founder English — no obvious internal-jargon
     leaks in the question text.

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this
test file so the suite is location-stable inside any worktree.
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
    / "VERIFICATION_QUESTIONS.md"
)

# ADRs the canonical must cross-reference. ADR-004 fixes the file's own
# location; ADR-007 fixes the adapter table; ADR-001 fixes the section
# name consumers use; ADR-003 fixes the per-WP verification: field shape;
# ADR-006 fixes the grandfather-edit edge case the usage block must call
# out so consumers know when not to apply the rubric.
_REQUIRED_ADR_REFS = (
    "ADR-001",
    "ADR-003",
    "ADR-004",
    "ADR-006",
    "ADR-007",
)

_REQUIRED_SRD_REFS = ("FR-006", "FR-007")

# Seven adapter kinds locked by ADR-007. The standard's adapter table
# MUST carry exactly these rows; new kinds extend by methodology change.
_REQUIRED_ADAPTER_KINDS = (
    "methodology",
    "backend",
    "frontend",
    "async",
    "infrastructure",
    "documentation",
    "contract",
)

# Substrings that would indicate the question text leaked operator
# jargon. The questions ship to founder-readable agents; these strings
# fail the FE-03 read-aloud test. List is conservative — the goal is to
# catch obvious leaks, not to police every word.
_FORBIDDEN_JARGON = (
    "OODA",
    "five whys",
    "scope-guard",
    "load-bearing",
    "facilitation",
)


@pytest.fixture(scope="module")
def canonical_text() -> str:
    """Read the canonical standard once per test module."""
    if not _CANONICAL.exists():
        pytest.fail(
            f"Canonical verification-questions standard missing at {_CANONICAL}. "
            "WP-001 authors this file; the structural assertions cannot run "
            "until it exists."
        )
    return _CANONICAL.read_text(encoding="utf-8")


def test_canonical_file_exists() -> None:
    """The canonical lives at the path fixed by ADR-004."""
    assert _CANONICAL.exists(), (
        f"Canonical standard missing at {_CANONICAL} "
        "(per ADR-004 — canonical location)."
    )


def test_canonical_has_version_field(canonical_text: str) -> None:
    """Header front matter carries ``version: 1.0.0``."""
    # Tolerate either bare YAML front matter (``version: 1.0.0``) or a
    # quoted variant. Bumps are minor on question add/remove.
    assert re.search(
        r"^version:\s*['\"]?1\.0\.0['\"]?\s*$",
        canonical_text,
        re.MULTILINE,
    ), "Expected `version: 1.0.0` field in the front matter."


def test_canonical_has_active_status(canonical_text: str) -> None:
    """Header carries ``status: active`` so consumers can gate on
    currency."""
    assert re.search(
        r"^status:\s*['\"]?active['\"]?\s*$",
        canonical_text,
        re.MULTILINE | re.IGNORECASE,
    ), "Expected `status: active` field in the front matter."


def test_canonical_has_twenty_questions(canonical_text: str) -> None:
    """Twenty questions numbered Q1. through Q20. — Foundational (1-4),
    Per-integration (5-13), Per-kind adapter (14-20)."""
    # Each question header appears as ``- Q<N>.`` at the start of a line
    # per the WP Contract's RED checklist (``^- Q\d+\.``).
    matches = re.findall(r"^- Q(\d+)\.", canonical_text, re.MULTILINE)
    numbers = sorted(int(m) for m in matches)
    assert numbers == list(range(1, 21)), (
        f"Expected questions Q1.-Q20. exactly once each; found numbers: {numbers}"
    )


def test_canonical_has_question_group_headings(canonical_text: str) -> None:
    """The three labelled groups split the 20 questions into the
    foundational, per-integration, and per-kind buckets."""
    # Groups per WP Contract structure block.
    assert re.search(
        r"^##\s+Foundational",
        canonical_text,
        re.MULTILINE,
    ), "Expected `## Foundational` group heading."
    assert re.search(
        r"^##\s+Per-integration",
        canonical_text,
        re.MULTILINE,
    ), "Expected `## Per-integration` group heading."
    assert re.search(
        r"^##\s+Per-kind",
        canonical_text,
        re.MULTILINE,
    ), "Expected `## Per-kind` group heading (the adapter questions)."


def test_canonical_has_seven_adapter_rows(canonical_text: str) -> None:
    """ADR-007 locks seven adapter kinds. The table MUST carry exactly
    these rows."""
    for kind in _REQUIRED_ADAPTER_KINDS:
        # Each adapter row starts with a backticked kind name in the
        # first cell of the table — ``| `methodology` |``.
        pattern = rf"^\|\s*`{re.escape(kind)}`\s*\|"
        assert re.search(pattern, canonical_text, re.MULTILINE), (
            f"Expected adapter table row for kind `{kind}` "
            "(per ADR-007's seven-row table)."
        )


def test_canonical_adapter_table_has_no_extra_kinds(
    canonical_text: str,
) -> None:
    """No row beyond the seven canonical kinds. New kinds extend via a
    methodology change per ADR-007 — they do not slip in inline."""
    # Find all backticked first-column cells in the adapter table.
    table_kinds = set(
        re.findall(
            r"^\|\s*`([a-z][a-z\-]*)`\s*\|",
            canonical_text,
            re.MULTILINE,
        )
    )
    extra = table_kinds - set(_REQUIRED_ADAPTER_KINDS)
    assert not extra, (
        f"Adapter table contains kinds beyond the canonical seven: "
        f"{sorted(extra)}. New kinds require a methodology change "
        "(ADR-007)."
    )


def test_canonical_has_html_comment_annotation_shape(
    canonical_text: str,
) -> None:
    """The usage block names the HTML-comment annotation shape consumers
    cite. The P-VER citation-presence check parses this comment."""
    # The shape per the WP Contract's usage block:
    #   <!-- VERIFICATION_QUESTIONS source: plugins/.../VERIFICATION_QUESTIONS.md v1.0.0 -->
    assert re.search(
        r"<!--\s*VERIFICATION_QUESTIONS\s+source:\s*"
        r"plugins/sulis/references/standards/VERIFICATION_QUESTIONS\.md"
        r"\s+v1\.0\.0\s*-->",
        canonical_text,
    ), (
        "Expected the HTML-comment annotation shape in the usage block "
        "(MUC-003 defence — consumers cite by this comment, not by "
        "inlining question text)."
    )


def test_canonical_cites_required_adrs(canonical_text: str) -> None:
    """Cross-references resolve to the design's ADRs so consumers can
    chase context."""
    for adr in _REQUIRED_ADR_REFS:
        assert adr in canonical_text, (
            f"Expected cross-reference to {adr} in the canonical "
            "(usage block or version history)."
        )


def test_canonical_cites_required_srd_frs(canonical_text: str) -> None:
    """FR-006 (SSOT) and FR-007 (citation discipline) are the SRD's
    invariants this file enforces; the file MUST point back at them."""
    for fr in _REQUIRED_SRD_REFS:
        assert fr in canonical_text, (
            f"Expected cross-reference to SRD {fr} in the canonical."
        )


def test_canonical_has_version_history_table(canonical_text: str) -> None:
    """Version history table seeded with the v1.0.0 row (Blue
    requirement)."""
    # The history table must contain the v1.0.0 entry on its own line.
    # Permit either a leading version column (``| v1.0.0 |``) or a
    # plain ``| 1.0.0 |`` entry per the existing standards' shapes.
    assert re.search(
        r"^\|\s*v?1\.0\.0\s*\|",
        canonical_text,
        re.MULTILINE,
    ), "Expected version history row for v1.0.0."


def test_canonical_no_obvious_operator_jargon(canonical_text: str) -> None:
    """Read-aloud test (FE-03) — flag obvious internal-vocabulary
    leaks. List is conservative; this catches accidental copy-paste of
    executor / facilitation terminology into the question text."""
    leaks: list[str] = []
    for term in _FORBIDDEN_JARGON:
        # Case-insensitive — catches "OODA loop", "Five Whys", etc.
        if re.search(rf"\b{re.escape(term)}\b", canonical_text, re.IGNORECASE):
            leaks.append(term)
    assert not leaks, (
        f"Found internal-jargon terms in the canonical text: {leaks}. "
        "The questions ship to founder-readable agents; rephrase in "
        "plain English (FE-03)."
    )
