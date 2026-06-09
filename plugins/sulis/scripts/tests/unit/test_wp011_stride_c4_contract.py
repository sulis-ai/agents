"""Behavioural tests for the STRIDE / C4 / interface-contract sub-templates (WP-011).

KIND = methodology: the happy-path test drives the specify stage on the
`sample-tool-surface` fixture (via `_drive_specify.py`) and asserts the produced
document carries an always-on STRIDE threat model (FR-15/SC-15), C4
architecture-at-levels (context/container/component — FR-16/SC-16), and an
interface contract whose every operation carries all four CF-10 founder-
reviewable dimensions (FR-18/SC-18). The three assertion scripts
(`_assert_stride.py`, `_assert_c4_levels.py`, `_assert_interface_contract.py`)
are invoked as CLI subprocesses — the same entrypoints the SC-15/16/18 scenarios
use.

The two negative tests build a small synthetic document inline so they can
exercise the *failure* path precisely: a C4 section with only two levels, and a
contract operation missing the user-guide CF-10 dimension.

Tests live here under `tests/unit/` (not `tests/`) because branch-ci runs only
`pytest tests/unit/` — a test placed at `tests/` would never run in CI
(lesson #60).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
# tests/unit/  →  tests/  →  scripts/
_SCRIPTS_DIR = _HERE.parent.parent
_DRIVER = _SCRIPTS_DIR / "_drive_specify.py"
_ASSERT_STRIDE = _SCRIPTS_DIR / "_assert_stride.py"
_ASSERT_C4 = _SCRIPTS_DIR / "_assert_c4_levels.py"
_ASSERT_CONTRACT = _SCRIPTS_DIR / "_assert_interface_contract.py"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Invoke an assertion script (or the driver) as a CLI subprocess."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _drive_tool_surface(out: Path) -> None:
    """Drive the sample-tool-surface fixture to a document at `out`."""
    proc = _run(
        _DRIVER,
        "--fixture",
        "sample-tool-surface",
        "--depth",
        "deep",
        "--out",
        str(out),
    )
    assert proc.returncode == 0, (
        f"drive-specify failed: rc={proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert out.exists(), "driver wrote no document"


def test_doc_carries_stride_c4_and_contract(tmp_path: Path) -> None:
    """SC-15/16/18 happy path: a driven tool-surface document passes all three
    sub-template assertions.

    Drives the sample-tool-surface fixture, then runs `_assert_stride`,
    `_assert_c4_levels`, and `_assert_interface_contract` over the produced
    document — each must exit 0.
    """
    doc = tmp_path / "design.md"
    _drive_tool_surface(doc)

    stride = _run(_ASSERT_STRIDE, str(doc))
    assert stride.returncode == 0, (
        f"_assert_stride failed on a driven document (SC-15):\n{stride.stderr}"
    )

    c4 = _run(_ASSERT_C4, str(doc))
    assert c4.returncode == 0, (
        f"_assert_c4_levels failed on a driven document (SC-16):\n{c4.stderr}"
    )

    contract = _run(_ASSERT_CONTRACT, str(doc))
    assert contract.returncode == 0, (
        f"_assert_interface_contract failed on a driven document (SC-18):\n"
        f"{contract.stderr}"
    )


def test_missing_cf10_dimension_is_incomplete(tmp_path: Path) -> None:
    """SC-18 negative: a contract operation missing the user-guide CF-10
    dimension is flagged incomplete (non-zero).

    Builds a document with an interface-contract operation that carries three of
    the four CF-10 dimensions (auth, audience, error fixes) but omits the
    plain-language user guide. The asserter must exit non-zero and name the
    missing dimension.
    """
    doc = tmp_path / "incomplete-contract.md"
    doc.write_text(
        "# Design — sample\n\n"
        "## 7. Solution Design\n\n"
        "### Interface Contract\n\n"
        "Interface contract — tool operations:\n\n"
        "#### Operation: `export_report`\n\n"
        "| Dimension | Value |\n"
        "|-----------|-------|\n"
        "| **Schema** | in: report_id, format; out: file_path |\n"
        "| **Errors** | Protocol: none. Expected: NotFound. Internal: none. |\n"
        "| **Auth / permissions** | none |\n"
        "| **Audience** | operator / agent |\n"
        "| **Error fixes** | NotFound — supply a valid report_id. |\n",
        encoding="utf-8",
    )

    proc = _run(_ASSERT_CONTRACT, str(doc))
    assert proc.returncode != 0, (
        "_assert_interface_contract passed a contract operation missing the "
        "user-guide CF-10 dimension; expected an incomplete (non-zero) verdict"
    )
    assert "user guide" in proc.stderr.lower(), (
        f"asserter did not name the missing 'user guide' dimension:\n{proc.stderr}"
    )


def test_two_levels_only_fails(tmp_path: Path) -> None:
    """A C4 section with only context + container (no component) fails.

    The architecture-at-levels assertion (FR-16/SC-16) requires all three
    levels. A document that documents context and container but not component is
    incomplete — the asserter must exit non-zero and name the missing level.
    """
    doc = tmp_path / "two-c4-levels.md"
    doc.write_text(
        "# Design — sample\n\n"
        "## 7. Solution Design\n\n"
        "### Architecture-at-Levels (C4)\n\n"
        "#### Level 1 — System Context\n\n"
        "```mermaid\ngraph TB\n  A --> B\n```\n\n"
        "#### Level 2 — Container\n\n"
        "```mermaid\ngraph TB\n  C --> D\n```\n",
        encoding="utf-8",
    )

    proc = _run(_ASSERT_C4, str(doc))
    assert proc.returncode != 0, (
        "_assert_c4_levels passed a two-level (context+container, no component) "
        "C4 section; expected a non-zero verdict"
    )
    assert "component" in proc.stderr.lower(), (
        f"asserter did not name the missing 'component' level:\n{proc.stderr}"
    )


# ─── In-process unit tests (importable surface + defensive branches) ─────────
#
# conftest at tests/ puts the scripts dir on sys.path, so these imports resolve.

import _assert_stride  # noqa: E402
import _assert_c4_levels  # noqa: E402
import _assert_interface_contract  # noqa: E402


def test_stride_detects_all_six_categories() -> None:
    """The STRIDE asserter recognises a section carrying all six categories."""
    text = (
        "## 4. Requirements\n\n"
        "### Threat Model\n\n"
        "STRIDE analysis:\n\n"
        "| Category | Threat |\n|---|---|\n"
        "| Spoofing | x |\n| Tampering | x |\n| Repudiation | x |\n"
        "| Information disclosure | x |\n| Denial of service | x |\n"
        "| Elevation of privilege | x |\n"
    )
    assert _assert_stride.stride_present(text) is True


def test_stride_absent_when_no_section() -> None:
    """A document with no threat-model section is flagged STRIDE-absent."""
    text = "# Design\n\n## 1. Executive Summary\n\nNothing here.\n"
    assert _assert_stride.stride_present(text) is False


def test_c4_missing_levels_lists_them() -> None:
    """The C4 helper lists exactly the missing levels."""
    text = (
        "### Architecture-at-Levels (C4)\n\n"
        "#### Level 1 — System Context\n\nx\n"
    )
    missing = _assert_c4_levels.missing_levels(text)
    assert "container" in missing
    assert "component" in missing
    assert "context" not in missing


def test_contract_missing_dimensions_reports_per_operation() -> None:
    """The contract helper reports the missing CF-10 dimension per operation."""
    text = (
        "### Interface Contract\n\n"
        "#### Operation: `foo`\n\n"
        "| **Auth / permissions** | none |\n"
        "| **Audience** | agent |\n"
        "| **User guide** | does foo |\n"
        "| **Error fixes** | n/a |\n\n"
        "#### Operation: `bar`\n\n"
        "| **Auth / permissions** | none |\n"
        "| **Audience** | agent |\n"
    )
    incomplete = _assert_interface_contract.incomplete_operations(text)
    # foo is complete (all 4); bar is missing user-guide + error-fixes.
    names = {op for op, _ in incomplete}
    assert "bar" in names
    assert "foo" not in names


def test_contract_no_operations_is_na_pass() -> None:
    """A contract section with the explicit n/a (no tool surface) passes —
    there are no operations to be incomplete."""
    text = (
        "### Interface Contract\n\n"
        "n/a — this change exposes no tool surface; the skeleton stands ready.\n"
    )
    assert _assert_interface_contract.incomplete_operations(text) == []


def test_main_exit_codes(tmp_path: Path) -> None:
    """Each asserter's main() returns 0 on a good doc, 2 on an unreadable path."""
    good = tmp_path / "good.md"
    # Build a doc that satisfies all three asserters.
    good.write_text(
        "# Design\n\n"
        "## 4. Requirements\n\n### Threat Model\n\n"
        "STRIDE: Spoofing Tampering Repudiation Information disclosure "
        "Denial of service Elevation of privilege\n\n"
        "## 7. Solution Design\n\n"
        "### Architecture-at-Levels (C4)\n\n"
        "#### Level 1 — System Context\n\nx\n\n"
        "#### Level 2 — Container\n\nx\n\n"
        "#### Level 3 — Component\n\nx\n\n"
        "### Interface Contract\n\n"
        "#### Operation: `foo`\n\n"
        "| **Auth / permissions** | none |\n"
        "| **Audience** | agent |\n"
        "| **User guide** | does foo |\n"
        "| **Error fixes** | n/a |\n",
        encoding="utf-8",
    )
    assert _assert_stride.main([str(good)]) == 0
    assert _assert_c4_levels.main([str(good)]) == 0
    assert _assert_interface_contract.main([str(good)]) == 0

    missing = tmp_path / "nope.md"
    assert _assert_stride.main([str(missing)]) == 2
    assert _assert_c4_levels.main([str(missing)]) == 2
    assert _assert_interface_contract.main([str(missing)]) == 2
