"""Tool invocation runner — produces structured ToolResult."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence

from ._detection import ToolMode


@dataclass(frozen=True)
class ToolResult:
    """Structured result from a tool invocation.

    Attributes:
        stdout: captured stdout (str)
        stderr: captured stderr (str)
        exit_code: process exit code
        mode_used: how the tool was invoked (DOCKER / NATIVE / NOT_AVAILABLE)
        version: tool version captured for provenance (empty if NOT_AVAILABLE)
        elapsed_seconds: wall-clock duration (for performance budgets)
    """

    stdout: str
    stderr: str
    exit_code: int
    mode_used: ToolMode
    version: str = ""
    elapsed_seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def not_assessed(self) -> bool:
        """True if the tool wasn't available at all."""
        return self.mode_used == ToolMode.NOT_AVAILABLE


def run_tool(
    command: Sequence[str],
    *,
    mode: ToolMode,
    version: str = "",
    timeout: int = 300,
    cwd: str | None = None,
) -> ToolResult:
    """Invoke a tool command and capture structured output.

    Args:
        command: argv as passed to subprocess.run
        mode: how the tool is being invoked (for provenance)
        version: tool version (caller is responsible for capturing)
        timeout: seconds before SIGTERM (default 300)
        cwd: working directory

    Returns:
        ToolResult with stdout / stderr / exit_code / mode_used / version.
        If mode is NOT_AVAILABLE, returns an empty ToolResult without invoking.
    """
    import time

    if mode == ToolMode.NOT_AVAILABLE:
        return ToolResult(
            stdout="",
            stderr="tool not available (neither Docker nor native binary present)",
            exit_code=127,
            mode_used=mode,
            version="",
            elapsed_seconds=0.0,
        )

    start = time.monotonic()
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
        )
        elapsed = time.monotonic() - start
        return ToolResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            mode_used=mode,
            version=version,
            elapsed_seconds=elapsed,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            stdout="",
            stderr=f"tool timed out after {timeout}s",
            exit_code=124,
            mode_used=mode,
            version=version,
            elapsed_seconds=float(timeout),
        )
    except (FileNotFoundError, OSError) as exc:
        return ToolResult(
            stdout="",
            stderr=f"tool invocation failed: {exc}",
            exit_code=127,
            mode_used=mode,
            version=version,
            elapsed_seconds=time.monotonic() - start,
        )
