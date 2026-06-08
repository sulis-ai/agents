"""Conformance tests for the ``ProviderAdapter`` seam's recovery extension
(WP-004, ADR-003).

WP-004 extends the ``@runtime_checkable`` ``ProviderAdapter`` Protocol with two
**defaulted, additive** methods — ``classify_failure`` and ``reauth`` — mirroring
the ``io_mode`` / ``brief_change_id`` additive precedent already in
``adapter.py``. These tests prove:

1. The Protocol exposes ``classify_failure`` + ``reauth`` (the shape Codex/Gemini
   adapters will bind against alongside the existing
   spawn_argv/encode/decode/turn_complete surface).
2. A *default* adapter — one that subclasses the Protocol and does NOT override
   ``classify_failure`` — returns ``None`` (the documented defer-to-neutral
   behaviour: the shared classifier applies its category-based default, ADR-003).

The detection *mapping* itself (Claude's 401→login-expired, 429→blip, …) is
WP-006 and lives in ``adapters/claude.py``; this WP only proves the seam shape
and the safe default.
"""

from __future__ import annotations

from _session_manager.adapter import (
    Capabilities,
    ProviderAdapter,
    SessionSpec,
)
from _session_manager.classifier import RecoveryClass
from _session_manager.events import Event, EventError
from _session_manager.recovery import ReauthTicket


class _DefaultAdapter(ProviderAdapter):
    """A minimal adapter that implements only the original four seam methods and
    leaves ``classify_failure`` / ``reauth`` to the Protocol defaults — the
    "brand-new adapter that doesn't override detection" case (ADR-003)."""

    capabilities = Capabilities(
        supports_resume=False,
        supports_tools=False,
        supports_partial_streaming=False,
    )

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return ["true"]

    def encode(self, command: str) -> bytes:
        return command.encode("utf-8")

    def decode(self, line: bytes) -> Event | None:
        return None

    def turn_complete(self, event: Event) -> bool:
        return False


def _an_error() -> EventError:
    """A representative ``EventError`` to feed ``classify_failure`` — its
    contents are irrelevant to the *default* path, which defers regardless."""
    return EventError(
        category="expected",
        code="NOT_AUTHORIZED",
        message="login expired",
    )


class TestProtocolShape:
    """The Protocol exposes the WP-004 recovery extension (ADR-003)."""

    def test_protocol_has_classify_failure_and_reauth(self) -> None:
        assert hasattr(ProviderAdapter, "classify_failure")
        assert hasattr(ProviderAdapter, "reauth")
        # The additive recovery surface composes with the original four seam
        # methods — none of which it disturbs (the io_mode/brief_change_id
        # additive precedent).
        for original in ("spawn_argv", "encode", "decode", "turn_complete"):
            assert hasattr(ProviderAdapter, original)


class TestDefaultDetection:
    """A default adapter defers to the neutral classifier (ADR-003)."""

    def test_default_classify_failure_returns_none(self) -> None:
        adapter = _DefaultAdapter()
        assert isinstance(adapter, ProviderAdapter)
        assert adapter.classify_failure(_an_error()) is None

    def test_default_adapter_conforms_structurally(self) -> None:
        # The default adapter still satisfies the runtime-checkable Protocol —
        # the recovery extension did not break structural conformance.
        assert isinstance(_DefaultAdapter(), ProviderAdapter)

    def test_recovery_types_are_the_wp001_value_objects(self) -> None:
        # reauth()'s declared return type is the WP-001 ReauthTicket, and the
        # hint vocabulary is the WP-001 RecoveryClass enum — pinned here so a
        # future re-spelling on either side of the seam is caught.
        assert RecoveryClass.LOGIN_EXPIRED.value == "login_expired"
        ticket = ReauthTicket(
            relogin_link="https://example/login", completion_handle="h"
        )
        assert ticket.relogin_link == "https://example/login"
