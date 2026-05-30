"""Incident entity (PD).

CLI-direct event emission. Records an unplanned operational disruption.
Required: severity (sev1/sev2/sev3), detected_at (timestamp). Optional:
resolved_at, mttr (ISO-8601 duration).

Determinism: ULID from `f"incident:{severity}:{detected_at}"`. Two
detections at the same instant at the same severity are the same
incident — a resolved_at update lands on the same record (the typical
lifecycle: emit at detection, re-emit with resolved_at + mttr at close).
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_DURATION_RE: Final = re.compile(
    r"^-?P(?=.)((\d+)Y)?((\d+)M)?((\d+)D)?(T(?=.)((\d+)H)?((\d+)M)?((\d+(\.\d+)?)S)?)?$"
)
_VALID_SEVERITIES: Final[set[str]] = {"sev1", "sev2", "sev3"}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_incident(
    *,
    severity: str,
    detected_at: str | None = None,
    resolved_at: str = "",
    mttr: str = "",
) -> dict:
    if severity not in _VALID_SEVERITIES:
        raise ValueError(f"incident severity must be one of {sorted(_VALID_SEVERITIES)}; got {severity!r}")
    if mttr and not _DURATION_RE.match(mttr):
        raise ValueError(f"incident mttr must be ISO-8601 duration (e.g. PT45M); got {mttr!r}")

    timestamp = detected_at or datetime.now(timezone.utc).isoformat()
    inc: dict = {
        "id": "dna:incident:" + _ulid(f"incident:{severity}:{timestamp}"),
        "severity": severity,
        "detected_at": timestamp,
        "sys_status": "active",
    }
    if resolved_at:
        inc["resolved_at"] = resolved_at
    if mttr:
        inc["mttr"] = mttr
    return inc


def emit_incident(
    *,
    repo: EntityRepository,
    severity: str,
    detected_at: str | None = None,
    resolved_at: str = "",
    mttr: str = "",
) -> dict:
    inc = compose_incident(
        severity=severity, detected_at=detected_at,
        resolved_at=resolved_at, mttr=mttr,
    )
    repo.save("incident", inc)
    return inc
