"""Hadolint wrapper — covers INF-01 (Dockerfile lint portion).

Docker-preferred (hadolint/hadolint:latest); native binary fallback.
Output: JSON array; each entry has file, line, code, level, message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._detection import ToolMode, tool_available
from ._runner import ToolResult, run_tool

DOCKER_IMAGE = "hadolint/hadolint:latest"
NATIVE_BINARY = "hadolint"
TOOL_NAME = "hadolint"


def is_available() -> ToolMode:
    return tool_available(TOOL_NAME, native_binary=NATIVE_BINARY, docker_image=DOCKER_IMAGE)


def run(
    *,
    dockerfile_path: str,
    repo_root: str,
    timeout: int = 60,
) -> ToolResult:
    """Invoke Hadolint against a Dockerfile.

    Args:
        dockerfile_path: relative path to Dockerfile from repo_root
        repo_root: absolute path to repository
        timeout: subprocess timeout in seconds
    """
    mode = is_available()
    if mode == ToolMode.DOCKER:
        # Hadolint Docker image reads Dockerfile from stdin
        # We use exec to redirect — simpler: bind-mount and pass path
        cmd = [
            "docker", "run", "--rm", "-i",
            DOCKER_IMAGE,
            "hadolint", "--format", "json", "-",
        ]
        # Read file content and pass via stdin
        full_path = Path(repo_root) / dockerfile_path
        try:
            stdin_content = full_path.read_text(errors="replace")
        except OSError:
            return ToolResult(
                stdout="",
                stderr=f"could not read {dockerfile_path}",
                exit_code=2,
                mode_used=mode,
            )
        result = _run_with_stdin(cmd, stdin_content, mode, timeout)
        # Tag with file path since hadolint doesn't know it
        return _retag_file(result, dockerfile_path)
    elif mode == ToolMode.NATIVE:
        cmd = [NATIVE_BINARY, "--format", "json", dockerfile_path]
        return run_tool(cmd, mode=mode, version="hadolint", timeout=timeout, cwd=repo_root)
    else:
        return run_tool([], mode=mode)


def _run_with_stdin(cmd: list[str], stdin_content: str, mode: ToolMode, timeout: int) -> ToolResult:
    """Run a command with stdin input. Wrapper around subprocess for Docker --stdin case."""
    import subprocess
    import time

    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_content,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        elapsed = time.monotonic() - start
        return ToolResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
            mode_used=mode,
            version="hadolint",
            elapsed_seconds=elapsed,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            stdout="",
            stderr=f"hadolint timed out after {timeout}s",
            exit_code=124,
            mode_used=mode,
            elapsed_seconds=float(timeout),
        )


def _retag_file(result: ToolResult, file_path: str) -> ToolResult:
    """Replace stdin reference with actual file path in JSON output."""
    if not result.stdout.strip():
        return result
    try:
        data = json.loads(result.stdout)
        for item in data:
            if item.get("file") in {"-", "<stdin>", ""}:
                item["file"] = file_path
        return ToolResult(
            stdout=json.dumps(data),
            stderr=result.stderr,
            exit_code=result.exit_code,
            mode_used=result.mode_used,
            version=result.version,
            elapsed_seconds=result.elapsed_seconds,
        )
    except (json.JSONDecodeError, ValueError):
        return result


def parse_findings(result: ToolResult, repo_root: str) -> list[dict[str, Any]]:
    """Parse Hadolint JSON output into sulis Finding envelope shape."""
    if result.not_assessed or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return []

    findings: list[dict[str, Any]] = []
    for item in data:
        file_path = item.get("file", "Dockerfile")
        line = item.get("line", 1)
        code = item.get("code", "DL0000")
        level = item.get("level", "info").lower()
        message = item.get("message", "")

        severity = _map_severity(level)

        findings.append({
            "tool": "hadolint",
            "rule_id": code,
            "file": file_path,
            "line": line,
            "severity": severity,
            "message": message,
            "extras": {
                "hadolint_level": level,
                "tool_mode": result.mode_used.value,
            },
        })
    return findings


def _map_severity(hadolint_level: str) -> str:
    """Map Hadolint level to sulis Finding severity."""
    mapping = {
        "error": "high",
        "warning": "concern",
        "info": "advisory",
        "style": "advisory",
    }
    return mapping.get(hadolint_level, "advisory")
