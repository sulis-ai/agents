"""
Runner base — error tree, subprocess helpers, and the Runner protocol.

Every runner conforms to:
    class XxxRunner:
        PHASE: str = "1.N"
        TOOL: str = "tool-name"
        def run(self, inp: RunnerInput) -> RunnerResult: ...

Errors form a tree so the orchestrator can decide policy (fail-fast vs
continue-on-error). The subprocess helpers enforce timeout + output-size
limits and always pass args as a list (never shell=True).
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..config import SUBPROCESS_MAX_OUTPUT_BYTES, TOOL_TIMEOUTS_SEC
from ..models import RunnerInput, RunnerResult


# ─── Error tree ───────────────────────────────────────────────────────────


class RunnerError(Exception):
    """Base for all runner failures.

    Attributes:
        tool:   the tool that failed
        phase:  the phase ID (e.g. "1.2")
        reason: short human-readable cause
        stderr: captured tool stderr (may be empty)
    """

    def __init__(self, tool: str, phase: str, reason: str, stderr: str = "") -> None:
        self.tool = tool
        self.phase = phase
        self.reason = reason
        self.stderr = stderr
        super().__init__(f"[{phase}/{tool}] {reason}" + (f"\nstderr:\n{stderr}" if stderr else ""))


class ToolMissingError(RunnerError):
    """The tool's binary is not on PATH."""


class ToolVersionError(RunnerError):
    """The tool's version is below the required minimum."""


class ToolTimeoutError(RunnerError):
    """The tool's subprocess exceeded its timeout."""


class ToolParseError(RunnerError):
    """Subprocess succeeded but the output couldn't be parsed."""


class ToolNonZeroExitError(RunnerError):
    """Subprocess exited non-zero with no recoverable output."""


# ─── Subprocess helpers ───────────────────────────────────────────────────


@dataclass
class SubprocessResult:
    """Captured result of a subprocess invocation."""
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    truncated: bool          # True if stdout was truncated to MAX_OUTPUT_BYTES


def is_tool_available(tool: str) -> bool:
    """Return True if `tool` is on PATH."""
    return shutil.which(tool) is not None


def run_tool(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
    tool: str,
    phase: str,
    timeout: int | None = None,
    extra_env: dict[str, str] | None = None,
) -> SubprocessResult:
    """
    Invoke a tool with safety nets.

    Always passes args as a list (no shell=True). Truncates stdout to
    SUBPROCESS_MAX_OUTPUT_BYTES. Wraps timeouts in ToolTimeoutError.

    Returns SubprocessResult even on non-zero exit — the caller decides
    whether to raise ToolNonZeroExitError. This lets some tools that emit
    findings via non-zero exit codes (e.g. lint tools) still be processed.
    """
    if timeout is None:
        timeout = TOOL_TIMEOUTS_SEC.get(tool, 120)

    env = None
    if extra_env:
        import os
        env = {**os.environ, **extra_env}

    started = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            check=False,
            text=True,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        raise ToolTimeoutError(
            tool=tool,
            phase=phase,
            reason=f"timed out after {timeout}s",
            stderr=(exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        ) from exc
    except FileNotFoundError as exc:
        raise ToolMissingError(
            tool=tool,
            phase=phase,
            reason=f"binary not found: {cmd[0]}",
        ) from exc

    elapsed_ms = int((time.monotonic() - started) * 1000)

    # Truncate runaway output
    stdout = completed.stdout or ""
    truncated = False
    if len(stdout.encode("utf-8", errors="ignore")) > SUBPROCESS_MAX_OUTPUT_BYTES:
        stdout = stdout[:SUBPROCESS_MAX_OUTPUT_BYTES]
        truncated = True

    return SubprocessResult(
        returncode=completed.returncode,
        stdout=stdout,
        stderr=completed.stderr or "",
        duration_ms=elapsed_ms,
        truncated=truncated,
    )


def now_iso() -> str:
    """ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ─── Runner protocol ──────────────────────────────────────────────────────


@runtime_checkable
class Runner(Protocol):
    """Every runner implements this protocol."""
    PHASE: str
    TOOL: str

    def run(self, inp: RunnerInput) -> RunnerResult:
        ...


def make_result(
    *,
    phase: str,
    tool: str,
    started_at: str,
    started_monotonic: float,
    payload: dict,
    raw_output_path: Path | None = None,
    warnings: list[str] | None = None,
) -> RunnerResult:
    """Convenience constructor for RunnerResult."""
    duration_ms = int((time.monotonic() - started_monotonic) * 1000)
    return RunnerResult(
        phase=phase,
        tool=tool,
        started_at=started_at,
        duration_ms=duration_ms,
        payload=payload,
        raw_output_path=str(raw_output_path) if raw_output_path else None,
        warnings=tuple(warnings or []),
    )
