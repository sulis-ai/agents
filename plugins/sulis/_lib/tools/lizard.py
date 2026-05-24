"""Lizard wrapper — covers CQ-01 (cyclomatic complexity).

Native pip-installable. Output: CSV format (avoids xml.etree dependency
which is broken in Python 3.14 on some platforms).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from ._detection import ToolMode, tool_available
from ._runner import ToolResult, run_tool

NATIVE_BINARY = "lizard"
TOOL_NAME = "lizard"

DEFAULT_CCN_THRESHOLD = 15
HIGH_CCN_THRESHOLD = 25


def is_available() -> ToolMode:
    return tool_available(TOOL_NAME, native_binary=NATIVE_BINARY)


def run(
    *,
    repo_root: str,
    threshold: int = DEFAULT_CCN_THRESHOLD,
    timeout: int = 180,
) -> ToolResult:
    """Invoke Lizard with CSV output against repo_root.

    Args:
        repo_root: absolute path to repository
        threshold: CCN threshold (functions above appear in --warnings, but
            we filter ourselves from CSV)
        timeout: subprocess timeout in seconds
    """
    mode = is_available()
    if mode == ToolMode.NOT_AVAILABLE:
        return run_tool([], mode=mode)

    cmd = [NATIVE_BINARY, "--csv", repo_root]
    return run_tool(cmd, mode=mode, version="lizard", timeout=timeout, cwd=repo_root)


def parse_findings(result: ToolResult, repo_root: str) -> list[dict[str, Any]]:
    """Parse Lizard CSV output. Format per row:
        NLOC, CCN, token, param_count, length, location

    Location format: '<func_name>@<line>-<endline>@<filepath>'
    """
    if result.not_assessed or not result.stdout.strip():
        return []

    findings: list[dict[str, Any]] = []
    repo_path = Path(repo_root)

    # CSV may have a header — sniff it
    reader = csv.reader(io.StringIO(result.stdout))
    for row in reader:
        if len(row) < 6:
            continue
        # Skip header row if present
        if not row[0].strip().isdigit():
            continue

        try:
            nloc = int(row[0])
            ccn = int(row[1])
        except ValueError:
            continue

        if ccn < DEFAULT_CCN_THRESHOLD:
            continue

        location = row[5].strip().strip('"')
        file_path, func_name, line = _parse_location(location)

        try:
            abs_path = Path(file_path)
            rel = abs_path.relative_to(repo_path) if abs_path.is_absolute() else abs_path
        except ValueError:
            rel = Path(file_path)

        severity = "high" if ccn >= HIGH_CCN_THRESHOLD else "concern"

        findings.append({
            "tool": "lizard",
            "rule_id": "CQ-01-cyclomatic-complexity",
            "file": str(rel),
            "line": line,
            "severity": severity,
            "message": f"Function {func_name} has cyclomatic complexity {ccn} (threshold {DEFAULT_CCN_THRESHOLD}; NLOC={nloc})",
            "extras": {
                "function_name": func_name,
                "ccn": ccn,
                "nloc": nloc,
                "tool_mode": result.mode_used.value,
            },
        })
    return findings


def _parse_location(location: str) -> tuple[str, str, int]:
    """Parse a Lizard CSV location like 'func_name@line-endline@filepath'."""
    parts = location.split("@")
    if len(parts) >= 3:
        func_name = parts[0]
        line_range = parts[1]
        file_path = "@".join(parts[2:])  # rejoin in case path contains @
        try:
            line = int(line_range.split("-")[0])
        except (ValueError, IndexError):
            line = 1
        return file_path, func_name, line

    # Fallback: try '@line@filepath' or 'func@filepath' shapes
    return location, "<unknown>", 1
