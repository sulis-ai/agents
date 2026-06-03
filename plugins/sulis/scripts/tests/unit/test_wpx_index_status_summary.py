"""Unit tests for #143 — `wpx-index flip-status` keeps the
`## Status Summary` counts in sync with WP-table cells.

Before the fix, flip-status updated the WP row but left the summary table
stale: after flipping WP-001 to done, the row read "done" while the summary
still said pending:N, done:0. The counts drifted from the row truth.

The fix recomputes the summary atomically with the row write. The summary
table's existing row order + status set is preserved (some projects track a
narrow set — pending/in_progress/done/blocked — others extend); only the
Count column is rewritten.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path


_SCRIPTS = Path(__file__).resolve().parents[2]
_WPX_INDEX = _SCRIPTS / "wpx-index"


def _load_wpx_index():
    loader = SourceFileLoader("wpx_index_mod", str(_WPX_INDEX))
    spec = importlib.util.spec_from_loader("wpx_index_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


wpx = _load_wpx_index()


_INDEX_WITH_SUMMARY = """# Work Package Index — Test

## Status Summary

| Status | Count |
|---|---|
| pending | 3 |
| in_progress | 0 |
| done | 0 |
| blocked | 0 |

## Work Packages

| ID     | Title  | Primitive | Status      | Depends On | Blocks |
|--------|--------|-----------|-------------|------------|--------|
| WP-001 | Alpha  | Create    | pending     | —          | WP-002 |
| WP-002 | Beta   | Extend    | pending     | WP-001     | —      |
| WP-003 | Gamma  | Harden    | pending     | —          | —      |
"""


def _write_project(tmp_path: Path, index_text: str) -> Path:
    wp_dir = tmp_path / ".architecture" / "proj" / "work-packages"
    wp_dir.mkdir(parents=True)
    (wp_dir / "INDEX.md").write_text(index_text, encoding="utf-8")
    return wp_dir


def _ns(tmp_path: Path, **kw) -> argparse.Namespace:
    base = {"repo_root": str(tmp_path), "project": "proj"}
    base.update(kw)
    return argparse.Namespace(**base)


def _run(fn, ns) -> dict:
    buf = io.StringIO()
    code = None
    with redirect_stdout(buf):
        try:
            fn(ns)
        except SystemExit as exc:
            code = exc.code
    out = buf.getvalue().strip()
    data = json.loads(out) if out else {}
    data["_exit"] = code
    return data


def _index_text(tmp_path: Path) -> str:
    return (tmp_path / ".architecture" / "proj" / "work-packages"
            / "INDEX.md").read_text(encoding="utf-8")


def test_flip_status_recomputes_summary_counts(tmp_path):
    """Flipping WP-001 pending→done must rewrite the summary so pending
    becomes 2 and done becomes 1, atomically with the row write."""
    _write_project(tmp_path, _INDEX_WITH_SUMMARY)
    ns = _ns(tmp_path, wp="WP-001", to="done", expected="pending")
    result = _run(wpx.cmd_flip_status, ns)
    assert result["ok"] is True, f"flip failed: {result}"

    text = _index_text(tmp_path)

    def _summary_count(status: str) -> str:
        """Read the count for `status` from the Status Summary table.
        Width-tolerant: parses cells, not raw substrings."""
        in_summary = False
        for line in text.splitlines():
            if line.strip().lower().startswith("## status summary"):
                in_summary = True
                continue
            if in_summary and line.startswith("## "):
                break
            if in_summary and line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 2 and cells[0] == status:
                    return cells[1]
        raise AssertionError(f"summary row {status!r} not found in:\n{text}")

    # Row updated (existing behaviour) — cell-based, width-tolerant.
    row_001 = next(
        (l for l in text.splitlines()
         if l.startswith("| WP-001 ")),
        None,
    )
    assert row_001 is not None and "done" in row_001, (
        f"WP-001 row not flipped to done: {row_001}"
    )
    # Summary counts updated (the fix).
    assert _summary_count("pending") == "2"
    assert _summary_count("done") == "1"
    assert _summary_count("in_progress") == "0"
    assert _summary_count("blocked") == "0"


def test_flip_status_summary_preserves_extra_statuses(tmp_path):
    """A summary with a status not present in the WPs (e.g. blocked) must
    keep that row at 0, not drop it. Projects pick which statuses to track."""
    _write_project(tmp_path, _INDEX_WITH_SUMMARY)
    ns = _ns(tmp_path, wp="WP-002", to="in_progress", expected="pending")
    result = _run(wpx.cmd_flip_status, ns)
    assert result["ok"] is True

    text = _index_text(tmp_path)
    # Summary now: pending:2, in_progress:1, done:0, blocked:0.
    for status, count in [
        ("pending", "2"),
        ("in_progress", "1"),
        ("done", "0"),
        ("blocked", "0"),
    ]:
        # Robust to column-width variation
        line = next(
            (l for l in text.splitlines()
             if l.startswith("|") and l.strip("|").strip().startswith(status + " ")
             or l.strip("|").strip() == status),
            None,
        )
        # Less brittle: locate row by its first cell, then assert count appears
        for l in text.splitlines():
            cells = [c.strip() for c in l.strip("|").split("|")]
            if cells[:1] == [status]:
                assert cells[1] == count, (
                    f"summary[{status}] expected {count}, got {cells[1]} "
                    f"in {text}"
                )
                break
        else:
            raise AssertionError(f"summary row for {status} missing: {text}")


def test_flip_status_no_summary_section_is_noop(tmp_path):
    """An INDEX without a `## Status Summary` section must still allow
    flip-status to succeed — the helper silently no-ops on missing summary."""
    minimal = """# WPs

## Work Packages

| ID     | Title | Primitive | Status  | Depends On | Blocks |
|--------|-------|-----------|---------|------------|--------|
| WP-001 | Alpha | Create    | pending | —          | —      |
"""
    _write_project(tmp_path, minimal)
    ns = _ns(tmp_path, wp="WP-001", to="done", expected="pending")
    result = _run(wpx.cmd_flip_status, ns)
    assert result["ok"] is True, f"flip failed: {result}"
    text = _index_text(tmp_path)
    assert "done" in text
    assert "## Status Summary" not in text
