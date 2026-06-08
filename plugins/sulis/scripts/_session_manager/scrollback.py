"""Bounded, append-only ring of raw terminal output bytes — the *second*
content model for a PTY-backed session.

Contract: ``SESSION_MANAGER_CONTRACT.extension.md`` §2.11 (terminal-scrollback
content model) and §2.11.3 (the Armor ceiling — bounded memory is a MUST).

Why raw bytes, not events (§2.11.1): xterm.js is a terminal *emulator* that
renders a raw byte stream of ANSI/VT escape sequences — those bytes *are* the
content, so scrollback is ``bytes``, not the offset-addressed ``Event`` log
(§2.5). This is a distinct content model from the ``EventLog`` (ADR-002): the
log carries DECODED structured chat events; this ring carries RAW terminal
bytes that the emulator renders.

Dependency direction (WPB-01 / MEA-01): this module imports only stdlib — no
manager, no pty, no infrastructure. It is a pure bounded byte ring; the pty
pump (WP-003) appends to it and the viewer (WP-004) snapshots it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScrollbackBuffer:
    """A bounded, append-only ring of raw terminal output bytes for a
    PTY-backed session — the "what's on the terminal screen" content model.

    Distinct from the :class:`~_session_manager.event_log.EventLog` (§2.5): the
    ``EventLog`` carries DECODED structured chat events; the
    ``ScrollbackBuffer`` carries RAW terminal bytes (escape codes, cursor moves,
    colour — the literal PTY output stream) that a terminal emulator (xterm.js)
    renders. Two content models, two purposes (ADR-002).

    Args:
        capacity_bytes: Hard byte ceiling (§2.11.3, MUST — the Armor ceiling).
            Appending past it drops the oldest bytes (ring discipline) so
            retained bytes never exceed it — unbounded scrollback is a
            memory-exhaustion vector. The recommended 1 MiB/session default is
            supplied by the caller (WP-003 at spawn), not hardcoded here.
    """

    #: Hard byte ceiling. Appending past it drops oldest bytes (§2.11.3, MUST).
    capacity_bytes: int
    #: Retained bytes, oldest→newest. Trimmed to ``capacity_bytes`` on append.
    _data: bytearray = field(default_factory=bytearray, repr=False)

    def __post_init__(self) -> None:
        if self.capacity_bytes <= 0:
            raise ValueError("capacity_bytes must be a positive integer")

    def append(self, data: bytes) -> None:
        """Append raw PTY output; drop oldest bytes past ``capacity_bytes``.

        After appending, retained bytes are trimmed from the front (oldest) so
        ``len(snapshot()) <= capacity_bytes`` always holds (§2.11.3). Amortised
        O(len(data)): a single extend plus an at-most-one front trim.
        """
        self._data.extend(data)
        overflow = len(self._data) - self.capacity_bytes
        if overflow > 0:
            del self._data[:overflow]

    def snapshot(self) -> bytes:
        """Return the current retained scrollback (oldest→newest) — what a
        newly-attached viewer renders before live bytes begin (§2.12).

        Returns an immutable copy: a caller cannot mutate the retained ring
        through the returned value.
        """
        return bytes(self._data)
