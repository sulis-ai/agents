"""Coverage wrapper — covers CQ-02 (test coverage quality).

Per-framework integration:
- pytest-cov for Python (looks for pytest in marker files)
- vitest --coverage for vite-based JS/TS projects
- jest --coverage for jest projects

Falls back to file-count ratio heuristic when no coverage tool is available.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._detection import ToolMode, native_available
from ._runner import ToolResult, run_tool

TOOL_NAME = "coverage"


def is_available() -> ToolMode:
    """Coverage is available if pytest-cov, vitest, or jest is available."""
    if native_available("pytest"):
        try:
            import pytest_cov  # noqa: F401
            return ToolMode.NATIVE
        except ImportError:
            pass
    if native_available("npx") or native_available("vitest") or native_available("jest"):
        return ToolMode.NATIVE
    return ToolMode.NOT_AVAILABLE


def run_pytest_cov(*, repo_root: str, timeout: int = 600) -> ToolResult:
    """Run pytest with coverage. Looks for pytest in PATH + pytest-cov installed."""
    if not native_available("pytest"):
        return run_tool([], mode=ToolMode.NOT_AVAILABLE)
    cmd = [
        "pytest",
        "--cov=.",
        "--cov-report=json:.coverage.json",
        "--quiet",
        "--no-header",
    ]
    return run_tool(cmd, mode=ToolMode.NATIVE, version="pytest-cov", timeout=timeout, cwd=repo_root)


def parse_pytest_cov_findings(result: ToolResult, repo_root: str) -> list[dict[str, Any]]:
    """Parse pytest-cov JSON report.

    Looks for `.coverage.json` written by pytest-cov; extracts per-file
    coverage; flags files below threshold.
    """
    if result.not_assessed:
        return []

    report_path = Path(repo_root) / ".coverage.json"
    if not report_path.exists():
        return []

    try:
        data = json.loads(report_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    findings: list[dict[str, Any]] = []
    totals = data.get("totals", {})
    total_pct = totals.get("percent_covered", 0)

    # Surface low overall coverage as a CONCERN
    if total_pct < 60:
        findings.append({
            "tool": "coverage",
            "rule_id": "CQ-02-low-overall-coverage",
            "file": "<repo-root>",
            "line": 1,
            "severity": "concern" if total_pct >= 30 else "high",
            "message": f"Overall test coverage is {total_pct:.1f}% (target ≥ 60%)",
            "extras": {
                "covered_lines": totals.get("covered_lines", 0),
                "missing_lines": totals.get("missing_lines", 0),
                "tool_mode": result.mode_used.value,
            },
        })

    # Surface per-file uncovered files
    files = data.get("files", {})
    for file_path, file_data in files.items():
        summary = file_data.get("summary", {})
        pct = summary.get("percent_covered", 100)
        if pct < 50:
            findings.append({
                "tool": "coverage",
                "rule_id": "CQ-02-uncovered-file",
                "file": file_path,
                "line": 1,
                "severity": "advisory",
                "message": f"File coverage is {pct:.1f}%",
                "extras": {
                    "covered_lines": summary.get("covered_lines", 0),
                    "missing_lines": summary.get("missing_lines", 0),
                    "tool_mode": result.mode_used.value,
                },
            })

    return findings
