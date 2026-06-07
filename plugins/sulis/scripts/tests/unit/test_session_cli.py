"""WP-009 — in-process unit cover for the CLI driver (``sulis_session.py``).

The integration smoke (``tests/integration/test_session_cli_smoke.py``) runs the
CLI as a *subprocess* — the honest end-to-end shape — but a subprocess is opaque
to coverage. These tests call ``main(argv)`` and the subcommand helpers
**in-process** (same fake-``claude`` seam, ``SULIS_SESSION_CLAUDE_ARGV``) so the
driver's branches are exercised and measured directly.

Still claude-free, still MEA-09: the spawned child is a real subprocess running a
deterministic script that speaks real ``claude`` stream-json; only the binary is
faked, the adapter's ``encode`` / ``decode`` / ``turn_complete`` are the real
ones.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import sulis_session

# The shared fake-claude child helper lives under tests/lib; add it to the path
# the same way the conftests add their own dirs (per-file insert convention).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests" / "lib"))
import fake_claude_child  # noqa: E402


@pytest.fixture
def fake_claude(tmp_path: Path, monkeypatch) -> Path:
    """Inject the shared fake-claude child (echo mode) via the CLI's test seam."""
    child = fake_claude_child.write_child(tmp_path)
    monkeypatch.setenv(
        "SULIS_SESSION_CLAUDE_ARGV",
        json.dumps(fake_claude_child.child_argv(child, mode="echo")),
    )
    return child


def test_demo_flow_streams_and_remembers(fake_claude, tmp_path, capsys):
    """``main(['demo', ...])`` runs the whole flow in-process: open, two sends,
    two live reads, status, health, close — exit 0."""
    rc = sulis_session.main(
        ["demo", "--key", "u1", "--cwd", str(tmp_path), "--message", "hello there"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "open:" in out
    assert "echo hello there" in out  # turn 1 streamed reply
    assert '"turn": 2' in out  # a second send over the warm session
    assert "status:" in out and "health:" in out
    assert "close:" in out


def test_open_subcommand(fake_claude, tmp_path, capsys):
    rc = sulis_session.main(["open", "--key", "o1", "--cwd", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("open:")
    payload = json.loads(out.split("open:", 1)[1])
    assert payload["provider"] == "claude"
    assert payload["resumed"] is False
    assert isinstance(payload["pid"], int)


def test_send_subcommand_prints_offset(fake_claude, tmp_path, capsys):
    rc = sulis_session.main(
        ["send", "--key", "s1", "--cwd", str(tmp_path), "--message", "ping"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    send_line = next(ln for ln in out.splitlines() if ln.startswith("send:"))
    assert json.loads(send_line.split("send:", 1)[1])["offset"] == 0


def test_read_history_empty_log_surfaces_expected_error(fake_claude, tmp_path, capsys):
    """``read`` without ``--follow`` (history mode) on a freshly-opened session
    with no turn yet asks for an offset at/beyond the log end — an Expected
    decline (§2.5: ``since > current max offset`` under ``follow=False``). The
    CLI surfaces it at its boundary as exit 1 with a readable error, not a
    crash."""
    rc = sulis_session.main(
        ["read", "--key", "r1", "--cwd", str(tmp_path), "--since", "0"]
    )
    assert rc == 1
    assert "error:" in capsys.readouterr().err


def test_status_subcommand_empty(fake_claude, capsys):
    """A fresh process owns no sessions → status is an empty list (the snapshot
    surface, side-effect-free)."""
    rc = sulis_session.main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("status:")
    assert json.loads(out.split("status:", 1)[1]) == []


def test_health_subcommand(fake_claude, tmp_path, capsys):
    rc = sulis_session.main(["health", "--key", "h1", "--cwd", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out.split("health:", 1)[1])
    assert payload["alive"] is True
    assert payload["provider"] == "claude"


def test_close_unknown_key_is_noop(capsys):
    """Closing a key with no live session is a no-op that still prints + exits
    0 (idempotent close, §2.2)."""
    rc = sulis_session.main(["close", "--key", "nope"])
    assert rc == 0
    assert capsys.readouterr().out.startswith("close:")


def test_no_command_prints_help_exit_2(capsys):
    rc = sulis_session.main([])
    assert rc == 2


def test_unknown_provider_cwd_error_returns_1(monkeypatch, tmp_path, capsys):
    """A spawn against a missing cwd surfaces the manager's Expected error at the
    CLI boundary as exit 1 (the top-level except), not a crash."""
    monkeypatch.setenv(
        "SULIS_SESSION_CLAUDE_ARGV", json.dumps([sys.executable, "-c", "pass"])
    )
    rc = sulis_session.main(
        ["open", "--key", "bad", "--cwd", str(tmp_path / "does-not-exist")]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err


def test_send_subcommand_streams_reply(fake_claude, tmp_path, capsys):
    """``send`` drains its turn (so the child isn't killed mid-write): the
    streamed reply text appears."""
    rc = sulis_session.main(
        ["send", "--key", "s2", "--cwd", str(tmp_path), "--message", "drain me"]
    )
    assert rc == 0
    assert "echo drain me" in capsys.readouterr().out


def _ev(kind, **payload):
    return sulis_session.Event(offset=0, key="k", turn=0, kind=kind, **payload)


def test_render_event_live_chunk_is_raw_text(capsys):
    sulis_session._render_event_live(_ev("chunk", text="hi"))
    assert capsys.readouterr().out == "hi"


def test_render_event_live_result_renders_usage(capsys):
    from _session_manager import TurnResult

    sulis_session._render_event_live(
        _ev(
            "result",
            result=TurnResult(
                input_tokens=2, output_tokens=3, duration_ms=4, stop_reason="end_turn"
            ),
        )
    )
    out = capsys.readouterr().out
    assert "result:" in out
    assert json.loads(out.split("result:", 1)[1])["stop_reason"] == "end_turn"


def test_render_event_live_error_renders_typed_payload(capsys):
    from _session_manager import EventError

    sulis_session._render_event_live(
        _ev(
            "error",
            error=EventError(category="expected", code="429", message="rate limit"),
        )
    )
    out = capsys.readouterr().out
    assert "error:" in out
    payload = json.loads(out.split("error:", 1)[1])
    assert payload["category"] == "expected"
    assert payload["code"] == "429"


def test_render_event_live_tool_use(capsys):
    from _session_manager import ToolUse

    sulis_session._render_event_live(
        _ev("tool_use", tool=ToolUse(name="Bash", input_summary="ls"))
    )
    assert "tool_use:" in capsys.readouterr().out


def test_demo_in_process_emits_full_trace(fake_claude, tmp_path, capsys):
    """Run the demo flow in-process (the same flow the integration smoke runs as
    a subprocess) so its branches are covered: open, two sends, two live reads,
    the per-turn timings, status, health, close."""
    import argparse

    args = argparse.Namespace(
        key="dip",
        cwd=str(tmp_path),
        message="remember this",
        resume_ref=None,
    )
    rc = sulis_session._run_demo(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "open:" in out
    assert "echo remember this" in out  # turn 1 reply streamed
    assert '"turn": 2' in out  # warm second turn
    assert "turn1_seconds:" in out and "turn2_seconds:" in out
    assert "status:" in out and "health:" in out
    assert out.rstrip().endswith('close: {"key": "dip"}')


def test_read_follow_streams_a_live_turn(fake_claude, tmp_path):
    """Drive an open+send, then read --follow from the offset in-process and
    confirm the reply streams to the terminal result (the live-tail path)."""
    mgr = sulis_session._build_manager()
    try:
        mgr.open(
            "rf",
            sulis_session.SessionSpec(provider="claude", cwd=str(tmp_path)),
        )
        offset = mgr.send("rf", "tail this")
        secs = sulis_session._stream_turn(mgr, "rf", offset)
        assert secs >= 0.0
        # The whole turn (chunks + result) is now in the log.
        events = list(mgr.read("rf", since=offset, follow=False))
        kinds = [e.kind for e in events]
        assert "chunk" in kinds and kinds[-1] == "result"
    finally:
        mgr.close("rf")
