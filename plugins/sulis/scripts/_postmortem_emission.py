"""PostMortem entity (PD).

CLI-direct emission. Records the structured record of an Incident —
findings + corrective actions. Required: for_incident (dna:incident ref),
findings (free-text summary), blameless (boolean). Optional: actions
(list of dna:requirement or dna:opportunity refs representing the
corrective work).

Determinism: ULID from `f"postmortem:{for_incident}"`. One incident → one
postmortem. Re-emitting with new findings / actions updates in place.
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_INCIDENT_RE: Final = re.compile(r"^dna:incident:[0-9A-HJKMNP-TV-Z]{26}$")
_ACTION_RE: Final = re.compile(
    r"^dna:(requirement|opportunity):[0-9A-HJKMNP-TV-Z]{26}$"
)


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_postmortem(
    *,
    for_incident: str,
    findings: str,
    blameless: bool = True,
    actions: list[str] | None = None,
) -> dict:
    if not _INCIDENT_RE.match(for_incident):
        raise ValueError(f"for_incident must be a dna:incident:<ulid>; got {for_incident!r}")
    if not findings or not findings.strip():
        raise ValueError("postmortem findings may not be empty")
    if actions:
        bad = [a for a in actions if not isinstance(a, str) or not _ACTION_RE.match(a)]
        if bad:
            raise ValueError(f"postmortem actions must be dna:requirement|opportunity refs; got {bad!r}")

    pm: dict = {
        "id": "dna:postmortem:" + _ulid(f"postmortem:{for_incident}"),
        "for_incident": for_incident,
        "findings": findings.strip(),
        "blameless": bool(blameless),
        "sys_status": "active",
    }
    if actions:
        pm["actions"] = list(actions)
    return pm


def emit_postmortem(
    *,
    repo: EntityRepository,
    for_incident: str,
    findings: str,
    blameless: bool = True,
    actions: list[str] | None = None,
) -> dict:
    pm = compose_postmortem(
        for_incident=for_incident, findings=findings,
        blameless=blameless, actions=actions,
    )
    repo.save("postmortem", pm)
    return pm
