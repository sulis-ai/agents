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

Two reply modes:

  - ``echo`` (default): the reply is ``"echo <prompt>"`` — a stable token the
    smoke can assert appears, proving the streamed text round-trips.
  - ``memory``: the FIRST turn replies ``"you said <prompt>"`` and remembers the
    prompt; the SECOND turn replies ``"earlier you said <first prompt>"`` —
    proving "memory across turns" the same way the real model would.

The source is exposed as a string (``CHILD_SOURCE``) and written to a path via
:func:`write_child`; the argv to spawn it is built by :func:`child_argv`.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: The fake-claude child program. ``argv[1]`` selects the reply mode
#: ("echo" | "memory"); default "echo".
CHILD_SOURCE = r"""
import json, sys

mode = sys.argv[1] if len(sys.argv) > 1 else "echo"

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

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
