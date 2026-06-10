"""Behavioural tests for the walk-⊆-contract assertion (WP-013, FR-19/SC-19/NFR-D03).

KIND = methodology. This is the **integration WP of the contract-first seam**
(CF-05): it ties the tool-surface journey-walk (WP-009 — the *consumer* of the
contract's operations) to the interface-contract section (WP-011 — the
*producer*), and verifies the consumer's operations are a SUBSET of the
producer's declared operations. A walked operation absent from the contract is
an `OperationNotInContract` violation (FR-19): the walk can only classify what
the contract declares, so an operation walked but never declared must be added
to the contract first.

The seam tie is end-to-end and *real*: the happy-path / negative
`test_end_to_end_*` cases drive the actual WP-009 walk driver
(`_drive_journey_walk.py`) over a fixture to produce a genuine tool `## Journey
Walk` table, splice it together with a real WP-011-shaped interface-contract
section, and run the new `_assert_walk_subset_of_contract.py` over the composed
document — exercising the same CLI entrypoint the SC-19 scenario uses.

Tests live here under `tests/unit/` (not `tests/`) because branch-ci runs only
`pytest tests/unit/` — a test placed at `tests/` would never run in CI
(lesson #60). The WP frontmatter's `verification.artifact` names a `tests/`
path; this file lives under `tests/unit/` so it actually runs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# tests/unit/  →  tests/  →  scripts/
_SCRIPTS_DIR = _HERE.parent.parent
_ASSERT = _SCRIPTS_DIR / "_assert_walk_subset_of_contract.py"
_WALK_DRIVER = _SCRIPTS_DIR / "_drive_journey_walk.py"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Invoke a script as a CLI subprocess (the same entrypoint a scenario uses)."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


# ─── Document builders ───────────────────────────────────────────────────────


def _contract_section(operations: list[str]) -> str:
    r"""A WP-011-shaped interface-contract section declaring `operations`.

    Mirrors DESIGN §7.6: a Solution-Design sub-section anchored by the phrase
    "interface contract", with one `#### Operation: \`name\`` block per
    operation. (The CF-10 dimension completeness is WP-011's concern; this WP
    only cares which operation names are *declared*.)
    """
    blocks = [
        "## 7. Solution Design",
        "",
        "### 7.6 Interface Contract / ServiceSpec",
        "",
        "Interface contract — tool operations:",
        "",
    ]
    for op in operations:
        blocks.extend(
            [
                f"#### Operation: `{op}`",
                "",
                "| Dimension | Value |",
                "|-----------|-------|",
                "| **Schema** | in: x; out: y |",
                "| **Auth / permissions** | none |",
                "| **Audience** | operator / agent |",
                f"| **User guide** | does {op}. |",
                "| **Error fixes** | n/a. |",
                "",
            ]
        )
    return "\n".join(blocks)


def _tool_walk_fixture(tmp_path: Path, operations: list[str]) -> Path:
    """Write a WP-009 walk fixture whose tool-surface walk references `operations`.

    Each operation becomes a hop in a single tool-surface scenario, classified
    EXISTS (a handler + binding cited) so the produced table carries the
    operation name in its `hop` column — exactly the surface this WP checks.
    """
    import json

    fixture = {
        "journey": "machine-consumer drives specify/design",
        "scenarios": [
            {
                "id": "SC-tool-walk",
                "surface": "tool",
                "hops": [
                    {
                        "name": op,
                        "handler": f"_mod.{op}",
                        "binding": "library (in-process)",
                    }
                    for op in operations
                ],
            }
        ],
    }
    path = tmp_path / "walk-fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    return path


def _drive_tool_walk(tmp_path: Path, operations: list[str]) -> str:
    """Drive the real WP-009 walk driver and return the tool `## Journey Walk` md."""
    fixture = _tool_walk_fixture(tmp_path, operations)
    out = tmp_path / "walk-section.md"
    proc = _run(
        _WALK_DRIVER, "--fixture", str(fixture), "--surface", "tool", "--out", str(out)
    )
    # rc may be 0 (no bare gap) — every hop here is EXISTS, so expect 0.
    assert proc.returncode == 0, (
        f"walk driver failed: rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert out.exists(), "walk driver wrote no section"
    return out.read_text(encoding="utf-8")


def _compose_doc(tmp_path: Path, walk_md: str, contract_ops: list[str]) -> Path:
    """Splice a real driven walk table + a real contract section into one doc."""
    doc = tmp_path / "design.md"
    doc.write_text(
        "# Design — sample tool surface\n\n"
        + walk_md
        + "\n\n"
        + _contract_section(contract_ops)
        + "\n",
        encoding="utf-8",
    )
    return doc


# ─── End-to-end seam tie (the integration WP's heart) ────────────────────────


def test_end_to_end_walk_subset_of_contract_passes(tmp_path: Path) -> None:
    """SC-19 happy path: every walked tool operation is declared in the contract.

    Drives the real WP-009 walk over three operations, builds a contract that
    declares all three (plus an extra), composes them into one document, and
    asserts the new check exits 0 — the walk is a subset of the contract.
    """
    ops = ["classify_depth", "walk_tool_surface", "author_scenario"]
    walk_md = _drive_tool_walk(tmp_path, ops)
    # Contract is a superset (declares an extra op the walk doesn't reference).
    doc = _compose_doc(tmp_path, walk_md, ops + ["emit_decision"])

    proc = _run(_ASSERT, str(doc))
    assert proc.returncode == 0, (
        "walk ⊆ contract should pass when every walked op is declared "
        f"in the contract:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )


def test_end_to_end_walked_op_absent_from_contract_is_flagged(tmp_path: Path) -> None:
    """SC-19 negative: a walked operation absent from the contract is flagged.

    Drives the real WP-009 walk over three operations, but the contract declares
    only two of them. The third is an `OperationNotInContract` violation
    (FR-19) — the check must exit non-zero and name the offending operation.
    """
    walked = ["classify_depth", "walk_tool_surface", "rogue_undeclared_op"]
    declared = ["classify_depth", "walk_tool_surface"]  # missing rogue_undeclared_op
    walk_md = _drive_tool_walk(tmp_path, walked)
    doc = _compose_doc(tmp_path, walk_md, declared)

    proc = _run(_ASSERT, str(doc))
    assert proc.returncode != 0, (
        "a walked operation absent from the contract must fail (FR-19, "
        f"OperationNotInContract):\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert "rogue_undeclared_op" in proc.stderr, (
        f"the check did not name the offending walked operation:\n{proc.stderr}"
    )


# ─── In-process unit surface (importable; conftest puts scripts dir on path) ──

import _assert_walk_subset_of_contract as wsoc  # noqa: E402


def test_walked_op_absent_from_contract_is_flagged() -> None:
    """A walked op not declared in the contract is reported (FR-19, SC-19)."""
    walk_ops = {"classify_depth", "walk_tool_surface", "missing_op"}
    contract_ops = {"classify_depth", "walk_tool_surface"}
    offenders = wsoc.operations_not_in_contract(walk_ops, contract_ops)
    assert offenders == ["missing_op"]


def test_walk_subset_of_contract_passes() -> None:
    """Every walked op present in the contract ⇒ no offenders ⇒ subset holds."""
    walk_ops = {"classify_depth", "walk_tool_surface"}
    contract_ops = {"classify_depth", "walk_tool_surface", "author_scenario"}
    assert wsoc.operations_not_in_contract(walk_ops, contract_ops) == []


def test_crosskind_side_without_contract_ref_flagged() -> None:
    """A cross-kind side with no contract reference at all is flagged (SC-19).

    The degenerate "cross-kind side with no contract" case: the walk references
    operations but the contract declares none (empty set). Every walked op is
    then `OperationNotInContract` — the seam is unreviewable, so it must fail.
    """
    walk_ops = {"author_scenario", "verify_uc_flow_coverage"}
    contract_ops: set[str] = set()  # no contract reference on this side
    offenders = wsoc.operations_not_in_contract(walk_ops, contract_ops)
    assert sorted(offenders) == ["author_scenario", "verify_uc_flow_coverage"]


def test_extract_walked_tool_operations_reads_hop_column() -> None:
    """The walked-operation extractor reads the tool walk table's hop column."""
    walk_md = (
        "## Journey Walk\n\n"
        "Journey: x\n"
        "Surface: tool\n\n"
        "### SC-1\n\n"
        "| hop | evidence | status |\n"
        "| --- | --- | --- |\n"
        "| classify_depth | _mod.classify_depth | EXISTS |\n"
        "| walk_tool_surface | planned | planned-WP |\n"
    )
    assert wsoc.walked_tool_operations(walk_md) == {
        "classify_depth",
        "walk_tool_surface",
    }


def test_extract_walked_tool_operations_ignores_ui_surface() -> None:
    """Only the *tool* surface walk feeds the subset check; the UI walk is skipped."""
    doc = (
        "## Journey Walk\n\nJourney: x\nSurface: ui\n\n"
        "### SC-ui\n\n| hop | evidence | status |\n| --- | --- | --- |\n"
        "| ui_only_hop | comp.X | EXISTS |\n\n"
        "## Journey Walk\n\nJourney: x\nSurface: tool\n\n"
        "### SC-tool\n\n| hop | evidence | status |\n| --- | --- | --- |\n"
        "| classify_depth | _mod.classify_depth | EXISTS |\n"
    )
    assert wsoc.walked_tool_operations(doc) == {"classify_depth"}


def test_no_tool_walk_passes() -> None:
    """A document with no tool-surface walk has no consumer ⇒ nothing to check."""
    doc = (
        "# Design\n\n## Journey Walk\n\nJourney: x\nSurface: ui\n\n"
        "### SC-ui\n\n| hop | evidence | status |\n| --- | --- | --- |\n"
        "| ui_hop | comp.X | EXISTS |\n"
    )
    ok, offenders = wsoc.check(doc)
    assert ok is True
    assert offenders == []


def test_check_flags_undeclared_walked_op() -> None:
    """`check` returns ok=False + the offender when a walked op is undeclared."""
    doc = (
        "# Design\n\n## Journey Walk\n\nJourney: x\nSurface: tool\n\n"
        "### SC-tool\n\n| hop | evidence | status |\n| --- | --- | --- |\n"
        "| classify_depth | _mod.classify_depth | EXISTS |\n"
        "| undeclared | planned | planned-WP |\n\n"
        "## 7. Solution Design\n\n### 7.6 Interface Contract\n\n"
        "#### Operation: `classify_depth`\n\n| Dimension | Value |\n|---|---|\n"
        "| Schema | x |\n"
    )
    ok, offenders = wsoc.check(doc)
    assert ok is False
    assert offenders == ["undeclared"]


def test_cli_unreadable_file_returns_2(tmp_path: Path) -> None:
    """A missing document yields the bad-input exit code 2."""
    missing = tmp_path / "does-not-exist.md"
    proc = _run(_ASSERT, str(missing))
    assert proc.returncode == 2, f"expected exit 2 for unreadable file:\n{proc.stderr}"


def test_extract_contract_operations_reads_operation_headings() -> None:
    r"""The contract-operation extractor reads `#### Operation: \`name\`` headings."""
    contract = (
        "## 7. Solution Design\n\n### 7.6 Interface Contract\n\n"
        "#### Operation: `classify_depth`\n\n| Dimension | Value |\n|---|---|\n"
        "| Schema | x |\n\n"
        "#### Operation: `walk_tool_surface`\n\n| Dimension | Value |\n|---|---|\n"
        "| Schema | y |\n"
    )
    assert wsoc.contract_operations(contract) == {"classify_depth", "walk_tool_surface"}
