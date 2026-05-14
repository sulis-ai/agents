"""
Tool detection — verify required binaries are present and report versions.

Mirrors the shell installer's `--check` mode but in Python. Used by the
orchestrator at the start of every run to short-circuit with exit code 2
if any required tool is missing.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from .config import (
    LIZARD_HELP_MARKER,
    TOOL_OPTIONAL,
    TOOL_REQUIRED,
    TOOL_VERSION_MIN,
)
from .runners.base import is_tool_available


@dataclass(frozen=True)
class ToolStatus:
    name: str
    available: bool
    version: str | None         # raw version string captured
    version_ok: bool            # True if version meets minimum
    sanity_ok: bool             # True if any tool-specific sanity check passed
    sanity_note: str | None     # explanation when sanity_ok is False
    required: bool


@dataclass(frozen=True)
class DetectionReport:
    tools: list[ToolStatus]
    all_required_present: bool
    all_required_valid: bool
    missing_required: list[str]
    missing_optional: list[str]
    failed_sanity: list[str]


_VERSION_REGEX = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def _parse_version(text: str) -> tuple[int, int, int] | None:
    """Parse the first X.Y or X.Y.Z found in `text`."""
    m = _VERSION_REGEX.search(text or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or "0"))


def _meets_min(version: tuple[int, int, int] | None, minimum: tuple[int, int]) -> bool:
    if version is None:
        return False
    return (version[0], version[1]) >= minimum


def _get_version(tool: str) -> str | None:
    """
    Invoke `<tool> --version` and capture the output. Returns None if the
    tool isn't on PATH or the call fails.

    Special-case: `go` and `cargo` use slightly different invocations but
    `--version` works for both modern versions.
    """
    try:
        completed = subprocess.run(
            [tool, "--version"],
            capture_output=True,
            timeout=10,
            check=False,
            text=True,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    # Some tools emit version on stderr (rare). Combine.
    return ((completed.stdout or "") + " " + (completed.stderr or "")).strip()


def _lizard_sanity_check() -> tuple[bool, str | None]:
    """
    Verify the `lizard` on PATH is Terry Yin's McCabe analyser, NOT the
    compression utility from `brew install lizard`. This was the v0.7.1
    Bug 1 — the installer fix uses pipx, but if a user has the wrong
    `lizard` from a prior brew install, we detect it here.
    """
    try:
        completed = subprocess.run(
            ["lizard", "--help"],
            capture_output=True,
            timeout=10,
            check=False,
            text=True,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "lizard --help did not execute"

    help_text = (completed.stdout or "") + (completed.stderr or "")
    if LIZARD_HELP_MARKER.lower() not in help_text.lower():
        return False, (
            "Wrong lizard detected — found a different tool of the same name. "
            "The McCabe complexity analyser shows 'Cyclomatic Complexity Analyzer' "
            "in --help. Fix: `brew uninstall lizard && pipx install lizard`"
        )
    return True, None


def detect_tools() -> DetectionReport:
    """
    Run the full detection sweep. Returns a structured report the
    orchestrator can use to decide whether to proceed.
    """
    statuses: list[ToolStatus] = []
    missing_required: list[str] = []
    missing_optional: list[str] = []
    failed_sanity: list[str] = []

    all_tools = [(name, True) for name in TOOL_REQUIRED] + \
                [(name, False) for name in TOOL_OPTIONAL]

    for tool, required in all_tools:
        available = is_tool_available(tool)
        version_str: str | None = None
        version_ok = True
        sanity_ok = True
        sanity_note: str | None = None

        if not available:
            if required:
                missing_required.append(tool)
            else:
                missing_optional.append(tool)
        else:
            version_str = _get_version(tool)
            min_ver = TOOL_VERSION_MIN.get(tool)
            if min_ver is not None:
                parsed = _parse_version(version_str or "")
                version_ok = _meets_min(parsed, min_ver)

            # Tool-specific sanity checks
            if tool == "lizard":
                sanity_ok, sanity_note = _lizard_sanity_check()
                if not sanity_ok and required:
                    failed_sanity.append(tool)

        statuses.append(
            ToolStatus(
                name=tool,
                available=available,
                version=version_str,
                version_ok=version_ok,
                sanity_ok=sanity_ok,
                sanity_note=sanity_note,
                required=required,
            )
        )

    return DetectionReport(
        tools=statuses,
        all_required_present=len(missing_required) == 0,
        all_required_valid=(
            len(missing_required) == 0
            and len(failed_sanity) == 0
            and all(s.version_ok for s in statuses if s.required and s.available)
        ),
        missing_required=missing_required,
        missing_optional=missing_optional,
        failed_sanity=failed_sanity,
    )


def format_report(report: DetectionReport) -> str:
    """Human-readable formatted detection report (mirrors installer style)."""
    lines: list[str] = ["Tool status:"]
    for s in report.tools:
        mark = "✓" if s.available and s.version_ok and s.sanity_ok else "✗"
        tag = "required" if s.required else "optional"
        version_info = f" ({s.version.splitlines()[0] if s.version else 'unknown'})" if s.available else ""
        line = f"  {mark} {s.name}{version_info}  ({tag})"
        if s.sanity_note:
            line += f"\n    ⚠ {s.sanity_note}"
        lines.append(line)

    if report.missing_required:
        lines.append("")
        lines.append("✗ Missing required tools: " + ", ".join(report.missing_required))
        lines.append("  Run: bash plugins/sea/skills/probe/scripts/install-probe-tools.sh")

    if report.missing_optional:
        lines.append("")
        lines.append("⚠ Missing optional tools: " + ", ".join(report.missing_optional))
        lines.append("  (corresponding phases will skip gracefully)")

    if report.failed_sanity:
        lines.append("")
        lines.append("✗ Failed sanity checks: " + ", ".join(report.failed_sanity))

    return "\n".join(lines)
