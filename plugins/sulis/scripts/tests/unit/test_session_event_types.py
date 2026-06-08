"""Tests for ``_session_manager.events`` — the shared, provider-neutral event
vocabulary + three-category error model.

Covers SESSION_MANAGER_CONTRACT §2.3 (the four-kind ``Event`` vocabulary) and
§2.9 (the Protocol / Expected / Internal error categories). These are the Form
invariant types every layer speaks — WP-001's log carries them, WP-003's
adapter produces them — so they are frozen, dependency-free, and validated at
construction.

Real value-object behaviour throughout: no mocks (MEA-09). The types are pure;
there is nothing to fake.
"""

from __future__ import annotations

import dataclasses

import pytest

from _session_manager.events import (
    CWD_NOT_FOUND,
    DECODE_FAILED,
    Event,
    EventError,
    ExpectedError,
    InternalError,
    LOG_CORRUPT,
    NO_SESSION,
    OFFSET_EVICTED,
    ProtocolError,
    SESSION_DISABLED,
    SOCKET_CLOSED,
    SPAWN_FAILED,
    STDIN_BROKEN,
    SessionError,
    ToolUse,
    TurnResult,
    UNKNOWN_PROVIDER,
)


class TestEventKindPayloadConsistency:
    """§2.3 — each ``kind`` carries exactly its own payload; the others stay
    ``None``. A malformed Event fails loudly at construction (boring
    ``__post_init__`` check), not three layers later."""

    def test_chunk_carries_text_only(self) -> None:
        ev = Event(offset=0, key="k", turn=1, kind="chunk", text="hi")
        assert ev.text == "hi"
        assert ev.tool is None
        assert ev.result is None
        assert ev.error is None

    def test_tool_use_carries_tool_only(self) -> None:
        tool = ToolUse(name="grep", input_summary="pattern=foo")
        ev = Event(offset=1, key="k", turn=1, kind="tool_use", tool=tool)
        assert ev.tool is tool
        assert ev.text is None
        assert ev.result is None
        assert ev.error is None

    def test_result_carries_result_only(self) -> None:
        res = TurnResult(
            input_tokens=1200,
            output_tokens=85,
            duration_ms=4200,
            stop_reason="end_turn",
        )
        ev = Event(offset=2, key="k", turn=1, kind="result", result=res)
        assert ev.result is res
        assert ev.text is None
        assert ev.tool is None
        assert ev.error is None

    def test_error_carries_error_only(self) -> None:
        err = EventError(category="expected", code=NO_SESSION, message="x")
        ev = Event(offset=3, key="k", turn=1, kind="error", error=err)
        assert ev.error is err
        assert ev.text is None
        assert ev.tool is None
        assert ev.result is None

    def test_chunk_without_text_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Event(offset=0, key="k", turn=1, kind="chunk")

    def test_chunk_with_foreign_payload_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Event(
                offset=0,
                key="k",
                turn=1,
                kind="chunk",
                text="hi",
                result=TurnResult(0, 0, 0, "end_turn"),
            )

    def test_result_without_result_payload_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Event(offset=0, key="k", turn=1, kind="result")

    def test_tool_use_without_tool_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Event(offset=0, key="k", turn=1, kind="tool_use")

    def test_error_without_error_payload_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Event(offset=0, key="k", turn=1, kind="error")

    def test_unknown_kind_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Event(offset=0, key="k", turn=1, kind="banana", text="hi")  # type: ignore[arg-type]


class TestEventIsFrozen:
    """§2.3 — immutability is the multi-viewer safety property (a shared log
    record must never mutate under a reader)."""

    def test_event_mutation_raises(self) -> None:
        ev = Event(offset=0, key="k", turn=1, kind="chunk", text="hi")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ev.text = "bye"  # type: ignore[misc]

    def test_tool_use_mutation_raises(self) -> None:
        tool = ToolUse(name="grep", input_summary="x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            tool.name = "sed"  # type: ignore[misc]

    def test_turn_result_mutation_raises(self) -> None:
        res = TurnResult(1, 2, 3, "end_turn")
        with pytest.raises(dataclasses.FrozenInstanceError):
            res.input_tokens = 99  # type: ignore[misc]

    def test_event_error_mutation_raises(self) -> None:
        err = EventError(category="internal", code=DECODE_FAILED, message="x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            err.message = "y"  # type: ignore[misc]


class TestErrorCategoriesExhaustive:
    """§2.9 — every code maps to exactly one of the three exception classes,
    and the class's ``category`` string matches the contract category."""

    PROTOCOL_CODES = {SPAWN_FAILED, STDIN_BROKEN, SOCKET_CLOSED}
    EXPECTED_CODES = {
        NO_SESSION,
        UNKNOWN_PROVIDER,
        CWD_NOT_FOUND,
        OFFSET_EVICTED,
        SESSION_DISABLED,
    }
    INTERNAL_CODES = {DECODE_FAILED, LOG_CORRUPT}

    def test_protocol_errors_carry_protocol_category(self) -> None:
        for code in self.PROTOCOL_CODES:
            exc = ProtocolError(code=code, message="boom")
            assert exc.category == "protocol"
            assert exc.code == code
            assert isinstance(exc, SessionError)

    def test_expected_errors_carry_expected_category(self) -> None:
        for code in self.EXPECTED_CODES:
            exc = ExpectedError(code=code, message="declined")
            assert exc.category == "expected"
            assert exc.code == code
            assert isinstance(exc, SessionError)

    def test_internal_errors_carry_internal_category(self) -> None:
        for code in self.INTERNAL_CODES:
            exc = InternalError(code=code, message="bug")
            assert exc.category == "internal"
            assert exc.code == code
            assert isinstance(exc, SessionError)

    def test_categories_are_mutually_exclusive(self) -> None:
        """No code appears in more than one category (exhaustive partition)."""
        assert self.PROTOCOL_CODES.isdisjoint(self.EXPECTED_CODES)
        assert self.PROTOCOL_CODES.isdisjoint(self.INTERNAL_CODES)
        assert self.EXPECTED_CODES.isdisjoint(self.INTERNAL_CODES)

    def test_three_categories_only(self) -> None:
        """The base ``SessionError`` is abstract about category; the three
        concrete subclasses are the only category-bearing types."""
        assert ProtocolError.category == "protocol"
        assert ExpectedError.category == "expected"
        assert InternalError.category == "internal"


class TestErrorCodesAreConstants:
    """§2.9 — the code constants exist and are exactly the contract strings
    (guards against typos drifting from the contract)."""

    def test_code_constant_values_match_contract(self) -> None:
        assert SPAWN_FAILED == "SPAWN_FAILED"
        assert STDIN_BROKEN == "STDIN_BROKEN"
        assert SOCKET_CLOSED == "SOCKET_CLOSED"
        assert NO_SESSION == "NO_SESSION"
        assert UNKNOWN_PROVIDER == "UNKNOWN_PROVIDER"
        assert CWD_NOT_FOUND == "CWD_NOT_FOUND"
        assert OFFSET_EVICTED == "OFFSET_EVICTED"
        assert SESSION_DISABLED == "SESSION_DISABLED"
        assert DECODE_FAILED == "DECODE_FAILED"
        assert LOG_CORRUPT == "LOG_CORRUPT"


class TestEventErrorRoundtripsToEvent:
    """§2.9 — the log carries failures as events too: an ``EventError`` wraps
    into an ``Event(kind="error")`` losslessly."""

    def test_event_error_wraps_into_event(self) -> None:
        err = EventError(
            category="expected",
            code=OFFSET_EVICTED,
            message="since predates oldest retained offset",
        )
        ev = Event(offset=7, key="chg_01", turn=3, kind="error", error=err)
        assert ev.kind == "error"
        assert ev.error is not None
        assert ev.error == err
        assert ev.error.category == "expected"
        assert ev.error.code == OFFSET_EVICTED
        assert ev.error.message == "since predates oldest retained offset"

    def test_session_error_payload_can_seed_an_event_error(self) -> None:
        """A raised ``SessionError`` carries the same (category, code, message)
        an ``EventError`` needs — the in-process exception and the logged event
        share one shape (§2.9)."""
        exc = ExpectedError(code=NO_SESSION, message="no open session for key")
        err = EventError(category=exc.category, code=exc.code, message=str(exc))
        ev = Event(offset=0, key="k", turn=1, kind="error", error=err)
        assert ev.error is not None
        assert ev.error.category == "expected"
        assert ev.error.code == "NO_SESSION"
