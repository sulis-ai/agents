"""WP-006 — cross-language grammar conformance (the green-but-broken guard).

TDD §2 (cross-language seam) / §4. The `SULIS_ORIGIN` env-var grammar is the
ONE contract that bridges the two languages: the TypeScript chat relay *emits*
the bare trailer body and the Python `prepare-commit-msg` hook *parses* it via
`_origin_stamp.parse_origin_env`. If either side drifts the grammar, an assisted
(or autonomous) commit silently fails to stamp and origin degrades to inferred —
green tests on each side, broken seam between them.

This test locks the seam from the Python side: it takes the EXACT strings the TS
side emits — golden fixtures sourced byte-for-byte from the TS producers, NOT
mocks of the grammar — and asserts `parse_origin_env` accepts them and recovers
the same fields (kind / conversation / **integer** turn; kind / run /
confidence). It also re-asserts #216's boundary guard (a control-char-bearing or
malformed body → None) so the conformance fixtures cannot loosen the parser.

Provenance of the golden strings (must stay byte-identical to the TS emitters):

  - **assisted** — `apps/cockpit/server/lib/relayOrigin.ts` emits
        `assisted; conversation=${thread.threadId}; turn=${thread.turn}`
    where `threadId` carries the `thread_<stem>` shape (ADR-016 / WP-003's
    `deriveThreadId`) and `turn` is the 1-based Message ordinal (an integer).
  - **autonomous** — `_origin_stamp.autonomous_env` emits the bare body of
        `autonomous; run=<ulid>[; confidence=<0..1>]`
    (WP-005). Asserted here against the SAME builder the executor uses, so the
    autonomous side of the seam round-trips too.

Consume #216 unchanged: this WP adds NO production code. It pins that the grammar
the TS side emits is exactly the grammar the Python side already accepts.
"""

from __future__ import annotations

import pytest

from _origin_stamp import (  # noqa: E402  (sys.path set up by conftest)
    autonomous_env,
    parse_origin_env,
)

# ─── golden fixtures: the EXACT bodies the TypeScript relay emits ───────────
#
# These mirror `relayOrigin.ts`'s template literal byte-for-byte. They are the
# canonical TS-emitted output, sourced from the producer's format — not a mock
# of the grammar. If the TS side changes its template (e.g. drops a space, or
# renames `conversation`/`turn`), these strings stop matching what production
# emits and the conformance intent is to catch that drift via this fixture +
# the matching TS-side test in `relayOrigin.test.ts`.

# A `thread_`-shaped Thread id (ADR-016) + a 1-based Message ordinal.
_THREAD_ID = "thread_abc123-session-id"
_ASSISTED_BODY = f"assisted; conversation={_THREAD_ID}; turn=3"

# A run-only autonomous body and one carrying confidence.
_RUN_ULID = "01KT500K2JTE2EGW6TPPQ4D4VN"
_AUTONOMOUS_BODY = f"autonomous; run={_RUN_ULID}"
_AUTONOMOUS_BODY_CONFIDENCE = f"autonomous; run={_RUN_ULID}; confidence=0.8"


# ─── assisted: TS-emitted body round-trips through the Python parser ────────


def test_assisted_ts_body_round_trips_through_python_parser():
    """The exact string `relayOrigin.ts` emits parses back to the assisted
    origin with the SAME conversation (the `thread_` id) and turn fields."""
    parsed = parse_origin_env(_ASSISTED_BODY)
    assert parsed == {
        "kind": "assisted",
        "conversation": _THREAD_ID,
        "turn": 3,
    }


def test_assisted_turn_is_an_integer_not_a_string():
    """The `turn=<n>` slot is integer-typed on both language sides (ADR-016);
    the Python parser must recover an `int`, not the string `'3'`."""
    parsed = parse_origin_env(_ASSISTED_BODY)
    assert parsed is not None
    assert isinstance(parsed["turn"], int)
    assert not isinstance(parsed["turn"], bool)  # bool is an int subclass


def test_assisted_conversation_carries_the_thread_shape_verbatim():
    """The `thread_`-shaped Thread id passes through the parser unmodified —
    no truncation, no re-encoding. The relay emits it AS-IS (no second
    sanitiser; #216's parser is the one boundary guard)."""
    parsed = parse_origin_env(_ASSISTED_BODY)
    assert parsed is not None
    assert parsed["conversation"] == _THREAD_ID
    assert parsed["conversation"].startswith("thread_")


def test_assisted_turn_one_round_trips():
    """A fresh thread's first turn (`turn=1`, no existing messages) — the
    boundary value the relay emits when `existing-turns == 0`."""
    body = f"assisted; conversation={_THREAD_ID}; turn=1"
    parsed = parse_origin_env(body)
    assert parsed == {"kind": "assisted", "conversation": _THREAD_ID, "turn": 1}


# ─── autonomous: the executor's own builder round-trips ─────────────────────


def test_autonomous_ts_body_round_trips_through_python_parser():
    """The canonical autonomous body (run-only) parses back to the autonomous
    origin. Sourced as a literal string to mirror the cross-language fixture
    style; equality with the builder's output is asserted separately below."""
    parsed = parse_origin_env(_AUTONOMOUS_BODY)
    assert parsed == {"kind": "autonomous", "run": _RUN_ULID}


def test_autonomous_body_with_confidence_round_trips():
    """The autonomous body carrying a confidence scalar round-trips, with
    confidence recovered as a float."""
    parsed = parse_origin_env(_AUTONOMOUS_BODY_CONFIDENCE)
    assert parsed == {
        "kind": "autonomous",
        "run": _RUN_ULID,
        "confidence": 0.8,
    }


def test_autonomous_builder_output_matches_the_golden_body():
    """The autonomous side of the seam is produced by `autonomous_env`
    (WP-005) — assert its emitted body is byte-identical to the golden fixture,
    so the fixture cannot drift from the real executor producer."""
    env = autonomous_env(run=_RUN_ULID, confidence=None)
    assert env["SULIS_ORIGIN"] == _AUTONOMOUS_BODY
    # And the producer's own output round-trips through the parser.
    assert parse_origin_env(env["SULIS_ORIGIN"]) == {
        "kind": "autonomous",
        "run": _RUN_ULID,
    }


# ─── full-trailer-line form is accepted too (the env may carry either) ──────


def test_assisted_full_trailer_line_form_round_trips():
    """`parse_origin_env` accepts both the bare body and a full trailer line
    (`Sulis-Origin: assisted; …`). The seam must tolerate either, since the
    env can carry either form."""
    full_line = f"Sulis-Origin: {_ASSISTED_BODY}"
    parsed = parse_origin_env(full_line)
    assert parsed == {
        "kind": "assisted",
        "conversation": _THREAD_ID,
        "turn": 3,
    }


# ─── boundary guard intact: malformed / injection input → None ─────────────


def test_control_char_in_assisted_body_returns_none():
    """A control character anywhere in the body (an embedded newline + forged
    trailer line) is rejected — the whole value is treated as malformed and
    `parse_origin_env` returns None (#216's trailer-injection guard). The
    conformance fixtures must not loosen this."""
    injected = f"assisted; conversation={_THREAD_ID}; turn=3\nForged-Trailer: malicious"
    assert parse_origin_env(injected) is None


@pytest.mark.parametrize(
    "malformed",
    [
        "",  # empty → None
        "   ",  # whitespace-only → None
        "assisted; turn=3",  # assisted with no conversation → None
        "autonomous; confidence=0.8",  # autonomous with no run → None
        "garbage; foo=bar",  # unknown kind → None
    ],
)
def test_malformed_bodies_return_none(malformed):
    """Bodies that don't satisfy the grammar return None (the graceful
    'unstamped' path) rather than a partial/invalid origin dict."""
    assert parse_origin_env(malformed) is None
