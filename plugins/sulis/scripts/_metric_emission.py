"""Metric entity (PD).

CLI-direct observation emission. Records a measured outcome — delivery
health (DORA, SPACE) or product outcome. Required: kind (DORA / SPACE /
product), measures (dna:release or dna:opportunity ref), value (number),
observed_at (timestamp). Optional: window (ISO-8601 duration like P7D).

Determinism: ULID from `f"metric:{kind}:{measures}:{observed_at}:{window}"`.
The same observation at the same moment is the same record.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_MEASURES_RE: Final = re.compile(
    r"^dna:(release|opportunity):[0-9A-HJKMNP-TV-Z]{26}$"
)
_DURATION_RE: Final = re.compile(
    r"^-?P(?=.)((\d+)Y)?((\d+)M)?((\d+)D)?(T(?=.)((\d+)H)?((\d+)M)?((\d+(\.\d+)?)S)?)?$"
)
_VALID_KINDS: Final[set[str]] = {"DORA", "SPACE", "product"}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_metric(
    *,
    kind: str,
    measures: str,
    value: float,
    observed_at: str | None = None,
    window: str = "",
) -> dict:
    if kind not in _VALID_KINDS:
        raise ValueError(f"metric kind must be one of {sorted(_VALID_KINDS)}; got {kind!r}")
    if not _MEASURES_RE.match(measures):
        raise ValueError(f"metric measures must be a dna:release|opportunity ref; got {measures!r}")
    if window and not _DURATION_RE.match(window):
        raise ValueError(f"metric window must be ISO-8601 duration (e.g. P7D); got {window!r}")

    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    m: dict = {
        "id": "dna:metric:" + _ulid(f"metric:{kind}:{measures}:{timestamp}:{window}"),
        "kind": kind,
        "measures": measures,
        "value": value,
        "observed_at": timestamp,
        "sys_status": "active",
    }
    if window:
        m["window"] = window
    return m


def emit_metric(
    *,
    repo: EntityRepository,
    kind: str,
    measures: str,
    value: float,
    observed_at: str | None = None,
    window: str = "",
) -> dict:
    m = compose_metric(
        kind=kind, measures=measures, value=value,
        observed_at=observed_at, window=window,
    )
    repo.save("metric", m)
    return m
