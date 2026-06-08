"""Tests for ``ClaudeAdapter.classify_failure`` + ``ClaudeAdapter.reauth``
(WP-006, ADR-003/004).

This is the **one place** Claude's HTTP-status vocabulary (``"401"`` …) is
interpreted (ADR-003): the adapter maps THIS provider's raw failure code to a
provider-neutral :class:`RecoveryClass`, and the shared classifier never sees a
raw status as a magic string. These tests pin the mapping table and the
re-auth ticket shape, and guard the no-leak invariant.

**Seeds, not live credentials.** ``classify_failure`` operates on the decoded
:class:`EventError` the adapter's ``_error_payload`` already produces — a
``category="expected"`` error whose ``code`` is the raw ``api_error_status``
(``"401"``, ``"429"``, ``"400"`` …) or, for a transport reset, the connection
shape. The recorded 404 fixture
(``tests/fixtures/session_manager/claude/error.jsonl``) is referenced as the
real-shape anchor for the dead-end branch; the auth/quota/reset codes are
synthesised as the same decoded ``EventError`` shape (the CLI's recorded
corpus does not carry an expired credential — that round-trip is the deferred
manual ``live-reauth-resume-claude`` check on the founder machine, TDD §4.3).
The live login itself is **not** performed here; this covers the mapping logic
and that ``reauth()`` returns a well-formed ticket.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from _session_manager.adapter import ProviderAdapter
from _session_manager.adapters.claude import ClaudeAdapter
from _session_manager.classifier import RecoveryClass
from _session_manager.events import EventError
from _session_manager.recovery import ReauthTicket

_FIXTURES = (
    Path(__file__).resolve().parent.parent / "fixtures" / "session_manager" / "claude"
)


def _expected_error(code: str, message: str = "claude declined") -> EventError:
    """Build the decoded ``EventError`` ``classify_failure`` sees for an
    HTTP-status-bearing decline — the exact ``category="expected"`` shape
    ``ClaudeAdapter._error_payload`` produces from a failed ``result`` line."""
    return EventError(category="expected", code=code, message=message)


def _recorded_error_payload() -> EventError:
    """Decode the recorded 404 error fixture into its ``EventError`` — the
    real-shape anchor for the dead-end branch (the corpus's only error turn)."""
    adapter = ClaudeAdapter()
    for raw in _FIXTURES.joinpath("error.jsonl").read_text("utf-8").splitlines():
        if not raw.strip():
            continue
        record = json.loads(raw)
        if record.get("type") == "result" and record.get("is_error") is True:
            event = adapter.decode(raw.encode("utf-8"))
            assert event is not None and event.error is not None
            return event.error
    raise AssertionError("no recorded error result line in error.jsonl")


class TestClassifyFailureMapping:
    """The Claude raw-code → ``RecoveryClass`` detection table (ADR-003)."""

    def test_401_403_maps_login_expired(self) -> None:
        adapter = ClaudeAdapter()
        # 401 (unauthenticated) and 403 (forbidden) are both an expired/declined
        # login for the founder — pause, surface the re-login link, resume.
        assert (
            adapter.classify_failure(_expected_error("401"))
            is RecoveryClass.LOGIN_EXPIRED
        )
        assert (
            adapter.classify_failure(_expected_error("403"))
            is RecoveryClass.LOGIN_EXPIRED
        )

    def test_429_and_reset_maps_transient_blip(self) -> None:
        adapter = ClaudeAdapter()
        # 429 (rate limit) backs off and retries — a transient blip, not a
        # dead-end.
        assert (
            adapter.classify_failure(_expected_error("429"))
            is RecoveryClass.TRANSIENT_BLIP
        )
        # A connection-reset shape (transport wobble) is likewise retryable. It
        # arrives as a protocol-category transport failure (the CLI's stream
        # dropped) rather than an HTTP status — the adapter still recognises it
        # as a blip.
        reset = EventError(
            category="protocol",
            code="SOCKET_CLOSED",
            message="connection reset by peer",
        )
        assert adapter.classify_failure(reset) is RecoveryClass.TRANSIENT_BLIP

    def test_400_and_other_maps_dead_end(self) -> None:
        adapter = ClaudeAdapter()
        # 400 (bad request) is a deterministic decline — retrying repeats it.
        assert (
            adapter.classify_failure(_expected_error("400")) is RecoveryClass.DEAD_END
        )
        # The recorded 404 (model-not-found) turn is the real-shape anchor: an
        # "other deterministic decline" → dead-end.
        assert (
            adapter.classify_failure(_recorded_error_payload())
            is RecoveryClass.DEAD_END
        )
        # An unrecognised future status falls through to the safe direction.
        assert (
            adapter.classify_failure(_expected_error("418")) is RecoveryClass.DEAD_END
        )

    def test_unrecognised_non_expected_defers_to_neutral(self) -> None:
        adapter = ClaudeAdapter()
        # An internal-category failure (a bug) the adapter has no specific
        # detection for must DEFER (return None) — the adapter does not guess
        # outside its own vocabulary; the shared classifier applies the neutral
        # category default (internal → dead-end). Returning None here is the
        # honest "I have no provider-specific hint" signal, distinct from the
        # adapter positively asserting a class.
        internal = EventError(
            category="internal", code="DECODE_FAILED", message="a bug"
        )
        assert adapter.classify_failure(internal) is None


class TestReauth:
    """``reauth()`` produces a well-formed re-auth ticket (ADR-003/004)."""

    def test_reauth_returns_ticket_with_link(self) -> None:
        adapter = ClaudeAdapter()
        ticket = adapter.reauth()
        assert isinstance(ticket, ReauthTicket)
        # The ticket carries the re-login link the notification surfaces …
        assert ticket.relogin_link
        assert isinstance(ticket.relogin_link, str)
        # … and a completion handle the driver waits on before resuming.
        assert ticket.completion_handle
        assert isinstance(ticket.completion_handle, str)


class TestConformanceWithDetection:
    """With the mapping live, ClaudeAdapter still conforms to the
    ``@runtime_checkable`` Protocol — the Codex/Gemini-will-slot-in guarantee
    now answered by a *real* (non-deferring) classify_failure + reauth."""

    def test_claude_adapter_answers_classify_failure_and_reauth(self) -> None:
        adapter = ClaudeAdapter()
        assert isinstance(adapter, ProviderAdapter)
        # classify_failure now returns a real class (not the WP-004 None stub)
        # for a code it recognises …
        assert adapter.classify_failure(_expected_error("401")) is not None
        # … and reauth no longer raises NotImplementedError.
        assert isinstance(adapter.reauth(), ReauthTicket)


class TestNoHttpVocabularyLeak:
    """ADR-003 invariant: Claude's HTTP-status vocabulary appears ONLY in the
    Claude adapter. The shared classifier (and the rest of the shared layer)
    must never carry a ``"401"``-style status as an executable magic string."""

    def test_no_http_status_magic_string_in_shared_layer(self) -> None:
        # The invariant is about *executable* leaks: a status used as a dict
        # key, a comparison operand, etc. Documentary mentions inside
        # docstrings (which explain WHY the vocabulary is quarantined) are not
        # a leak. So parse with ``ast`` and inspect only string *Constant*
        # nodes that are NOT module/class/function docstrings — that is exactly
        # the set of executable string literals.
        statuses = {"401", "403", "429", "400"}
        shared = Path(__file__).resolve().parent.parent.parent / "_session_manager"
        offenders: list[str] = []

        def _docstring_nodes(tree: ast.Module) -> set[int]:
            ids: set[int] = set()
            for node in ast.walk(tree):
                if isinstance(
                    node,
                    (
                        ast.Module,
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                        ast.ClassDef,
                    ),
                ):
                    body = getattr(node, "body", [])
                    if (
                        body
                        and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)
                    ):
                        ids.add(id(body[0].value))
            return ids

        for module in sorted(shared.glob("*.py")):
            tree = ast.parse(module.read_text("utf-8"))
            docstrings = _docstring_nodes(tree)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node.value in statuses
                    and id(node) not in docstrings
                ):
                    offenders.append(f"{module.name}:{node.lineno}: {node.value!r}")

        assert not offenders, (
            "HTTP-status magic strings used as executable literals in the "
            "shared layer (must live only in adapters/claude.py): "
            + "; ".join(offenders)
        )
