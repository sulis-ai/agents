"""sulis-session — a minimal real driver for the session manager.

This is the **observed-done gate** for Phase 1 of the persistent-chat-sessions
change (SESSION_MANAGER_CONTRACT). The phase is *not* done when the unit tests
are green — it is done when a human (or CI driving the real ``claude`` binary)
has watched ``open → send → read --follow → close`` stream a live turn
end-to-end. This driver is what makes that observation possible.

It is **not** the full Sulis plugin CLI: just enough of a driver to exercise and
prove the core. It mirrors the ``sulis_list_changes.py`` entrypoint convention
(argparse, ``main(argv)`` returning an exit code) and imports the
:class:`SessionManager` + the Claude adapter **in-process** — the Phase-1
library binding. (Cross-process serving over the Unix-domain socket is Phase 2,
contract §2.8; single-process here is correct, not a limitation.)

Subcommands — the six-method surface (contract §2.2):

    sulis_session.py open   --key K --cwd DIR [--resume-ref REF]
    sulis_session.py send   --key K --message "..."
    sulis_session.py read   --key K [--since N] [--follow]
    sulis_session.py status
    sulis_session.py health --key K
    sulis_session.py close  --key K

…plus the single-process observable demo (the whole flow in one process, since
the manager is in-process and per-invocation state would otherwise not survive):

    sulis_session.py demo   --key K --cwd DIR --message "..."

``demo`` runs: open → send → ``read --follow`` (streaming the reply live,
flushed per chunk) → a SECOND send (proving warm reuse: fast, remembers) →
status + health → close. It proves the four founder-visible wins against a
warm session: live streaming, memory across turns, fast second turn, clean
close.

**Destructive-path caution.** ``demo`` (and ``open``) spawn a real ``claude``
with ``--dangerously-skip-permissions`` in the given ``--cwd``. Run them against
a benign prompt in a safe directory. The observed-done evidence run used the
prompt "say hi in 3 words" (see ``tests/manual/session_driver_observed.md``).

**Test seam.** ``SULIS_SESSION_CLAUDE_ARGV`` (a JSON list), when set, makes the
Claude adapter spawn that argv instead of the real ``claude`` binary — keeping
its real ``encode`` / ``decode`` / ``turn_complete``. CI's smoke uses this to
drive a deterministic scripted child that speaks real stream-json, so the
plumbing is proven claude-free. Production leaves it unset.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Sequence

# Sibling package — the in-process session manager. Path-insert mirrors the
# convention used by sulis_list_changes.py (and the test conftest): the scripts
# dir on sys.path so ``_session_manager`` imports by package name.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _session_manager import (  # noqa: E402
    ClaudeAdapter,
    Event,
    SessionManager,
    SessionSpec,
)

#: The env var the CI smoke uses to inject a fake-claude argv (a JSON list). The
#: adapter keeps its real encode/decode/turn_complete; only the spawned binary
#: changes. Unset in production (the real ``claude`` is spawned).
_CLAUDE_ARGV_ENV = "SULIS_SESSION_CLAUDE_ARGV"

#: Default provider name registered with the manager.
_PROVIDER = "claude"

#: Bounded wait for a turn to stream to its terminal ``result`` — long enough
#: never to flake under a loaded CI runner, short enough that a genuine hang
#: fails fast rather than blocking forever.
_TURN_TIMEOUT_SECONDS = 120.0


class _InjectableClaudeAdapter(ClaudeAdapter):
    """The real Claude adapter with one test seam: ``spawn_argv``.

    When ``SULIS_SESSION_CLAUDE_ARGV`` is set (a JSON list), the spawned argv is
    that list (a scripted child) instead of the real ``claude`` invocation —
    everything else (``encode`` / ``decode`` / ``turn_complete`` /
    ``capabilities``) is the real adapter's, so the CLI under test exercises the
    genuine stream-json decode path. Unset → the real ``claude`` argv (§2.4)."""

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        override = os.environ.get(_CLAUDE_ARGV_ENV)
        if override:
            return list(json.loads(override))
        return super().spawn_argv(spec)


def _build_manager() -> SessionManager:
    """Construct the in-process manager with the Claude adapter registered.

    Maintenance is left at its boring defaults; the driver is short-lived (one
    flow per process) so idle-eviction / memory-cap never fire in a demo run."""
    return SessionManager({_PROVIDER: _InjectableClaudeAdapter()})


# ── output helpers — JSON for machine lines, plain text for the live stream ──


def _emit_json(label: str, payload: object) -> None:
    """Print a labelled JSON line (open/send/health/status results)."""
    sys.stdout.write(f"{label}: {json.dumps(payload, sort_keys=True)}\n")
    sys.stdout.flush()


def _render_event_live(event: Event) -> None:
    """Stream ONE event to stdout the moment it arrives (flush per chunk — the
    whole point is *live*). ``chunk`` text is written raw (no newline) so the
    reply reads as continuous prose; ``result`` / ``error`` / ``tool_use`` are
    rendered as their own labelled lines."""
    if event.kind == "chunk":
        sys.stdout.write(event.text or "")
        sys.stdout.flush()
        return
    if event.kind == "result":
        r = event.result
        usage = (
            {
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "duration_ms": r.duration_ms,
                "stop_reason": r.stop_reason,
            }
            if r is not None
            else {}
        )
        sys.stdout.write(f"\nresult: {json.dumps(usage, sort_keys=True)}\n")
        sys.stdout.flush()
        return
    if event.kind == "error":
        e = event.error
        payload = (
            {"category": e.category, "code": e.code, "message": e.message}
            if e is not None
            else {}
        )
        sys.stdout.write(f"\nerror: {json.dumps(payload, sort_keys=True)}\n")
        sys.stdout.flush()
        return
    if event.kind == "tool_use":
        sys.stdout.write(f"\ntool_use: {event.tool}\n")
        sys.stdout.flush()


def _stream_turn(mgr: SessionManager, key: str, since: int) -> float:
    """Follow-read one turn from ``since``, rendering each event live, and stop
    at the turn-terminal ``result`` (or ``error``). Returns the wall-clock
    seconds the turn took to stream (used to show the warm second turn is fast).

    A bounded deadline guards against a never-arriving terminal so the CLI can't
    hang CI; on timeout it stops following and returns."""
    start = time.monotonic()
    deadline = start + _TURN_TIMEOUT_SECONDS
    for event in mgr.read(key, since=since, follow=True):
        _render_event_live(event)
        if event.kind in ("result", "error"):
            break
        if time.monotonic() > deadline:
            sys.stdout.write("\n(turn stream timed out)\n")
            sys.stdout.flush()
            break
    return time.monotonic() - start


def _health_payload(mgr: SessionManager, key: str) -> dict:
    h = mgr.health(key)
    return {
        "alive": h.alive,
        "state": h.state,
        "pid": h.pid,
        "provider": h.provider,
    }


def _status_payload(mgr: SessionManager) -> list[dict]:
    return [
        {
            "key": s.key,
            "state": s.state,
            "pid": s.pid,
            "provider": s.provider,
            "memory_bytes": s.memory_bytes,
            "log_len": s.log_len,
        }
        for s in mgr.status()
    ]


# ── the single-process observable demo (the observed-done flow) ──────────────


def _run_demo(args: argparse.Namespace) -> int:
    """open → send → read --follow (live) → second send (warm) → status +
    health → close, all in one process. Each of the six methods is named in the
    trace so the flow is observable end-to-end (contract Part 1 wins)."""
    mgr = _build_manager()
    key = args.key
    try:
        # 1. open — get-or-spawn the warm session (§2.2).
        session = mgr.open(
            key,
            SessionSpec(
                provider=_PROVIDER,
                cwd=args.cwd,
                resume_ref=args.resume_ref,
            ),
        )
        _emit_json(
            "open",
            {
                "key": key,
                "pid": session.pid,
                "provider": session.spec.provider,
                "resumed": session.resumed,
                "state": session.state_machine.state.value,
            },
        )

        # 2. send turn one — returns the landing offset immediately (§2.2).
        offset = mgr.send(key, args.message)
        _emit_json("send", {"turn": 1, "offset": offset})

        # 3. read --follow — stream the reply LIVE from the landing offset.
        sys.stdout.write("read (turn 1, follow): ")
        sys.stdout.flush()
        first_secs = _stream_turn(mgr, key, offset)
        _emit_json("turn1_seconds", round(first_secs, 3))

        # 4. send turn two — SAME warm session, no re-open (warm reuse). The
        #    reply should remember turn one (memory across turns).
        second_offset = mgr.send(key, "what did I just say?")
        _emit_json("send", {"turn": 2, "offset": second_offset})
        sys.stdout.write("read (turn 2, follow): ")
        sys.stdout.flush()
        second_secs = _stream_turn(mgr, key, second_offset)
        _emit_json("turn2_seconds", round(second_secs, 3))

        # 5. status + health — the snapshot surface (§2.2/§2.3).
        _emit_json("status", _status_payload(mgr))
        _emit_json("health", _health_payload(mgr, key))

        return 0
    finally:
        # 6. close — terminate + release, idempotent (§2.2). In ``finally`` so a
        #    mid-flow failure still tears the warm child down cleanly.
        mgr.close(key)
        _emit_json("close", {"key": key})


# ── discrete subcommands (the six-method surface, one method per invocation) ──
#
# These are documented for completeness, but a fresh process starts a fresh
# in-process manager, so a session opened by one invocation is gone by the next
# — the demo flow is the observable Phase-1 shape. Cross-process persistence is
# the Phase-2 socket server (§2.8). Each subcommand still proves its method
# wires correctly in isolation.


def _run_open(args: argparse.Namespace) -> int:
    mgr = _build_manager()
    session = mgr.open(
        args.key,
        SessionSpec(provider=_PROVIDER, cwd=args.cwd, resume_ref=args.resume_ref),
    )
    _emit_json(
        "open",
        {
            "pid": session.pid,
            "provider": session.spec.provider,
            "resumed": session.resumed,
            "state": session.state_machine.state.value,
        },
    )
    mgr.close(args.key)
    return 0


def _run_send(args: argparse.Namespace) -> int:
    mgr = _build_manager()
    mgr.open(args.key, SessionSpec(provider=_PROVIDER, cwd=args.cwd))
    try:
        offset = mgr.send(args.key, args.message)
        _emit_json("send", {"offset": offset})
        # Drain the turn so the child isn't killed mid-write on close.
        _stream_turn(mgr, args.key, offset)
        return 0
    finally:
        mgr.close(args.key)


def _run_read(args: argparse.Namespace) -> int:
    mgr = _build_manager()
    mgr.open(args.key, SessionSpec(provider=_PROVIDER, cwd=args.cwd))
    try:
        if args.follow:
            _stream_turn(mgr, args.key, args.since)
        else:
            for event in mgr.read(args.key, since=args.since, follow=False):
                _render_event_live(event)
        sys.stdout.write("\n")
        return 0
    finally:
        mgr.close(args.key)


def _run_status(_args: argparse.Namespace) -> int:
    mgr = _build_manager()
    _emit_json("status", _status_payload(mgr))
    return 0


def _run_health(args: argparse.Namespace) -> int:
    mgr = _build_manager()
    mgr.open(args.key, SessionSpec(provider=_PROVIDER, cwd=args.cwd))
    try:
        _emit_json("health", _health_payload(mgr, args.key))
        return 0
    finally:
        mgr.close(args.key)


def _run_close(args: argparse.Namespace) -> int:
    mgr = _build_manager()
    mgr.close(args.key)
    _emit_json("close", {"key": args.key})
    return 0


# ── argparse wiring ──────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sulis-session",
        description=(
            "Minimal real driver for the in-process session manager — the "
            "Phase-1 observed-done gate. Spawns a real `claude` per session "
            "(or a test child via SULIS_SESSION_CLAUDE_ARGV)."
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    def _add_key(p: argparse.ArgumentParser) -> None:
        p.add_argument("--key", required=True, help="the session key")

    def _add_cwd(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--cwd",
            required=True,
            help="working directory the agent CLI is launched in",
        )

    demo = sub.add_parser(
        "demo",
        help="single-process observable flow: open→send→read --follow→close",
    )
    _add_key(demo)
    _add_cwd(demo)
    demo.add_argument("--message", required=True, help="the first turn's message")
    demo.add_argument("--resume-ref", default=None, help="prior-context handle")
    demo.set_defaults(func=_run_demo)

    open_p = sub.add_parser("open", help="get-or-spawn the warm session")
    _add_key(open_p)
    _add_cwd(open_p)
    open_p.add_argument("--resume-ref", default=None, help="prior-context handle")
    open_p.set_defaults(func=_run_open)

    send_p = sub.add_parser("send", help="submit a turn; print the landing offset")
    _add_key(send_p)
    _add_cwd(send_p)
    send_p.add_argument("--message", required=True, help="the turn's message")
    send_p.set_defaults(func=_run_send)

    read_p = sub.add_parser("read", help="stream events from an offset")
    _add_key(read_p)
    _add_cwd(read_p)
    read_p.add_argument("--since", type=int, default=0, help="start offset")
    read_p.add_argument(
        "--follow", action="store_true", help="follow live until turn end"
    )
    read_p.set_defaults(func=_run_read)

    status_p = sub.add_parser("status", help="snapshot every owned session")
    status_p.set_defaults(func=_run_status)

    health_p = sub.add_parser("health", help="liveness + identity for one session")
    _add_key(health_p)
    _add_cwd(health_p)
    health_p.set_defaults(func=_run_health)

    close_p = sub.add_parser("close", help="terminate + release a session")
    _add_key(close_p)
    close_p.set_defaults(func=_run_close)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch to the requested subcommand. Returns the process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 — top-level CLI boundary
        sys.stderr.write(f"error: {type(exc).__name__}: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
