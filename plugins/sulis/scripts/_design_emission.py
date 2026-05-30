"""TDD.md → Design entity (PD).

A Design records how a TDD satisfies one or more Requirements. Source is
`.architecture/{project}/TDD.md` (the technical design document). The
emitter:

  1. Reads the TDD body to detect referenced Requirement IDs (the SRD's
     `FR-NN` / `NFR-NN` style markers — looked up via the same hashing
     contract Requirement-emission uses, so a TDD that names `FR-001` for
     a known SRD produces the entity-graph reference to the actual
     Requirement entity).
  2. Reads optional ADRs alongside TDD.md (`adrs/ADR-NNN-*.md`) and emits
     the parallel `decisions: [dna:decision:<ulid>]` array — IDs derived
     deterministically the same way `_decision_emission.py` does.

Determinism contracts:
  - Design ULID derived from `f"design-from-tdd:{tdd_path}"`. Re-emitting
    the same TDD always produces the same Design ID.
  - Requirement refs match the same seed Requirement-emission uses:
    `f"req:{srd_path}:{fr_id}"`. The SRD path is inferred from the TDD's
    sibling structure (`.architecture/{project}/TDD.md` →
    `.specifications/{project}/SRD.md`) or supplied explicitly.
  - Decision refs match the same seed Decision-emission uses (one Decision
    per ADR file path).

State defaults to `draft`. The author can promote to `reviewed` /
`accepted` by passing `--state` to the CLI.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_FR_REF_RE: Final = re.compile(r"\b((?:FR|NFR)-\d+(?:\.\d+)?)\b")
_VALID_STATES: Final[set[str]] = {"draft", "reviewed", "accepted"}
_VALID_VIEWS: Final[set[str]] = {"context", "container", "component", "deployment"}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def _infer_srd_path(tdd_path: Path) -> Path | None:
    """`.architecture/{project}/TDD.md` → `.specifications/{project}/SRD.md`."""
    parts = tdd_path.resolve().parts
    try:
        arch_idx = parts.index(".architecture")
    except ValueError:
        return None
    if arch_idx + 1 >= len(parts):
        return None
    project = parts[arch_idx + 1]
    repo_root = Path(*parts[:arch_idx])
    candidate = repo_root / ".specifications" / project / "SRD.md"
    return candidate if candidate.exists() else None


def _collect_requirement_refs(tdd_text: str, srd_path: Path | None) -> list[str]:
    if not srd_path:
        return []
    fr_ids = sorted(set(_FR_REF_RE.findall(tdd_text)))
    return [
        f"dna:requirement:{_ulid(f'req:{srd_path}:{fr_id}')}"
        for fr_id in fr_ids
    ]


def _collect_decision_refs(tdd_path: Path) -> list[str]:
    adrs_dir = tdd_path.parent / "adrs"
    if not adrs_dir.exists():
        return []
    refs: list[str] = []
    for adr in sorted(adrs_dir.glob("ADR-*.md")):
        refs.append(f"dna:decision:{_ulid(f'decision:{adr}')}")
    return refs


def compose_design_from_tdd(
    tdd_text: str,
    *,
    tdd_path: Path,
    srd_path: Path | None = None,
    state: str = "draft",
    views: list[str] | None = None,
    interface_contracts: list[str] | None = None,
) -> list[dict]:
    if state not in _VALID_STATES:
        raise ValueError(f"design state must be one of {sorted(_VALID_STATES)}; got {state!r}")
    if views:
        bad = [v for v in views if v not in _VALID_VIEWS]
        if bad:
            raise ValueError(f"design views must be subset of {sorted(_VALID_VIEWS)}; got {bad!r}")

    resolved_srd = srd_path or _infer_srd_path(tdd_path)
    requirement_refs = _collect_requirement_refs(tdd_text, resolved_srd)
    if not requirement_refs:
        return []  # no SRD or no FR markers found; skip silently

    design: dict = {
        "id": "dna:design:" + _ulid(f"design-from-tdd:{tdd_path}"),
        "satisfies": requirement_refs,
        "state": state,
        "sys_status": "active",
    }
    decision_refs = _collect_decision_refs(tdd_path)
    if decision_refs:
        design["decisions"] = decision_refs
    if views:
        design["views"] = views
    if interface_contracts:
        design["interface_contracts"] = interface_contracts
    return [design]


def emit_design_from_tdd(
    tdd_path: Path,
    repo: EntityRepository,
    *,
    srd_path: Path | None = None,
    state: str = "draft",
    views: list[str] | None = None,
    interface_contracts: list[str] | None = None,
) -> list[dict]:
    designs = compose_design_from_tdd(
        Path(tdd_path).read_text(),
        tdd_path=Path(tdd_path),
        srd_path=srd_path,
        state=state,
        views=views,
        interface_contracts=interface_contracts,
    )
    for d in designs:
        repo.save("design", d)
    return designs
