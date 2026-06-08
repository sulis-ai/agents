"""``_session_manager.adapters.claude`` — Claude adapter #1
(SESSION_MANAGER_CONTRACT §2.4).

Translates the `claude` CLI's headless ``--output-format stream-json`` protocol
into the shared, provider-neutral event vocabulary (``events.py``, §2.3). It is
the first concrete :class:`ProviderAdapter`; Codex and Gemini follow the same
shape with zero change to the manager.

**Reused mapping rules, not reused code.** The cockpit already encodes the
Claude stream-json → event mapping in
``apps/cockpit/server/lib/streamJsonToEvents.ts``. The manager is Python, so
the *rules* (not the TypeScript) are reimplemented here and kept aligned via
§2.3's mapping table:

| recorded line | Event |
|---|---|
| ``stream_event`` / ``content_block_delta`` (non-empty ``delta.text``) | ``chunk`` (text) |
| ``result`` with ``is_error`` falsey | ``result`` (usage + stop_reason) |
| ``result`` with ``is_error`` truthy | ``error`` (typed category) |
| ``system`` / init, and any other bookkeeping line | ``None`` |
| unparseable line | raises ``InternalError("DECODE_FAILED")`` |

The ``is_error`` flag — not ``subtype`` — is the error discriminator: a failed
turn's terminal line is recorded as ``subtype:"success", is_error:true`` (see
``tests/fixtures/session_manager/claude/error.jsonl``).

**The decode seam.** ``decode()`` returns a *partial* :class:`Event`: ``kind``
and the matching payload are filled, but ``offset`` / ``key`` / ``turn`` are
placeholders (``-1`` / ``""`` / ``-1``). The manager (WP-004) owns the log and
assigns those on append; the adapter never sees log state.

**Boring, explicit parsing.** Dict access is explicit with ``.get`` and clear
fallbacks; no reflection, no dynamic dispatch. A shape the CLI didn't produce
fails loudly at the typed boundary rather than silently mis-mapping.
"""

from __future__ import annotations

import json

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.classifier import RecoveryClass
from _session_manager.events import (
    DECODE_FAILED,
    Event,
    EventError,
    InternalError,
    TurnResult,
)
from _session_manager.recovery import ReauthTicket

# Placeholder log-coordinate values for the partial Event decode() returns.
# The manager (WP-004) overwrites these when it appends the event; the adapter
# is deliberately ignorant of where the event lands in the log.
_UNASSIGNED_OFFSET = -1
_UNASSIGNED_TURN = -1
_UNASSIGNED_KEY = ""

# The base streaming argv (§2.4). cwd is NOT here — the CLI is launched *in*
# cwd by the manager's Popen, so cwd is a process attribute, not a flag.
#
# ``--verbose`` is REQUIRED: with ``-p`` (--print) and
# ``--output-format stream-json``, the `claude` CLI (verified against v2.1.165)
# refuses to start without it — "When using --print, --output-format=stream-json
# requires --verbose" — and exits 1 before emitting any line, which the manager
# surfaces as ``STDIN_BROKEN``. This was caught by WP-009's observed-done gate
# (the first run against the real binary); the recorded-fixture unit tests can't
# see it because they never spawn the real CLI.
_BASE_ARGV: tuple[str, ...] = (
    "claude",
    "-p",
    "--input-format",
    "stream-json",
    "--output-format",
    "stream-json",
    "--include-partial-messages",
    "--verbose",
    "--dangerously-skip-permissions",
)


class ClaudeAdapter:
    """The Claude provider adapter (§2.4). Stateless: one instance serves any
    number of sessions; all per-session state lives on the :class:`SessionSpec`
    the manager passes in."""

    #: Honest capability flags (§2.7). Claude resumes, runs tools, and streams
    #: partial messages.
    capabilities = Capabilities(
        supports_resume=True,
        supports_tools=True,
        supports_partial_streaming=True,
    )

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        """Shape the argv to start `claude` in streaming mode. Appends
        ``--resume <ref>`` iff ``spec.resume_ref`` is set (the manager only
        passes a ref when this adapter's ``capabilities.supports_resume`` is
        true, §2.7)."""
        argv = list(_BASE_ARGV)
        if spec.resume_ref:
            argv.extend(["--resume", spec.resume_ref])
        return argv

    def encode(self, command: str) -> bytes:
        """Frame one turn as a single stream-json user-message NDJSON line,
        newline-terminated (§2.4)."""
        record = {
            "type": "user",
            "message": {"role": "user", "content": command},
        }
        return (json.dumps(record) + "\n").encode("utf-8")

    def decode(self, line: bytes) -> Event | None:
        """Map ONE recorded stdout line to a partial :class:`Event`, or
        ``None`` for bookkeeping. Raises :class:`InternalError`
        (``DECODE_FAILED``) on a line that is not valid JSON."""
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, ValueError) as exc:
            raise InternalError(
                DECODE_FAILED,
                f"could not parse claude stream-json line: {exc}",
            ) from exc

        record_type = record.get("type")

        if record_type == "stream_event":
            return self._decode_stream_event(record)
        if record_type == "result":
            return self._decode_result(record)

        # system/init, assistant, rate_limit_event, and any other line carry no
        # founder-facing chunk/result/error.
        return None

    def turn_complete(self, event: Event) -> bool:
        """True only for a successful turn-terminal result (§2.6). An ``error``
        event does NOT free the slot via this signal — the manager handles a
        failed turn through the state machine (§2.7), not the normal
        completion path."""
        return event.kind == "result"

    def classify_failure(self, error: EventError) -> RecoveryClass | None:
        """Provider detection hint (WP-004 seam; defer-to-neutral for now).

        WP-004 only proves the seam shape: this returns ``None`` so the shared
        classifier applies its category-based default (ADR-003). Claude's
        HTTP-status mapping (``"401"``/``"403"`` → login-expired, ``"429"`` →
        transient-blip, ``"400"`` → dead-end) is WP-006 — it overrides this
        method then, the only place Claude's ``api_error_status`` vocabulary is
        interpreted. Until then the neutral default (``NOT_AUTHORIZED`` →
        login-expired, etc.) is correct and safe."""
        return None

    def reauth(self) -> ReauthTicket:
        """Begin Claude re-auth (WP-004 seam stub; ADR-003/004).

        Wired into the conformance shape by WP-004; the real re-login-link
        production is WP-006. Raising here keeps the stub honest — the driver
        only calls ``reauth`` after ``classify_failure`` yields
        ``LOGIN_EXPIRED``, which this adapter does not do until WP-006."""
        raise NotImplementedError(
            "Claude reauth() is implemented in WP-006; the WP-004 seam only "
            "establishes the Protocol shape."
        )

    # ── internal mapping helpers (one record shape each) ──────────────────

    def _decode_stream_event(self, record: dict) -> Event | None:
        """``stream_event`` / ``content_block_delta`` with non-empty text →
        ``chunk``. Other stream events (block start/stop, message delta) carry
        no text → ``None``."""
        event = record.get("event") or {}
        if event.get("type") != "content_block_delta":
            return None
        text = (event.get("delta") or {}).get("text")
        if not isinstance(text, str) or text == "":
            return None
        return self._partial_event(kind="chunk", text=text)

    def _decode_result(self, record: dict) -> Event:
        """``result`` → ``error`` if ``is_error`` is truthy, else ``result``.
        ``is_error`` — not ``subtype`` — is the discriminator (§2.4)."""
        if record.get("is_error"):
            return self._partial_event(
                kind="error",
                error=self._error_payload(record),
            )
        usage = record.get("usage") or {}
        return self._partial_event(
            kind="result",
            result=TurnResult(
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                duration_ms=int(record.get("duration_ms", 0)),
                stop_reason=str(record.get("stop_reason", "")),
            ),
        )

    @staticmethod
    def _error_payload(record: dict) -> EventError:
        """Build the typed error payload for a failed result.

        An HTTP-status-bearing failure (``api_error_status``) is an **Expected**
        decline — the op ran and the provider deterministically refused (bad
        model, auth, quota); the consumer adjusts inputs (§2.9). The CLI's
        human-readable ``result`` text is the message; the status (or
        ``stop_reason``) is the code."""
        api_status = record.get("api_error_status")
        code = (
            str(api_status)
            if api_status is not None
            else str(record.get("stop_reason", "ERROR"))
        )
        message = str(record.get("result") or "claude turn ended with an error")
        return EventError(category="expected", code=code, message=message)

    @staticmethod
    def _partial_event(*, kind, **payload) -> Event:
        """Construct the partial Event decode() returns — real ``kind`` +
        payload, placeholder log coordinates the manager fills on append."""
        return Event(
            offset=_UNASSIGNED_OFFSET,
            key=_UNASSIGNED_KEY,
            turn=_UNASSIGNED_TURN,
            kind=kind,
            **payload,
        )
