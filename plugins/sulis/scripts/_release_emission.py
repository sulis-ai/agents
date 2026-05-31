"""Release entity (PD).

CLI-direct emission. Typical caller: the release-train at the moment of
tag-push. The entity records a versioned, immutable shipped unit —
SemVer version, the components it comprises, an SBOM URI, optionally
shipped_at + changelog.

Determinism: ULID derived from `f"release:{version}"`. Version is the
release's natural key. Once a Release with a given version is emitted,
re-emitting (same version, possibly more components) updates in place.
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_COMPONENT_REF_RE: Final = re.compile(
    r"^dna:component:[0-9A-HJKMNP-TV-Z]{26}$"
)


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_release(
    *,
    version: str,
    comprises: list[str],
    sbom: str,
    changelog: str = "",
    shipped_at: str | None = None,
) -> dict:
    if not version or not version.strip():
        raise ValueError("release version may not be empty")
    if not isinstance(comprises, list) or not comprises:
        raise ValueError("release comprises must be a non-empty list of dna:component:<ulid>")
    bad = [c for c in comprises if not isinstance(c, str) or not _COMPONENT_REF_RE.match(c)]
    if bad:
        raise ValueError(f"release comprises entries must match dna:component:<ulid>; got {bad!r}")
    if not sbom or not sbom.strip():
        raise ValueError("release sbom may not be empty (URI to SPDX or CycloneDX)")

    rel: dict = {
        "id": "dna:release:" + _ulid(f"release:{version.strip()}"),
        "version": version.strip(),
        "comprises": list(comprises),
        "sbom": sbom.strip(),
        "sys_status": "active",
    }
    if changelog:
        rel["changelog"] = changelog
    if shipped_at:
        rel["shipped_at"] = shipped_at
    return rel


def emit_release(
    *,
    repo: EntityRepository,
    version: str,
    comprises: list[str],
    sbom: str,
    changelog: str = "",
    shipped_at: str | None = None,
) -> dict:
    rel = compose_release(
        version=version, comprises=comprises, sbom=sbom,
        changelog=changelog, shipped_at=shipped_at,
    )
    repo.save("release", rel)
    return rel
