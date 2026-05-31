"""Deployment entity (PD).

CLI-direct event emission. Records the act of pushing a Release into an
Environment. Required: of_release (dna:release ref), to_environment
(dna:environment ref), at (timestamp), outcome (succeeded/failed/
rolled-back/in-progress). Optional: by_actor (dna:actor ref).

Determinism: ULID from `f"deployment:{of_release}:{to_environment}:{at}"`.
Same release + env + timestamp → same deployment ID (idempotent
re-emission). A retry to the same env at a different timestamp is a new
deployment.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_RELEASE_RE: Final = re.compile(r"^dna:release:[0-9A-HJKMNP-TV-Z]{26}$")
_ENV_RE: Final = re.compile(r"^dna:environment:[0-9A-HJKMNP-TV-Z]{26}$")
_ACTOR_RE: Final = re.compile(r"^dna:actor:[0-9A-HJKMNP-TV-Z]{26}$")
_VALID_OUTCOMES: Final[set[str]] = {
    "succeeded", "failed", "rolled-back", "in-progress",
}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_deployment(
    *,
    of_release: str,
    to_environment: str,
    outcome: str,
    at: str | None = None,
    by_actor: str = "",
) -> dict:
    if not _RELEASE_RE.match(of_release):
        raise ValueError(f"of_release must be a valid dna:release:<ulid>; got {of_release!r}")
    if not _ENV_RE.match(to_environment):
        raise ValueError(f"to_environment must be a valid dna:environment:<ulid>; got {to_environment!r}")
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"deployment outcome must be one of {sorted(_VALID_OUTCOMES)}; got {outcome!r}")
    if by_actor and not _ACTOR_RE.match(by_actor):
        raise ValueError(f"by_actor must be a valid dna:actor:<ulid>; got {by_actor!r}")

    timestamp = at or datetime.now(timezone.utc).isoformat()
    dep: dict = {
        "id": "dna:deployment:" + _ulid(f"deployment:{of_release}:{to_environment}:{timestamp}"),
        "of_release": of_release,
        "to_environment": to_environment,
        "at": timestamp,
        "outcome": outcome,
        "sys_status": "active",
    }
    if by_actor:
        dep["by_actor"] = by_actor
    return dep


def emit_deployment(
    *,
    repo: EntityRepository,
    of_release: str,
    to_environment: str,
    outcome: str,
    at: str | None = None,
    by_actor: str = "",
) -> dict:
    dep = compose_deployment(
        of_release=of_release, to_environment=to_environment,
        outcome=outcome, at=at, by_actor=by_actor,
    )
    repo.save("deployment", dep)
    return dep
