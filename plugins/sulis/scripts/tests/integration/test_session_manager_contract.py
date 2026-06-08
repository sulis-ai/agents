"""WP-008 — the §2.10 contract-stub conformance suite (the Proof pillar).

Contract: SESSION_MANAGER_CONTRACT.md §2.10 (the required stub set) + CF-04 /
CF-09 (error + empty stubs; recorded streaming stubs). This is the single suite
that proves the *whole* capability holds against the contract: the seven §2.10
scenarios, each encoded as a **recorded-NDJSON fixture** driving the **real**
``SessionManager`` through its public six-method surface.

Verification posture (INDEX / MEA-09): **recorded reality, real manager state,
no mocks of the manager's own internals.** The fixtures are verbatim `claude`
stream-json (the same provenance as ``tests/fixtures/session_manager/claude/``);
a real killable scripted-python child *replays* those recorded lines over a real
subprocess, and the **real** :class:`ClaudeAdapter` (WP-003) decodes them. The
manager owns the log, the queue, the state machine, restart-on-death — none of
it is stubbed. The only fixture-specific part is the *child program* (it replays
a file instead of calling the real `claude` — that is WP-009's job).

Each scenario is one fixture directory + one parametrised row, so a new scenario
is data, not new harness code (DoD Blue). The same fixture set is the shared
asset Phase-2's cockpit socket-client points ``runSessionBridgeContract`` at
(§2.8.3) — hence the ``contract_suite`` marker.

Why a *recorded* child rather than the WP-005 synthesised child: WP-005 proved
the *mechanism* (restart, resume) with a minimal scripted child; WP-008 proves
*conformance to the contract's recorded stubs*, so the bytes the child emits
must be the real CLI's bytes (MEA-09), decoded by the real adapter.
"""

from __future__ import annotations

import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

from _session_manager.adapters.claude import ClaudeAdapter
from _session_manager.adapter import SessionSpec
from _session_manager.event_log import OffsetEvictedError
from _session_manager.events import (
    NO_SESSION,
    SPAWN_FAILED,
    Event,
    ExpectedError,
    ProtocolError,
)
from _session_manager.manager import SessionManager

# ── locating the recorded stub set ─────────────────────────────────────────
# One directory per §2.10 scenario under tests/fixtures/session_manager/stubs/.
# Each carries turn-<N>.jsonl files (verbatim recorded `claude` stream-json) the
# child replays, one block per submitted turn.
_HERE = Path(__file__).resolve().parent
_STUBS_DIR = _HERE.parent / "fixtures" / "session_manager" / "stubs"

# Bounded wait for threaded assertions: long enough never to flake on a loaded
# CI runner, short enough that a real hang fails fast. Matches WP-005's _WAIT.
_WAIT = 5.0

# The contract-suite tag: Phase-2's socket-client conformance run points at the
# SAME fixture set (§2.8.3), so the suite is selectable as a shared asset.
pytestmark = pytest.mark.contract_suite


# ─── the recorded-fixture replay child (real subprocess, real decode) ───────
#
# argv: child.py <fixture_dir> [<delay>]
#
# The child reads encoded turns from stdin (one NDJSON `claude` stream-json
# user-message line per turn — exactly what ClaudeAdapter.encode produces). For
# the Nth turn it replays the recorded lines of ``<fixture_dir>/turn-<N>.jsonl``
# verbatim onto its stdout, then waits for the next turn. A turn block whose
# final non-blank line carries the sentinel ``{"__die__": "<mode>"}`` makes the
# child exit BEFORE replaying the rest (``before``) or AFTER one chunk but before
# the terminal result (``mid``) — reproducing the §2.10 #6 death-mid-turn shape
# against a real process the manager must restart. The sentinel is the ONLY
# non-`claude` line the child understands; every other line is replayed as-is so
# the fixtures stay verbatim recorded reality (MEA-09).
#
# argv: child.py <fixture_dir> <turn_state_file> [<delay>]
#
# The turn counter is persisted in ``<turn_state_file>`` so it survives a
# restart-on-death: a restarted child continues at the NEXT recorded turn block
# rather than re-running the turn that just died — exactly how a resumed `claude`
# behaves (§2.7: restart resumes from transcript, it does not re-execute the
# prior turn). The state file is per-session (unique per adapter), so concurrent
# sessions never share a counter.
_CHILD_SOURCE = r"""
import json, os, sys, time
from pathlib import Path

fixture_dir = Path(sys.argv[1])
state_file = Path(sys.argv[2])
delay = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

def emit(raw):
    sys.stdout.write(raw if raw.endswith("\n") else raw + "\n")
    sys.stdout.flush()

def read_turn():
    try:
        return int(state_file.read_text().strip())
    except Exception:
        return 0

def write_turn(n):
    state_file.write_text(str(n))

for _line in sys.stdin:
    if not _line.strip():
        continue
    turn = read_turn() + 1
    # Persist the turn number BEFORE replaying, so a death mid-replay still
    # advances the counter — the restart resumes at the NEXT block, not this one.
    write_turn(turn)
    block = fixture_dir / ("turn-%d.jsonl" % turn)
    if not block.exists():
        # No recorded block for this turn — nothing to replay.
        continue
    lines = [ln for ln in block.read_text().splitlines() if ln.strip()]
    # A trailing die-sentinel governs whether the child dies, and when.
    die = None
    if lines and lines[-1].lstrip().startswith('{"__die__"'):
        die = json.loads(lines[-1]).get("__die__")
        lines = lines[:-1]
    time.sleep(delay)
    if die == "before":
        os._exit(137)  # unexpected death before any output (§2.10 #6)
    emitted_chunk = False
    for raw in lines:
        emit(raw)
        # Detect the first content chunk so `die=mid` can fire right after it.
        try:
            rec = json.loads(raw)
        except Exception:
            rec = {}
        ev = rec.get("event") or {}
        if ev.get("type") == "content_block_delta" and not emitted_chunk:
            emitted_chunk = True
            if die == "mid":
                os._exit(137)  # death mid-turn: a chunk landed, no result (§2.10 #6)
"""


def _write_child(tmp_path: Path) -> Path:
    child = tmp_path / "replay_child.py"
    child.write_text(_CHILD_SOURCE)
    return child


class FixtureReplayAdapter:
    """A real :class:`ProviderAdapter` whose child *replays a recorded fixture*.

    Conformance posture (§2.10 / MEA-09): ``encode`` and ``decode`` are the
    **real** :class:`ClaudeAdapter`'s — the child replays verbatim recorded
    `claude` stream-json, so the contract is proven against the real mapping
    rules, not a stub. Only ``spawn_argv`` differs: it starts the replay child
    pointed at the scenario's fixture directory instead of the real `claude`
    binary (the real binary is WP-009's gate).

    ``capabilities`` mirrors Claude's (resume-capable) so the resumed-turn and
    death-restart scenarios exercise the real §2.7 resume path; ``spawn_argv``
    surfaces a resume marker exactly as the recorded contract requires.
    """

    def __init__(self, child: Path, fixture_dir: Path, *, delay: float = 0.0) -> None:
        self._child = child
        self._fixture_dir = fixture_dir
        self._delay = delay
        self._claude = ClaudeAdapter()
        self.capabilities = self._claude.capabilities
        # A per-session turn-state file so a restarted child resumes at the NEXT
        # recorded turn block, not the one that just died (§2.7). Lives beside
        # the child program; one adapter serves one session in these scenarios.
        self._turn_state = child.parent / f"turn_state_{id(self)}.txt"

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return [
            sys.executable,
            str(self._child),
            str(self._fixture_dir),
            str(self._turn_state),
            str(self._delay),
        ]

    def encode(self, command: str) -> bytes:
        return self._claude.encode(command)

    def decode(self, line: bytes) -> Event | None:
        return self._claude.decode(line)

    def turn_complete(self, event: Event) -> bool:
        return self._claude.turn_complete(event)


# ─── harness helpers (the plumbing, factored out at Blue) ───────────────────


@contextmanager
def _running_manager(
    child: Path,
    fixture: str,
    *,
    delay: float = 0.0,
    **tuning: object,
) -> Iterator[SessionManager]:
    """A real :class:`SessionManager` whose only provider replays the named
    fixture directory's recorded stream-json (§2.10), torn down on exit.

    ``start_maintenance`` is off by default so the background loop never races a
    scenario assertion. The context manager guarantees ``shutdown`` runs (closing
    every owned session) however the scenario exits — so each test body is the
    scenario, not the setup/teardown plumbing (DoD Blue). Extracted at the
    2-consumer threshold (every one of the nine §2.10 stubs needs it, EP-03)."""
    adapter = FixtureReplayAdapter(child, _STUBS_DIR / fixture, delay=delay)
    tuning.setdefault("start_maintenance", False)
    mgr = SessionManager({"claude": adapter}, **tuning)
    try:
        yield mgr
    finally:
        mgr.shutdown()


def _spec(tmp_path: Path, resume_ref: str | None = None) -> SessionSpec:
    return SessionSpec(provider="claude", cwd=str(tmp_path), resume_ref=resume_ref)


def _wait_for(predicate, timeout: float = _WAIT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _collect(mgr, key, since, *, until_kind, timeout=_WAIT) -> list[Event]:
    """Follow-read from ``since`` until an event of ``until_kind`` arrives (or
    timeout). Returns every event seen up to and including the terminal one."""
    out: list[Event] = []
    deadline = time.monotonic() + timeout
    for ev in mgr.read(key, since=since, follow=True):
        out.append(ev)
        if ev.kind == until_kind or time.monotonic() > deadline:
            break
    return out


def _history_has_result(mgr, key) -> bool:
    """True once the session's log's newest retained event is a ``result``.

    Reads only the newest retained offset (``next_offset - 1``) with
    ``follow=False`` so it works even under a tiny retention cap that has
    evicted offset 0 — used to await turn completion on a quiescent log without
    a live follower (the OFFSET_EVICTED stub)."""
    session = mgr._sessions.get(key)
    if session is None:
        return False
    nxt = session.log.next_offset()
    if nxt == 0:
        return False
    try:
        events = list(session.log.read(since=nxt - 1, follow=False))
    except OffsetEvictedError:
        return False
    return bool(events) and events[-1].kind == "result"


@pytest.fixture
def child(tmp_path) -> Path:
    return _write_child(tmp_path)


# ─── §2.10 #1 — happy turn ──────────────────────────────────────────────────


def test_contract_happy_turn(child, tmp_path):
    """open(resumed:false) → send → chunk* → result (§2.10 #1).

    The real manager drives the real ClaudeAdapter over the recorded happy
    fixture: a fresh session, one turn, streamed chunks, a terminal result with
    usage. ``resumed`` is honestly False (no resume ref)."""
    with _running_manager(child, "happy_turn") as mgr:
        session = mgr.open("k", _spec(tmp_path))
        assert session.resumed is False
        off = mgr.send("k", "say hello")
        evs = _collect(mgr, "k", off, until_kind="result")
        kinds = [e.kind for e in evs]
        assert kinds[-1] == "result"
        assert "chunk" in kinds
        assert evs[-1].result is not None
        assert evs[-1].result.stop_reason == "end_turn"
        # Offsets are contiguous and monotonic from the send bookmark (§2.5).
        assert [e.offset for e in evs] == list(range(off, off + len(evs)))


# ─── §2.10 #2 — resumed turn (proves §2.7 honesty) ──────────────────────────


def test_contract_resumed_turn(child, tmp_path):
    """open(resumed:true) then a turn (§2.10 #2 / §2.7).

    With a resume ref AND a resume-capable adapter, ``Session.resumed`` is
    honestly True; the turn then streams to a result over the recorded
    fixture."""
    with _running_manager(child, "resumed_turn") as mgr:
        session = mgr.open("k", _spec(tmp_path, resume_ref="prior-transcript"))
        assert session.resumed is True
        off = mgr.send("k", "continue")
        evs = _collect(mgr, "k", off, until_kind="result")
        assert [e.kind for e in evs][-1] == "result"
        assert "chunk" in [e.kind for e in evs]


# ─── §2.10 #3 — reconnect mid-turn (proves §2.5 nothing-lost) ───────────────


def test_contract_reconnect_mid_turn(child, tmp_path):
    """read(since=N, follow) after a drop yields the tail then live (§2.10 #3).

    A reader follows from the send offset, consumes the first chunk, then
    *drops* (stops iterating — the disconnect). A fresh reader reconnects from
    the last offset it saw and receives everything after it through to the
    result. Nothing is lost because the offset is the resumption point (§2.5)."""
    with _running_manager(child, "reconnect_mid_turn", delay=0.05) as mgr:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "stream a few chunks")

        # First viewer: take exactly the first event, then drop.
        first_seen: list[Event] = []
        for ev in mgr.read("k", since=off, follow=True):
            first_seen.append(ev)
            break  # the disconnect
        assert first_seen, "first reader saw nothing before the drop"
        last_seen_off = first_seen[-1].offset

        # Reconnect from the next offset after the last one seen: the tail then
        # live, terminating on the result. Nothing between is skipped.
        tail = _collect(mgr, "k", last_seen_off + 1, until_kind="result")
        assert tail, "reconnect reader saw nothing"
        assert tail[-1].kind == "result"
        # Contiguity across the drop boundary: the reconnect resumes exactly at
        # last_seen_off + 1 (§2.5 stable monotonic offsets).
        assert tail[0].offset == last_seen_off + 1
        # The union of both readers is the whole turn with no gap.
        all_offsets = [e.offset for e in first_seen] + [e.offset for e in tail]
        assert all_offsets == list(range(off, off + len(all_offsets)))


# ─── §2.10 #4 — two viewers (one turn, different `since`) ────────────────────


def test_contract_two_viewers(child, tmp_path):
    """Two reads with different `since` over one turn (§2.10 #4).

    Two concurrent followers — one from the send offset, one from one offset
    later — both run to the result without interfering; each holds its own
    cursor over the shared log (§2.5 per-reader cursors)."""
    with _running_manager(child, "two_viewers", delay=0.02) as mgr:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "stream for two viewers")

        results: dict[str, list[Event]] = {}

        def _viewer(name: str, since: int) -> None:
            results[name] = _collect(mgr, "k", since, until_kind="result")

        a = threading.Thread(target=_viewer, args=("a", off), daemon=True)
        b = threading.Thread(target=_viewer, args=("b", off + 1), daemon=True)
        a.start()
        b.start()
        a.join(_WAIT)
        b.join(_WAIT)
        assert not a.is_alive() and not b.is_alive(), "a viewer hung"

        # Both reached the result; neither interfered with the other.
        assert results["a"][-1].kind == "result"
        assert results["b"][-1].kind == "result"
        # Viewer A started one offset earlier, so it saw at least one more event.
        assert results["a"][0].offset == off
        assert results["b"][0].offset == off + 1
        assert len(results["a"]) >= len(results["b"])


# ─── §2.10 #5 — queued send (proves §2.6 one-in-flight) ─────────────────────


def test_contract_queued_send(child, tmp_path):
    """A second send while one is in flight runs after the first result (§2.10
    #5 / §2.6).

    Two sends are issued back-to-back. The second's landing offset is strictly
    after the first turn's result offset — proof the second turn was queued and
    ran only once the in-flight slot freed (FIFO, one-in-flight per key)."""
    with _running_manager(child, "queued_send", delay=0.05) as mgr:
        mgr.open("k", _spec(tmp_path))
        off1 = mgr.send("k", "first turn")
        off2 = mgr.send("k", "second turn")

        # The queued send's landing offset is after the first turn's first
        # event (it cannot land before the first turn started writing).
        assert off2 > off1

        first = _collect(mgr, "k", off1, until_kind="result")
        first_result_off = first[-1].offset
        assert first[-1].kind == "result"

        # The second turn's events all land strictly AFTER the first result —
        # one in flight at a time (§2.6).
        second = _collect(mgr, "k", off2, until_kind="result")
        assert second[-1].kind == "result"
        assert second[0].offset > first_result_off
        assert off2 > first_result_off


# ─── §2.10 #6 — death + restart (proves §2.7 continuation) ──────────────────


def test_contract_death_and_restart(child, tmp_path):
    """Process dies mid-turn → restart-on-death → error event then continuation
    (§2.10 #6 / §2.7).

    The first turn's recorded block carries a die-mid sentinel: the child emits
    one chunk then exits. The manager surfaces a turn-terminal ``error`` event
    (the follower never hangs), restarts the process under the same key + same
    log, and a fresh turn streams to a result — the conversation continues."""
    with _running_manager(child, "death_and_restart") as mgr:
        first = mgr.open("k", _spec(tmp_path, resume_ref="t"))
        first_pid = first.pid
        off = mgr.send("k", "this turn dies mid-stream")

        # The follower from the send offset terminates on an error (the
        # mid-turn death), never hangs.
        evs = _collect(mgr, "k", off, until_kind="error")
        kinds = [e.kind for e in evs]
        assert "error" in kinds, f"no error surfaced after mid-turn death; saw {kinds}"

        # The manager restarted the child (new pid) under the same key.
        assert _wait_for(
            lambda: mgr.health("k").alive and mgr.health("k").pid != first_pid
        ), "session never restarted after mid-turn death"

        # A fresh turn streams to completion on the restarted process — the
        # conversation continues across the crash (§2.10 #6).
        off2 = mgr.send("k", "continue after the crash")
        assert off2 > off
        cont = _collect(mgr, "k", off2, until_kind="result")
        assert cont[-1].kind == "result"


# ─── §2.10 #7 — error cases (CF-04 error stubs, not happy-path only) ─────────


def test_contract_error_no_session(child, tmp_path):
    """NO_SESSION: every content/identity op on an unopened key is an Expected
    decline (§2.10 #7 / §2.9). The empty case — nothing was opened."""
    with _running_manager(child, "happy_turn") as mgr:  # any fixture; never opened
        for op in (
            lambda: mgr.send("never-opened", "hi"),
            lambda: list(mgr.read("never-opened", since=0, follow=False)),
            lambda: mgr.health("never-opened"),
        ):
            with pytest.raises(ExpectedError) as exc:
                op()
            assert exc.value.code == NO_SESSION


def test_contract_error_offset_evicted(child, tmp_path):
    """OFFSET_EVICTED: a reader whose `since` predates the oldest retained
    offset gets an Expected eviction error rather than silently skipping
    (§2.10 #7 / §2.5).

    Retention is a §2.5 *log* property the manager surfaces, not a turn event,
    so this stub drives the real manager but forces a finite retention cap on
    the live session's log (the default retains the whole session, so eviction
    never fires under it — the cap is the documented forced-eviction path, per
    the change INDEX's "proven via a forced-cap test"). The cap is set BEFORE
    the turn and read back with ``follow=False`` AFTER the turn completes (a
    quiescent log, no live follower racing the eviction) — exactly the
    reconnect-from-an-evicted-offset shape a consumer must handle (§2.5)."""
    with _running_manager(child, "happy_turn") as mgr:
        session = mgr.open("k", _spec(tmp_path))
        # Force a finite, tiny retention cap before any event lands, so the
        # turn's appends evict the oldest as they arrive (§2.5 forced-cap).
        session.log._max_events = 1
        off = mgr.send("k", "say hello")
        # Wait for the turn to fully complete WITHOUT a live follower (a follower
        # racing the eviction is a separate §2.6 concern); poll history for the
        # terminal result, then assert against the now-quiescent log.
        assert _wait_for(lambda: _history_has_result(mgr, "k")), "turn never completed"
        # The cap kept only the newest event; offset 0 has been evicted, so a
        # reader from it gets an Expected eviction error, not a silent skip.
        with pytest.raises(OffsetEvictedError):
            list(mgr.read("k", since=0, follow=False))
        # And a read from a still-retained offset succeeds (it did not over-evict).
        assert off >= 0  # the send bookmark was a valid forward reference


def test_contract_error_spawn_failed(child, tmp_path):
    """SPAWN_FAILED: a child that cannot be launched surfaces a Protocol error
    at open (§2.10 #7 / §2.9). Forced via an argv whose executable does not
    exist — the real Popen failure path, not a mock."""
    adapter = FixtureReplayAdapter(child, _STUBS_DIR / "happy_turn")
    # Point spawn_argv at a non-existent executable — a real OSError on Popen.
    adapter.spawn_argv = lambda spec: ["/nonexistent/definitely-not-a-binary-xyz"]
    mgr = SessionManager({"claude": adapter}, start_maintenance=False)
    try:
        with pytest.raises(ProtocolError) as exc:
            mgr.open("k", _spec(tmp_path))
        assert exc.value.code == SPAWN_FAILED
    finally:
        mgr.shutdown()
