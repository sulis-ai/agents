"""testssl.sh wrapper — covers DAT-02 (TLS / cipher suite).

Docker-preferred (drwetter/testssl.sh:latest); native fallback (if testssl.sh
installed). Only runs when --url is provided to the consuming skill.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from ._detection import ToolMode, tool_available
from ._runner import ToolResult, run_tool

DOCKER_IMAGE = "drwetter/testssl.sh:latest"
NATIVE_BINARY = "testssl.sh"
TOOL_NAME = "testssl"


def is_available() -> ToolMode:
    return tool_available(TOOL_NAME, native_binary=NATIVE_BINARY, docker_image=DOCKER_IMAGE)


def run(
    *,
    url: str,
    timeout: int = 600,
) -> ToolResult:
    """Invoke testssl.sh against a URL.

    Args:
        url: deployed URL (e.g., "https://example.com")
        timeout: subprocess timeout (testssl is slow — default 10min)
    """
    mode = is_available()
    if mode == ToolMode.NOT_AVAILABLE:
        return run_tool([], mode=mode)

    # testssl.sh writes JSON to a file; we use --jsonfile-pretty for parsing
    tmp_dir = Path(tempfile.mkdtemp(prefix="testssl_"))
    jsonfile = tmp_dir / "result.json"

    if mode == ToolMode.DOCKER:
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{tmp_dir}:/output",
            DOCKER_IMAGE,
            "--jsonfile-pretty", "/output/result.json",
            "--quiet",
            "--color", "0",
            url,
        ]
    elif mode == ToolMode.NATIVE:
        cmd = [
            NATIVE_BINARY,
            "--jsonfile-pretty", str(jsonfile),
            "--quiet",
            "--color", "0",
            url,
        ]
    else:
        cmd = []

    result = run_tool(cmd, mode=mode, version="testssl", timeout=timeout)

    # Stitch the file content into the result's stdout for parse_findings
    if jsonfile.exists():
        try:
            content = jsonfile.read_text()
            return ToolResult(
                stdout=content,
                stderr=result.stderr,
                exit_code=result.exit_code,
                mode_used=result.mode_used,
                version=result.version,
                elapsed_seconds=result.elapsed_seconds,
            )
        except OSError:
            pass
    return result


def parse_findings(result: ToolResult, repo_root: str = "") -> list[dict[str, Any]]:
    """Parse testssl.sh JSON output into sulis Finding envelope shape."""
    if result.not_assessed or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return []

    findings: list[dict[str, Any]] = []
    # testssl.sh JSON shape: list of finding dicts
    items = data if isinstance(data, list) else data.get("scanResult", [])
    for item in items:
        severity_raw = item.get("severity", "INFO").upper()
        if severity_raw in {"OK", "INFO", "DEBUG"}:
            continue  # not actionable
        severity = _map_severity(severity_raw)
        finding_id = item.get("id", "tls-finding")
        finding_msg = item.get("finding", "")
        target = item.get("ip", item.get("host", "<deployed-url>"))

        findings.append({
            "tool": "testssl",
            "rule_id": f"DAT-02-{finding_id}",
            "file": str(target),
            "line": 1,
            "severity": severity,
            "message": finding_msg,
            "extras": {
                "testssl_severity": severity_raw,
                "tool_mode": result.mode_used.value,
            },
        })
    return findings


def _map_severity(testssl_severity: str) -> str:
    mapping = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "concern",
        "LOW": "advisory",
        "WARN": "concern",
    }
    return mapping.get(testssl_severity, "advisory")
