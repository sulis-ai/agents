"""The shared session-manager **daemon** — the singleton, on-demand, long-lived
manager both views attach to (TDD §2.1/§3, ADR-001, WP-003).

This is the *spine* of the change-owned-terminal-shared-session model: one
manager instance owns a change's session, and the cockpit (browser) and the
desktop terminal are two **views** of that one session. The daemon is what makes
"two views, one session" true — without it you are back to three parallel worlds
(an ephemeral cockpit host on a temp socket, a standalone desktop ``claude``).

It is a thin **singleton + stable-socket + lifecycle** wrapper around the frozen
engine (``_session_manager/``), composing exactly the pieces the (now-retired)
``session_manager_host`` standalone ``main`` composed — the
:class:`SessionManager` + :class:`SocketServer` + the WP-001
:class:`BindingManager` / :class:`ConnectionBindingRegistry` (the §2.13.4 guard)
— but at three points the host did not:

1. **Stable socket** (``~/.sulis/session-manager.sock``, env-overridable) instead
   of an ephemeral temp path, so both views find the *same* manager (ADR-001).
2. **Singleton via ``fcntl.flock``** (``LOCK_EX | LOCK_NB``) on
   ``~/.sulis/session-manager.lock``, taken **before** binding the socket. The
   lock-holder is the **sole binder**: only it reaches the engine's
   ``SocketServer.start`` (whose unconditional stale-socket ``os.unlink`` is the
   race ADR-001 closes). A second daemon that fails the lock confirms the
   existing socket answers a ``status`` ping and exits **0** — losing the race is
   normal, not an error.
3. **The real interactive Claude pty adapter** (WP-004) registered under provider
   ``pty``, so a get-or-spawn for a change runs the change's interactive
   ``claude --agent sulis`` in its worktree — not the fake echo child the host
   wired. (The fake child stays test-only, reachable via the
   ``SULIS_DAEMON_PTY_CHILD`` seam so the integration suite runs without the real
   binary — the WP-009 ``--verbose`` lesson: CI cannot run real ``claude``.)
4. **Daemon-level idle-empty auto-exit** — when the manager has held **zero
   sessions** continuously for ``SULIS_DAEMON_IDLE_EXIT_SECS`` (default 1800s)
   the daemon self-shuts-down (server stop, manager shutdown, socket unlink, lock
   release) and exits 0; the next ``ensure-daemon`` restarts it. This bounds a
   forgotten daemon without coupling its lifetime to any window. It is **distinct
   from** the engine's per-session idle eviction (``maintenance.py``, which stays
   ON): that reaps one *idle session*; this reaps the *whole empty daemon*.

**Independence (founder directive, MUST; ADR-003).** This module imports nothing
from the cockpit chat relay, the chat ``SessionBridge``, or the ``platform``
communication service. The daemon owns the engine for the **terminal** over the
socket directly — terminal-only. (Codified by an import-graph test.)

The engine is reused, **never modified**: the flock gates the engine's existing
stale-socket unlink so only the lock-holder binds — no engine edit needed
(ADR-001 § Consequences).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

# Run from any cwd: the engine package + the daemon-presence binding live under
# this file's directory; the shared test pty child lives in tests/lib. Mirror the
# host's import wiring so the daemon resolves its imports regardless of cwd.
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_SCRIPTS / "tests" / "lib") not in sys.path:
    sys.path.insert(0, str(_SCRIPTS / "tests" / "lib"))

import fcntl  # noqa: E402

from _session_manager import daemon_client  # noqa: E402
from _session_manager.adapter import ProviderAdapter  # noqa: E402
from _session_manager.adapters.claude_pty import (  # noqa: E402
    InteractiveClaudePtyAdapter,
)
from _session_manager.binding import (  # noqa: E402
    BindingManager,
    ConnectionBindingRegistry,
)
from _session_manager.manager import SessionManager  # noqa: E402
from _session_manager.socket_server import SocketServer  # noqa: E402

# ── tuning defaults ───────────────────────────────────────────────────────────

#: Default daemon idle-empty window in seconds (ADR-001): zero sessions held
#: continuously for this long → the daemon self-shuts-down. 30 minutes — generous
#: enough that an active founder never trips it, bounded enough that a forgotten
#: daemon does not linger forever. Overridable via ``SULIS_DAEMON_IDLE_EXIT_SECS``
#: (the test/CI injection seam, mirroring the socket override).
DEFAULT_IDLE_EXIT_SECS = 1800.0

#: Default wedge-grace window in seconds (HD-003): in the race-loser branch the
#: daemon polls this long for the singleton holder's socket to come live. A
#: holder whose socket comes live *within* this window is mid-boot (reused); a
#: holder still without a live socket *past* it is wedged (escalated to reclaim).
#: 10s — deliberately **longer** than the legacy 5s mid-boot poll so a slow-but-
#: legitimate boot the old code already tolerated is strictly preserved; the
#: breaker only trips beyond the legitimate window. Overridable via
#: ``SULIS_DAEMON_WEDGE_GRACE_SECS`` (the test/CI injection seam, mirroring the
#: idle-exit + socket overrides).
DEFAULT_WEDGE_GRACE_SECS = 10.0

#: How often the idle-empty watcher samples the manager, in seconds. Small
#: relative to the window so the daemon exits promptly after it crosses the
#: threshold, but not so small it busy-spins.
_IDLE_WATCH_INTERVAL_SECS = 30.0

#: Bounded SIGTERM→SIGKILL wait when reclaiming a wedged holder (HD-003). The
#: verified holder is given this long to stop cleanly on SIGTERM (it unlinks its
#: own socket + releases its lock) before the reclaim escalates to SIGKILL.
#: ``_reclaim_wedged_holder`` floors this at 5.0s internally, matching
#: ``daemon_client._stop_stale_daemon``'s teardown budget.
_RECLAIM_TERM_WAIT_SECS = 5.0

#: Env seams (test/CI injection). ``SULIS_DAEMON_PTY_CHILD`` points the pty
#: provider at the shared fake child (a real subprocess, not a mock — MEA-09) so
#: the integration suite runs without the real ``claude`` binary; production
#: leaves it unset and the real interactive adapter is wired.
_ENV_IDLE_EXIT = "SULIS_DAEMON_IDLE_EXIT_SECS"
_ENV_WEDGE_GRACE = "SULIS_DAEMON_WEDGE_GRACE_SECS"
_ENV_PTY_CHILD = "SULIS_DAEMON_PTY_CHILD"

#: The stable singleton lock path (ADR-001), parallel to the stable socket the
#: daemon-presence binding resolves. Overridable via ``--lock`` so each test gets
#: an isolated lock + socket pair.
_LOCK_FILENAME = "session-manager.lock"

#: The stable identity-pidfile path (HD-001), beside the lock + socket. The
#: daemon writes its PID + process-start-token + cmdline marker here once it
#: holds the flock, so a later reclaim (WP-002) can verify a kill target PID-
#: reuse-safely. Overridable via ``--pidfile`` to mirror the ``--lock`` /
#: ``--socket`` test-isolation seams.
_PIDFILE_FILENAME = "session-manager.pid"

#: The cmdline marker recorded in the pidfile — the constant the daemon entry
#: point is named by. WP-002 matches this against a live process's command line
#: (one half of the PID-reuse-safe identity check; the other half is the
#: start-token).
_CMDLINE_MARKER = "session_manager_daemon.py"


def resolve_default_lock() -> str:
    """The stable singleton-lock path: ``~/.sulis/session-manager.lock``.

    Lives beside the stable socket (``daemon_client.resolve_default_socket``);
    the flock on it is the daemon's single-instance arbiter (ADR-001). Always an
    absolute path.
    """
    return str(Path.home() / ".sulis" / _LOCK_FILENAME)


def resolve_default_pidfile() -> str:
    """The stable identity-pidfile path: ``~/.sulis/session-manager.pid``.

    Lives beside the lock + stable socket; the daemon writes its durable
    identity (PID + process-start-token + cmdline marker) here once it holds the
    flock, so a later reclaim can verify a kill target PID-reuse-safely (HD-001).
    Mirrors :func:`resolve_default_lock`. Always an absolute path.
    """
    return str(Path.home() / ".sulis" / _PIDFILE_FILENAME)


def resolve_idle_exit_secs() -> float:
    """The idle-empty window in seconds (``SULIS_DAEMON_IDLE_EXIT_SECS`` or the
    default). A non-positive, non-finite, or unparseable override falls back to
    the default — a bad tuning value must degrade to the safe bound, not crash
    the daemon. Non-finite is rejected on purpose: ``float('inf')`` /
    ``float('1e400')`` parse cleanly and pass ``> 0``, so without the finite
    check an ``inf`` override would be accepted as an *infinite* window — the
    daemon would never time out. ``nan`` is already caught by ``> 0`` (always
    False), but the explicit finite check states the intent."""
    raw = os.environ.get(_ENV_IDLE_EXIT)
    if not raw:
        return DEFAULT_IDLE_EXIT_SECS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_IDLE_EXIT_SECS
    return value if math.isfinite(value) and value > 0 else DEFAULT_IDLE_EXIT_SECS


def resolve_wedge_grace_secs() -> float:
    """The wedge grace window in seconds (``SULIS_DAEMON_WEDGE_GRACE_SECS`` or the
    default). A non-positive, non-finite, or unparseable override falls back to
    the default — a bad tuning value must degrade to the safe bound, not crash
    the daemon, and never shrink the window so far it mistakes a slow boot for a
    wedge. Non-finite is rejected on purpose: an ``inf`` / ``1e400`` override
    parses cleanly and passes ``> 0``, so without the finite check it would be
    accepted as an *infinite* grace window — the daemon would then never declare
    a wedge, silently defeating the whole self-heal. Mirrors
    :func:`resolve_idle_exit_secs` exactly (HD-003)."""
    raw = os.environ.get(_ENV_WEDGE_GRACE)
    if not raw:
        return DEFAULT_WEDGE_GRACE_SECS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_WEDGE_GRACE_SECS
    return value if math.isfinite(value) and value > 0 else DEFAULT_WEDGE_GRACE_SECS


# ── the identity pidfile (HD-001): durable on-disk process identity ──────────


def _ps_field(pid: int, field: str) -> str | None:
    """Best-effort single-field ``ps`` probe: ``ps -o <field> -p <pid>``.

    The shared subprocess guard behind both :func:`_process_start_token`
    (``lstart=``) and :func:`_process_cmdline` (``command=``) — extracted at the
    two-consumer threshold (EP-03 / Non-Negotiable #2) so the ``ps`` probe's
    portability + best-effort contract live in exactly one place. ``ps`` is
    portable across the daemon's two targets (macOS + Linux), unlike Linux-only
    ``/proc``. Returns the trimmed field value, or ``None`` if ``ps`` is
    unreadable / the PID is gone / the field is empty. **Never raises.**

    ``field`` is the literal ``ps -o`` spec including the trailing ``=`` that
    suppresses the header (e.g. ``"lstart="``, ``"command="``).
    """
    try:
        completed = subprocess.run(
            ["ps", "-o", field, "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _process_start_token(pid: int) -> str | None:
    """The OS process start-time for ``pid``, the start-token that pins this
    exact process.

    Read via ``ps -o lstart= -p <pid>`` (through :func:`_ps_field`, the shared
    best-effort probe) — portable across the daemon's two targets (macOS +
    Linux), unlike Linux-only ``/proc``. A recycled PID cannot reproduce this
    value, so it is the safety anchor for the PID-reuse-safe reclaim (WP-002).
    Best-effort: returns the trimmed start-time string, or ``None`` if ``ps`` is
    unreadable / the PID is gone — never raises.
    """
    return _ps_field(pid, "lstart=")


def _write_pidfile(pidfile_path: str, pid: int) -> None:
    """Atomically write the daemon's identity record to ``pidfile_path``.

    The record is ``{"pid", "start_token", "cmdline_marker"}`` —
    ``start_token`` is :func:`_process_start_token` for ``pid``,
    ``cmdline_marker`` the daemon entrypoint constant. Written via a tmp file +
    :func:`os.replace` so a reader never sees a half-written record. The tmp is
    opened ``0o600`` with ``O_EXCL | O_NOFOLLOW`` — matching the singleton lock's
    ``0o600`` (this file feeds a later kill decision, so it is never more
    permissively scoped than the lock beside it, and the open never follows a
    pre-planted symlink). Best-effort: a failed write is caught + logged to
    stderr; the daemon still boots (a missing pidfile degrades reclaim to today's
    fail-closed exit-1, it never crashes the boot). Mirrors the env-seam / best-
    effort voice of the lock helpers.
    """
    record = {
        "pid": pid,
        "start_token": _process_start_token(pid),
        "cmdline_marker": _CMDLINE_MARKER,
    }
    tmp_path = f"{pidfile_path}.{pid}.tmp"
    try:
        # 0o600 + O_EXCL|O_NOFOLLOW: confidentiality/integrity parity with the
        # lock (``_acquire_singleton_lock``), and a refusal to follow / clobber a
        # pre-existing symlink or file at the predictable tmp path.
        fd = os.open(
            tmp_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(record, fh)
        os.replace(tmp_path, pidfile_path)
    except OSError as exc:
        # Best-effort: never crash the boot on identity-record I/O. Clean up the
        # tmp file if it was left behind by a mid-write failure.
        try:
            os.unlink(tmp_path)
        except OSError:  # pragma: no cover - best-effort cleanup
            pass
        sys.stderr.write(
            f"could not write identity pidfile at {pidfile_path}: {exc} — "
            "continuing without a durable identity record\n"
        )


def _remove_pidfile(pidfile_path: str) -> None:
    """Best-effort removal of the identity pidfile (the daemon records a *live*
    identity only). Catches ``OSError`` (which covers the already-gone
    ``FileNotFoundError`` case) so a clean shutdown never crashes on teardown
    I/O. Mirrors :func:`_release_singleton_lock`'s idempotent best-effort shape.
    """
    try:
        os.unlink(pidfile_path)
    except OSError:  # pragma: no cover - best-effort (already gone / unreadable)
        pass


# ── the PID-reuse-safe reclaim (HD-002): verify identity, then kill ──────────
#
# A *wedged* holder holds the singleton flock but never answers ``status`` —
# so ``daemon_client._stop_stale_daemon`` (which reads the kill-target PID from
# a live status reply) cannot be used. The kill target's identity comes from the
# WP-001 pidfile instead, and is verified to *still be our daemon* before any
# kill. **Verification fails CLOSED**: if identity cannot be proven (no pidfile,
# torn record, unreadable ps, cmdline mismatch, start-token mismatch), we do NOT
# kill — the caller (WP-003) falls back to today's exit-1. This is the
# load-bearing safety invariant of the change: a recycled PID is never killed.


def _read_pidfile(pidfile_path: str) -> "dict | None":
    """Best-effort parse of the WP-001 identity record at ``pidfile_path``.

    Returns the parsed ``{"pid", "start_token", "cmdline_marker"}`` mapping, or
    ``None`` on a missing / torn / unparseable / non-mapping file. **Never
    raises** — a missing or torn record means 'no durable identity recorded', and
    the reclaim must then **fail closed** (it does not kill). The complement of
    :func:`_write_pidfile`.
    """
    try:
        with open(pidfile_path, encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, ValueError):
        # OSError: missing / unreadable. ValueError: torn / non-JSON (covers
        # json.JSONDecodeError). Either way → no durable identity → fail closed.
        return None
    if not isinstance(record, dict):
        return None
    return record


def _process_cmdline(pid: int) -> str | None:
    """The live command line of ``pid`` via ``ps -o command= -p <pid>``.

    Portable across the daemon's two targets (macOS + Linux), unlike Linux-only
    ``/proc``. Mirrors :func:`_process_start_token`'s best-effort ``ps`` probe
    (both go through :func:`_ps_field`, the shared subprocess guard). Returns the
    trimmed command-line string, or ``None`` if the PID is gone / ``ps`` is
    unreadable. **Never raises.** One half of the PID-reuse-safe identity check
    (the daemon's recorded ``cmdline_marker`` must be a substring of this); the
    other half is :func:`_process_start_token`.
    """
    return _ps_field(pid, "command=")


def _is_our_daemon(
    record: dict,
    pid: int,
    *,
    start_token_of: "Callable[[int], str | None] | None" = None,
    cmdline_of: "Callable[[int], str | None] | None" = None,
) -> bool:
    """FAIL-CLOSED verifier — a **pure decision function**, no side effects.

    Returns ``True`` IFF **all** of the following hold for the live process at
    ``pid``:

    * the process exists and its command line is readable
      (``cmdline_of(pid)`` is not ``None``), **and**
    * that command line contains the record's ``cmdline_marker``, **and**
    * the process's start-token (``start_token_of(pid)``) is non-``None`` and
      **equals** the record's ``start_token`` — the PID-reuse anchor: a recycled
      PID cannot reproduce the original process's start time.

    **Any** missing / unprovable input → ``False``. This is non-negotiable: do
    not weaken it to "match on PID alone" or "match if the start-token is
    unavailable". The kill in :func:`_reclaim_wedged_holder` is gated entirely on
    this; the probes are injected so every branch is unit-tested without ever
    touching a real process.

    The probes default to the module-level :func:`_process_start_token` /
    :func:`_process_cmdline`, resolved **at call time** (via ``None`` sentinels)
    so a test can swap the module attributes and have the default path pick them
    up — the same probe the production caller (:func:`_reclaim_wedged_holder`,
    which passes no probes) goes through.
    """
    if start_token_of is None:
        start_token_of = _process_start_token
    if cmdline_of is None:
        cmdline_of = _process_cmdline

    recorded_marker = record.get("cmdline_marker")
    recorded_token = record.get("start_token")
    # No recorded identity at all → cannot prove → fail closed.
    if not recorded_marker or not recorded_token:
        return False

    live_cmdline = cmdline_of(pid)
    if live_cmdline is None:  # process gone / ps unreadable
        return False
    if recorded_marker not in live_cmdline:  # cmdline marker mismatch
        return False

    live_token = start_token_of(pid)
    if live_token is None:  # start-token unreadable → cannot pin → fail closed
        return False
    return live_token == recorded_token  # PID-reuse anchor: must match exactly


def _reclaim_wedged_holder(
    pidfile_path: str,
    socket_path: str,
    *,
    term_wait_secs: float,
) -> bool:
    """Reclaim a **verified-ours** wedged daemon holder, PID-reuse-safely.

    Read the identity pidfile → verify it is *still our daemon*
    (:func:`_is_our_daemon`, fail-closed). If verification fails (no pidfile,
    torn record, cmdline mismatch, start-token mismatch, unreadable probes) →
    return ``False`` and **make no destructive change** — DO NOT KILL; the
    caller (WP-003) falls back to today's exit-1. This is the load-bearing safety
    invariant: a recycled PID is never killed.

    On a verified holder: ``SIGTERM`` → bounded wait (``term_wait_secs``, with
    the same ``deadline = time.monotonic() + max(...)`` floor as
    :func:`daemon_client._stop_stale_daemon`) → ``SIGKILL`` only if it outlives
    the wait **and re-verifies as still ours** (a fresh :func:`_is_our_daemon`
    call immediately before SIGKILL — liveness alone can't tell our daemon from
    an unrelated process that recycled its PID mid-wait, so a re-verify failure
    skips the kill and fails closed) → unlink the stale pidfile + socket
    (best-effort). Returns ``True`` on a completed reclaim. A kill racing the
    holder's natural death (``ProcessLookupError``) is a *completed* reclaim (the
    holder is gone), not a failure. **Never raises out of the function** —
    best-effort recovery I/O.

    Mirrors :func:`daemon_client._stop_stale_daemon`'s
    SIGTERM→bounded-wait→unlink shape (EP-03); the only difference is the
    identity source (the pidfile, not a live status reply).
    """
    record = _read_pidfile(pidfile_path)
    if record is None:
        return False  # no durable identity → fail closed
    pid = record.get("pid")
    if not isinstance(pid, int):
        return False  # malformed record → fail closed
    if not _is_our_daemon(record, pid):
        return False  # NOT our daemon (or unprovable) → DO NOT KILL

    # Verified ours. SIGTERM and give it a bounded window to stop cleanly (it
    # unlinks its own socket + releases its lock on SIGTERM); SIGKILL only if it
    # outlives the wait. Best-effort throughout — a kill racing a natural death
    # is a completed reclaim.
    if not _signal_pid(pid, signal.SIGTERM):
        # The holder was already gone when we tried to SIGTERM it — it died
        # between verify and signal. A completed reclaim; clear the stale files.
        _clear_stale_files(pidfile_path, socket_path)
        return True

    deadline = time.monotonic() + max(term_wait_secs, 5.0)
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            break
        time.sleep(0.1)
    else:
        # Outlived the wait → escalate to SIGKILL — but RE-VERIFY identity first.
        # ``_pid_alive`` is a signal-0 liveness probe: it cannot tell our daemon
        # from an unrelated process that recycled its PID while we waited (the
        # verified holder may have died under SIGTERM and the OS reused its PID).
        # Re-call the fail-closed identity check immediately before SIGKILL and
        # only escalate if it STILL proves ours; if it no longer matches, the
        # holder is already gone — do NOT SIGKILL (that would land on the wrong
        # process) and fall through to clear the stale files, fail-closed exactly
        # like a holder that died within the wait. This closes the verify→SIGKILL
        # TOCTOU wrong-kill window (the change's load-bearing invariant: never
        # kill the wrong PID).
        if _is_our_daemon(record, pid):
            _signal_pid(pid, signal.SIGKILL)

    _clear_stale_files(pidfile_path, socket_path)
    return True


def _signal_pid(pid: int, sig: int) -> bool:
    """Best-effort ``os.kill(pid, sig)``. Returns ``True`` if the signal was
    delivered, ``False`` if the process was already gone
    (``ProcessLookupError`` — a kill racing a natural death). Other ``OSError``
    (e.g. ``PermissionError``) is swallowed as ``False`` too; the reclaim never
    crashes on a signal it cannot deliver."""
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return False  # already gone — the holder died first
    except OSError:  # pragma: no cover - e.g. EPERM; best-effort
        return False
    return True


def _pid_alive(pid: int) -> bool:
    """Best-effort liveness check via signal 0 (``os.kill(pid, 0)`` — the
    portable 'does this process exist and can I signal it' probe). ``True`` if
    the process exists, ``False`` if it is gone. Never raises."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:  # pragma: no cover - e.g. EPERM (exists but not signalable)
        return True
    return True


def _clear_stale_files(pidfile_path: str, socket_path: str) -> None:
    """Best-effort unlink of the stale pidfile + socket left by a reclaimed
    holder. Reuses :func:`_remove_pidfile`'s idempotent best-effort shape for
    the pidfile; the socket unlink is the same shape. Never raises."""
    _remove_pidfile(pidfile_path)
    try:
        os.unlink(socket_path)
    except OSError:  # pragma: no cover - best-effort (already gone / unreadable)
        pass


# ── the idle-empty auto-exit watcher (the daemon's lifecycle policy) ──────────


class IdleEmptyExitWatcher:
    """Fires a shutdown callback when the manager has owned **zero sessions**
    continuously for ``idle_exit_secs`` (ADR-001 daemon-level idle-empty auto-
    exit).

    This is the *daemon's* lifecycle policy, distinct from the engine's per-
    session idle eviction (``maintenance.py``): it reaps the whole daemon when it
    is *empty*, not one idle session. A small pure-ish helper taking an injected
    ``clock`` + a ``status_keys`` callable so it is unit-testable without real
    sleeping (MEA-09): a test steps the clock and calls :meth:`tick`.

    The window is *continuous* emptiness — a session appearing resets the empty-
    since mark, so the daemon only exits after a full window with no sessions at
    all. Shutdown is a one-way door: :meth:`tick` fires ``on_idle_empty`` at most
    once (a second call would double-stop the server).

    Args:
        status_keys: returns the set of keys the manager currently owns (the
            manager's cheap, side-effect-free ``status_keys`` — consumed, not
            re-implemented).
        idle_exit_secs: the continuous-empty window before shutdown. Must be > 0.
        on_idle_empty: the shutdown callback, invoked once when the window
            elapses with the manager continuously empty.
        clock: the monotonic clock used to measure the window — injectable so a
            test drives it deterministically. Defaults to ``time.monotonic``.
    """

    def __init__(
        self,
        *,
        status_keys: Callable[[], set[str]],
        idle_exit_secs: float,
        on_idle_empty: Callable[[], None],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if idle_exit_secs <= 0:
            raise ValueError("idle_exit_secs must be > 0")
        self._status_keys = status_keys
        self._idle_exit_secs = float(idle_exit_secs)
        self._on_idle_empty = on_idle_empty
        self._clock = clock
        #: When the manager last became (or was first observed) empty; ``None``
        #: while a session exists. The empty window is measured from this mark.
        self._empty_since: float | None = None
        #: One-way latch so shutdown fires at most once.
        self._fired = False

    def tick(self) -> None:
        """Sample the manager once; fire the shutdown callback iff it has been
        continuously empty for the window. Idempotent after firing."""
        if self._fired:
            return
        now = self._clock()
        if self._status_keys():
            # A session exists → not idle-empty; reset the empty-since mark so the
            # window must restart from the next time the daemon goes empty.
            self._empty_since = None
            return
        if self._empty_since is None:
            # First observation of emptiness — start the window here.
            self._empty_since = now
            return
        if (now - self._empty_since) >= self._idle_exit_secs:
            self._fired = True
            self._on_idle_empty()


# ── composition root (WPB-07): adapters + server wiring ──────────────────────


def _build_pty_adapter() -> ProviderAdapter:
    """The pty provider for this daemon.

    Production: the **real** interactive Claude pty adapter (WP-004) — a get-or-
    spawn runs the change's interactive ``claude --agent sulis`` in its worktree.
    Test/CI (``SULIS_DAEMON_PTY_CHILD`` set): the shared fake pty child via
    :class:`PtyChildAdapter` — a real subprocess (MEA-09), not a mock, so the
    integration suite exercises the real socket + manager + a real pty without
    the real binary (the WP-009 ``--verbose`` lesson)."""
    child = os.environ.get(_ENV_PTY_CHILD)
    if child:
        # Test seam only: the fake child + its adapter live under tests/lib (on
        # sys.path above). Imported lazily so production never loads test code.
        from session_child_adapters import PtyChildAdapter

        return PtyChildAdapter(Path(child))
    return InteractiveClaudePtyAdapter()


def _build_server(socket_path: str) -> tuple[SocketServer, SessionManager]:
    """Wire a real :class:`SessionManager` (pty provider) + a :class:`SocketServer`
    over ``socket_path`` with the §2.13.4 binding guard **ON**.

    Session-level idle eviction is the engine's job, so ``start_maintenance=True``
    (the daemon's own idle-empty auto-exit is separate; see
    :class:`IdleEmptyExitWatcher`). Returns ``(server, manager)`` so the caller
    can stop both on shutdown. Mirrors the (retired) host's bound-server shape so
    the two share one binding resolver (EP-03) — the host's standalone ``main``
    is gone; this is the single composition root for the engine over the socket.
    """
    manager = SessionManager(
        {"pty": _build_pty_adapter()},
        start_maintenance=True,  # engine's per-session idle eviction ON
    )
    registry = ConnectionBindingRegistry()
    server = SocketServer(
        BindingManager(manager, registry),
        socket_path,
        bound_key_for=registry.resolve,
    )
    return server, manager


# ── the daemon lifecycle ──────────────────────────────────────────────────────


def _acquire_singleton_lock(lock_path: str) -> "int | None":
    """Take the singleton flock (``LOCK_EX | LOCK_NB``) for the daemon's life.

    Returns the open lock fd on success (this process is THE daemon; the fd is
    held for the process's life — ``fcntl.flock`` auto-releases on death, so no
    stale-lock cleanup is needed, ADR-001). Returns ``None`` if another daemon
    already holds the lock (losing the race is normal — the caller confirms the
    live socket and exits 0).

    The lock's parent dir is created ``0o700`` first (the stable-socket dir gate,
    §2.8.1 parity) so a fresh ``~/.sulis`` works without a separate mkdir."""
    parent = Path(lock_path).resolve().parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def _release_singleton_lock(lock_fd: int) -> None:
    """Release + close the singleton lock fd (idempotent best-effort)."""
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    except OSError:  # pragma: no cover - best-effort
        pass
    try:
        os.close(lock_fd)
    except OSError:  # pragma: no cover - best-effort
        pass


def _poll_socket_live(socket_path: str, *, window_secs: float) -> bool:
    """Poll up to ``window_secs`` for ``socket_path`` to answer a ``status`` ping.

    The shared "is the singleton holder serving yet?" probe used by the race-
    loser branch (both the initial mid-boot/wedge grace window AND the brief
    post-reclaim peer-race poll). Returns ``True`` the instant the socket goes
    live, ``False`` if the window elapses with it still dark. Extracted at the
    two-consumer threshold (EP-03) so the poll cadence + liveness check live in
    one place."""
    deadline = time.monotonic() + window_secs
    while time.monotonic() < deadline:
        if daemon_client.daemon_is_live(socket_path):
            return True
        time.sleep(0.05)
    return False


def _boot_and_serve(args: argparse.Namespace, lock_fd: int) -> int:
    """Boot THE daemon: bind the socket, write the identity pidfile, run the idle-
    empty watcher, print READY, serve until stopped, then tear down cleanly.

    The single composition root for "this process holds the lock and is the
    daemon" (WPB-07). Reached by **both** the first-acquire path and the post-
    reclaim re-acquire path in :func:`main`, so the bind→serve→teardown sequence
    exists exactly once (no duplicated boot code). ``lock_fd`` is the held
    singleton flock; it is released as part of the clean teardown. Always returns
    0 (a clean stop)."""
    # Ensure the socket's parent dir exists 0o700 (the §2.8.1 gate; the engine
    # chmods the socket itself 0o600 at bind).
    Path(args.socket).resolve().parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    stop = threading.Event()

    def _stop() -> None:
        """The single clean-stop path (signal-driven OR idle-empty-driven): stop
        the server, shut the manager down, unlink the socket (server.stop does),
        release the lock. Idempotent via the stop Event."""
        stop.set()

    # SIGTERM / SIGINT → the same clean stop. Installed BEFORE binding + READY so
    # a signal arriving the instant a view (or test) sees READY is caught by this
    # handler, never the default disposition (which would kill with -SIGTERM, not
    # exit 0). Signal handlers must be set on the main thread — this is it.
    signal.signal(signal.SIGTERM, lambda *_a: _stop())
    signal.signal(signal.SIGINT, lambda *_a: _stop())

    server, manager = _build_server(args.socket)
    server.start()  # only the lock-holder reaches the engine's unlink+bind

    # Write the identity pidfile now — only once genuinely bound + holding the
    # flock, so the on-disk record always names a process that is THE daemon
    # (HD-001). Best-effort: a failed write degrades the later reclaim to fail-
    # closed, it never crashes the boot.
    _write_pidfile(args.pidfile, os.getpid())

    # Idle-empty auto-exit watcher on a background daemon thread. When the manager
    # has been empty for the window, it sets the stop Event — the same clean
    # teardown SIGTERM drives (one stop path, ADR-001).
    watcher = IdleEmptyExitWatcher(
        status_keys=manager.status_keys,
        idle_exit_secs=resolve_idle_exit_secs(),
        on_idle_empty=_stop,
    )

    def _idle_loop() -> None:
        # Interruptible wait (not a bare sleep) so shutdown is prompt.
        while not stop.wait(_IDLE_WATCH_INTERVAL_SECS):
            watcher.tick()

    idle_thread = threading.Thread(
        target=_idle_loop, name="daemon-idle-empty-watch", daemon=True
    )
    idle_thread.start()

    # Signal readiness (both views wait for this before connecting). By now the
    # socket is bound AND the signal handlers are installed.
    sys.stdout.write(f"READY {args.socket}\n")
    sys.stdout.flush()

    try:
        stop.wait()
    finally:
        server.stop()  # shuts the server down + unlinks the socket
        manager.shutdown()  # stops engine maintenance + closes every session
        _remove_pidfile(args.pidfile)  # the pidfile records a *live* identity only
        _release_singleton_lock(lock_fd)
    return 0


def _fail_closed_retry(socket_path: str) -> int:
    """Emit today's exact race-loser give-up line and return 1. The fail-closed
    terminus of :func:`_handle_lost_race` — reached when the holder cannot be
    verified for a reclaim, or when a peer won the reclaim race and never came
    live. Byte-for-byte the message the pre-HD-003 branch wrote (the #131
    ``DaemonStartError`` cause-folding reads it), in exactly one place (EP-03)."""
    sys.stderr.write(
        f"singleton lock held but no live socket at {socket_path} — "
        "a daemon is mid-boot or wedged; ensure-daemon will retry\n"
    )
    return 1


def _handle_lost_race(args: argparse.Namespace) -> int:
    """The race-loser branch: this process lost the singleton flock. Distinguish a
    **mid-boot** holder (reuse) from a **wedged** holder (reclaim) and act (HD-003).

    1. Poll up to :func:`resolve_wedge_grace_secs` for the holder's socket to come
       live. A holder whose socket comes live *within* the window is mid-boot —
       reuse it: print READY, exit 0 (today's legitimate race-loser path, now
       generously windowed so a slow boot is never mistaken for a wedge).
    2. The window elapses with the lock still held and no live socket → the holder
       is **wedged**. Call the PID-reuse-safe reclaim (WP-002), which verifies the
       holder is still our daemon before any kill and fails closed otherwise.
    3. Reclaim succeeded → re-acquire the flock and fall through to the normal
       boot path (one composition root, :func:`_boot_and_serve`). If a peer won
       the reclaim race (re-acquire fails), poll briefly for *their* socket and
       exit 0 if it comes live.
    4. Reclaim failed (verification fell closed / no pidfile) → today's exact
       behaviour: the 'mid-boot or wedged; ensure-daemon will retry' stderr line +
       ``return 1``. Fail closed — a recycled PID is never killed."""
    # 1. Mid-boot grace window: a holder whose socket comes live in time is reused.
    if _poll_socket_live(args.socket, window_secs=resolve_wedge_grace_secs()):
        sys.stdout.write(f"READY {args.socket}\n")
        sys.stdout.flush()
        return 0

    # 2. Window elapsed, lock held, no live socket → wedged. Escalate to the
    #    PID-reuse-safe reclaim (it fails closed if it cannot verify the holder).
    reclaimed = _reclaim_wedged_holder(
        args.pidfile, args.socket, term_wait_secs=_RECLAIM_TERM_WAIT_SECS
    )
    if not reclaimed:
        # 4. Verification failed closed (no/torn pidfile, identity mismatch, dead
        #    probes) → today's exact behaviour. Fail closed; never kill a PID we
        #    cannot prove is our daemon.
        return _fail_closed_retry(args.socket)

    # 3. Reclaimed. Re-acquire the now-free flock and boot a fresh daemon via the
    #    single composition root. If a peer won the reclaim race, re-acquire fails
    #    — poll briefly for their socket and exit 0 if it comes live.
    lock_fd = _acquire_singleton_lock(args.lock)
    if lock_fd is None:
        if _poll_socket_live(args.socket, window_secs=resolve_wedge_grace_secs()):
            sys.stdout.write(f"READY {args.socket}\n")
            sys.stdout.flush()
            return 0
        return _fail_closed_retry(args.socket)
    return _boot_and_serve(args, lock_fd)


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="The shared session-manager daemon")
    parser.add_argument(
        "--socket",
        default=daemon_client.resolve_default_socket(),
        help="stable AF_UNIX socket path to serve on (default: the stable socket)",
    )
    parser.add_argument(
        "--lock",
        default=resolve_default_lock(),
        help="singleton flock path (default: the stable lock beside the socket)",
    )
    parser.add_argument(
        "--pidfile",
        default=resolve_default_pidfile(),
        help="identity pidfile path (default: the stable pidfile beside the lock)",
    )
    args = parser.parse_args(argv)

    # Singleton arbitration: take the flock BEFORE binding so only the holder
    # reaches SocketServer.start's unlink+bind (closes the race, ADR-001).
    lock_fd = _acquire_singleton_lock(args.lock)
    if lock_fd is None:
        # Lost the race → distinguish a mid-boot holder (reuse) from a wedged one
        # (reclaim + boot fresh), failing closed when the holder cannot be
        # verified (HD-003).
        return _handle_lost_race(args)

    # This process is THE daemon — boot + serve via the single composition root.
    return _boot_and_serve(args, lock_fd)


if __name__ == "__main__":
    raise SystemExit(main())
