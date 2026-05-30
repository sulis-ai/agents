"""Credential entity (foundation, cross-cutting).

CLI-direct emission — typical caller is a script registering a credential
(test fixture creds, CI deploy tokens, OAuth client secrets) under a known
holder Actor. The actual secret value never enters Sulis-code; `token_ref`
is a URI pointing at the platform's Secret Manager (see SPEC-006 sensitive-
field handling). For local-dev today, token_ref is a `secret://...` URI
that signals where the real secret lives — the entity records its
existence, not its value.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ACTOR_ID_RE: Final = re.compile(r"^dna:actor:[0-9A-HJKMNP-TV-Z]{26}$")
_VALID_KINDS: Final[set[str]] = {
    "oauth", "api-key", "service-account", "certificate",
    "password", "mfa-token", "webhook-signing-key", "other",
}
_VALID_STATES: Final[set[str]] = {"active", "expired", "revoked", "rotated"}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_credential(
    *,
    holder: str,
    kind: str,
    token_ref: str,
    state: str = "active",
    issuer: str = "",
    scope: str = "",
    issued_at: str | None = None,
    expires_at: str | None = None,
) -> dict:
    if kind not in _VALID_KINDS:
        raise ValueError(f"credential kind must be one of {sorted(_VALID_KINDS)}; got {kind!r}")
    if state not in _VALID_STATES:
        raise ValueError(f"credential state must be one of {sorted(_VALID_STATES)}; got {state!r}")
    if not _ACTOR_ID_RE.match(holder):
        raise ValueError(f"credential holder must be a valid dna:actor:<ulid>; got {holder!r}")
    if not token_ref or not token_ref.strip():
        raise ValueError("credential token_ref may not be empty")

    cred: dict = {
        "id": "dna:credential:" + _ulid(f"credential:{holder}:{kind}:{scope}:{token_ref}"),
        "holder": holder,
        "kind": kind,
        "token_ref": token_ref,
        "state": state,
        "sys_status": "active",
    }
    if issuer:
        cred["issuer"] = issuer
    if scope:
        cred["scope"] = scope
    if issued_at:
        cred["issued_at"] = issued_at
    if expires_at:
        cred["expires_at"] = expires_at
    return cred


def emit_credential(
    *,
    repo: EntityRepository,
    holder: str,
    kind: str,
    token_ref: str,
    state: str = "active",
    issuer: str = "",
    scope: str = "",
    issued_at: str | None = None,
    expires_at: str | None = None,
) -> dict:
    cred = compose_credential(
        holder=holder, kind=kind, token_ref=token_ref, state=state,
        issuer=issuer, scope=scope, issued_at=issued_at, expires_at=expires_at,
    )
    repo.save("credential", cred)
    return cred
