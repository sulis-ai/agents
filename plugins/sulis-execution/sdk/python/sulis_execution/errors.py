"""Error hierarchy for the sulis-execution SDK.

Per the agent-consumable SDK spec v0.2.0 Part 3, errors are organised
into three universal outcome categories:

- ProtocolError: the transport itself failed (subprocess couldn't run)
- ExpectedError: the operation reached the implementation but reported
  a deterministic failure (bad inputs, validation, conflict)
- InternalError: the operation crashed or produced an unexpected mode

These map onto the underlying CLI's exit codes:

| Exit code | JSON envelope        | Category       |
|-----------|----------------------|----------------|
| 0         | ok: true             | Success (no exception) |
| 1         | ok: true, outcome=blocker | Success (no exception); caller inspects outcome |
| 1         | ok: false, error     | ExpectedError  |
| 2         | (traceback on stderr)| InternalError  |
| --        | exec failed          | ProtocolError  |

`outcome: blocker` is NOT an exception. It's part of a successful
operation's result. Exceptions are reserved for cases where the SDK
couldn't return a meaningful result at all.
"""
from __future__ import annotations

from typing import Any


class SulisExecutionError(Exception):
    """Base class for all sulis-execution SDK errors.

    Per the SDK spec v0.2.0 Part 3.5, every error exposes:

    - message: human-readable
    - category: 'protocol' / 'expected' / 'internal'
    - transport_code: the underlying CLI's exit code (and JSON context)
    - correlation_id: PID + start timestamp
    - body: the parsed JSON envelope (when present)
    - code: domain-specific code if present in context
    """

    category: str = ""

    def __init__(
        self,
        message: str,
        *,
        transport_code: int | str | None = None,
        correlation_id: str | None = None,
        body: dict[str, Any] | None = None,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.transport_code = transport_code
        self.correlation_id = correlation_id
        self.body = body
        self.code = code
        self.context = context or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"category={self.category!r}, "
            f"transport_code={self.transport_code!r}, "
            f"correlation_id={self.correlation_id!r})"
        )


# ─── ProtocolError ────────────────────────────────────────────────────


class ProtocolError(SulisExecutionError):
    """The transport itself failed — the CLI couldn't be invoked.

    Typical causes: binary not found, permission denied, exec failure.
    Retrying without addressing the cause is unlikely to succeed.
    """

    category = "protocol"


class BinaryNotFoundError(ProtocolError):
    """The wpx-* binary or sulis-change binary couldn't be located.

    Check that the sulis-execution plugin is installed and on PATH, or
    set the WPX_DIR environment variable to the scripts directory.
    """


# ─── ExpectedError ─────────────────────────────────────────────────────


class ExpectedError(SulisExecutionError):
    """The operation ran but reported a deterministic failure.

    Typical causes: invalid arguments, validation failure, conflict,
    missing resource. Retrying with the same inputs produces the same
    error.
    """

    category = "expected"


class InvalidArgumentError(ExpectedError):
    """An argument failed validation (e.g., bad WP format, missing required field)."""


# ─── InternalError ─────────────────────────────────────────────────────


class InternalError(SulisExecutionError):
    """The operation crashed or returned an unexpected failure mode.

    Typical causes: a bug in the underlying CLI; should not happen.
    Caller logs and escalates; usually don't retry.
    """

    category = "internal"


class UnexpectedOutputError(InternalError):
    """The CLI produced output that couldn't be parsed as the expected schema.

    Possible if the underlying tool changed its output shape without the
    SDK being updated, or if the JSON on stdout was corrupted.
    """
