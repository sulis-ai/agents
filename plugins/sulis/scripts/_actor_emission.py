"""`.sulis/actors/{slug}.yaml` → Actor entity (foundation, cross-cutting).

Resolves `belongs_to_tenant` from sibling `.sulis/tenant.yaml`. Deterministic
ID from sha256(name + ":" + tenant_ref) so the same actor is the same actor
across repos.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Final

import yaml

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TENANT_ID_RE: Final = re.compile(r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$")


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def _resolve_tenant_ref(data: dict, source_path: str) -> str | None:
    explicit = data.get("belongs_to_tenant")
    if isinstance(explicit, str):
        return explicit if _TENANT_ID_RE.match(explicit) else None
    p = Path(source_path)
    for candidate in (p.parent.parent / "tenant.yaml", p.parent / "tenant.yaml"):
        if candidate.exists():
            try:
                t = yaml.safe_load(candidate.read_text())
            except yaml.YAMLError:
                continue
            if isinstance(t, dict) and isinstance(t.get("name"), str):
                tenant_name = t["name"].strip()
                return f"dna:tenant:{_ulid(f'tenant-name:{tenant_name}')}"
    return None


def compose_actor_from_yaml(yaml_text: str, *, source_path: str) -> list[dict]:
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []
    name = data.get("name")
    kind = data.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        return []
    tenant_ref = _resolve_tenant_ref(data, source_path)
    actor: dict = {
        "id": "dna:actor:" + _ulid(f"actor:{name or 'unnamed'}:{tenant_ref or 'unbound'}"),
        "kind": kind,
        "belongs_to_tenant": tenant_ref or "",
        "sys_status": "active",
    }
    if isinstance(name, str) and name.strip():
        actor["name"] = name.strip()
    return [actor]


def emit_actor_from_yaml(yaml_path: Path, repo: EntityRepository) -> list[dict]:
    actors = compose_actor_from_yaml(
        Path(yaml_path).read_text(), source_path=str(yaml_path)
    )
    for a in actors:
        repo.save("actor", a)
    return actors
