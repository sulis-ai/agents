"""``_session_manager.daemon_client`` — the daemon-presence contract binding.

The Python half of the CONTRACT_FIRST seam documented in ``DAEMON_CONTRACT.md``
(TDD §5, ADR-001). Both views start the shared session-manager daemon through
this contract before connecting: this module is the desktop launcher's caller
(WP-005); the cockpit's Node ``ensureDaemon`` (WP-006) is the sibling binding
over the same wire.

What this module owns is the **caller** side of the presence contract:

- ``resolve_default_socket`` / ``DEFAULT_SOCKET`` — the stable socket location,
  env-overridable (``SULIS_SESSION_MANAGER_SOCKET``).
- ``daemon_is_live`` — the liveness probe: connect + a ``status`` round-trip
  that must return ``ok:true``, with a short timeout so a dead socket fails fast.
- ``ensure_daemon`` — probe-first, spawn-at-most-once, race-tolerant start. If
  no daemon answers, spawn one **detached** and wait for ``READY``; if a peer
  caller wins the singleton race, poll until its daemon answers.

The flock singleton arbitration itself is the **daemon's** job (WP-003); the
caller contract here is the matching half — never assume a spawn won, always
re-confirm liveness, and tolerate a peer having started the daemon instead.

Independence (founder directive, MUST): this module imports the **Python stdlib
only**. No chat relay, no ``platform`` communication service, no engine
internals — it speaks the engine's §2.13 NDJSON wire as a plain socket client.
The import-graph note: ``import socket, subprocess, fcntl, json, os, time`` and
nothing from ``_session_manager`` itself. The terminal daemon is terminal-only.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

# The real daemon entrypoint (WP-003) lives beside this package's parent — the
# scripts dir that already hosts ``session_manager_host.py``. The default spawn
# argv points at it; tests inject ``spawn_command`` instead, so this WP does not
# depend on WP-003 having landed.
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_DAEMON_ENTRYPOINT = _SCRIPTS_DIR / "session_manager_daemon.py"

# The token in a spawn argv that ``ensure_daemon`` replaces with the resolved
# socket path (so an injected command names the socket without re-spelling it).
_SOCKET_TOKEN = "{socket}"

_ENV_SOCKET_OVERRIDE = "SULIS_SESSION_MANAGER_SOCKET"

# Process-local arbitration: concurrent ``ensure_daemon`` callers *within one
# process* (e.g. several threads in the desktop launcher) collapse to a single
# probe→spawn critical section per socket, so they yield one spawn rather than
# each racing a launch. Cross-process arbitration is the daemon's ``fcntl.flock``
# (ADR-001, WP-003): a launch that loses the flock exits 0 and the caller polls.
# The two together give the "at most one daemon" guarantee end to end.
_spawn_locks: dict[str, threading.Lock] = {}
_spawn_locks_guard = threading.Lock()


def _spawn_lock_for(socket_path: str) -> threading.Lock:
    """The per-socket process-local spawn lock (created on first use)."""
    with _spawn_locks_guard:
        lock = _spawn_locks.get(socket_path)
        if lock is None:
            lock = threading.Lock()
            _spawn_locks[socket_path] = lock
        return lock


class DaemonStartError(RuntimeError):
    """The daemon was spawned but did not become live within ``ready_timeout``.

    This is the contract's **Internal** category (CF-03): the daemon exists but
    is broken, distinct from "no daemon present" (which ``ensure_daemon`` heals
    by spawning). Callers log + escalate; retrying unchanged repeats it.
    """


def resolve_default_socket() -> str:
    """The stable daemon socket path.

    ``~/.sulis/session-manager.sock`` by default, overridable by the
    ``SULIS_SESSION_MANAGER_SOCKET`` env var (the test/CI injection seam,
    mirroring the existing ``SULIS_SESSION_MANAGER_HOST`` override). Always an
    absolute path.
    """
    override = os.environ.get(_ENV_SOCKET_OVERRIDE)
    if override:
        return override
    return str(Path.home() / ".sulis" / "session-manager.sock")


# Snapshot at import for the default-argument ergonomics the contract names. A
# caller wanting the live env value calls ``resolve_default_socket()`` directly.
DEFAULT_SOCKET: str = resolve_default_socket()


def _status_probe(socket_path: str, timeout: float) -> bool:
    """Connect and run one ``status`` round-trip; True iff it returns ok:true.

    Any transport failure (missing socket, refused connect, timeout, malformed
    reply) is mapped to False — the contract's Protocol/Expected categories both
    mean "not live → the caller should (re)start". The short timeout makes a
    dead-but-present socket file fail fast instead of blocking.
    """
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(socket_path)
            request = json.dumps({"id": "live", "method": "status", "params": {}})
            sock.sendall((request + "\n").encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    return False
                buf += chunk
            line, _ = buf.split(b"\n", 1)
            reply = json.loads(line)
            return reply.get("ok") is True
    except (OSError, json.JSONDecodeError):
        return False


def daemon_is_live(socket_path: str = DEFAULT_SOCKET, timeout: float = 1.0) -> bool:
    """True iff a daemon serves ``socket_path``: connect succeeds AND a ``status``
    request returns ``ok:true`` (``DAEMON_CONTRACT.md`` § Liveness).

    Fails fast on a dead or absent socket — the connect+read is bounded by
    ``timeout`` so a stale socket file never blocks the caller.
    """
    if not os.path.exists(socket_path):
        return False
    return _status_probe(socket_path, timeout)


def _default_spawn_command(python: str) -> list[str]:
    """The argv to launch the real daemon (WP-003). The socket token is filled
    in by ``ensure_daemon``."""
    return [python, str(_DEFAULT_DAEMON_ENTRYPOINT), "--socket", _SOCKET_TOKEN]


def _materialise_command(spawn_command: list[str], socket_path: str) -> list[str]:
    """Substitute the socket token in the spawn argv with the resolved path."""
    return [
        socket_path
        if part == _SOCKET_TOKEN
        else part.replace(_SOCKET_TOKEN, socket_path)
        for part in spawn_command
    ]


def _await_ready(
    proc: subprocess.Popen[str], socket_path: str, deadline: float
) -> bool:
    """Block until the spawned daemon prints ``READY <socket>``.

    Returns True on the READY handshake, False if the process exited first (it
    lost the singleton race and exited 0 — the caller then polls for the
    winner). Bounded by ``deadline``.
    """
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            # The process exited before printing READY. For a race-loser this is
            # the normal "another daemon won, I exited 0" path — return False so
            # the caller polls the live socket. (A non-zero exit is still treated
            # as "not ready"; the deadline poll below catches a genuinely broken
            # daemon.)
            return False
        if proc.stdout is None:
            return False
        line = proc.stdout.readline()
        if not line:
            # EOF on stdout without READY — let poll()/deadline decide.
            if proc.poll() is not None:
                return False
            continue
        if line.startswith("READY"):
            return True
    return False


def _poll_until_live(socket_path: str, deadline: float, probe_timeout: float) -> bool:
    """Poll the liveness probe until the socket answers or the deadline passes.

    The race-loser's path (``DAEMON_CONTRACT.md`` § Idempotent ensure): a caller
    whose spawn lost the singleton race waits here for the winner's daemon.
    """
    while time.monotonic() < deadline:
        if daemon_is_live(socket_path, timeout=probe_timeout):
            return True
        time.sleep(0.05)
    return daemon_is_live(socket_path, timeout=probe_timeout)


def ensure_daemon(
    socket_path: str = DEFAULT_SOCKET,
    *,
    python: str = "python3",
    ready_timeout: float = 30.0,
    spawn_command: list[str] | None = None,
) -> str:
    """Return ``socket_path`` with a live daemon serving it.

    Probe-first, spawn-at-most-once, race-tolerant (``DAEMON_CONTRACT.md``
    § Idempotent ensure):

    1. If a daemon already answers the ``status`` probe → return immediately,
       spawn nothing.
    2. Otherwise spawn the daemon **detached** (``start_new_session=True`` — it
       survives this caller's exit), wait for the ``READY <socket>`` handshake,
       confirm liveness, and return.
    3. If the spawn lost the singleton race (the process exited before READY
       because a peer's flock won), **poll** the socket until the winner answers,
       then return.

    Concurrent callers therefore yield **at most one** serving daemon and all
    return the same ``socket_path``.

    ``spawn_command`` is the argv to launch; the literal ``"{socket}"`` token in
    it is replaced with ``socket_path``. When ``None`` it defaults to the real
    daemon entrypoint (WP-003). Injecting it keeps this binding independent of
    WP-003 and testable against a fake daemon.

    Raises :class:`DaemonStartError` if, after spawning, no live daemon answers
    within ``ready_timeout`` (the daemon is broken — Internal, not absent).
    """
    probe_timeout = min(1.0, ready_timeout)

    # 1. Warm path: a daemon already serves the socket (no lock needed).
    if daemon_is_live(socket_path, timeout=probe_timeout):
        return socket_path

    deadline = time.monotonic() + ready_timeout

    # Serialise the probe→spawn critical section across in-process callers so
    # concurrent threads collapse to one spawn. A caller that blocks here and
    # then finds the daemon already live (the winner started it) returns without
    # spawning — the double-checked probe below.
    with _spawn_lock_for(socket_path):
        if daemon_is_live(socket_path, timeout=probe_timeout):
            return socket_path
        return _spawn_and_wait(
            socket_path,
            python=python,
            spawn_command=spawn_command,
            probe_timeout=probe_timeout,
            ready_timeout=ready_timeout,
            deadline=deadline,
        )


def _spawn_and_wait(
    socket_path: str,
    *,
    python: str,
    spawn_command: list[str] | None,
    probe_timeout: float,
    ready_timeout: float,
    deadline: float,
) -> str:
    """Spawn the daemon detached, wait for READY, confirm liveness (the cold-
    start body of :func:`ensure_daemon`, run under the per-socket spawn lock)."""
    # Ensure the parent dir exists (0o700) before the daemon tries to bind there.
    parent = Path(socket_path).resolve().parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    command = _materialise_command(
        spawn_command if spawn_command is not None else _default_spawn_command(python),
        socket_path,
    )

    # 2. Spawn detached. stdout is piped only to read the READY line; the daemon
    # is a new session leader (start_new_session=True) so it outlives this caller.
    proc = subprocess.Popen(  # noqa: S603 - argv is contract-controlled, not shell
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )

    ready = _await_ready(proc, socket_path, deadline)
    # Release our hold on the pipe regardless — the detached daemon keeps running;
    # we only needed the READY line. Closing avoids holding the read end open.
    if proc.stdout is not None:
        try:
            proc.stdout.close()
        except OSError:  # pragma: no cover - best-effort
            pass

    if ready and daemon_is_live(socket_path, timeout=probe_timeout):
        return socket_path

    # 3. Either we did not see READY (lost the singleton race, or a slow start)
    # or READY came but the probe has not caught up yet — poll until the socket
    # answers. This is the race-loser's wait for the winner's daemon.
    if _poll_until_live(socket_path, deadline, probe_timeout):
        return socket_path

    raise DaemonStartError(
        f"daemon did not become live at {socket_path!r} within {ready_timeout}s "
        f"(spawn argv: {command!r})"
    )
