"""Tests for ``_session_manager.adapter`` (the ``ProviderAdapter`` seam) and
``_session_manager.adapters.claude`` (Claude adapter #1).

Covers SESSION_MANAGER_CONTRACT §2.4 — the only agent-specific surface. The
adapter is **EXPAND-Create**: a Protocol *we* own, with the Claude CLI called
*by* its methods, not wrapped at the architecture level (§2.4 Stripe-rule
discriminator).

`decode()` is driven by **recorded real `claude` stream-json lines**
(``tests/fixtures/session_manager/claude/``), not hand-mocked JSON shapes — so
the mapping rules can never silently drift from the real CLI (MEA-09 / §2.10).
``spawn_argv`` / ``encode`` / ``turn_complete`` / ``capabilities`` are pure
value behaviour with nothing to fake.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _session_manager.adapter import (
    Capabilities,
    ProviderAdapter,
    SessionSpec,
)
from _session_manager.adapters.claude import ClaudeAdapter
from _session_manager.events import Event, InternalError

_FIXTURES = (
    Path(__file__).resolve().parent.parent / "fixtures" / "session_manager" / "claude"
)


def _recorded_lines(name: str) -> list[bytes]:
    """Return every non-blank line of a recorded fixture, as raw bytes — the
    same shape ``decode()`` sees off the child's stdout."""
    path = _FIXTURES / name
    return [
        line.encode("utf-8")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _first_matching(lines: list[bytes], pred) -> bytes:
    for raw in lines:
        if pred(json.loads(raw)):
            return raw
    raise AssertionError("no recorded line matched the predicate")


@pytest.fixture
def adapter() -> ClaudeAdapter:
    return ClaudeAdapter()


@pytest.fixture
def happy_lines() -> list[bytes]:
    return _recorded_lines("happy.jsonl")


@pytest.fixture
def error_lines() -> list[bytes]:
    return _recorded_lines("error.jsonl")


class TestSpawnArgv:
    """§2.4 — how to start the CLI in streaming mode, in spec.cwd."""

    def test_spawn_argv_streaming_flags(self, adapter: ClaudeAdapter) -> None:
        spec = SessionSpec(provider="claude", cwd="/some/work")
        argv = adapter.spawn_argv(spec)
        assert argv[0] == "claude"
        for flag in (
            "-p",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
            # --verbose is mandatory with -p + --output-format=stream-json or the
            # real claude CLI (v2.1.165) refuses to start. Caught by WP-009's
            # observed-done gate; pinned here so a future edit can't drop it.
            "--verbose",
            "--dangerously-skip-permissions",
        ):
            assert flag in argv, f"missing streaming flag {flag!r}"

    def test_spawn_argv_resume_flag_iff_resume_ref(
        self, adapter: ClaudeAdapter
    ) -> None:
        # No resume_ref → no --resume flag.
        fresh = adapter.spawn_argv(SessionSpec(provider="claude", cwd="/w"))
        assert "--resume" not in fresh

        # resume_ref set → --resume <ref> present, in order.
        resumed = adapter.spawn_argv(
            SessionSpec(provider="claude", cwd="/w", resume_ref="sess-abc")
        )
        assert "--resume" in resumed
        assert resumed[resumed.index("--resume") + 1] == "sess-abc"

    def test_spawn_argv_runs_in_cwd(self, adapter: ClaudeAdapter) -> None:
        # The adapter shapes argv; the manager passes spec.cwd to Popen. The
        # adapter's contract is that cwd is carried on the spec it shaped argv
        # from — assert the spec round-trips (cwd is not an argv flag for the
        # claude CLI; it is the Popen cwd). This pins the seam: argv shaping is
        # cwd-independent, so the manager owns cwd placement.
        spec = SessionSpec(provider="claude", cwd="/some/specific/work")
        argv = adapter.spawn_argv(spec)
        assert spec.cwd == "/some/specific/work"
        # cwd must NOT leak into argv as a flag (the CLI is launched IN cwd).
        assert "/some/specific/work" not in argv


class TestEncode:
    """§2.4 — frame one submitted turn for the CLI's stdin."""

    def test_encode_is_ndjson_user_message(self, adapter: ClaudeAdapter) -> None:
        framed = adapter.encode("hi there")
        assert isinstance(framed, bytes)
        assert framed.endswith(b"\n"), "must be newline-terminated NDJSON"
        # Exactly one JSON object (one line before the trailing newline).
        body = framed.rstrip(b"\n")
        assert b"\n" not in body, "must be a single NDJSON line"
        record = json.loads(body)
        # stream-json user-message shape: a user role carrying the command.
        assert record["type"] == "user"
        assert record["message"]["role"] == "user"
        content = record["message"]["content"]
        # content is the text the founder typed (string or text-block form).
        as_text = (
            content
            if isinstance(content, str)
            else "".join(
                block.get("text", "")
                for block in content
                if block.get("type") == "text"
            )
        )
        assert as_text == "hi there"


class TestDecode:
    """§2.4 — map ONE recorded stdout line into a shared Event, or None."""

    def test_decode_chunk(
        self, adapter: ClaudeAdapter, happy_lines: list[bytes]
    ) -> None:
        line = _first_matching(
            happy_lines,
            lambda o: (
                o.get("type") == "stream_event"
                and (o.get("event") or {}).get("type") == "content_block_delta"
            ),
        )
        ev = adapter.decode(line)
        assert isinstance(ev, Event)
        assert ev.kind == "chunk"
        # The first recorded delta in happy.jsonl is the text "h".
        assert ev.text == "h"

    def test_decode_result(
        self, adapter: ClaudeAdapter, happy_lines: list[bytes]
    ) -> None:
        line = _first_matching(
            happy_lines,
            lambda o: (
                o.get("type") == "result"
                and o.get("subtype") == "success"
                and not o.get("is_error")
            ),
        )
        ev = adapter.decode(line)
        assert isinstance(ev, Event)
        assert ev.kind == "result"
        assert ev.result is not None
        # Recorded usage from the real turn.
        assert ev.result.input_tokens == 9074
        assert ev.result.output_tokens == 5
        assert ev.result.duration_ms == 4205
        assert ev.result.stop_reason == "end_turn"

    def test_decode_error(
        self, adapter: ClaudeAdapter, error_lines: list[bytes]
    ) -> None:
        # The recorded error turn's terminal result carries is_error=true even
        # though subtype is still "success" — is_error is the discriminator.
        line = _first_matching(
            error_lines,
            lambda o: o.get("type") == "result" and o.get("is_error") is True,
        )
        ev = adapter.decode(line)
        assert isinstance(ev, Event)
        assert ev.kind == "error"
        assert ev.error is not None
        # A model-not-found / api_error_status=404 is an EXPECTED decline
        # (the op ran and the provider declined), not an Internal bug.
        assert ev.error.category == "expected"
        assert ev.error.message  # carries the CLI's human message

    def test_decode_bookkeeping_returns_none(
        self, adapter: ClaudeAdapter, happy_lines: list[bytes]
    ) -> None:
        line = _first_matching(
            happy_lines,
            lambda o: o.get("type") == "system" and o.get("subtype") == "init",
        )
        assert adapter.decode(line) is None

    def test_decode_non_delta_stream_event_returns_none(
        self, adapter: ClaudeAdapter, happy_lines: list[bytes]
    ) -> None:
        # A recorded stream_event that is NOT a content_block_delta (e.g.
        # content_block_start / message_stop) carries no founder-facing text.
        line = _first_matching(
            happy_lines,
            lambda o: (
                o.get("type") == "stream_event"
                and (o.get("event") or {}).get("type") != "content_block_delta"
            ),
        )
        assert adapter.decode(line) is None

    def test_decode_empty_text_delta_returns_none(self, adapter: ClaudeAdapter) -> None:
        # A content_block_delta whose text is empty must yield no chunk (an
        # empty chunk is noise). The recorded fixtures never carry an empty
        # delta, but the CLI's framing permits one, so the guard is exercised
        # against a minimal real-shape delta line.
        empty_delta = json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": ""},
                },
            }
        ).encode("utf-8")
        assert adapter.decode(empty_delta) is None

    def test_decode_garbage_raises_internal(self, adapter: ClaudeAdapter) -> None:
        with pytest.raises(InternalError) as exc:
            adapter.decode(b"this is not json {{{")
        assert exc.value.code == "DECODE_FAILED"


class TestTurnComplete:
    """§2.4/§2.6 — the 'turn done' signal that frees the one-in-flight slot."""

    def test_turn_complete_true_only_on_result_success(
        self, adapter: ClaudeAdapter, happy_lines: list[bytes]
    ) -> None:
        result_line = _first_matching(
            happy_lines,
            lambda o: (
                o.get("type") == "result"
                and o.get("subtype") == "success"
                and not o.get("is_error")
            ),
        )
        result_ev = adapter.decode(result_line)
        assert result_ev is not None
        assert adapter.turn_complete(result_ev) is True

        chunk_line = _first_matching(
            happy_lines,
            lambda o: (
                o.get("type") == "stream_event"
                and (o.get("event") or {}).get("type") == "content_block_delta"
            ),
        )
        chunk_ev = adapter.decode(chunk_line)
        assert chunk_ev is not None
        assert adapter.turn_complete(chunk_ev) is False

        # An error event is terminal-ish but is NOT the success completion the
        # slot-release keys on — turn_complete must be False for it.
        error_line = _first_matching(
            _recorded_lines("error.jsonl"),
            lambda o: o.get("type") == "result" and o.get("is_error") is True,
        )
        error_ev = adapter.decode(error_line)
        assert error_ev is not None
        assert adapter.turn_complete(error_ev) is False


class TestCapabilities:
    """§2.4/§2.7 — honest capability flags."""

    def test_capabilities_claude_supports_resume(self, adapter: ClaudeAdapter) -> None:
        caps = adapter.capabilities
        assert isinstance(caps, Capabilities)
        assert caps.supports_resume is True
        assert caps.supports_tools is True
        assert caps.supports_partial_streaming is True


class TestProtocolConformance:
    """The Claude adapter satisfies the structural ProviderAdapter Protocol —
    proves Codex/Gemini can slot in against the same seam (§2.4)."""

    def test_claude_adapter_is_a_provider_adapter(self, adapter: ClaudeAdapter) -> None:
        assert isinstance(adapter, ProviderAdapter)
