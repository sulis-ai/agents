"""``_session_manager.maintenance`` — idle-eviction + LRU memory-cap +
dead-process detection (the periodic maintenance tick).

Contract: SESSION_MANAGER_CONTRACT.md §2.7 (idle-eviction, memory cap with LRU
eviction, dead-process detection). This is the **Armor** primitive for resource
bounds: warm sessions cost RAM, so the manager caps how many it holds and reaps
idle ones — adapted from the AE ``terminal_pool.py`` ``perform_maintenance``
loop + idle-eviction + dead-process detection (ADR-001).

**Why its own module (WPB-04/WPB-07).** The manager (WP-004) exposes a no-op
``_maintenance_tick`` hook precisely so this logic attaches without swelling the
core flow. :class:`MaintenanceManager` is that logic, injected with the
capabilities it needs from the manager — a snapshot of the live sessions,
WP-004's ``is_alive`` liveness predicate, WP-004/005's ``_on_process_death``
recovery routing, and an ``evict`` callback (the manager's ``close``) — so it
owns *scheduling* (the tick) while the manager keeps owning the registry, the
six-method surface, and the liveness primitive this consumes.

**What this owns vs consumes (§ INDEX liveness ownership).** This WP owns the
maintenance *tick* (idle-eviction + LRU memory-cap + the *scheduling* of
dead-process detection). It **consumes, never re-implements:**

- WP-004's ``is_alive(session)`` for liveness — death *detection* in the tick
  calls it; the poll itself is not forked here;
- WP-004/005's ``_on_process_death`` for *recovery* routing of a detected death
  (restart-on-death vs PERMANENTLY_DISABLED is WP-005's, not this WP's);
- the ``last_activity`` timestamp WP-004 bumps on send/read — this WP only
  *reads* it as the idle / LRU key, it does not fork activity tracking.

**The cap default derives from host RAM with a conservative floor**
(:func:`derive_cap`), the decided-by-default tuning (Working Set
2026-06-05T12:24:53Z; contract Part 3 Q3) — an operational value, not an
interface change, with no founder-facing consequence until eviction is observed.
Read via the stdlib (``os.sysconf``) so a tuning floor adds no dependency
(§ WP Notes: prefer stdlib if a good-enough reading exists).
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable, Iterable

from _session_manager.session import Session

# ── memory-cap derivation (decided default: derive-from-RAM, floored) ───────

#: The conservative floor on the warm-session cap. Even on a tiny host the
#: manager keeps at least this many warm sessions, so the cap derivation can
#: never collapse to zero (which would make ``open`` evict-then-spawn in a loop).
#: A small boring integer (§2.7 conservative floor); the cap only grows above it
#: on hosts with the RAM to back more warm processes.
MEMORY_CAP_FLOOR = 2

#: A conservative estimate of the resident memory one warm agent process costs,
#: in bytes. Used only to translate "available RAM" into "how many warm sessions
#: fit" for the default cap; it is intentionally generous (over-estimating cost
#: → a smaller, safer cap) so a founder laptop is never driven to OOM by the
#: default. ~512 MiB per warm session.
_PER_SESSION_RAM_ESTIMATE = 512 * 1024 * 1024

#: The fraction of total host RAM the manager is willing to dedicate to warm
#: sessions by default — half, leaving the other half for the OS, the cockpit /
#: CLI process itself, and headroom. Conservative + boring (§2.7).
_RAM_BUDGET_FRACTION = 0.5


def total_host_ram_bytes() -> int:
    """Total physical RAM of the host in bytes, via the stdlib (no dependency).

    Uses ``os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')`` — the
    POSIX way to read physical memory, present on Linux + macOS (the dev + CI
    hosts). If the platform does not expose it (a non-POSIX host, or the names
    are missing), returns ``0`` so :func:`derive_cap` falls back to the floor
    rather than crashing — a missing reading must degrade to the safe default,
    not raise (§ WP Notes: prefer stdlib; avoid a dep for a tuning floor)."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (ValueError, AttributeError, OSError):
        return 0
    if pages < 0 or page_size < 0:
        return 0
    return pages * page_size


def derive_cap(total_ram_bytes: int) -> int:
    """Derive the default warm-session cap from total host RAM, floored (§2.7).

    The cap is a conservative fraction of total RAM divided by a generous
    per-session RAM estimate, clamped up to :data:`MEMORY_CAP_FLOOR`. So a tiny
    (or unreadable, ``0``) host clamps to the floor — never zero — while a
    generous host scales above it. Monotonic in ``total_ram_bytes`` (more RAM
    never yields a smaller cap), explicit and boring — no weakref/GC trickery
    (§ Green)."""
    budget = int(total_ram_bytes * _RAM_BUDGET_FRACTION)
    fits = budget // _PER_SESSION_RAM_ESTIMATE
    return max(MEMORY_CAP_FLOOR, fits)


def default_cap() -> int:
    """The RAM-derived default cap for this host (floored). The manager adopts
    this when no explicit ``memory_cap`` tuning is supplied (§2.7)."""
    return derive_cap(total_host_ram_bytes())


def memory_bytes_for_pids(pids: list[int]) -> dict[int, int]:
    """Best-effort resident memory (bytes) for several pids in **one** ``ps``
    call — the batched reading that backs ``status()``'s ``memory_bytes`` (§2.3).

    A single ``ps -o pid=,rss= -p p1,p2,…`` invocation reads every owned
    session's RSS at once, so ``status()`` forks exactly one subprocess
    regardless of how many warm sessions the manager holds — not one ``ps`` per
    session (which, at the RAM-derived cap, would be a fork-heavy snapshot of a
    method documented as cheap). Read via the stdlib (``ps``, KiB on Linux +
    macOS) so the snapshot adds no dependency — the cap itself is a *count*
    derived from RAM (:func:`derive_cap`), not a live RSS sum, so this is purely
    the status surface, not a control input.

    Returns a ``{pid: bytes}`` map; a pid absent from the reading (process gone,
    or the whole reading unavailable) is simply omitted, so a caller defaults it
    to ``0`` — a missing reading degrades to a benign 0, never raises into the
    side-effect-free snapshot."""
    if not pids:
        return {}
    try:
        out = subprocess.run(
            ["ps", "-o", "pid=,rss=", "-p", ",".join(str(p) for p in pids)],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    result: dict[int, int] = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        result[int(parts[0])] = int(parts[1]) * 1024  # ps reports KiB
    return result


def session_memory_bytes(session: Session) -> int:
    """Best-effort resident memory of one ``session``'s child process, in bytes
    (§2.3) — the single-session convenience over :func:`memory_bytes_for_pids`.

    Returns ``0`` when the process is gone or the reading is unavailable. The
    batched :func:`memory_bytes_for_pids` is what ``status()`` uses so a snapshot
    of N sessions forks one ``ps``, not N; this stays for callers (and tests)
    that want one session's reading."""
    pid = session.pid
    if pid is None:
        return 0
    return memory_bytes_for_pids([pid]).get(pid, 0)


# ── tuning defaults ─────────────────────────────────────────────────────────

#: Default idle timeout in seconds — a warm session untouched for longer than
#: this is reaped by the tick. Generous + boring: a session genuinely in use is
#: bumped on every send/read, so only truly-abandoned sessions cross it. Ten
#: minutes (operational tuning, no founder-facing consequence until observed).
DEFAULT_IDLE_TIMEOUT_SECONDS = 600.0

#: How often the background maintenance thread runs the tick, in seconds. Small
#: relative to the idle timeout so an idle session is reaped promptly after it
#: crosses the threshold, but not so small it busy-spins.
DEFAULT_MAINTENANCE_INTERVAL_SECONDS = 30.0


class MaintenanceManager:
    """Owns the maintenance tick for one manager: idle-eviction + LRU
    memory-cap + dead-process detection (§2.7).

    Args:
        idle_timeout: seconds of inactivity past which a session is reaped.
            Defaults to :data:`DEFAULT_IDLE_TIMEOUT_SECONDS`.
        memory_cap: the maximum number of warm sessions. Defaults to the
            RAM-derived :func:`default_cap` (floored at :data:`MEMORY_CAP_FLOOR`).
        clock: the monotonic clock used to decide idle — injectable so tests
            drive eviction deterministically without real sleep (MEA-09).
            Defaults to :func:`time.monotonic`, the same clock WP-004 stamps
            ``last_activity`` with, so the two are comparable.

    The manager constructs one :class:`MaintenanceManager` and routes its
    no-op ``_maintenance_tick`` hook to :meth:`tick`, and consults
    :meth:`over_cap_victims` from ``open`` before admitting a new session.
    """

    def __init__(
        self,
        *,
        idle_timeout: float = DEFAULT_IDLE_TIMEOUT_SECONDS,
        memory_cap: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if idle_timeout <= 0:
            raise ValueError("idle_timeout must be > 0")
        self._idle_timeout = float(idle_timeout)
        self._memory_cap = int(memory_cap) if memory_cap is not None else default_cap()
        if self._memory_cap < 1:
            raise ValueError("memory_cap must be >= 1")
        self._clock = clock

    @property
    def idle_timeout(self) -> float:
        """The configured idle timeout in seconds."""
        return self._idle_timeout

    @property
    def memory_cap(self) -> int:
        """The configured (or RAM-derived) maximum number of warm sessions."""
        return self._memory_cap

    def clock(self) -> float:
        """The current value of the injected monotonic clock — exposed so a
        test can stamp ``last_activity`` against the same clock the idle
        predicate uses (MEA-09 determinism)."""
        return self._clock()

    # ── idle predicate (the single idle decision) ──────────────────────────

    def is_idle(self, *, last_activity: float) -> bool:
        """Whether a session last active at ``last_activity`` is idle now —
        i.e. more than ``idle_timeout`` has elapsed on the injected clock
        (§2.7). The single place the idle decision lives, so the tick and any
        test agree on it."""
        return (self._clock() - last_activity) > self._idle_timeout

    # ── the maintenance tick (idle-eviction + dead-process detection) ──────

    def tick(
        self,
        sessions: Iterable[tuple[str, Session]],
        *,
        is_alive: Callable[[Session], bool],
        on_death: Callable[[Session], None],
        evict: Callable[[str], None],
    ) -> None:
        """One maintenance pass over a snapshot of the live sessions (§2.7).

        For each ``(key, session)``:

        1. **Dead-process detection** — consume WP-004's ``is_alive``; on a dead
           process route it through WP-004/005's ``on_death`` (recovery is
           WP-005's, this WP only *detects* in the tick) and move on (a dead
           session is not also idle-evicted in the same pass — recovery owns it).
        2. **Idle-eviction** — a live session idle past the timeout is reaped
           via ``evict`` (the manager's ``close``: SIGTERM→SIGKILL, log closed,
           registry entry removed — graceful).

        The caller passes a *snapshot* (not the live registry) so eviction
        mutating the registry mid-pass is safe.

        Args:
            sessions: a snapshot of ``(key, session)`` the manager owns.
            is_alive: WP-004's liveness predicate (consumed, not re-implemented).
            on_death: WP-004/005's death-recovery routing (consumed).
            evict: the manager's graceful close, ``evict(key) -> None``.
        """
        for key, session in sessions:
            if not is_alive(session):
                # Dead → recovery routing (WP-005 decides restart vs disable).
                # Detection is this WP's; recovery is not. A dead session is not
                # idle-evicted in the same pass — the death path owns it.
                on_death(session)
                continue
            if self.is_idle(last_activity=session.last_activity):
                evict(key)

    # ── LRU memory-cap (eviction victims when admitting a new session) ─────

    def over_cap_victims(
        self,
        sessions: Iterable[tuple[str, Session]],
        *,
        admitting: int = 1,
    ) -> list[str]:
        """The keys to evict, least-recently-used first, so that admitting
        ``admitting`` new session(s) keeps the total at or below the cap (§2.7).

        ``last_activity`` (WP-004's send/read-bumped timestamp, read here only)
        is the LRU key: the oldest-activity sessions are the victims. Returns an
        empty list when there is already room. The manager calls this from
        ``open`` before spawning, evicts each returned key gracefully, then
        admits the new session — so the cap is a hard bound on warm sessions."""
        current = list(sessions)
        # How many must go so that (current - victims + admitting) <= cap.
        overflow = (len(current) + admitting) - self._memory_cap
        if overflow <= 0:
            return []
        # Least-recently-used first: ascending by last_activity.
        by_lru = sorted(current, key=lambda item: item[1].last_activity)
        return [key for key, _ in by_lru[:overflow]]
