"""WP-002 — tests for the bounded scrollback ring (the second content model).

Contract: ``SESSION_MANAGER_CONTRACT.extension.md`` §2.11 (terminal-scrollback
content model) and §2.11.3 (the Armor ceiling — bounded memory is a MUST).
ADR-002 records *why* this is a second content model distinct from the offset
``EventLog`` (§2.5): the ``EventLog`` carries DECODED structured chat events;
the ``ScrollbackBuffer`` carries RAW terminal bytes (escape codes, cursor
moves, colour) that a terminal emulator (xterm.js) renders.

Verification posture (INDEX, MEA-09): real in-process behaviour against the
real type — no mocks. The bound test drives the §2.11.3 DoS ceiling for real
(2 MiB into a 1 MiB ring), the boring proof that the ring cannot grow unbounded.
"""

from __future__ import annotations

from _session_manager.scrollback import ScrollbackBuffer

_MIB = 1024 * 1024


def test_append_past_cap_drops_oldest() -> None:
    """Append 2 MiB into a 1 MiB ring; retained bytes are bounded by the cap and
    the retained tail is the most-recent bytes (§2.11.3 — oldest dropped)."""
    buf = ScrollbackBuffer(capacity_bytes=_MIB)

    first = b"A" * _MIB  # fills the ring exactly
    second = b"B" * _MIB  # forces the whole first block out
    buf.append(first)
    buf.append(second)

    snap = buf.snapshot()
    # The Armor ceiling MUST hold: retained bytes never exceed the cap.
    assert len(snap) <= _MIB
    # The retained tail is the most-recent bytes — the oldest were dropped.
    assert snap == second
    assert b"A" not in snap


def test_snapshot_order() -> None:
    """Appends accumulate oldest→newest; snapshot returns them in that order —
    what a newly-attached viewer renders before live bytes begin (§2.11/§2.12)."""
    buf = ScrollbackBuffer(capacity_bytes=_MIB)

    buf.append(b"abc")
    buf.append(b"def")

    assert buf.snapshot() == b"abcdef"
