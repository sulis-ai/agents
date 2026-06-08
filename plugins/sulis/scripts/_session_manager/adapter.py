"""``_session_manager.adapter`` — the provider-adapter seam
(SESSION_MANAGER_CONTRACT §2.4).

This is **the only agent-specific surface**. The manager (WP-004) depends on
this ``ProviderAdapter`` Protocol; it never touches a vendor CLI or SDK
directly. One adapter per agent CLI translates that CLI's process invocation,
stdin framing, and stdout lines into the shared, provider-neutral vocabulary
(``events.py``, §2.3). Because the manager only ever speaks this Protocol, a
new provider (Codex, Gemini) slots in as **one new file** with zero change to
the manager or either consumer — that guarantee *is* the contract.

This is **EXPAND-Create**, not a SUBSTITUTE-Wrap of any vendor CLI: the public
face of this code is the Protocol *we* own (§2.4 Stripe-rule discriminator).
A provider's CLI is *called by* an adapter's methods; it is not the architecture
seam.

**Dependency direction (WPB-01, dependency-inward).** This module imports only
the WP-002 domain types from ``events`` — never the log, the manager, or any
subprocess/IO machinery. An adapter is testable with zero subprocess: it shapes
argv (the manager spawns), frames bytes (the manager writes), and parses one
line at a time (the manager reads). The IO lives outside; the mapping lives
here.

**The decode seam (§2.4 note).** ``decode()`` returns a *partial* :class:`Event`
— it fills ``kind`` and the matching payload, but the ``offset`` / ``key`` /
``turn`` fields are **placeholders** (``offset=-1``, ``key=""``, ``turn=-1``).
The manager (WP-004) owns the log and assigns the real offset/key/turn when it
appends the event. Splitting it this way keeps the adapter ignorant of log
state: it knows how to read one line of its CLI, nothing about where that line
lands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from _session_manager.classifier import RecoveryClass
from _session_manager.events import Event, EventError
from _session_manager.recovery import ReauthTicket


@dataclass(frozen=True)
class Capabilities:
    """What a provider can honestly do (§2.4/§2.7).

    Capabilities are declared, never assumed: ``open`` resumes prior context
    only if ``supports_resume`` is true, and tells the consumer honestly when
    it could not (the cockpit's ``resumed`` honesty, FR-26). Frozen because a
    provider's capability set is fixed for the life of the adapter.
    """

    supports_resume: bool
    supports_tools: bool
    supports_partial_streaming: bool


@dataclass(frozen=True)
class SessionSpec:
    """How to start one session (§2.4 input to ``spawn_argv``).

    ``cwd`` is the working directory the CLI is launched *in* — the manager
    passes it to ``Popen``; it is not an argv flag. ``resume_ref`` is the
    provider-specific handle to prior context (a session id, a transcript
    path); ``None`` means start fresh.

    ``io_mode`` (NEW, additive, defaulted — contract §2.12.1, ADR-001) selects
    the session's io-model and is **immutable for the session's life** ("PTY from
    birth"): ``"pipe"`` (the DEFAULT) is today's ``subprocess.PIPE`` stdin/stdout
    io-model that decodes structured chat into the offset event log, so every
    existing caller is byte-for-byte unchanged; ``"pty"`` is a PTY the manager
    owns from spawn (``os.openpty``) whose master end feeds a
    :class:`~_session_manager.scrollback.ScrollbackBuffer` (§2.11). A viewer
    attaching (WP-004) does NOT toggle this on — a pty session is pty whether or
    not a viewer is attached (visible = a viewer attached; headless = none).

    ``brief_change_id`` (NEW, additive, defaulted — this change's ADR-001) is
    the change whose pre-prompt brief the interactive-pty adapter should resolve
    (``~/.sulis/changes/{brief_change_id}/pre_prompt.txt``). ``None`` (the
    DEFAULT) means "no brief" — every frozen caller that does not set it is
    byte-for-byte unchanged, exactly the ``io_mode`` precedent. It exists because
    the brief target is **per-session** identity: under the shared daemon the
    ambient ``SULIS_CHANGE_ID`` is constant across every spawned session, so the
    old "brief from the env" path briefed every session for the daemon's
    start-time change (the bug ADR-001 corrects). The consumer (cockpit sidecar,
    desktop viewer) sets this to the same change id it already uses as the
    ``open()`` key, and the value reaches the adapter through the spec the
    manager already passes — the ``ProviderAdapter`` Protocol signature is
    untouched.
    """

    provider: str
    cwd: str
    resume_ref: str | None = None
    io_mode: Literal["pipe", "pty"] = "pipe"
    brief_change_id: str | None = None

    def __post_init__(self) -> None:
        # Defence-in-depth (SEC CONCERN-1): ``resume_ref`` is an opaque,
        # caller-supplied provider handle that flows into argv (e.g. Claude's
        # ``--resume <ref>``). Argv-list construction already prevents a shell
        # or separate-flag injection, but validate the shape centrally here so
        # EVERY adapter — including future Codex/Gemini adapters that may place
        # the ref differently — inherits the guard. Reject a leading ``-`` (so
        # it can never be mistaken for a flag) and any control character /
        # newline (so it can never split or smuggle across a line boundary).
        rr = self.resume_ref
        if rr is not None:
            if rr.startswith("-"):
                raise ValueError(
                    "resume_ref must not start with '-' (could be read as a flag)"
                )
            if any(ord(ch) < 0x20 for ch in rr):
                raise ValueError("resume_ref must not contain control characters")

        # Same defence-in-depth shape guard for ``brief_change_id``: it flows
        # into a filesystem path (``~/.sulis/changes/{brief_change_id}/…``), so
        # reject a leading ``-`` (never mistaken for a flag) and any control
        # character / newline (never split or smuggle across a path or line
        # boundary). The adapter additionally validates it is a real change ULID
        # before the path join (defence in depth); this guard is the central,
        # every-adapter-inherits-it shape check, mirroring ``resume_ref``.
        bci = self.brief_change_id
        if bci is not None:
            if bci.startswith("-"):
                raise ValueError(
                    "brief_change_id must not start with '-' (could be read as a flag)"
                )
            if any(ord(ch) < 0x20 for ch in bci):
                raise ValueError("brief_change_id must not contain control characters")


@runtime_checkable
class ProviderAdapter(Protocol):
    """The one agent-specific seam (§2.4).

    ``@runtime_checkable`` so a concrete adapter can be asserted to conform
    structurally — the conformance test that proves Codex/Gemini will slot in
    against the same shape.
    """

    capabilities: Capabilities

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        """How to start this CLI in streaming mode, to be launched in
        ``spec.cwd``."""
        ...

    def encode(self, command: str) -> bytes:
        """Frame one submitted turn for this CLI's stdin."""
        ...

    def decode(self, line: bytes) -> Event | None:
        """Parse ONE line of this CLI's stdout into a shared :class:`Event`,
        or ``None`` for lines carrying no founder-facing event (init /
        bookkeeping). Raises :class:`InternalError` (``DECODE_FAILED``) on an
        unparseable line. The returned Event has placeholder offset/key/turn —
        the manager fills them on append."""
        ...

    def turn_complete(self, event: Event) -> bool:
        """This agent's 'turn done' signal — the manager uses it to release the
        one-in-flight slot (§2.6) and run the next queued send."""
        ...

    def classify_failure(self, error: EventError) -> RecoveryClass | None:
        """Provider-specific *detection hint* (NEW, additive, defaulted — ADR-003).

        Map THIS provider's raw failure to a neutral :class:`RecoveryClass`, or
        return ``None`` to **defer to the neutral classifier** (the
        category-based default in ``classifier.py``). The default implementation
        below returns ``None``, so a brand-new adapter that does not override it
        stays safe and honest — it simply opts out of provider-specific
        detection and lets the shared arbiter decide (protocol→retry,
        internal/expected→dead-end, ``NOT_AUTHORIZED``→login-expired).

        This mirrors the ``io_mode`` / ``brief_change_id`` additive precedent:
        new optional surface, every existing method signature byte-unchanged.
        Only the provider that *can* read its own raw codes (e.g. the Claude
        adapter's 401→login-expired, 429→blip mapping, WP-006) overrides it; the
        raw vocabulary never leaks into the shared layer."""
        return None

    def reauth(self) -> ReauthTicket:
        """Begin re-auth for this provider; return the WP-001 :class:`ReauthTicket`
        (NEW, additive — ADR-003/004).

        Called **only** when ``classify_failure`` yields
        :attr:`RecoveryClass.LOGIN_EXPIRED`. The ticket carries the re-login link
        the notification surfaces on the existing ``error`` Event stream and a
        completion handle the driver waits on before resuming the paused run — no
        new store, no new stream (ADR-004). A default adapter never reaches here
        (it never returns ``LOGIN_EXPIRED``), so this has no neutral default; the
        provider that detects login-expiry is the one that supplies it."""
        ...
