"""``_session_manager.classifier`` — the provider-neutral recovery vocabulary.

This module owns ``RecoveryClass``, the neutral verdict vocabulary the
reliability layer speaks (ADR-003). The **classifier** (WP-002) produces a
``RecoveryClass`` from an observed :class:`~_session_manager.events.EventError`
plus an optional per-provider hint; the **recovery driver** (WP-005) consumes
it to decide retry / abandon / pause. Pinning the vocabulary here — once,
neutral — keeps the verdict words from being re-spelled on either side of the
seam (CONTRACT_FIRST CF-11).

WP-001 contributes only the vocabulary (the enum). The pure ``classify``
function (WP-002) lives beside it, so the neutral arbiter stays here and
provider-specific knowledge stays behind the provider seam (ADR-003).

**Deliberately dependency-light.** The enum is a pure value type; the
classification mapping references the existing ``events.py`` category
constants — it never redeclares an error code, and it never imports the
provider seam (ADR-003: ``NOT_AUTHORIZED`` already carries login-expiry, and a
provider's raw-code interpretation — Claude's ``"401"`` → login, etc. — lives
in that provider's ``classify_failure`` hint, never in this neutral arbiter).
"""

from __future__ import annotations

from enum import Enum

from _session_manager.events import NOT_AUTHORIZED, EventError


class RecoveryClass(Enum):
    """The neutral recovery verdict the classifier produces (ADR-003).

    Three members, provider-neutral:

    - ``TRANSIENT_BLIP`` — transport wobble; retry with backoff (the
      ``ProtocolError`` posture already documented in ``events.py``).
    - ``DEAD_END`` — a deterministic decline or a bug; retrying just repeats
      it. The safe default for an unrecognised future code.
    - ``LOGIN_EXPIRED`` — auth expired; pause, surface the re-login link,
      resume after re-auth (ADR-004). Maps to the existing ``NOT_AUTHORIZED``
      code — no new code is introduced.
    """

    TRANSIENT_BLIP = "transient_blip"
    DEAD_END = "dead_end"
    LOGIN_EXPIRED = "login_expired"


# ── the neutral category default (ADR-003, contract truth table) ──────────
# Derived from ``category`` alone — no raw-code interpretation. A flat mapping,
# no reflection, no string-keyed dispatch into provider vocabulary. An
# unrecognised future category is impossible (``EventError.category`` is a
# closed ``Literal``), but if one ever arrived it falls through to the safe
# direction (dead-end) via ``.get`` rather than raising — ``classify`` is total.
_CATEGORY_DEFAULT: dict[str, RecoveryClass] = {
    "protocol": RecoveryClass.TRANSIENT_BLIP,  # transport wobble; retry-with-backoff
    "internal": RecoveryClass.DEAD_END,  # a bug; log + escalate, don't retry
    "expected": RecoveryClass.DEAD_END,  # deterministic decline; retry repeats it
}


def classify(error: EventError, adapter_hint: RecoveryClass | None) -> RecoveryClass:
    """Map an observed ``EventError`` to exactly one ``RecoveryClass``.

    Pure and **total**: every ``(category, code, hint)`` triple yields a class
    and the function never raises — an unrecognised future code with no hint
    falls through to the category default (dead-end, the safe direction).

    The policy (ADR-003, contract truth table):

    1. If ``adapter_hint`` is a ``RecoveryClass``, use it — the provider knows
       better (it interpreted its own raw vocabulary in ``classify_failure``).
    2. Otherwise apply the neutral default from ``category`` alone:
       ``protocol`` → ``TRANSIENT_BLIP``; ``internal`` → ``DEAD_END``;
       ``expected`` → ``DEAD_END`` **except** ``NOT_AUTHORIZED`` →
       ``LOGIN_EXPIRED`` (the one ``expected`` code with a neutral login
       meaning, already defined in ``events.py``).

    :param error: the observed failure (the existing ``events.py`` value
        object — referenced, never re-declared).
    :param adapter_hint: the provider's ``classify_failure`` result, or
        ``None`` to defer to the neutral default.
    :returns: the recovery verdict the driver consumes.
    """
    if adapter_hint is not None:
        return adapter_hint
    if error.category == "expected" and error.code == NOT_AUTHORIZED:
        return RecoveryClass.LOGIN_EXPIRED
    return _CATEGORY_DEFAULT.get(error.category, RecoveryClass.DEAD_END)
