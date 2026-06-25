"""``_session_manager.adapters.agy_pty`` — the interactive Google Antigravity
(``agy``) pty adapter (WP-001, CH-M7WSQ4; TDD §Form/§Armor/§Proof, PC-001,
ADR-001/002/003).

Phase 1 of the Claude↔agy failover capability: make ``agy`` a **selectable
execution target**, seeded by the CH-GJ9KQR portable-context brief. This adapter
is the pty sibling of :class:`~_session_manager.adapters.claude_pty.InteractiveClaudePtyAdapter`
— it runs the **real interactive** ``agy --prompt-interactive`` whose master pty
the manager reads directly (raw bytes, no decode).

**EXPAND-Create, not a wrap (TDD §Form, §2.4 Stripe-rule discriminator).** The
public face is the :class:`ProviderAdapter` Protocol *we* own; the ``agy`` CLI is
*called by* ``spawn_argv``. A new provider is **one new file**, leaving the
manager and the Claude adapter untouched — exactly the contract's shape.

**Mirrors the SHAPE, not the Claude-specific behaviours (ADR-002, grounded in
PC-001).** It reproduces the structure (``_BASE_ARGV``; brief-as-trailing-positional
read from the CH-GJ9KQR sidecar; unused ``encode``/``decode``/``turn_complete``;
``classify_failure -> None``) but **omits** the two Claude-only behaviours ``agy``
lacks:

- **No Remote Control fragment** — ``agy`` has no ``--remote-control`` flag.
- **No deterministic pre-spawn ``--session-id`` pin** — ``agy`` assigns its own
  conversation ids; resume is by ``--conversation <id>`` (``--continue`` is the
  documented most-recent fallback). Faking a flag the platform rejects is dead
  surface (ADR-002).

So this adapter does NOT import ``_change_session`` (no id pin) and adds no Remote
Control surface.

**Permission posture is the one genuine hardening decision (ADR-003, the Armor
gate; PC-001 §5).** Default ``--sandbox`` (``agy``'s first-class terminal-restriction
mode), **never** blanket ``--dangerously-skip-permissions``. A default-OFF / opt-in
``SULIS_AGY_SKIP_PERMISSIONS`` knob lets an operator who accepts the risk drop
``--sandbox`` and pass ``--dangerously-skip-permissions`` instead. This is the
**inverse polarity** of the Claude adapter's default-ON Remote Control knob,
deliberately: a permission-*loosening* knob must be opt-in.

**The pty io-model has no decode seam.** A pty session is a terminal view, not a
structured-chat stream: the manager reads the pty master as raw bytes and feeds a
scrollback buffer (§2.11). So ``encode`` raises, ``decode`` returns ``None``,
``turn_complete`` returns ``False`` — mirroring the Claude pty adapter.

**Pre-prompt delivery REUSES the launcher's sidecar file (#86, EP-03).** The
change's brief lives in ``~/.sulis/changes/{change_id}/pre_prompt.txt`` — the
launcher writes it; this adapter resolves the same path (importing the launcher's
:data:`~_terminal_launcher._PRE_PROMPT_SIDECAR` filename rather than duplicating
the literal) and reads its bytes, passing the brief as **one execv token**. The
manager spawns argv **directly** (``subprocess.Popen(argv, …)`` with no
``shell=True``, §2.12), so a ``$(cat …)`` element would reach ``agy`` as a literal
string, never expanded — reading the sidecar here and passing the brief as a single
argv element is the correct realisation, preserving the property that matters: the
brief's bytes are NEVER shell-parsed (apostrophes/quotes/backticks safe, MUC-2 / #86).

**The change id rides the SessionSpec, not the process environment (CH-GJ9KQR
ADR-001).** Under the shared daemon (one long-lived process spawns every change's
session) the ambient ``SULIS_CHANGE_ID`` is constant across sessions, so reading
the brief target from the env briefs every session for the daemon's start-time
change. The adapter reads ``spec.brief_change_id`` — the per-session change id the
consumer already uses as the ``open()`` key — and the ambient env is **never
consulted**. The value is validated as a real change ULID before it is joined into
a filesystem path (defence in depth, on top of ``SessionSpec.__post_init__``'s
leading-``-`` / control-char guard).

**The real interactive ``agy`` cannot run a prompt-bearing session in CI** (real
Google auth required). So this adapter has unit conformance + argv-shape tests in
CI, plus read-only binary introspection (``tests/integration/test_agy_binary_introspection.py``);
the real prompt round-trip is the deferred ``agy-real-session-driver-google``,
observed at verify time / Phase 2.
"""

from __future__ import annotations

import os

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.adapters._pre_prompt import read_pre_prompt_sidecar
from _session_manager.classifier import RecoveryClass
from _session_manager.events import Event, EventError
from _session_manager.recovery import ReauthTicket

# The interactive argv base (PC-001 §4). cwd is NOT here as a process attribute —
# it is passed *explicitly* as ``--add-dir <cwd>`` (agy's workspace is set by
# --add-dir, not by the launch dir), appended by ``spawn_argv``. Deliberately
# none of the headless ``-p`` / ``--print`` / ``--prompt`` flags: this is the
# terminal io-model. The permission posture (--sandbox by default, ADR-003) is
# appended by ``spawn_argv`` so the opt-in knob can flip it.
_BASE_ARGV: tuple[str, ...] = ("agy", "--prompt-interactive")

# ─── Permission posture opt-in knob (ADR-003; default-OFF / opt-in) ──────────
# agy is a write/exec platform. The DEFAULT posture is agy's first-class
# ``--sandbox`` (terminal restrictions); blanket ``--dangerously-skip-permissions``
# is NEVER the default. This knob is the inverse polarity of the Claude adapter's
# default-ON Remote Control knob: a permission-*loosening* knob must be opt-in
# (a truthy value turns it ON), never default-on. An unset/empty/falsey value
# keeps the guarded ``--sandbox`` posture.
_SKIP_PERMISSIONS_KNOB = "SULIS_AGY_SKIP_PERMISSIONS"
_SKIP_PERMISSIONS_TRUTHY = frozenset({"1", "true", "yes", "on"})

# ─── Optional model knob (PC-001 §6) ─────────────────────────────────────────
# When set, appends ``--model <value>``; unset → agy uses its own default model.
_MODEL_KNOB = "SULIS_AGY_MODEL"


def _skip_permissions_enabled() -> bool:
    """Return True only when the opt-in knob is set to a truthy value (ADR-003).

    Default-OFF: an unset/empty/falsey ``SULIS_AGY_SKIP_PERMISSIONS`` keeps the
    guarded ``--sandbox`` posture. A truthy value (``1``/``true``/``yes``/``on``,
    case-insensitive) loosens to ``--dangerously-skip-permissions``."""
    return (
        os.environ.get(_SKIP_PERMISSIONS_KNOB, "").strip().lower()
        in _SKIP_PERMISSIONS_TRUTHY
    )


class InteractiveAgyPtyAdapter:
    """The interactive ``agy`` pty :class:`ProviderAdapter` (PC-001, ADR-001/002/003).

    Stateless: one instance serves any number of sessions (the daemon registers a
    single instance under both ``"agy"`` and ``"antigravity"`` keys); all
    per-session state lives on the :class:`SessionSpec` the manager passes in —
    ``cwd`` (passed as ``--add-dir``), ``brief_change_id`` (which change to brief),
    and ``resume_ref`` (the agy conversation id to resume).
    """

    #: Honest capability flags (§2.7). Interactive agy resumes and runs tools; it
    #: does NOT emit a partial-message chunk stream (a pty is a raw terminal, read
    #: byte-by-byte). Identical honest flags to the Claude pty adapter.
    capabilities = Capabilities(
        supports_resume=True,
        supports_tools=True,
        supports_partial_streaming=False,
    )

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        """Shape the argv to start the **interactive** ``agy`` (PC-001 §4).

        Token order:

        1. ``agy --prompt-interactive`` (``_BASE_ARGV``).
        2. ``--add-dir <spec.cwd>`` — grants the agent the worktree as workspace.
        3. permission posture (ADR-003): ``--sandbox`` by default; if
           ``SULIS_AGY_SKIP_PERMISSIONS`` is truthy → ``--dangerously-skip-permissions``
           instead (no ``--sandbox``).
        4. optional ``--model <SULIS_AGY_MODEL>`` when the env var is set.
        5. resume (ADR-002): ``spec.resume_ref`` set → ``--conversation <ref>``;
           else nothing (no pre-spawn pin — agy has no ``--session-id``).
        6. the brief as the **trailing positional**, read from the CH-GJ9KQR
           sidecar iff ``spec.brief_change_id`` is a valid change ULID AND the
           sidecar exists; else no positional.

        Deliberately emits neither ``--remote-control`` nor ``--session-id`` —
        agy has neither flag (ADR-002).
        """
        argv = list(_BASE_ARGV)
        argv.extend(["--add-dir", spec.cwd])
        argv.extend(self._permission_flags())
        argv.extend(self._model_flags())
        argv.extend(self._conversation_flags(spec))
        pre_prompt = read_pre_prompt_sidecar(spec)
        if pre_prompt is not None:
            argv.append(pre_prompt)
        return argv

    def encode(self, command: str) -> bytes:
        """Unused on the pty path — the manager writes raw bytes to the pty
        master, it does not frame structured turns (§2.4)."""
        raise NotImplementedError(
            "encode is unused on the pty io-model: the manager writes raw "
            "bytes to the pty master, not framed turns"
        )

    def decode(self, line: bytes) -> Event | None:
        """Unused on the pty path — a pty session is a terminal view, not a
        per-line event stream; the manager reads raw terminal bytes into a
        scrollback buffer (§2.11)."""
        return None

    def turn_complete(self, event: Event) -> bool:
        """Unused on the pty path — a terminal has no structured turn-done
        signal, so the one-in-flight slot model (§2.6) does not apply."""
        return False

    def classify_failure(self, error: EventError) -> RecoveryClass | None:
        """Provider detection hint — defer to the neutral classifier (PC-001 §8).

        Returns ``None`` in Phase 1: agy's raw failure / auth-expiry codes are not
        yet read. Provider-specific detection (the failover seam) is Phase 2,
        exactly as the Claude pty adapter deferred its own. The pty io-model
        surfaces failures as raw terminal output, not a structured error stream,
        so there is nothing to mis-detect in Phase 1."""
        return None

    def reauth(self) -> ReauthTicket:
        """Begin re-auth — Phase-2 seam stub (PC-001 §8).

        Raising keeps the stub honest: the driver only calls ``reauth`` after
        ``classify_failure`` yields ``LOGIN_EXPIRED``, which this adapter does not
        do in Phase 1. agy auth is Google Sign-In and does not transfer at outage
        time; the real re-login flow is Phase-2 work."""
        raise NotImplementedError(
            "agy interactive-pty reauth() is Phase-2 work; Phase 1 defers failure "
            "detection to the neutral classifier and never returns LOGIN_EXPIRED."
        )

    # ── internal: permission posture (ADR-003 Armor gate) ──────────────────

    def _permission_flags(self) -> list[str]:
        """Return the permission-posture argv fragment (ADR-003).

        Default-guarded: ``["--sandbox"]``. With the opt-in
        ``SULIS_AGY_SKIP_PERMISSIONS`` knob truthy, the loosened
        ``["--dangerously-skip-permissions"]`` instead (and no ``--sandbox``)."""
        if _skip_permissions_enabled():
            return ["--dangerously-skip-permissions"]
        return ["--sandbox"]

    # ── internal: optional model (PC-001 §6) ───────────────────────────────

    def _model_flags(self) -> list[str]:
        """Return ``["--model", <value>]`` iff ``SULIS_AGY_MODEL`` is set
        (non-empty); else ``[]`` so agy uses its own default model."""
        model = os.environ.get(_MODEL_KNOB, "").strip()
        if model:
            return ["--model", model]
        return []

    # ── internal: resume (ADR-002 / PC-001 §7) ──────────────────────────────

    def _conversation_flags(self, spec: SessionSpec) -> list[str]:
        """Return the resume argv fragment (ADR-002).

        ``spec.resume_ref`` set → ``["--conversation", <ref>]`` (agy resumes a
        previous conversation by its agy-assigned id). Unset → ``[]`` (no
        pre-spawn pin — agy has no ``--session-id``; ``--continue`` is the
        documented most-recent fallback, not emitted here in Phase 1).

        ``resume_ref`` already passed ``SessionSpec.__post_init__``'s shape guard
        (no leading ``-``, no control chars) → safe to place after
        ``--conversation``."""
        if spec.resume_ref:
            return ["--conversation", spec.resume_ref]
        return []

    # The pre-prompt sidecar read is the shared
    # :func:`_session_manager.adapters._pre_prompt.read_pre_prompt_sidecar`
    # primitive (EP-02 — extracted at the 2-consumer threshold; the Claude pty
    # adapter is the other consumer). ``spawn_argv`` calls it directly.
