"""`.sulis/environments/{name}.yaml` → Environment entity (PD).

Source format — `.sulis/environments/{name}.yaml`:

    name: production    # required
    kind: production    # required — enum
    region: eu-west-1   # optional
    retired_at: ...     # optional ISO timestamp
"""

from __future__ import annotations

import hashlib
import yaml
from pathlib import Path
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_VALID_KINDS: Final[set[str]] = {
    "production", "staging", "test", "dev", "preview", "other",
}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_environment_from_yaml(yaml_text: str, *, source_path: str) -> list[dict]:
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []
    name = data.get("name")
    kind = data.get("kind")
    if not isinstance(name, str) or not name.strip():
        return []
    env: dict = {
        "id": "dna:environment:" + _ulid(f"env:{name.strip()}"),
        "name": name.strip(),
        "kind": str(kind) if isinstance(kind, str) else "other",
        "sys_status": "active",
    }
    if isinstance(data.get("region"), str):
        env["region"] = data["region"]
    if isinstance(data.get("retired_at"), str):
        env["retired_at"] = data["retired_at"]
    return [env]


def emit_environment_from_yaml(yaml_path: Path, repo: EntityRepository) -> list[dict]:
    envs = compose_environment_from_yaml(
        Path(yaml_path).read_text(), source_path=str(yaml_path)
    )
    for e in envs:
        repo.save("environment", e)
    return envs
