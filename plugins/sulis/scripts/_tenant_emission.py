"""`.sulis/tenant.yaml` → Tenant-entity transformation + persistence helper.

Third worked entity emission (after Decision + Requirement). The Tenant is
foundation-domain (cross-cutting per L13 promotion); every customer-namespace
of marketplace work is bounded by one Tenant. The marketplace's local entity
store is namespaced by Tenant ID (`~/.sulis/instances/{tenant_id}/...`). That
follow-up slice is now live (ADR-005): `_brain_emit_helper.central_tenant_home`
resolves this home and the living-entity emit (`evolve_entity`) writes there via
the existing `LocalFileEntityAdapter`, read back cross-repo by
`_brain_query.find_current_for_tenant` — reuse, not a new store.

Source format — `.sulis/tenant.yaml`:

```yaml
name: Sulis AI                  # required — used to derive ULID
kind: company                   # required — enum (see schema)
legal_name: Sulis AI Ltd        # optional
jurisdiction: GB-ENG            # optional
state: active                   # optional — defaults to active
```

ID strategy: deterministic Crockford-base32 ULID derived from sha256 of the
tenant name. Same name everywhere produces the same Tenant ID — this is what
makes the cross-repo namespace work (every repo with `.sulis/tenant.yaml`
naming the same tenant resolves to one identity). Override the auto-derived
ULID by setting `id: dna:tenant:...` in the yaml explicitly.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Final

import yaml

from _entity_repository import EntityRepository


_CROCKFORD_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _deterministic_ulid_from(seed: str) -> str:
    """Stable 26-char Crockford-base32 ULID derived from `seed`."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    n = int.from_bytes(digest[:17], "big") & ((1 << 130) - 1)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD_ALPHABET[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))


# Schema id pattern: `dna:tenant:<26 Crockford>`
_TENANT_ID_RE: Final = re.compile(r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$")


def compose_tenant_from_yaml(
    yaml_text: str,
    *,
    source_path: str,
) -> list[dict]:
    """Pure transformation: tenant-yaml text → list of one Tenant entity dict.

    Returns a list of length one (the n=1 / one-per-call shape, represented
    uniformly as a list per the entity-emitter skill convention). Returns
    `[]` if the yaml has no `name` field — i.e. the file isn't a real
    tenant marker.
    """
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return []

    # ID: explicit takes precedence, else deterministic from name.
    if isinstance(data.get("id"), str) and _TENANT_ID_RE.match(data["id"]):
        tenant_id = data["id"]
    else:
        ulid = _deterministic_ulid_from(f"tenant-name:{name.strip()}")
        tenant_id = f"dna:tenant:{ulid}"

    tenant: dict = {
        "id": tenant_id,
        "name": name.strip(),
        "kind": str(data.get("kind", "other")),
        "state": str(data.get("state", "active")),
        "sys_status": "active",
    }
    # Optional fields — only emit when source-provided to keep
    # `unevaluatedProperties:false` clean.
    if isinstance(data.get("legal_name"), str):
        tenant["legal_name"] = data["legal_name"]
    if isinstance(data.get("jurisdiction"), str):
        tenant["jurisdiction"] = data["jurisdiction"]

    return [tenant]


def emit_tenant_from_yaml(
    yaml_path: Path,
    repo: EntityRepository,
) -> list[dict]:
    """Read a `.sulis/tenant.yaml` file and emit its Tenant entity."""
    yaml_text = Path(yaml_path).read_text(encoding="utf-8")
    tenants = compose_tenant_from_yaml(yaml_text, source_path=str(yaml_path))
    for tenant in tenants:
        repo.save("tenant", tenant)
    return tenants
