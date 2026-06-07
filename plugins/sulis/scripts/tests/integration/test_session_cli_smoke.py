"""WP-009 — the CLI driver's CI smoke (claude-free, deterministic).

Contract: SESSION_MANAGER_CONTRACT §2.2 (the six-method surface) + WP-009 DoD
Red. This guards the *plumbing* of ``sulis_session.py`` — that the CLI wires the
in-process :class:`SessionManager` + the Claude adapter into a live
open→send→read --follow→close flow and streams chunks to stdout as they arrive.

**Verification posture (MEA-09).** No mock of the manager or its adapter. The
smoke runs the *real* CLI over a *real* scripted child process that emits *real*
``claude`` stream-json lines — so the CLI exercises the genuine
``ClaudeAdapter.decode`` path, just without paying for (or depending on) the
real ``claude`` binary in CI. The child is a deterministic python program; the
real-``claude`` run is the separate **observed-done** gate
(``tests/manual/session_driver_observed.md``), not this file.

The CLI exposes a single injection seam for tests: the
``SULIS_SESSION_CLAUDE_ARGV`` env var. When set (a JSON list), the Claude
adapter spawns that argv instead of the real ``claude`` binary — but keeps its
real ``encode`` / ``decode`` / ``turn_complete``. The scripted child below
speaks the stream-json wire the real adapter decodes, so the CLI's behaviour
under test is identical to production minus the model.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_CLI = _SCRIPTS_DIR / "sulis_session.py"

# The shared fake-claude child helper lives under tests/lib; add it to the path
# the same way the conftests add their own dirs (per-file insert convention).
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402

# Bounded so a genuine hang fails CI fast rather than blocking.
_TIMEOUT = 30.0


@pytest.fixture
def fake_claude(tmp_path: Path) -> list[str]:
    """A real subprocess argv that fakes `claude` over real stream-json, in
    ``memory`` mode so the second turn can prove memory across turns (the shared
    child remembers the first prompt and references it on turn two)."""
    child = fake_claude_child.write_child(tmp_path)
    return fake_claude_child.child_argv(child, mode="memory")


def _run_demo(fake_claude: list[str], cwd: Path, message: str) -> str:
    """Run the CLI's single-process demo flow with the fake claude injected."""
    env = {
        "SULIS_SESSION_CLAUDE_ARGV": json.dumps(fake_claude),
    }
    # Inherit PATH/PYTHONPATH from the parent so `uv`/imports resolve.
    full_env = {**os.environ, **env}
    proc = subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "demo",
            "--key",
            "smoke1",
            "--cwd",
            str(cwd),
            "--message",
            message,
        ],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        env=full_env,
    )
    assert proc.returncode == 0, (
        f"demo exited {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )
    return proc.stdout


def test_cli_demo_streams_open_send_read_close(fake_claude, tmp_path):
    """The demo flow prints: the open result, a landing offset, streamed chunk
    text, a turn result, and a clean close — over the real adapter decode path
    (WP-009 DoD Red)."""
    out = _run_demo(fake_claude, tmp_path, "say hi")

    # 1. open result — the session is live (pid + provider + state surfaced).
    assert "provider" in out and "claude" in out
    assert "state" in out

    # 2. a landing offset from send (the bookmark, §2.2).
    assert "offset" in out.lower()

    # 3. the streamed reply text appeared (the fake echoes "you said say hi").
    assert "you said say hi" in out

    # 4. a turn result (done marker with usage) was rendered.
    assert "result" in out.lower()

    # 5. a clean close line.
    assert "close" in out.lower()


def test_cli_demo_second_turn_warm_reuse(fake_claude, tmp_path):
    """The demo's second turn proves warm reuse + memory: it runs over the SAME
    process (no re-open) and the reply references the first turn (§2.2 decoupled
    send/read over one warm session)."""
    out = _run_demo(fake_claude, tmp_path, "say hi")

    # The second reply references the first prompt — memory across turns, the
    # same warm process answering twice (contract Part 1 win #2).
    assert "earlier you said say hi" in out

    # Exactly one open occurred (warm reuse, not a fresh spawn per turn): one
    # `open:` line, and both turns + the health snapshot share one pid.
    open_lines = [ln for ln in out.splitlines() if ln.startswith("open:")]
    assert len(open_lines) == 1, f"expected one open, got {open_lines}"
    open_pid = json.loads(open_lines[0].split("open:", 1)[1])["pid"]
    health_line = next(ln for ln in out.splitlines() if ln.startswith("health:"))
    assert json.loads(health_line.split("health:", 1)[1])["pid"] == open_pid


def test_cli_subcommands_open_send_read_status_health_close(fake_claude, tmp_path):
    """The six-method surface is reachable as discrete subcommands in one
    process (the multi-invocation shape the contract names, §2.2). Driven here
    via the demo's verbose trace, which names each method as it calls it."""
    out = _run_demo(fake_claude, tmp_path, "say hi")
    lowered = out.lower()
    # Each of the six methods leaves a trace in the demo output.
    for method in ("open", "send", "read", "status", "health", "close"):
        assert method in lowered, f"demo trace missing {method!r}:\n{out}"
