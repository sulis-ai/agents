"""Trivy wrapper — covers SC-01..04 + INF-01 (base image).

Docker-preferred (aquasec/trivy:latest); native binary fallback.
Output: JSON with Results[] array containing Vulnerabilities[] per target.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._detection import ToolMode, tool_available
from ._runner import ToolResult, run_tool

DOCKER_IMAGE = "aquasec/trivy:latest"
NATIVE_BINARY = "trivy"
TOOL_NAME = "trivy"


def is_available() -> ToolMode:
    return tool_available(TOOL_NAME, native_binary=NATIVE_BINARY, docker_image=DOCKER_IMAGE)


def run_fs_scan(
    *,
    repo_root: str,
    severity_filter: str = "HIGH,CRITICAL",
    timeout: int = 600,
) -> ToolResult:
    """Invoke Trivy filesystem scan against repo_root.

    Covers SC-01 CVEs in dependencies; also feeds SC-02 (freshness) +
    SC-03 (SBOM) + SC-04 (transitive depth) via the same scan output.
    """
    mode = is_available()
    args = [
        "fs",
        "--format", "json",
        "--quiet",
        "--severity", severity_filter,
        "--scanners", "vuln",
        "/src" if mode == ToolMode.DOCKER else repo_root,
    ]

    if mode == ToolMode.DOCKER:
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{repo_root}:/src",
            "--workdir", "/src",
            DOCKER_IMAGE,
            *args,
        ]
    elif mode == ToolMode.NATIVE:
        cmd = [NATIVE_BINARY, *args]
    else:
        cmd = []

    return run_tool(cmd, mode=mode, version="trivy", timeout=timeout, cwd=repo_root)


def parse_findings(result: ToolResult, repo_root: str) -> list[dict[str, Any]]:
    """Parse Trivy JSON output into sulis Finding envelope shape."""
    if result.not_assessed or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return []

    findings: list[dict[str, Any]] = []
    repo_path = Path(repo_root)

    for trivy_result in data.get("Results", []):
        target = trivy_result.get("Target", "")
        # Strip Docker /src/ prefix if present
        if target.startswith("/src/"):
            target = target[len("/src/"):]
        try:
            abs_path = Path(target)
            rel = abs_path.relative_to(repo_path) if abs_path.is_absolute() else abs_path
        except ValueError:
            rel = Path(target)

        for vuln in trivy_result.get("Vulnerabilities", []) or []:
            vuln_id = vuln.get("VulnerabilityID", "unknown-cve")
            pkg_name = vuln.get("PkgName", "")
            installed = vuln.get("InstalledVersion", "")
            fixed = vuln.get("FixedVersion", "")
            severity_raw = vuln.get("Severity", "MEDIUM").upper()
            title = vuln.get("Title", "")

            severity = _map_severity(severity_raw)
            fix_note = f" (fix: {fixed})" if fixed else " (no fix yet)"
            message = f"{vuln_id} in {pkg_name}@{installed}{fix_note}"
            if title:
                message += f": {title}"

            findings.append({
                "tool": "trivy",
                "rule_id": vuln_id,
                "file": str(rel),
                "line": 1,
                "severity": severity,
                "message": message,
                "extras": {
                    "pkg_name": pkg_name,
                    "installed_version": installed,
                    "fixed_version": fixed,
                    "trivy_severity": severity_raw,
                    "tool_mode": result.mode_used.value,
                },
            })
    return findings


def _map_severity(trivy_severity: str) -> str:
    """Map Trivy severity to sulis Finding severity."""
    mapping = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "concern",
        "LOW": "advisory",
        "UNKNOWN": "advisory",
    }
    return mapping.get(trivy_severity, "advisory")
