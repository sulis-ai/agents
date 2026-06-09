"""WP-002 (change-owned-terminal-shared-session) — the ``ensure-daemon`` /
stable-socket presence contract (Python binding).

Contract: ``_session_manager/DAEMON_CONTRACT.md`` + TDD §2.2/§5 (the new
CONTRACT_FIRST producer/consumer seam) + ADR-001 (shared daemon: singleton via
``fcntl.flock``, stable socket, on-demand start). This is the one function both
views — the desktop launcher (this WP) and the cockpit (WP-006, Node binding) —
call before connecting.

Verification posture (MEA-09, no mocks): every test drives a **real** detached
process over a **real** AF_UNIX socket. The process is a *fake daemon* — a tiny
stdlib script that answers the contract's ``status`` liveness probe with
``ok:true`` and prints the ``READY <socket>`` handshake, exactly as the real
daemon (WP-003) will. Spawning is **injected** so this WP does not depend on
WP-003's entrypoint: ``ensure_daemon`` accepts the spawn argv to run, and the
fake daemon records each launch by appending to a counter file. That counter is
the literal proof of the singleton / idempotent-ensure guarantees.

Tests (RED first, per the WP Definition of Done):
    test_ensure_daemon.py::test_daemon_is_live_false_when_nothing_serves
    test_ensure_daemon.py::test_ensure_daemon_cold_start_then_warm_is_noop
    test_ensure_daemon.py::test_concurrent_ensure_daemon_yields_one_spawn
"""

from __future__ import annotations

import ast
import os
import threading
import time
from pathlib import Path

import pytest

# The daemon-presence binding lives in the engine's home alongside the frozen
# modules it composes (it speaks the engine's §2.13 NDJSON wire).
from _session_manager import daemon_client


# Bounded wait for a process/thread assertion — long enough never to flake on a
# loaded CI runner, short enough that a real hang fails fast (mirrors the host
# integration suite's ``_WAIT``).
_WAIT = 8.0


# ─── the fake daemon: a real detached process honouring the contract ──────────
#
# It is the test substrate the way ``fake_claude_child`` is for the pty path: a
# real program, not a mock. It binds the contract's socket, answers the
# ``status`` liveness probe with a framed ``ok:true`` line, prints ``READY``,
# and — critically — records every launch so the tests can assert exactly one
# spawn. It deliberately does NOT take the flock; the flock is the *daemon's*
# job (WP-003). What WP-002 owns and proves here is the *caller* contract:
# probe-first, spawn-once, race-tolerant.

_FAKE_DAEMON_SOURCE = r"""
import argparse
import json
import socket
import socketserver
import sys
import threading
import time

parser = argparse.ArgumentParser()
parser.add_argument("--socket", required=True)
parser.add_argument("--counter", required=True)
parser.add_argument("--bind-delay", type=float, default=0.0)
args = parser.parse_args()

# Record this launch (append a byte) BEFORE binding, so a launch that races and
# loses is still counted — the assertion is "how many processes were started",
# which is the singleton property under test.
with open(args.counter, "ab") as fh:
    fh.write(b"x")
    fh.flush()

# Simulated bind latency widens the race window for the concurrency test.
if args.bind_delay:
    time.sleep(args.bind_delay)


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        buf = b""
        while True:
            chunk = self.rfile.read1(65536) if hasattr(self.rfile, "read1") else self.connection.recv(65536)
            if not chunk:
                return
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    req = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if req.get("method") == "status":
                    resp = {"id": req.get("id"), "ok": True, "result": []}
                else:
                    resp = {"id": req.get("id"), "ok": False,
                            "error": {"category": "expected", "code": "UNKNOWN_METHOD"}}
                self.connection.sendall((json.dumps(resp) + "\n").encode("utf-8"))


class _Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


server = _Server(args.socket, _Handler, bind_and_activate=False)
try:
    server.server_bind()
except OSError:
    # Another launcher won the socket — losing the bind race is normal for a
    # non-flock fake. Exit 0; the winner serves. (The real daemon uses flock to
    # arbitrate this; the caller contract only needs "the socket answers".)
    sys.exit(0)
server.server_activate()

sys.stdout.write("READY " + args.socket + "\n")
sys.stdout.flush()

threading.Thread(target=server.serve_forever, daemon=True).start()
# Stay alive so the socket keeps answering for the duration of the test.
time.sleep(3600)
"""


@pytest.fixture
def fake_daemon_script(tmp_path: Path) -> Path:
    """Write the fake-daemon program once per test and return its path."""
    script = tmp_path / "fake_daemon.py"
    script.write_text(_FAKE_DAEMON_SOURCE)
    return script


@pytest.fixture
def socket_path(tmp_path: Path) -> str:
    """The stable-socket stand-in for the test (kept short — AF_UNIX path
    length is bounded at ~104 bytes on macOS)."""
    return str(tmp_path / "d.sock")


@pytest.fixture
def counter(tmp_path: Path) -> Path:
    """A file the fake daemon appends one byte to per launch — the spawn count."""
    return tmp_path / "spawns"


def _spawn_count(counter: Path) -> int:
    return counter.stat().st_size if counter.exists() else 0


def _spawn_command(
    python: str, script: Path, counter: Path, *, bind_delay: float = 0.0
) -> list[str]:
    """The injected argv ``ensure_daemon`` runs to start a (fake) daemon. The
    placeholder mirrors how the real call substitutes the socket — ``{socket}``
    is filled by ``ensure_daemon`` with the resolved socket path."""
    cmd = [python, str(script), "--socket", "{socket}", "--counter", str(counter)]
    if bind_delay:
        cmd += ["--bind-delay", str(bind_delay)]
    return cmd


# ─── the RED tests ────────────────────────────────────────────────────────────


def test_daemon_is_live_false_when_nothing_serves(socket_path: str) -> None:
    """Liveness is False when no process serves the path: a fresh socket path
    has nothing to ``connect`` to, so the probe must report dead — fast, not
    hang. Fails before ``daemon_client`` exists."""
    assert not Path(socket_path).exists()
    start = time.monotonic()
    assert daemon_client.daemon_is_live(socket_path) is False
    # A dead socket must fail fast (Blue: short connect timeout), never block on
    # the default OS connect timeout.
    assert time.monotonic() - start < _WAIT, "liveness probe on a dead socket hung"


def test_ensure_daemon_cold_start_then_warm_is_noop(
    socket_path: str, fake_daemon_script: Path, counter: Path
) -> None:
    """Cold start spawns the daemon exactly once and returns the socket with a
    live daemon serving it; a second call (now warm) spawns nothing and returns
    the same path. The idempotent-ensure guarantee. Fails before the binding
    exists."""
    cmd = _spawn_command("python3", fake_daemon_script, counter)

    returned = daemon_client.ensure_daemon(
        socket_path, spawn_command=cmd, ready_timeout=_WAIT
    )
    assert returned == socket_path
    assert daemon_client.daemon_is_live(socket_path) is True
    assert _spawn_count(counter) == 1, "cold start did not spawn exactly once"

    # Warm call: the daemon already answers, so ensure_daemon must NOT spawn.
    returned2 = daemon_client.ensure_daemon(
        socket_path, spawn_command=cmd, ready_timeout=_WAIT
    )
    assert returned2 == socket_path
    assert _spawn_count(counter) == 1, "warm ensure_daemon spawned a second daemon"


def test_concurrent_ensure_daemon_yields_one_spawn(
    socket_path: str, fake_daemon_script: Path, counter: Path
) -> None:
    """N callers racing ``ensure_daemon`` for a cold socket yield **exactly one**
    live daemon; losers of the race poll until the winner answers and return the
    same socket. The race-tolerant / singleton guarantee (ADR-001). A small bind
    delay widens the window so the race is real. Fails before the binding
    exists."""
    cmd = _spawn_command("python3", fake_daemon_script, counter, bind_delay=0.4)

    n = 6
    results: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker() -> None:
        try:
            barrier.wait(timeout=_WAIT)
            got = daemon_client.ensure_daemon(
                socket_path, spawn_command=cmd, ready_timeout=_WAIT
            )
            with lock:
                results.append(got)
        except BaseException as exc:  # noqa: BLE001 - surface any worker failure
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=_WAIT * 2)

    assert not errors, f"concurrent ensure_daemon raised: {errors!r}"
    assert len(results) == n, "not every concurrent caller returned"
    assert all(r == socket_path for r in results), results
    assert daemon_client.daemon_is_live(socket_path) is True
    assert _spawn_count(counter) == 1, (
        f"concurrent ensure_daemon spawned {_spawn_count(counter)} daemons, "
        "expected exactly one"
    )


def test_module_is_terminal_only_no_chat_or_platform_import() -> None:
    """Independence directive (founder, MUST; ADR-003): the daemon-presence
    binding imports the **Python stdlib only** — never the cockpit chat relay,
    the chat ``SessionBridge``, or the ``platform`` communication service. The
    terminal daemon is terminal-only.

    This is the codified import-graph note the WP Blue checklist requires: it
    parses the module's import statements and asserts none names a forbidden
    dependency, so the directive cannot regress silently."""
    module_path = Path(daemon_client.__file__)
    tree = ast.parse(module_path.read_text())

    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # Relative imports (level>0) stay inside _session_manager; flag them
            # too — the contract is stdlib-only, not even engine internals.
            if node.module:
                imported_roots.add(node.module.split(".")[0])
            if node.level:
                imported_roots.add("<relative>")

    forbidden = {"chat", "platform", "sessionbridge", "_session_manager", "<relative>"}
    leaked = imported_roots & forbidden
    assert not leaked, (
        f"daemon_client.py imports forbidden modules {leaked!r} — it must be "
        "terminal-only stdlib (independence directive, ADR-003)"
    )

    stdlib_allow = {
        "__future__",
        "json",
        "os",
        "signal",  # #102: SIGTERM a version-skewed daemon (still stdlib-only)
        "socket",
        "subprocess",
        "threading",
        "time",
        "pathlib",
    }
    unexpected = imported_roots - stdlib_allow
    assert not unexpected, (
        f"daemon_client.py imports unexpected non-stdlib modules: {unexpected!r}"
    )


def test_default_socket_honours_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """``DEFAULT_SOCKET`` resolves to ``~/.sulis/session-manager.sock`` and is
    overridable by ``SULIS_SESSION_MANAGER_SOCKET`` (the test/CI injection seam,
    mirroring ``SULIS_SESSION_MANAGER_HOST``). Fails before the binding exists."""
    monkeypatch.setenv("SULIS_SESSION_MANAGER_SOCKET", "/tmp/override.sock")
    assert daemon_client.resolve_default_socket() == "/tmp/override.sock"

    monkeypatch.delenv("SULIS_SESSION_MANAGER_SOCKET", raising=False)
    resolved = daemon_client.resolve_default_socket()
    assert resolved.endswith(os.path.join(".sulis", "session-manager.sock")), resolved
    assert os.path.isabs(resolved), resolved


# ─── contract-edge coverage: error categories + race-loser polling ────────────


# A daemon that connects + answers but reports ``ok:false`` is NOT live (the
# contract's Expected category — a present-but-unhealthy daemon). Same shape as
# the fake, but the ``status`` reply carries ok:false.
_UNHEALTHY_DAEMON_SOURCE = _FAKE_DAEMON_SOURCE.replace(
    '"ok": True, "result": []', '"ok": False, "error": {"category": "internal"}'
)


def test_daemon_is_live_false_when_status_not_ok(
    tmp_path: Path, socket_path: str, counter: Path
) -> None:
    """A daemon that connects but answers ``status`` with ``ok:false`` is treated
    as dead (Expected category): connect alone is not liveness, the round-trip
    must return ok:true (``DAEMON_CONTRACT.md`` § Liveness)."""
    script = tmp_path / "unhealthy.py"
    script.write_text(_UNHEALTHY_DAEMON_SOURCE)
    import subprocess

    proc = subprocess.Popen(  # noqa: S603 - test-controlled argv
        ["python3", str(script), "--socket", socket_path, "--counter", str(counter)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        # Wait for READY so the socket is genuinely serving before probing.
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            line = proc.stdout.readline() if proc.stdout else ""
            if line.startswith("READY"):
                break
        assert daemon_client.daemon_is_live(socket_path) is False
    finally:
        proc.terminate()
        proc.wait(timeout=_WAIT)


def test_ensure_daemon_raises_when_daemon_never_becomes_live(
    tmp_path: Path, socket_path: str
) -> None:
    """A spawn that runs but never serves the socket (no READY, no liveness)
    raises :class:`DaemonStartError` within ``ready_timeout`` — the Internal
    category (the daemon is broken, not absent)."""
    # A do-nothing program: it exits 0 immediately, never binds, never prints
    # READY. ensure_daemon must give up after the deadline and raise.
    dud = tmp_path / "dud.py"
    dud.write_text("import sys; sys.exit(0)\n")
    cmd = ["python3", str(dud), "--socket", "{socket}"]

    with pytest.raises(daemon_client.DaemonStartError):
        daemon_client.ensure_daemon(socket_path, spawn_command=cmd, ready_timeout=1.0)


def test_ensure_daemon_polls_when_spawn_loses_race(
    tmp_path: Path, fake_daemon_script: Path, socket_path: str, counter: Path
) -> None:
    """Race-loser path: the caller's own spawn exits 0 without printing READY
    (it lost the singleton race), but a peer daemon becomes live during the
    poll window — so ``ensure_daemon`` does NOT raise; it polls and returns the
    live socket. Models the flock-loser branch (ADR-001) at the caller seam.

    Determinism: the injected spawn is a dud that exits 0 immediately (never
    serves). Concurrently, a peer fake daemon is launched in a background thread
    so the socket goes live *after* ensure_daemon has spawned its dud and dropped
    into the poll loop — exercising ``_await_ready``'s exit-without-READY branch
    and ``_poll_until_live``'s success branch."""
    import subprocess

    dud = tmp_path / "loser.py"
    dud.write_text("import sys; sys.exit(0)\n")

    peer_holder: dict[str, subprocess.Popen] = {}

    def launch_peer() -> None:
        # Small delay so ensure_daemon's dud has spawned + exited and is polling.
        time.sleep(0.3)
        peer_holder["proc"] = subprocess.Popen(  # noqa: S603 - test-controlled
            [
                "python3",
                str(fake_daemon_script),
                "--socket",
                socket_path,
                "--counter",
                str(counter),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    peer_thread = threading.Thread(target=launch_peer)
    peer_thread.start()
    try:
        returned = daemon_client.ensure_daemon(
            socket_path,
            spawn_command=["python3", str(dud), "--socket", "{socket}"],
            ready_timeout=_WAIT,
        )
        assert returned == socket_path
        assert daemon_client.daemon_is_live(socket_path) is True
    finally:
        peer_thread.join(timeout=_WAIT)
        proc = peer_holder.get("proc")
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=_WAIT)
