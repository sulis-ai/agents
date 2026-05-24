"""curl-based HTTP header probe — covers INF-03 (HTTP security headers).

Native curl (universally available). Checks for presence of:
- Strict-Transport-Security (HSTS)
- X-Frame-Options
- Content-Security-Policy (CSP)
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy

Each missing header produces an ADVISORY-level finding.
"""

from __future__ import annotations

from typing import Any

from ._detection import ToolMode, native_available
from ._runner import ToolResult, run_tool

NATIVE_BINARY = "curl"
TOOL_NAME = "curl_probe"

REQUIRED_HEADERS = {
    "Strict-Transport-Security": "HSTS missing — TLS connections may be downgraded",
    "X-Frame-Options": "Missing — clickjacking protection absent (use DENY or SAMEORIGIN)",
    "Content-Security-Policy": "CSP missing — XSS + injection mitigation absent",
    "X-Content-Type-Options": "Missing 'nosniff' — MIME-type sniffing protection absent",
    "Referrer-Policy": "Missing — leaks full referrer to third parties",
}


def is_available() -> ToolMode:
    if native_available(NATIVE_BINARY):
        return ToolMode.NATIVE
    return ToolMode.NOT_AVAILABLE


def run(*, url: str, timeout: int = 30) -> ToolResult:
    """Probe headers of a URL with curl -I."""
    mode = is_available()
    if mode == ToolMode.NOT_AVAILABLE:
        return run_tool([], mode=mode)

    cmd = [
        NATIVE_BINARY,
        "-sIL",
        "--max-time", str(timeout),
        "--user-agent", "sulis-check-security/curl_probe",
        url,
    ]
    return run_tool(cmd, mode=mode, version="curl", timeout=timeout)


def parse_findings(result: ToolResult, url: str = "<deployed-url>") -> list[dict[str, Any]]:
    """Parse curl headers output; produce finding per missing security header.

    Args:
        result: ToolResult from `run()`
        url: original URL for message context

    Returns:
        list of findings — one per missing header.
    """
    if result.not_assessed or not result.stdout.strip():
        return []

    headers = _parse_headers(result.stdout)
    findings: list[dict[str, Any]] = []
    for required, message in REQUIRED_HEADERS.items():
        if required.lower() not in headers:
            findings.append({
                "tool": "curl_probe",
                "rule_id": f"INF-03-missing-{required.lower()}",
                "file": url,
                "line": 1,
                "severity": "advisory",
                "message": message,
                "extras": {
                    "missing_header": required,
                    "tool_mode": result.mode_used.value,
                },
            })
    return findings


def _parse_headers(stdout: str) -> dict[str, str]:
    """Extract HTTP headers from curl -I output (lowercased keys)."""
    headers: dict[str, str] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("HTTP/"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    return headers
