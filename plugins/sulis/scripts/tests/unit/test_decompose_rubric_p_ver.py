"""Structural verification for WP-002 (verification-by-design change).

WP-002 extends ``plugins/sulis/references/decompose-validation-rubric.md``
to v0.3.0 with **Phase 9 — P-VER (Verification Plan)**: eight failure-mode
checks (9.01..9.08), a grandfather sub-phase (ADR-002 + ADR-006), and a
``verification_required_from:`` front-matter constant the
``sulis-change finish`` flow fills in at merge time.

The rubric ships as prose, not Python — the enforcement happens at
invocation time by the validating skill (WP-005/006). This test module
is the RED-phase verification: it pins the documented contract on the
live file as structural assertions.

Per the WP Contract (`Definition of Done > Red`), the rubric MUST:

  1. Carry a ``verification_required_from:`` field in YAML front matter.
  2. Declare ``Version: 0.3.0`` (or front-matter equivalent).
  3. List Phase 9 — P-VER in the top "Phase-by-phase results" table.
  4. Declare a P9 row in the Methodology self-attestation block.
  5. Carry a ``## Phase 9 — P-VER (Verification Plan)`` section header
     between Phase 8 and "Anti-patterns for the validation run itself".
  6. Enumerate exactly eight check rows 9.01..9.08, each with an
     adjacent MUST severity and a Pass criterion column populated.
  7. Cite ``VERIFICATION_QUESTIONS.md`` by relative path.
  8. Carry grandfather sub-phase prose citing both ADR-002 and ADR-006.
  9. Append a 0.3.0 row to the Version history table.

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this
test file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_RUBRIC = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "references"
    / "decompose-validation-rubric.md"
)

# Failure-mode check IDs the WP Contract enumerates (one per Armor
# pillar table row in the TDD — eight modes, 9.01..9.08).
_REQUIRED_CHECK_IDS = (
    "9.01",
    "9.02",
    "9.03",
    "9.04",
    "9.05",
    "9.06",
    "9.07",
    "9.08",
)

# The grandfather sub-phase cites both ADRs by ID.
_REQUIRED_ADR_CITATIONS = ("ADR-002", "ADR-006")

# Canonical relative path the rubric must cite (no inline duplication
# of question text — citation only).
_CANONICAL_REL_PATH = (
    "plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md"
)


@pytest.fixture(scope="module")
def rubric_text() -> str:
    """Read the live rubric once per test module."""
    if not _RUBRIC.exists():
        pytest.fail(
            f"Decompose-validation rubric missing at {_RUBRIC}. WP-002 "
            "extends this file; the structural assertions cannot run "
            "until it exists."
        )
    return _RUBRIC.read_text(encoding="utf-8")


def test_rubric_has_verification_required_from_field(
    rubric_text: str,
) -> None:
    """ADR-002 fixes the merge-date constant at the rubric's front
    matter. The field is populated by ``sulis-change finish`` at merge
    time; until then it carries an empty-string default."""
    # Accept ``verification_required_from:`` followed by optional value
    # (empty, quoted-empty, or ISO-8601 date).
    assert re.search(
        r"^verification_required_from:",
        rubric_text,
        re.MULTILINE,
    ), (
        "Expected `verification_required_from:` field in the rubric "
        "front matter (ADR-002 — merge-date constant)."
    )


def test_rubric_version_bumped_to_0_3_0(rubric_text: str) -> None:
    """Version bumps v0.2.0 → v0.3.0 per the WP Contract."""
    # The rubric's version line lives at the top of the file
    # (``> **Version:** 0.3.0``) — match either the bare or backticked
    # variant, with optional leading ``v``.
    assert re.search(
        r"\*\*Version:\*\*\s*v?0\.3\.0\b",
        rubric_text,
    ), "Expected `**Version:** 0.3.0` (or v0.3.0) header marker."


def test_phase_by_phase_table_has_p9_row(rubric_text: str) -> None:
    """The top "Phase-by-phase results" table is extended with a P9 /
    Phase 9 row so the summary table includes P-VER."""
    # The existing table rows look like ``| 1 Inventory completeness …``
    # — a row beginning with ``| 9`` (with optional leading whitespace)
    # is the P-VER row.
    assert re.search(
        r"^\|\s*9\s+",
        rubric_text,
        re.MULTILINE,
    ), (
        "Expected the top Phase-by-phase results table to carry a "
        "row beginning `| 9 ` for Phase 9 (P-VER)."
    )


def test_methodology_self_attestation_has_p9_row(rubric_text: str) -> None:
    """The Methodology self-attestation block carries a P9 row so the
    rubric run reports its P-VER coverage."""
    assert re.search(
        r"\*\*P9\b.*P-VER",
        rubric_text,
    ), (
        "Expected the Methodology self-attestation block to carry a "
        "`**P9 P-VER (Verification Plan).**` row."
    )


def test_phase_9_section_header_present(rubric_text: str) -> None:
    """The new ``## Phase 9 — P-VER (Verification Plan)`` section header
    lives between Phase 8 and the Anti-patterns section."""
    # Match the canonical header shape — em-dash, exact title.
    match = re.search(
        r"^##\s+Phase\s+9\s+[—-]\s+P-VER\s+\(Verification Plan\)\s*$",
        rubric_text,
        re.MULTILINE,
    )
    assert match, (
        "Expected `## Phase 9 — P-VER (Verification Plan)` section "
        "header (em-dash or hyphen accepted)."
    )


def test_phase_9_appears_between_phase_8_and_anti_patterns(
    rubric_text: str,
) -> None:
    """Section ordering preserved (Phase 9 between Phase 8 and the
    Anti-patterns section)."""
    # Locate the three section anchors and assert ordering.
    p8 = re.search(
        r"^##\s+Phase\s+8\s+",
        rubric_text,
        re.MULTILINE,
    )
    p9 = re.search(
        r"^##\s+Phase\s+9\s+[—-]\s+P-VER",
        rubric_text,
        re.MULTILINE,
    )
    anti = re.search(
        r"^##\s+Anti-patterns\s+for\s+the\s+validation\s+run\s+itself",
        rubric_text,
        re.MULTILINE,
    )
    assert p8 and p9 and anti, (
        "Expected to find Phase 8, Phase 9, and Anti-patterns headers."
    )
    assert p8.start() < p9.start() < anti.start(), (
        f"Section order wrong: Phase 8 @ {p8.start()}, "
        f"Phase 9 @ {p9.start()}, Anti-patterns @ {anti.start()}. "
        "Phase 9 must sit between Phase 8 and Anti-patterns."
    )


def test_phase_9_has_eight_failure_mode_rows(rubric_text: str) -> None:
    """Exactly eight check rows 9.01..9.08, one per Armor-pillar table
    row in the TDD."""
    # Each row begins with ``| **9.NN** |`` per the WP Contract's
    # tabular shape.
    found = sorted(
        set(re.findall(r"\|\s*\*\*9\.(\d{2})\*\*\s*\|", rubric_text))
    )
    expected = sorted({cid.split(".")[1] for cid in _REQUIRED_CHECK_IDS})
    assert found == expected, (
        f"Expected exactly eight P-VER check rows 9.01..9.08 (suffixes "
        f"{expected}); found {found}."
    )


def test_phase_9_rows_all_severity_must(rubric_text: str) -> None:
    """Each 9.01..9.08 row is severity MUST (Armor-pillar checks are
    hard gates — see ADR-002)."""
    # Find each row by check ID and assert MUST appears in the same row.
    for cid in _REQUIRED_CHECK_IDS:
        # Match the full row to its newline so we only capture one line.
        pattern = rf"\|\s*\*\*{re.escape(cid)}\*\*\s*\|([^\n]*)"
        m = re.search(pattern, rubric_text)
        assert m, f"Check row {cid} missing from rubric."
        row = m.group(1)
        assert "MUST" in row, (
            f"Check row {cid} must be severity MUST; row content: "
            f"{row.strip()!r}"
        )


def test_phase_9_cites_canonical_by_relative_path(
    rubric_text: str,
) -> None:
    """The P-VER section cites VERIFICATION_QUESTIONS.md by relative
    path — no inline duplication of question text (MUC-003 defence;
    NFR-004 SSOT)."""
    # Locate Phase 9 + extract its body up to the next ``## `` header.
    phase9_anchor = re.search(
        r"^##\s+Phase\s+9\s+[—-]\s+P-VER",
        rubric_text,
        re.MULTILINE,
    )
    assert phase9_anchor, "Phase 9 header missing."
    body_start = phase9_anchor.end()
    next_h2 = re.search(
        r"^##\s+", rubric_text[body_start:], re.MULTILINE
    )
    body_end = body_start + next_h2.start() if next_h2 else len(rubric_text)
    body = rubric_text[body_start:body_end]
    assert _CANONICAL_REL_PATH in body, (
        f"Phase 9 must cite the canonical by relative path "
        f"`{_CANONICAL_REL_PATH}`; not found in section body."
    )


def test_phase_9_grandfather_subphase_cites_both_adrs(
    rubric_text: str,
) -> None:
    """The grandfather sub-phase cites BOTH ADR-002 (merge-date scope)
    and ADR-006 (edits inherit status). Both citations live inside
    Phase 9."""
    phase9_anchor = re.search(
        r"^##\s+Phase\s+9\s+[—-]\s+P-VER",
        rubric_text,
        re.MULTILINE,
    )
    assert phase9_anchor, "Phase 9 header missing."
    body_start = phase9_anchor.end()
    next_h2 = re.search(
        r"^##\s+", rubric_text[body_start:], re.MULTILINE
    )
    body_end = body_start + next_h2.start() if next_h2 else len(rubric_text)
    body = rubric_text[body_start:body_end]
    for adr in _REQUIRED_ADR_CITATIONS:
        assert adr in body, (
            f"Phase 9 grandfather sub-phase must cite {adr}; not "
            "found in section body."
        )
    # The word "grandfather" (any case) must appear so the sub-phase
    # is discoverable to a reader.
    assert re.search(r"grandfather", body, re.IGNORECASE), (
        "Phase 9 must include `grandfather` prose for the sub-phase."
    )


def test_phase_9_references_started_at(rubric_text: str) -> None:
    """The grandfather sub-phase reads ``started_at`` from the change
    record (per ADR-002 detection logic)."""
    phase9_anchor = re.search(
        r"^##\s+Phase\s+9\s+[—-]\s+P-VER",
        rubric_text,
        re.MULTILINE,
    )
    assert phase9_anchor, "Phase 9 header missing."
    body_start = phase9_anchor.end()
    next_h2 = re.search(
        r"^##\s+", rubric_text[body_start:], re.MULTILINE
    )
    body_end = body_start + next_h2.start() if next_h2 else len(rubric_text)
    body = rubric_text[body_start:body_end]
    assert "started_at" in body, (
        "Phase 9 grandfather sub-phase must reference `started_at` "
        "(the field it compares against the merge-date constant)."
    )


def test_version_history_has_0_3_0_row(rubric_text: str) -> None:
    """The Version history table gets a new 0.3.0 row noting the
    Phase 9 addition (per the WP Contract's version-history block)."""
    assert re.search(
        r"^\|\s*0\.3\.0\s*\|",
        rubric_text,
        re.MULTILINE,
    ), "Expected version history row for 0.3.0."


def test_version_history_0_3_0_row_names_p_ver(rubric_text: str) -> None:
    """The 0.3.0 row notes the Phase 9 / P-VER addition so the change
    is discoverable."""
    # Pull the line and confirm it mentions P-VER (or Phase 9).
    m = re.search(
        r"^\|\s*0\.3\.0\s*\|[^\n]+",
        rubric_text,
        re.MULTILINE,
    )
    assert m, "Version history row for 0.3.0 missing."
    row = m.group(0)
    assert "P-VER" in row or "Phase 9" in row, (
        f"Version history 0.3.0 row must name `P-VER` or `Phase 9`; "
        f"row was: {row!r}"
    )
