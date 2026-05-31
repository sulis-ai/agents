"""`.sulis/components/{slug}.yaml` → Component entity (PD).

A Component records one shipped unit of implementation — typically a
package, module, or app within the monorepo. Source format:

    repo: github.com/sulis-ai/agents          # required
    path: plugins/sulis/scripts                # required
    version: 525b79d                           # required (git SHA or SemVer)
    license: MIT                               # required (SPDX id)
    implements:                                # optional
      - dna:design:01ABCD...                   # design refs
      - dna:requirement:01EFGH...              # OR requirement refs (per schema)
    dependencies:                              # optional
      - pkg:pypi/jsonschema@4.21.1             # purl
      - pkg:npm/react@18.2.0

Determinism: ULID derived from `f"component:{repo}:{path}"` — the same
logical component (same repo/path) always resolves to the same ID across
versions. Version moves; identity doesn't.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Final

import yaml

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_IMPL_REF_RE: Final = re.compile(
    r"^dna:(design|requirement):[0-9A-HJKMNP-TV-Z]{26}$"
)


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_component_from_yaml(yaml_text: str, *, source_path: str) -> list[dict]:
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []

    repo = data.get("repo")
    path = data.get("path")
    version = data.get("version")
    license_id = data.get("license")
    if not all(isinstance(x, str) and x.strip() for x in (repo, path, version, license_id)):
        return []

    comp: dict = {
        "id": "dna:component:" + _ulid(f"component:{repo}:{path}"),
        "repo": repo.strip(),
        "path": path.strip(),
        "version": version.strip(),
        "license": license_id.strip(),
        "sys_status": "active",
    }

    implements = data.get("implements")
    if isinstance(implements, list):
        clean = [
            x for x in implements
            if isinstance(x, str) and _IMPL_REF_RE.match(x)
        ]
        if clean:
            comp["implements"] = clean

    deps = data.get("dependencies")
    if isinstance(deps, list):
        clean_deps = [d for d in deps if isinstance(d, str) and d.strip()]
        if clean_deps:
            comp["dependencies"] = clean_deps

    return [comp]


def emit_component_from_yaml(yaml_path: Path, repo: EntityRepository) -> list[dict]:
    comps = compose_component_from_yaml(
        Path(yaml_path).read_text(), source_path=str(yaml_path)
    )
    for c in comps:
        repo.save("component", c)
    return comps
