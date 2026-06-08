"""Shared test helper (WP-009): a deterministic fake-``claude`` child that speaks
real ``claude`` stream-json.

Both the CLI smoke (``tests/integration/test_session_cli_smoke.py``) and the
in-process CLI unit cover (``tests/unit/test_session_cli.py``) drive the real
``ClaudeAdapter`` (its real ``encode`` / ``decode`` / ``turn_complete``) against
this child instead of the real ``claude`` binary — so the CLI's behaviour under
test is production minus the model (MEA-09: a real subprocess emitting a real
recorded wire shape, not a mock). Extracted here once the second consumer
appeared (EP-03 2-consumer rule).

The child reads the adapter's stream-json user-message NDJSON from stdin (one
line per turn) and emits, per turn:

  - a ``content_block_delta`` per word fragment  → the adapter decodes ``chunk``
  - a ``result`` (``is_error`` falsey, with usage) → the turn-terminal ``result``

Three reply modes:

  - ``echo`` (default): the reply is ``"echo <prompt>"`` — a stable token the
    smoke can assert appears, proving the streamed text round-trips.
  - ``memory``: the FIRST turn replies ``"you said <prompt>"`` and remembers the
    prompt; the SECOND turn replies ``"earlier you said <first prompt>"`` —
    proving "memory across turns" the same way the real model would.
  - ``pty``: the child behaves like a raw terminal child — it echoes stdin bytes
    back to stdout, and on the sentinel line ``__PTY_PING__`` writes the known
    output line ``PTY_PONG``. This is the **real** PTY-backed child the
    interactive-terminal integration tests run against (MEA-09: no mocks in
    integration) — consumed by WP-003 (master-read), WP-004 (viewer), WP-005
    (socket), WP-010 (end-to-end round-trip).

The source is exposed as a string (``CHILD_SOURCE``) and written to a path via
:func:`write_child`; the argv to spawn it is built by :func:`child_argv`.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: The fake-claude child program. ``argv[1]`` selects the reply mode
#: ("echo" | "memory" | "pty"); default "echo".
CHILD_SOURCE = r"""
import json, sys

mode = sys.argv[1] if len(sys.argv) > 1 else "echo"

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

if mode == "pty":
    # Raw-terminal child: the real PTY-backed adapter the interactive-terminal
    # integration tests drive (WP-003/004/005/010). It speaks bytes, not
    # stream-json — it echoes stdin straight back to stdout (so a master read
    # surfaces what was typed even with the tty's own ECHO off), and on the
    # sentinel line "__PTY_PING__" writes the deterministic line "PTY_PONG".
    in_fd = sys.stdin.fileno()
    out_fd = sys.stdout.fileno()
    import os as _os
    line_buf = b""
    while True:
        data = _os.read(in_fd, 1024)
        if not data:
            break
        _os.write(out_fd, data)  # echo input back verbatim
        line_buf += data
        while b"\n" in line_buf:
            one, line_buf = line_buf.split(b"\n", 1)
            if one.strip() == b"__PTY_PING__":
                _os.write(out_fd, b"PTY_PONG\n")
    sys.exit(0)

first_prompt = None
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    content = msg.get("message", {}).get("content", "")
    if mode == "memory":
        if first_prompt is None:
            first_prompt = content
            reply = "you said " + content
        else:
            reply = "earlier you said " + first_prompt
    else:
        reply = "echo " + content

    for i, word in enumerate(reply.split(" ")):
        frag = word if i == 0 else " " + word
        emit({
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": frag},
            },
        })
    emit({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 1,
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1, "output_tokens": len(reply)},
    })
"""


def write_child(tmp_path: Path) -> Path:
    """Write the child program under ``tmp_path`` and return its path."""
    child = tmp_path / "fake_claude.py"
    child.write_text(CHILD_SOURCE)
    return child


def child_argv(child: Path, mode: str = "echo") -> list[str]:
    """The argv that spawns the child in the given reply mode. Suitable as the
    JSON value of ``SULIS_SESSION_CLAUDE_ARGV``."""
    return [sys.executable, str(child), mode]
