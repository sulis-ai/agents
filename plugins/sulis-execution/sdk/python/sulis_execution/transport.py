"""Subprocess transport for the sulis-execution SDK.

Per agent-consumable SDK spec v0.2.0 Part 4.3 (Subprocess + JSON-on-stdout).

The transport spawns the underlying CLI binary, writes argv (and optionally
stdin), reads stdout, parses JSON, and maps the exit code + envelope to
either a successful result or one of the canonical error classes.

Two implementations:

- SubprocessTransport: sync, uses stdlib subprocess
- AsyncSubprocessTransport: async, uses asyncio.create_subprocess_exec

Both share the binary-resolution and envelope-parsing logic.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sulis_execution.errors import (
    BinaryNotFoundError,
    ExpectedError,
    InternalError,
    InvalidArgumentError,
    ProtocolError,
    UnexpectedOutputError,
)


@dataclass(frozen=True)
class TransportConfig:
    """Configuration shared across both sync and async transports."""

    repo_root: Path
    project: str
    timeout_seconds: float = 5400.0  # 90 min cap (matches wpx-pipeline default)
    wpx_dir: Path | None = None  # Override the CLI binary discovery path


def _resolve_binary(binary_name: str, config: TransportConfig) -> Path:
    """Find the CLI binary on disk.

    Resolution order:
    1. <wpx_dir>/binary_name (if wpx_dir is set in config)
    2. <WPX_DIR env var>/binary_name (if WPX_DIR is set in env)
    3. PATH (via shutil.which)
    """
    # 1. Explicit config override
    if config.wpx_dir is not None:
        candidate = config.wpx_dir / binary_name
        if candidate.exists():
            return candidate

    # 2. Env var override
    env_dir = os.environ.get("WPX_DIR")
    if env_dir:
        candidate = Path(env_dir) / binary_name
        if candidate.exists():
            return candidate

    # 3. PATH lookup
    on_path = shutil.which(binary_name)
    if on_path:
        return Path(on_path)

    raise BinaryNotFoundError(
        f"Could not find binary {binary_name!r}. "
        f"Set WPX_DIR env var to point at the scripts directory, "
        f"or pass wpx_dir to the client.",
        transport_code="exec_failure",
        context={"binary": binary_name},
    )


def _correlation_id(pid: int) -> str:
    """Generate a correlation ID from PID + monotonic timestamp.

    Used as the SDK's substitute for the request-id header that HTTP-shaped
    SDKs use. Per SDK spec v0.2.0 Part 4.3, subprocess transport correlation
    is PID + timestamp.
    """
    return f"pid-{pid}-{int(time.time() * 1000)}"


def _build_argv(binary: Path, subcommand: str, params: dict[str, Any]) -> list[str]:
    """Convert (binary, subcommand, params) into argv.

    Params with None or False values are skipped. Booleans become --flag
    when True; everything else becomes --kebab-case-key value.
    """
    argv: list[str] = [str(binary), subcommand]
    for key, value in params.items():
        if value is None:
            continue
        flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        else:
            argv.extend([flag, str(value)])
    return argv


def _parse_envelope(
    stdout: str,
    stderr: str,
    exit_code: int,
    correlation_id: str,
    argv: list[str],
) -> dict[str, Any]:
    """Map exit code + JSON envelope onto either a result dict or an exception.

    Returns the parsed envelope's data on success. Raises one of the
    canonical exceptions on error.
    """
    # Try to parse stdout as JSON; if that fails, treat as InternalError
    parsed: dict[str, Any] | None = None
    if stdout.strip():
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise UnexpectedOutputError(
                f"CLI output was not valid JSON: {exc}",
                transport_code=exit_code,
                correlation_id=correlation_id,
                body={"stdout": stdout, "stderr": stderr},
                context={"argv": argv},
            ) from exc

    # Exit code 2 → internal crash. Stderr usually has the traceback.
    if exit_code == 2:
        message = (
            (parsed or {}).get("error")
            or f"CLI crashed with traceback:\n{stderr.strip()[-1000:]}"
        )
        raise InternalError(
            message,
            transport_code=exit_code,
            correlation_id=correlation_id,
            body=parsed,
            context={"stderr_tail": stderr.strip()[-2000:]},
        )

    # Exit code 1 with ok:false → expected error
    if exit_code == 1 and parsed and not parsed.get("ok", True):
        raise ExpectedError(
            parsed.get("error", "Unknown expected error"),
            transport_code=exit_code,
            correlation_id=correlation_id,
            body=parsed,
            context=parsed.get("context") or {},
            code=(parsed.get("context") or {}).get("code"),
        )

    # Anything else with exit != 0 and we have a parsed envelope: treat
    # it as expected — this is the "exit 1 with ok:true, outcome:blocker"
    # case where the operation succeeded as far as the CLI is concerned
    # but the result reports a deterministic failure mode. The caller
    # decides what to do with it.
    if exit_code != 0 and not parsed:
        # No JSON, unexpected exit code → internal
        raise InternalError(
            f"CLI exited {exit_code} with no JSON output",
            transport_code=exit_code,
            correlation_id=correlation_id,
            context={"stderr_tail": stderr.strip()[-2000:]},
        )

    return parsed or {}


# ─── Sync transport ───────────────────────────────────────────────────


class SubprocessTransport:
    """Sync subprocess transport.

    Spawns the CLI binary, captures stdout/stderr, maps to result or
    exception per SDK spec v0.2.0 Part 4.3.
    """

    def __init__(self, config: TransportConfig) -> None:
        self.config = config

    def invoke(
        self, binary_name: str, subcommand: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke a CLI subcommand and return the parsed envelope.

        Raises ProtocolError, ExpectedError, or InternalError per the
        canonical error hierarchy.
        """
        binary = _resolve_binary(binary_name, self.config)
        argv = _build_argv(binary, subcommand, params)

        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                cwd=str(self.config.repo_root),
            )
        except FileNotFoundError as exc:
            raise BinaryNotFoundError(
                f"Binary {binary} could not be executed",
                context={"argv": argv},
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProtocolError(
                f"CLI timed out after {self.config.timeout_seconds}s",
                transport_code="timeout",
                correlation_id=_correlation_id(os.getpid()),
                context={"argv": argv},
            ) from exc

        return _parse_envelope(
            proc.stdout,
            proc.stderr,
            proc.returncode,
            _correlation_id(proc.pid if hasattr(proc, "pid") else os.getpid()),
            argv,
        )


# ─── Async transport ──────────────────────────────────────────────────


class AsyncSubprocessTransport:
    """Async subprocess transport.

    Same semantics as SubprocessTransport but non-blocking. Used by
    AsyncSulisExecution.
    """

    def __init__(self, config: TransportConfig) -> None:
        self.config = config

    async def invoke(
        self, binary_name: str, subcommand: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        binary = _resolve_binary(binary_name, self.config)
        argv = _build_argv(binary, subcommand, params)

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.config.repo_root),
            )
        except FileNotFoundError as exc:
            raise BinaryNotFoundError(
                f"Binary {binary} could not be executed",
                context={"argv": argv},
            ) from exc

        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            raise ProtocolError(
                f"CLI timed out after {self.config.timeout_seconds}s",
                transport_code="timeout",
                correlation_id=_correlation_id(proc.pid),
                context={"argv": argv},
            ) from exc

        return _parse_envelope(
            stdout_b.decode("utf-8", errors="replace"),
            stderr_b.decode("utf-8", errors="replace"),
            proc.returncode or 0,
            _correlation_id(proc.pid),
            argv,
        )
