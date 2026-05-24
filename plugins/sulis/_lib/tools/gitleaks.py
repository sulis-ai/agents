"""Gitleaks wrapper — covers SEC-07 (git history secrets), DAT-04, INF-02.

Docker-preferred (zricethezav/gitleaks:latest); native binary fallback.
Output: JSON report array; each entry has File, StartLine, RuleID, Description.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._detection import ToolMode, tool_available
from ._runner import ToolResult, run_tool

DOCKER_IMAGE = "zricethezav/gitleaks:latest"
NATIVE_BINARY = "gitleaks"
TOOL_NAME = "gitleaks"


def is_available() -> ToolMode:
    return tool_available(TOOL_NAME, native_binary=NATIVE_BINARY, docker_image=DOCKER_IMAGE)


def run(
    *,
    repo_root: str,
    scan_history: bool = False,
    timeout: int = 600,
) -> ToolResult:
    """Invoke Gitleaks against repo_root.

    Args:
        repo_root: absolute path to repository
        scan_history: if True, scans git history (full SEC-07 coverage);
            otherwise scans HEAD only. History scan is slower but catches
            secrets that were committed and later removed.
        timeout: subprocess timeout in seconds

    Returns:
        ToolResult; stdout contains the JSON report content.
    """
    import os
    import tempfile

    mode = is_available()
    subcommand = "detect"

    # Use a temp file under repo_root so both Docker bind-mount + native invocation
    # can access it. Gitleaks doesn't reliably write JSON to /dev/stdout under
    # Docker (banner / info lines interleave).
    report_basename = f".gitleaks-report-{os.getpid()}.json"
    report_in_repo = os.path.join(repo_root, report_basename)
    args = ["--no-banner", "--report-format", "json"]
    if not scan_history:
        args.append("--no-git")

    if mode == ToolMode.DOCKER:
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{repo_root}:/src",
            "--workdir", "/src",
            DOCKER_IMAGE,
            subcommand,
            *args,
            "--report-path", f"/src/{report_basename}",
            "--source", "/src",
        ]
    elif mode == ToolMode.NATIVE:
        cmd = [
            NATIVE_BINARY, subcommand,
            *args,
            "--report-path", report_in_repo,
            "--source", repo_root,
        ]
    else:
        cmd = []

    raw_result = run_tool(cmd, mode=mode, version="gitleaks", timeout=timeout, cwd=repo_root)

    # Read the JSON report file into stdout
    if mode != ToolMode.NOT_AVAILABLE and os.path.exists(report_in_repo):
        try:
            with open(report_in_repo) as f:
                report_content = f.read()
            os.remove(report_in_repo)
            return ToolResult(
                stdout=report_content,
                stderr=raw_result.stderr,
                exit_code=raw_result.exit_code,
                mode_used=raw_result.mode_used,
                version=raw_result.version,
                elapsed_seconds=raw_result.elapsed_seconds,
            )
        except OSError:
            pass
    return raw_result


def parse_findings(result: ToolResult, repo_root: str) -> list[dict[str, Any]]:
    """Parse Gitleaks JSON output into sulis Finding envelope shape.

    Gitleaks exits non-zero (1) when secrets are found — that's the success
    case for us. Parse the JSON regardless of exit code.
    """
    if result.not_assessed or not result.stdout.strip():
        return []
    try:
        # Gitleaks may emit non-JSON banner lines; extract JSON array
        data = _extract_json_array(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return []

    findings: list[dict[str, Any]] = []
    repo_path = Path(repo_root)
    # Post-parse skip patterns — gitleaks lacks a path-regex CLI flag with
    # --no-git, so we filter here.
    skip_dir_fragments = (
        "/__pycache__/", "/.venv/", "/node_modules/", "/.git/",
        "/dist/", "/build/", "/.checkup/", "/.security/", "/.architecture/",
    )
    skip_extensions = (".pyc", ".pyo", ".class")

    for item in data:
        file_path = item.get("File", "")
        # Strip Docker /src/ prefix if present
        if file_path.startswith("/src/"):
            file_path = file_path[len("/src/"):]
        # Skip compiled / vendored / ignored content
        normalized = f"/{file_path}" if not file_path.startswith("/") else file_path
        if any(frag in normalized for frag in skip_dir_fragments):
            continue
        if any(file_path.endswith(ext) for ext in skip_extensions):
            continue
        try:
            abs_path = Path(file_path)
            rel = abs_path.relative_to(repo_path) if abs_path.is_absolute() else abs_path
        except ValueError:
            rel = Path(file_path)

        rule_id = item.get("RuleID", "unknown-secret")
        description = item.get("Description", "")
        line = item.get("StartLine", 1)

        findings.append({
            "tool": "gitleaks",
            "rule_id": rule_id,
            "file": str(rel),
            "line": line,
            "severity": "critical",  # secrets are always critical
            "message": f"Secret detected ({description})" if description else f"Secret detected: {rule_id}",
            "extras": {
                "commit": item.get("Commit", ""),
                "author": item.get("Author", ""),
                "tool_mode": result.mode_used.value,
            },
        })
    return findings


def _extract_json_array(stdout: str) -> list[dict[str, Any]]:
    """Extract JSON array from stdout that may contain non-JSON preamble."""
    stripped = stdout.strip()
    # Try direct parse first
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        pass
    # Fallback: find first `[` and parse from there
    start = stripped.find("[")
    if start < 0:
        return []
    try:
        parsed = json.loads(stripped[start:])
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []
