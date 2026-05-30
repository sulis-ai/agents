"""`.sulis/products/{slug}.yaml` → Product-entity transformation.

Fourth worked entity emission. Sits between Tenant (foundation) and
Opportunity (PD spine headwater) — the missing tier the
multi-product/multi-repo discussion surfaced.

Source format — `.sulis/products/{slug}.yaml`:

```yaml
name: Team Todo App                  # required
description: Shared todo for teams   # optional
category: saas                       # optional
state: active                        # optional — defaults to active
launched_at: 2026-01-01              # optional
# belongs_to_tenant: dna:tenant:...  # optional — auto-resolved from sibling .sulis/tenant.yaml
```

Tenant resolution: by default looks for `.sulis/tenant.yaml` in the same
directory as the product yaml's parent (`<product_path>/../tenant.yaml`)
and derives the Tenant ULID from its `name`. Explicit `belongs_to_tenant`
in the product yaml takes precedence.

ID strategy: deterministic Crockford-base32 ULID from
sha256(tenant_name + ":product-name:" + product_name). Same Tenant ×
same Product name → same Product ID, so Opportunity emission can
deterministically reference Products that haven't been emitted yet.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Final

import yaml

from _entity_repository import EntityRepository


_CROCKFORD_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TENANT_ID_RE: Final = re.compile(r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$")


def _deterministic_ulid_from(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    n = int.from_bytes(digest[:17], "big") & ((1 << 130) - 1)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD_ALPHABET[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))


def _tenant_id_from_name(tenant_name: str) -> str:
    """Same derivation _tenant_emission uses — keep in lockstep."""
    return f"dna:tenant:{_deterministic_ulid_from(f'tenant-name:{tenant_name.strip()}')}"


def _resolve_tenant_ref(product_data: dict, product_path: str) -> str | None:
    """Resolve Product.belongs_to_tenant.

    Precedence:
      1. Explicit `belongs_to_tenant` in the product yaml (must match the
         schema pattern; else None to surface a validation failure).
      2. `.sulis/tenant.yaml` in the same `.sulis/` directory (i.e.,
         `<product_path>/../tenant.yaml`). Derive the Tenant ULID from its
         `name`.
      3. None — caller surfaces the gap; entity will fail schema validation
         on `belongs_to_tenant` being required.
    """
    explicit = product_data.get("belongs_to_tenant")
    if isinstance(explicit, str):
        return explicit if _TENANT_ID_RE.match(explicit) else None

    # Walk to .sulis/tenant.yaml as a sibling under the same .sulis/ dir.
    product_p = Path(product_path)
    # Common layouts: .sulis/products/{slug}.yaml → .sulis/tenant.yaml is `../tenant.yaml`
    # Also accept .sulis/tenant.yaml directly co-located if products is flat.
    candidates = [
        product_p.parent.parent / "tenant.yaml",
        product_p.parent / "tenant.yaml",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict):
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return _tenant_id_from_name(name)
    return None


def compose_product_from_yaml(
    yaml_text: str,
    *,
    source_path: str,
) -> list[dict]:
    """Pure transformation: product-yaml text → list of one Product dict.

    Cross-entity ref to Tenant is resolved against the on-disk filesystem
    (sibling `.sulis/tenant.yaml`) — this is the one place the otherwise-pure
    compose function does I/O, in service of cross-entity resolution.
    Returns `[]` on a missing name (file isn't a product marker).
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

    tenant_ref = _resolve_tenant_ref(data, source_path)
    # If tenant_ref is None we still emit — the adapter's validation surfaces
    # the missing-required-ref error with a clear schema message.
    product: dict = {
        "id": "dna:product:" + _deterministic_ulid_from(
            f"product-name:{name.strip()}:tenant:{tenant_ref or 'unbound'}"
        ),
        "name": name.strip(),
        "belongs_to_tenant": tenant_ref or "",
        "state": str(data.get("state", "active")),
        "sys_status": "active",
    }
    if isinstance(data.get("description"), str):
        product["description"] = data["description"]
    if isinstance(data.get("category"), str):
        product["category"] = data["category"]
    if isinstance(data.get("launched_at"), str):
        product["launched_at"] = data["launched_at"]

    return [product]


def emit_product_from_yaml(
    yaml_path: Path,
    repo: EntityRepository,
) -> list[dict]:
    yaml_text = Path(yaml_path).read_text(encoding="utf-8")
    products = compose_product_from_yaml(yaml_text, source_path=str(yaml_path))
    for product in products:
        repo.save("product", product)
    return products
