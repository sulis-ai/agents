"""jscpd wrapper — covers CQ-03 (code duplication).

Docker-preferred (sebbo2002/jscpd:latest); npx fallback if Node available.
Output: JSON report with duplicates[] array.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ._detection import ToolMode, tool_available
from ._runner import ToolResult, run_tool

DOCKER_IMAGE = "sebbo2002/jscpd:latest"
NATIVE_BINARY = "jscpd"
TOOL_NAME = "jscpd"


def is_available() -> ToolMode:
    """jscpd: prefer Docker; fall back to native (npx fallback handled by caller)."""
    mode = tool_available(TOOL_NAME, native_binary=NATIVE_BINARY, docker_image=DOCKER_IMAGE)
    if mode != ToolMode.NOT_AVAILABLE:
        return mode
    # Check for npx (Node) as a deeper fallback
    if shutil.which("npx") is not None:
        return ToolMode.NATIVE  # we'll use npx in run()
    return ToolMode.NOT_AVAILABLE


def run(
    *,
    repo_root: str,
    min_lines: int = 5,
    min_tokens: int = 50,
    timeout: int = 300,
) -> ToolResult:
    """Invoke jscpd against repo_root.

    Args:
        repo_root: absolute path to repository
        min_lines: minimum duplicate length in lines (default 5)
        min_tokens: minimum duplicate length in tokens (default 50)
        timeout: subprocess timeout
    """
    mode = is_available()
    if mode == ToolMode.NOT_AVAILABLE:
        return run_tool([], mode=mode)

    common_args = [
        "--reporters", "json",
        "--silent",
        "--min-lines", str(min_lines),
        "--min-tokens", str(min_tokens),
    ]

    if mode == ToolMode.DOCKER:
        # Output directory for the JSON report
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{repo_root}:/src",
            "--workdir", "/src",
            DOCKER_IMAGE,
            "--output", "/src/.jscpd_temp",
            "--path", "/src",
            *common_args,
        ]
    elif shutil.which(NATIVE_BINARY):
        cmd = [
            NATIVE_BINARY,
            "--output", str(Path(repo_root) / ".jscpd_temp"),
            "--path", repo_root,
            *common_args,
        ]
    else:
        # npx fallback
        cmd = [
            "npx", "--yes", "jscpd",
            "--output", str(Path(repo_root) / ".jscpd_temp"),
            "--path", repo_root,
            *common_args,
        ]

    return run_tool(cmd, mode=mode, version="jscpd", timeout=timeout, cwd=repo_root)


def parse_findings(result: ToolResult, repo_root: str) -> list[dict[str, Any]]:
    """Parse jscpd output into sulis Finding envelope shape.

    jscpd writes to {output}/jscpd-report.json. Read that file.
    """
    if result.not_assessed:
        return []

    report_path = Path(repo_root) / ".jscpd_temp" / "jscpd-report.json"
    if not report_path.exists():
        return []

    try:
        data = json.loads(report_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    findings: list[dict[str, Any]] = []
    repo_path = Path(repo_root)

    for dup in data.get("duplicates", []):
        first = dup.get("firstFile", {})
        second = dup.get("secondFile", {})
        lines = dup.get("lines", 0)

        first_name = first.get("name", "")
        second_name = second.get("name", "")
        try:
            rel_first = Path(first_name).relative_to(repo_path) if Path(first_name).is_absolute() else Path(first_name)
        except ValueError:
            rel_first = Path(first_name)
        try:
            rel_second = Path(second_name).relative_to(repo_path) if Path(second_name).is_absolute() else Path(second_name)
        except ValueError:
            rel_second = Path(second_name)

        severity = "concern" if lines >= 10 else "advisory"

        findings.append({
            "tool": "jscpd",
            "rule_id": "CQ-03-code-duplication",
            "file": str(rel_first),
            "line": first.get("start", 1),
            "severity": severity,
            "message": f"{lines}-line duplicate also at {rel_second}:{second.get('start', 1)}",
            "extras": {
                "duplicate_file": str(rel_second),
                "duplicate_start": second.get("start", 1),
                "duplicate_end": second.get("end", 1),
                "lines": lines,
                "tokens": dup.get("tokens", 0),
                "tool_mode": result.mode_used.value,
            },
        })

    # Clean up the temp directory
    try:
        shutil.rmtree(report_path.parent)
    except OSError:
        pass

    return findings
