"""``_session_manager.adapters.claude_pty`` — the interactive Claude pty adapter
(SESSION_MANAGER_CONTRACT §2.4 / ADR-004, WP-004).

The shipped :class:`~_session_manager.adapters.claude.ClaudeAdapter` is the
headless ``-p`` stream-json *chat* io-model. This adapter is its **pty
sibling**: it runs the **real interactive** ``claude --agent sulis`` whose
master pty the manager reads directly (raw bytes, no decode). It is the
production producer the spec's "one manager pty session per change" assumes —
the host wired a fake echo child before this existed (ADR-004 Context).

**EXPAND-Create, not a wrap.** The public face is the :class:`ProviderAdapter`
Protocol *we* own; the Claude CLI is *called by* ``spawn_argv`` (the §2.4
Stripe-rule discriminator). A new io-model for a provider is a new adapter
file, leaving the frozen :class:`ClaudeAdapter` untouched — the two coexist,
one per (provider, io-model), exactly the contract's shape.

**The pty io-model has no decode seam.** A pty session is a terminal view, not
a structured-chat stream: the manager reads the pty master as raw bytes and
feeds a scrollback buffer (§2.11). So ``encode`` / ``decode`` / ``turn_complete``
are unused — ``encode`` raises, ``decode`` returns ``None``,
``turn_complete`` returns ``False`` — mirroring the ``PtyChildAdapter`` test
sibling (``tests/lib/session_child_adapters.py``).

**Pre-prompt delivery REUSES the launcher's sidecar file (#86).** The change's
brief lives in ``~/.sulis/changes/{change_id}/pre_prompt.txt`` — the launcher
writes it; this adapter resolves the same path (importing the launcher's
:data:`~_terminal_launcher._PRE_PROMPT_SIDECAR` filename rather than
duplicating the literal, EP-03, so a re-point of the constant is followed here
for free) and **reads its bytes**, passing the brief as one argv element.

The launcher delivers the brief via a shell ``"$(cat <sidecar>)"`` because the
launcher writes a bash script bash then executes — a shell is in the loop to
expand the command-substitution. This adapter does NOT have that luxury: the
manager spawns the adapter's argv **directly** (``subprocess.Popen(argv, …)``
with no ``shell=True``, §2.12), so a ``$(cat …)`` element would reach ``claude``
as a literal string, never expanded. Reading the sidecar here and passing the
brief as a single argv element is the correct realisation under direct-execv
spawn, and it preserves the property that matters: the brief's bytes are NEVER
shell-parsed (apostrophes/quotes/backticks are safe; MUC-2 / #86).

**The change id rides the process environment, not argv (ADR-004).** The
daemon exports ``SULIS_CHANGE_ID`` on the spawned child's environment; this
adapter reads it from :data:`os.environ` to resolve the sidecar. That is the
contract-note-preferred path: it needs **no** new ``SessionSpec`` field, so
the frozen spec is untouched. An env value is attacker-influenceable in
principle, so it is validated as a real change ULID before it is ever joined
into a filesystem path (defence in depth) — a malformed value is ignored, not
turned into a path.

**The real interactive ``claude`` cannot run in CI** (the WP-009
``--verbose``-required lesson: recorded-fixture unit tests never see the real
binary). So this adapter has unit conformance + argv-shape tests in CI; the
real-pty round-trip is **observed-done** in WP-007.
"""

from __future__ import annotations

import os
from pathlib import Path

import _terminal_launcher
from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.events import Event
from _wpxlib import validate_change_ulid

# The interactive argv (§2.4 / ADR-004). cwd is NOT here — the CLI is launched
# *in* cwd by the manager's spawn, so cwd is a process attribute, not a flag.
# Deliberately none of the headless ``-p`` / stream-json flags the chat adapter
# carries: this is the terminal io-model the founder uses interactively.
# ``--dangerously-skip-permissions`` matches how a change session runs
# unattended (the launcher's default entry command).
_BASE_ARGV: tuple[str, ...] = (
    "claude",
    "--dangerously-skip-permissions",
    "--agent",
    "sulis",
)

# The env var the daemon exports to bind the spawned child to its change
# (ADR-004). Read here to resolve the pre-prompt sidecar without a SessionSpec
# field — the frozen spec stays untouched.
_CHANGE_ID_ENV = "SULIS_CHANGE_ID"


class InteractiveClaudePtyAdapter:
    """The interactive Claude pty :class:`ProviderAdapter` (§2.4 / ADR-004).

    Stateless: one instance serves any number of sessions; all per-session
    state lives on the :class:`SessionSpec` the manager passes in (cwd) and the
    ``SULIS_CHANGE_ID`` process environment (the change binding).
    """

    #: Honest capability flags (§2.7). Interactive Claude resumes and runs
    #: tools; it does NOT emit the partial-message chunk stream the chat
    #: adapter does (a pty is a raw terminal, read byte-by-byte).
    capabilities = Capabilities(
        supports_resume=True,
        supports_tools=True,
        supports_partial_streaming=False,
    )

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        """Shape the argv to start the **interactive** ``claude`` in
        ``spec.cwd``.

        Appends the change's pre-prompt as a single positional argv element
        iff a valid ``SULIS_CHANGE_ID`` is in the environment AND that change's
        sidecar file exists. Otherwise returns the bare interactive argv (a
        session with no briefed pre-prompt comes up bound to the change but
        idle until the founder types — the launcher's #93 default fills the
        sidecar for the spawn path).

        **Why the brief is read here, not deferred to a shell ``$(cat …)``.**
        The launcher's exec line uses ``"$(cat <sidecar>)"`` because the
        launcher writes a **bash script** that bash then executes — a shell is
        in the loop to expand the command-substitution. The manager spawns this
        adapter's argv **directly** (``subprocess.Popen(argv, …)`` with NO
        ``shell=True``, §2.12 ``_spawn_pty_process``), so each list element is a
        literal ``execv`` token — a ``$(cat …)`` element would reach ``claude``
        as the seven-character literal string, never expanded. So we resolve the
        same sidecar (reusing the launcher's path + constant) and read its bytes
        here, passing the brief as one argv element. This preserves the sidecar
        property that matters (the brief's bytes are NEVER shell-parsed —
        apostrophes/quotes/backticks are safe; #86 / MUC-2) without depending on
        a shell that is not in this spawn path."""
        argv = list(_BASE_ARGV)
        pre_prompt = self._read_pre_prompt()
        if pre_prompt is not None:
            argv.append(pre_prompt)
        return argv

    def encode(self, command: str) -> bytes:
        """Unused on the pty path — the manager writes raw bytes to the pty
        master, it does not frame structured turns (§2.4 / ADR-004)."""
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

    # ── internal: pre-prompt sidecar resolution ───────────────────────────

    def _read_pre_prompt(self) -> str | None:
        """Return the change's pre-prompt brief text iff a valid change id is in
        the environment and the sidecar file exists; else ``None``.

        Resolves the same sidecar the launcher writes
        (``~/.sulis/changes/{change_id}/{_PRE_PROMPT_SIDECAR}``, reusing the
        launcher's constant — imported, not duplicated, EP-03) and reads its
        bytes. The brief is returned as text to be passed as a single argv
        element by :meth:`spawn_argv` (the manager spawns argv directly, no
        shell — see that method's note).

        The change id comes from ``SULIS_CHANGE_ID`` (ADR-004) and is validated
        as a real change ULID before it is joined into a filesystem path — an
        env value is attacker-influenceable in principle, so a malformed value
        is ignored rather than turned into a path (defence in depth)."""
        change_id = os.environ.get(_CHANGE_ID_ENV, "").strip()
        if not change_id:
            return None
        ok, _reason = validate_change_ulid(change_id)
        if not ok:
            return None
        sidecar = (
            Path.home()
            / ".sulis"
            / "changes"
            / change_id
            / _terminal_launcher._PRE_PROMPT_SIDECAR
        )
        if not sidecar.is_file():
            return None
        return sidecar.read_text(encoding="utf-8")
