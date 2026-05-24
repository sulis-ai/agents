"""Semgrep wrapper — covers SEC-01/03/04/05/06 + DAT-03 + INF-04.

Docker-preferred (returntocorp/semgrep:latest); native binary fallback.
Output parsing: Semgrep --json results[] array.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._detection import ToolMode, tool_available
from ._runner import ToolResult, run_tool

DOCKER_IMAGE = "returntocorp/semgrep:latest"
NATIVE_BINARY = "semgrep"
TOOL_NAME = "semgrep"

# Default rule packs — broad coverage across SEC + DAT + INF primitives.
# Founder skill picks the appropriate config based on primitive scope.
DEFAULT_CONFIGS = ["p/security-audit", "p/owasp-top-ten", "p/secrets"]


def is_available() -> ToolMode:
    """Return DOCKER / NATIVE / NOT_AVAILABLE."""
    return tool_available(TOOL_NAME, native_binary=NATIVE_BINARY, docker_image=DOCKER_IMAGE)


def run(
    *,
    repo_root: str,
    configs: list[str] | None = None,
    timeout: int = 300,
) -> ToolResult:
    """Invoke Semgrep against repo_root with the given rule configs.

    Args:
        repo_root: absolute path to repository
        configs: Semgrep config arguments (--config). Defaults to DEFAULT_CONFIGS.
        timeout: subprocess timeout in seconds

    Returns:
        ToolResult with JSON-formatted stdout on success.
    """
    mode = is_available()
    configs = configs or DEFAULT_CONFIGS

    if mode == ToolMode.DOCKER:
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{repo_root}:/src",
            "--workdir", "/src",
            DOCKER_IMAGE,
            "semgrep", "scan",
            "--json", "--quiet",
            "--metrics=off",
        ]
        for config in configs:
            cmd.extend(["--config", config])
    elif mode == ToolMode.NATIVE:
        cmd = [NATIVE_BINARY, "scan", "--json", "--quiet", "--metrics=off"]
        for config in configs:
            cmd.extend(["--config", config])
        cmd.append(repo_root)
    else:
        cmd = []

    return run_tool(cmd, mode=mode, version="semgrep", timeout=timeout, cwd=repo_root)


def parse_findings(result: ToolResult, repo_root: str) -> list[dict[str, Any]]:
    """Parse Semgrep JSON output into sulis Finding envelope shape.

    Returns list of findings; empty list on NOT_AVAILABLE or parse failure.
    """
    if result.not_assessed or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return []

    findings: list[dict[str, Any]] = []
    repo_path = Path(repo_root)
    for item in data.get("results", []):
        path = item.get("path", "")
        # Strip Docker /src/ prefix if present
        if path.startswith("/src/"):
            path = path[len("/src/"):]
        try:
            abs_path = Path(path)
            if abs_path.is_absolute():
                rel = abs_path.relative_to(repo_path)
            else:
                rel = abs_path
        except ValueError:
            rel = Path(path)

        check_id = item.get("check_id", "unknown")
        severity_raw = item.get("extra", {}).get("severity", "INFO").upper()
        severity = _map_severity(severity_raw)
        message = item.get("extra", {}).get("message", "")
        line = item.get("start", {}).get("line", 1)

        findings.append({
            "tool": "semgrep",
            "rule_id": check_id,
            "file": str(rel),
            "line": line,
            "severity": severity,
            "message": message.strip().splitlines()[0] if message else check_id,
            "extras": {
                "semgrep_severity": severity_raw,
                "tool_mode": result.mode_used.value,
            },
        })
    return findings


def _map_severity(semgrep_severity: str) -> str:
    """Map Semgrep severity to sulis Finding severity."""
    mapping = {
        "ERROR": "critical",
        "WARNING": "high",
        "INFO": "advisory",
    }
    return mapping.get(semgrep_severity, "advisory")
