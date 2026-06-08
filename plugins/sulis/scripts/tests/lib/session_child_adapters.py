"""Shared test ``ProviderAdapter`` implementations for the session-manager
interactive-terminal suites (CH-01KTGY).

Extracted here once the second consumer appeared (EP-03, the 2-consumer rule):
``tests/unit/test_viewer.py`` (WP-004) and ``tests/integration/test_socket_server.py``
(WP-005) each drove a real pty-backed child and a tiny scripted pipe child
through identical adapter shells. The adapter trio (``spawn_argv`` /
``encode`` / ``decode`` / ``turn_complete``) is the same in both; only the test
*assertions* differ. This module is the single home so a third consumer
(WP-010's end-to-end round-trip) reuses it rather than re-pasting.

Posture (MEA-09, no mocks): both adapters spawn a **real** subprocess —
:class:`PtyChildAdapter` runs WP-006's ``fake_claude_child`` in ``pty`` mode (a
real PTY-backed child echoing input + emitting ``PTY_PONG`` on the
``__PTY_PING__`` sentinel); :class:`PipeChildAdapter` runs a tiny scripted child
that emits one chunk + a terminal result per stdin turn over real pipes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.events import Event, TurnResult

# The shared fake-claude child helper lives alongside this module under tests/lib.
import fake_claude_child


#: A tiny scripted pipe child: emits one ``chunk`` then a terminal ``result`` per
#: stdin turn. The :class:`PipeChildAdapter`'s decode maps its JSON back to the
#: shared event vocabulary. Write it to a tmp path and spawn it via the adapter.
PIPE_CHILD_SOURCE = r"""
import json, sys

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    text = str(msg.get("command", ""))
    emit({"kind": "chunk", "text": text})
    emit({"kind": "result", "input_tokens": 1, "output_tokens": len(text),
          "duration_ms": 1, "stop_reason": "end_turn"})
"""


class PtyChildAdapter:
    """A real :class:`ProviderAdapter` whose child runs as a raw PTY terminal.

    ``spawn_argv`` starts WP-006's ``fake_claude_child`` in ``pty`` mode (echoes
    stdin to stdout, emits ``PTY_PONG`` on the ``__PTY_PING__`` sentinel). The
    encode/decode/turn_complete trio is unused on the pty path (a pty session is a
    terminal view, not a structured-chat stream), but the Protocol shape is
    honoured so the manager treats it like any other adapter.
    """

    capabilities = Capabilities(
        supports_resume=False,
        supports_tools=False,
        supports_partial_streaming=False,
    )

    def __init__(self, child: Path) -> None:
        self._child = child

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return fake_claude_child.child_argv(self._child, mode="pty")

    def encode(self, command: str) -> bytes:  # pragma: no cover - unused on pty
        return command.encode("utf-8")

    def decode(self, line: bytes):  # pragma: no cover - unused on pty
        return None

    def turn_complete(self, event) -> bool:  # pragma: no cover - unused on pty
        return False


class PipeChildAdapter:
    """A real pipe-mode :class:`ProviderAdapter` over the scripted pipe child.

    Spawns :data:`PIPE_CHILD_SOURCE` (written to a tmp path) and maps its JSON
    lines back to the shared :class:`Event` vocabulary — the structured-chat path
    the base contract serves (§2.2 / §2.5).
    """

    capabilities = Capabilities(
        supports_resume=False,
        supports_tools=False,
        supports_partial_streaming=True,
    )

    def __init__(self, child: Path) -> None:
        self._child = child

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return [sys.executable, str(self._child)]

    def encode(self, command: str) -> bytes:
        return (json.dumps({"command": command}) + "\n").encode("utf-8")

    def decode(self, line: bytes) -> Event | None:
        record = json.loads(line)
        if record.get("kind") == "chunk":
            return Event(offset=-1, key="", turn=-1, kind="chunk", text=record["text"])
        if record.get("kind") == "result":
            return Event(
                offset=-1,
                key="",
                turn=-1,
                kind="result",
                result=TurnResult(
                    input_tokens=int(record.get("input_tokens", 0)),
                    output_tokens=int(record.get("output_tokens", 0)),
                    duration_ms=int(record.get("duration_ms", 0)),
                    stop_reason=str(record.get("stop_reason", "")),
                ),
            )
        return None

    def turn_complete(self, event: Event) -> bool:
        return event.kind == "result"
