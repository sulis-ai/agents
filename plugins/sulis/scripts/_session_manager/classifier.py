"""``_session_manager.classifier`` — the provider-neutral recovery vocabulary.

This module owns ``RecoveryClass``, the neutral verdict vocabulary the
reliability layer speaks (ADR-003). The **classifier** (WP-002) produces a
``RecoveryClass`` from an observed :class:`~_session_manager.events.EventError`
plus an optional per-provider hint; the **recovery driver** (WP-005) consumes
it to decide retry / abandon / pause. Pinning the vocabulary here — once,
neutral — keeps the verdict words from being re-spelled on either side of the
seam (CONTRACT_FIRST CF-11).

WP-001 contributes only the vocabulary (the enum). The pure ``classify``
function that maps ``EventError`` → ``RecoveryClass`` arrives with WP-002; it
will live beside this enum so provider knowledge stays in the adapter
(ADR-003) and the neutral arbiter stays here.

**Deliberately dependency-light.** The enum is a pure value type; the
classification mapping (WP-002) will reference the existing ``events.py``
category + code constants — it never redeclares an error code (ADR-003:
``NOT_AUTHORIZED`` already carries login-expiry).
"""

from __future__ import annotations

from enum import Enum


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
