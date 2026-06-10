"""Behavioural tests for the always-comprehensive document emitter (WP-006).

KIND = methodology: each test drives the real specify path on a fixture via
``_drive_specify.py`` (the WP-001 harness) and asserts the produced document
through the WP-003 document inspectors (``_assert_doc_sections``,
``_assert_same_section_set``, ``_assert_section_na``, ``_assert_measurable_nfr``)
run as the same CLI subprocesses the SC-01/02/03/05 scenarios use.

These live under ``tests/unit/`` deliberately: branch-ci runs ``pytest
tests/unit/`` only (lesson #60). A test placed at the top of ``tests/`` would
not be in the CI gate.

The emitter contract (ADR-002, FR-01/02/06/11):
  - SC-01: the document carries every mandatory Target-Structure section,
    regardless of depth.
  - SC-02: the section set is identical across lite / standard / deep — depth
    sizes the interview, never which sections exist.
  - SC-03: a section a fixture cannot populate is marked ``n/a — <reason>``,
    never dropped (NFR-R01, "degrade detail, not existence").
  - SC-05: the NFR section always carries a measurable target per category
    (FR-06), not an adjective.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # tests/unit/ -> tests/ -> scripts/
_DRIVER = _SCRIPTS_DIR / "_drive_specify.py"
_ASSERT_DOC_SECTIONS = _SCRIPTS_DIR / "_assert_doc_sections.py"
_ASSERT_SAME_SECTION_SET = _SCRIPTS_DIR / "_assert_same_section_set.py"
_ASSERT_SECTION_NA = _SCRIPTS_DIR / "_assert_section_na.py"
_ASSERT_MEASURABLE_NFR = _SCRIPTS_DIR / "_assert_measurable_nfr.py"

# The full mandatory Target-Structure section set (ADR-002, FR-11). These are
# the canonical headings the always-comprehensive document MUST carry at every
# depth, in the exact form the emitter writes them — the numbered §1..§10
# spine matches the canonical `entity-crud/DESIGN.md`; the always-on NFR /
# STRIDE / Constraints / Assumptions / Dependencies sub-sections and the
# interface-contract skeleton are un-numbered named sub-headings beneath the
# spine. Kept here as the assertion's source of truth so a drift in the emitter
# fails this test loudly rather than silently shrinking the document.
_MANDATORY_SECTIONS = [
    "1. Executive Summary",
    "2. Problem Discovery",
    "3. Stakeholders / Personas",
    "4. Requirements",
    "Non-Functional Requirements",
    "Threat Model",
    "Constraints",
    "Assumptions",
    "Dependencies",
    "5. Scope",
    "6. Use Cases",
    "7. Solution Design",
    "Interface Contract",
    "10. Verification Plan",
]


def _drive(*, fixture: str, depth: str, out: Path) -> None:
    """Drive the real specify emitter on a fixture; raise on a stage failure."""
    proc = subprocess.run(
        [
            sys.executable,
            str(_DRIVER),
            "--fixture",
            fixture,
            "--depth",
            depth,
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, (
        f"driver failed for {fixture}@{depth}: rc={proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert out.exists(), f"driver wrote no document for {fixture}@{depth}"


def _run_inspector(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a WP-003 inspector as a subprocess from the scripts dir.

    ``cwd`` is the scripts dir so the inspector's ``from _doc_section_parse
    import ...`` resolves — exactly how the scenarios invoke it.
    """
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        cwd=str(_SCRIPTS_DIR),
        timeout=60,
    )


def test_lite_document_has_all_mandatory_sections(tmp_path: Path) -> None:
    """SC-01 / FR-01 / FR-11: driving sample-user-facing at LITE produces a
    document carrying every mandatory Target-Structure section.

    The whole point of always-comprehensive: the cheapest depth still emits the
    full structure. ``_assert_doc_sections --require <all>`` must exit 0.
    """
    out = tmp_path / "design.md"
    _drive(fixture="sample-user-facing", depth="lite", out=out)

    proc = _run_inspector(
        _ASSERT_DOC_SECTIONS,
        ["--require", ",".join(_MANDATORY_SECTIONS), str(out)],
    )
    assert proc.returncode == 0, (
        "lite document is missing mandatory section(s) — always-comprehensive "
        f"emission is not complete:\n{proc.stderr}"
    )


def test_section_set_identical_across_depths(tmp_path: Path) -> None:
    """SC-02 / FR-02: lite, standard, and deep documents have the IDENTICAL
    section set. Depth sizes only the interview, never which sections exist.

    ``_assert_same_section_set`` over all three must exit 0.
    """
    lite = tmp_path / "lite.md"
    standard = tmp_path / "standard.md"
    deep = tmp_path / "deep.md"
    _drive(fixture="sample-user-facing", depth="lite", out=lite)
    _drive(fixture="sample-user-facing", depth="standard", out=standard)
    _drive(fixture="sample-user-facing", depth="deep", out=deep)

    proc = _run_inspector(
        _ASSERT_SAME_SECTION_SET,
        [str(lite), str(standard), str(deep)],
    )
    assert proc.returncode == 0, (
        "section sets differ across depths — depth is still coupled to "
        f"doc-existence (FR-02 violation):\n{proc.stderr}"
    )


def test_unpopulated_section_marked_na(tmp_path: Path) -> None:
    """SC-03 / NFR-R01: a fixture with no dependencies marks the Dependencies
    section ``n/a — <reason>`` rather than dropping it.

    ``_assert_section_na --section dependencies`` must exit 0 (present AND a
    justified n/a or populated).
    """
    out = tmp_path / "no-deps.md"
    _drive(fixture="no-dependencies", depth="lite", out=out)

    proc = _run_inspector(
        _ASSERT_SECTION_NA,
        ["--section", "dependencies", str(out)],
    )
    assert proc.returncode == 0, (
        "Dependencies section is missing or a bare n/a — degrade detail, not "
        f"existence (NFR-R01 violation):\n{proc.stderr}"
    )


def test_nfr_section_measurable(tmp_path: Path) -> None:
    """SC-05 / FR-06: the always-on NFR section carries a MEASURABLE target per
    category — performance, security, reliability — not an adjective.

    ``_assert_measurable_nfr --categories performance,security,reliability``
    must exit 0.
    """
    out = tmp_path / "design.md"
    _drive(fixture="sample-user-facing", depth="lite", out=out)

    proc = _run_inspector(
        _ASSERT_MEASURABLE_NFR,
        ["--categories", "performance,security,reliability", str(out)],
    )
    assert proc.returncode == 0, (
        "an NFR category is missing or adjective-only — the always-on NFR "
        f"section must state measurable targets (FR-06 violation):\n{proc.stderr}"
    )


@pytest.mark.parametrize("depth", ["lite", "standard", "deep"])
def test_interface_contract_skeleton_present_at_every_depth(
    depth: str, tmp_path: Path
) -> None:
    """CF-05 stub: the interface-contract section skeleton is present at every
    depth. WP-011 fills it to full CF-10; this WP lands the skeleton so WP-009's
    tool-walk has a target and contract-first ordering is preserved (BDR-001).
    """
    out = tmp_path / f"design-{depth}.md"
    _drive(fixture="sample-user-facing", depth=depth, out=out)

    proc = _run_inspector(
        _ASSERT_SECTION_NA,
        ["--section", "interface contract", str(out)],
    )
    assert proc.returncode == 0, (
        "Interface Contract section skeleton is missing or a bare n/a at "
        f"{depth} (CF-05 stub not landed):\n{proc.stderr}"
    )
