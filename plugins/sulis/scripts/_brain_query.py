"""Brain-graph read seam — typed queries over `.brain/instances/`.

The companion to `EntityRepository` (the write seam). Lifecycle skills,
DoD checkers, dashboards, the cockpit — anything that needs to ask
*"which entities match this predicate?"* — goes through here. Without it,
every consumer reaches into the on-disk JSON-LD layout directly and the
layout becomes a de-facto API surface.

Why a separate module (not extra methods on EntityRepository):

The repository port is per-instance — save, find_by_id, validate. Those
are *one entity at a time*. Queries are *set-shaped* — *"all TestResults
where verifies includes X"* / *"all Designs in state=draft"*. Mixing the
two shapes on one port couples the write-validation discipline to the
read patterns of downstream consumers. Keep them separate; when the
Storage Service substrate (Track 2) lands, it gets a parallel query
adapter that satisfies the same protocol shape this module exposes.

Today, the implementation walks the file tree (`base_dir/{domain}/{entity_type}/*.jsonld`).
N is small (<200 instances per repo at present); a flat-file walk is the
boring choice. When N gets uncomfortable, swap the impl behind the same
function signatures — callers don't move.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Final, Iterator

from _brain_labels import roadmap_sidecar_path


_INSTANCE_FILE_GLOB: Final[str] = "*.jsonld"
_ENTITY_ID_RE: Final = re.compile(r"^dna:[a-z]+:[0-9A-HJKMNP-TV-Z]{26}$")


def iter_entities(
    base_dir: Path,
    *,
    domain: str | None = None,
    entity_type: str | None = None,
) -> Iterator[dict]:
    """Yield every entity instance under `base_dir`, optionally scoped by
    domain and/or entity_type.

    Args:
        base_dir: the `.brain/instances/` root.
        domain: limit to one domain (foundation / product-development /
            insurance-broking). None = walk all domains.
        entity_type: limit to one entity type (decision / requirement /
            testresult / …). None = walk all entity types in scope.

    Yields:
        Each entity instance as a dict (the parsed JSON-LD).

    Performance: file-system walk + JSON parse per file. O(N) where N is
    total instance count. Acceptable for N < ~5000; revisit when that
    ceiling matters.
    """
    base = Path(base_dir)
    if not base.exists():
        return

    domains = [domain] if domain else [p.name for p in base.iterdir() if p.is_dir()]
    for d in domains:
        domain_dir = base / d
        if not domain_dir.exists():
            continue
        types = (
            [entity_type]
            if entity_type
            else [p.name for p in domain_dir.iterdir() if p.is_dir()]
        )
        for t in types:
            type_dir = domain_dir / t
            if not type_dir.exists():
                continue
            for f in sorted(type_dir.glob(_INSTANCE_FILE_GLOB)):
                try:
                    yield json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    # Malformed instance file — skip silently. The write
                    # path validates; corruption at rest means something
                    # else touched the store.
                    continue


def find_entities(
    base_dir: Path,
    *,
    domain: str | None = None,
    entity_type: str | None = None,
    predicate: Callable[[dict], bool] | None = None,
) -> list[dict]:
    """Return all entities matching the given filters.

    Convenience wrapper around `iter_entities` for the common case where
    the caller wants a materialised list.

    Args:
        predicate: optional callable applied to each entity; only entities
            for which the callable returns truthy are included. Use this
            for ad-hoc shape-of-data filtering (the typed predicates below
            cover the common cases).
    """
    out: list[dict] = []
    for inst in iter_entities(base_dir, domain=domain, entity_type=entity_type):
        if predicate is None or predicate(inst):
            out.append(inst)
    return out


# ─── Typed predicates ───────────────────────────────────────────────────
# Common query shapes the DoD-flow needs. Each returns a predicate
# (callable) so they compose cheaply with `find_entities(..., predicate=...)`.


def where_field_equals(field: str, value: object) -> Callable[[dict], bool]:
    """Predicate: entity's `field` value is equal to `value`."""

    def _pred(inst: dict) -> bool:
        return inst.get(field) == value

    return _pred


def where_field_in(field: str, values: set | list) -> Callable[[dict], bool]:
    """Predicate: entity's `field` value is in `values`."""
    value_set = set(values)

    def _pred(inst: dict) -> bool:
        return inst.get(field) in value_set

    return _pred


def where_list_field_contains(field: str, target: object) -> Callable[[dict], bool]:
    """Predicate: entity's `field` is a list and contains `target`.

    Use this for `verifies` (a TestResult verifies a list of Requirements),
    `decisions` (a Design references a list of Decisions), etc.
    """

    def _pred(inst: dict) -> bool:
        v = inst.get(field)
        return isinstance(v, list) and target in v

    return _pred


def where_id_in(ids: set | list) -> Callable[[dict], bool]:
    """Predicate: entity's `id` is in `ids`."""
    id_set = set(ids)

    def _pred(inst: dict) -> bool:
        return inst.get("id") in id_set

    return _pred


# ─── Backlog state sets — the single source (ADR-006) ──────────────────
# The open/done view definitions live here, once, as immutable frozensets.
# The `/sulis:backlog` skill (WP-010) and the Sulis agent body (WP-012) import
# these rather than re-deriving the state→view mapping, so the two FR-07/FR-08
# consumers cannot drift (ADR-006 — "no duplication across the two consumers").
#
# Requirement states (vendored schema enum): draft / approved / implemented /
# verified. Opportunity states: hypothesis / validated / defined / dropped.

_OPEN_REQUIREMENT_STATES: Final[frozenset[str]] = frozenset({"draft"})
_OPEN_OPPORTUNITY_STATES: Final[frozenset[str]] = frozenset({"hypothesis"})
_DONE_REQUIREMENT_STATES: Final[frozenset[str]] = frozenset({"implemented", "verified"})


# ─── Domain-specific high-level queries ────────────────────────────────


def _find_typed(
    base_dir: Path,
    entity_type: str,
    *,
    domain: str,
    state: str | None,
) -> list[dict]:
    """Enumerate one entity type, optionally narrowed to a single `state`.

    Shared shape behind `find_requirements` and `find_opportunities`. When
    `state` is None the type filter is the only predicate (preserving the
    historical `find_requirements` behaviour exactly); otherwise the existing
    `where_field_equals("state", …)` combinator narrows the result.
    """
    predicate = where_field_equals("state", state) if state is not None else None
    return find_entities(
        base_dir, domain=domain, entity_type=entity_type, predicate=predicate
    )


def find_testresults_verifying(
    base_dir: Path,
    requirement_id: str,
    *,
    domain: str = "product-development",
) -> list[dict]:
    """All TestResults whose `verifies` array contains `requirement_id`.

    The load-bearing query for the verification DoD: given a Requirement,
    has anyone written a passing TestResult that claims to verify it?

    Args:
        requirement_id: a full `dna:requirement:<ulid>` string.
    """
    if not _ENTITY_ID_RE.match(requirement_id):
        raise ValueError(
            f"requirement_id must match dna:<type>:<ulid>; got {requirement_id!r}"
        )
    return find_entities(
        base_dir,
        domain=domain,
        entity_type="testresult",
        predicate=where_list_field_contains("verifies", requirement_id),
    )


def find_requirements(
    base_dir: Path,
    *,
    domain: str = "product-development",
    state: str | None = None,
) -> list[dict]:
    """All Requirement entities under `base_dir`, optionally filtered by state.

    Used by the DoD checker: enumerate every Requirement, then for each
    ask whether any TestResult verifies it.

    Args:
        state: optional requirement state to narrow to (`draft` / `approved` /
            `implemented` / `verified`). The default `None` reproduces the
            historical behaviour exactly — every Requirement, unfiltered — so
            existing callers (the DoD verification flow) are unaffected.
    """
    return _find_typed(base_dir, "requirement", domain=domain, state=state)


def find_opportunities(
    base_dir: Path,
    *,
    domain: str = "product-development",
    state: str | None = None,
) -> list[dict]:
    """All Opportunity entities under `base_dir`, optionally filtered by state.

    The sibling to `find_requirements` (ADR-006 — the module had the
    requirement enumerator but not the opportunity one). State filtering uses
    the existing `where_field_equals` combinator; no new traversal primitive.

    Args:
        state: optional opportunity state to narrow to (`hypothesis` /
            `validated` / `defined` / `dropped`). `None` returns every
            Opportunity.
    """
    return _find_typed(base_dir, "opportunity", domain=domain, state=state)


def find_passing_testresults_verifying(
    base_dir: Path,
    requirement_id: str,
    *,
    domain: str = "product-development",
) -> list[dict]:
    """All TestResults verifying `requirement_id` with outcome=pass."""
    return [
        r
        for r in find_testresults_verifying(base_dir, requirement_id, domain=domain)
        if r.get("outcome") == "pass"
    ]


# ─── Roadmap sidecar — the member reader (ADR-001 / FR-07) ───────────────
# The Roadmap flag is a per-repo sidecar label file, NOT a field on the
# entity (the vendored schemas are ``unevaluatedProperties: false``; ADR-001).
# This module is the single read seam (ADR-006). The on-disk shape (filename,
# layout) is defined once in ``_brain_labels`` and shared with the writer
# (``_brain_capture``).


def roadmap_members(base_dir: Path) -> list[str]:
    """Read the Roadmap sidecar → its member entity ids, sorted.

    Reads ``<base_dir>/labels/roadmap.jsonld`` (ADR-001 shape
    ``{"label": "roadmap", "members": [...]}``) and returns the member ids
    sorted (diff-friendly, deterministic).

    Best-effort (NFR-01): if the sidecar is missing OR malformed (not valid
    JSON, or the wrong shape), returns ``[]`` and never raises — the same
    degradation contract as the entity store (`iter_entities` skips corrupt
    files silently).

    Args:
        base_dir: the ``.brain/`` root. The sidecar lives at
            ``base_dir / "labels" / "roadmap.jsonld"``.

    Returns:
        Sorted list of member entity ids; ``[]`` when absent or malformed.
    """
    sidecar = roadmap_sidecar_path(base_dir)
    try:
        data = json.loads(sidecar.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    members = data.get("members", []) if isinstance(data, dict) else []
    if not isinstance(members, list):
        return []
    return sorted(m for m in members if isinstance(m, str))


def find_roadmap(
    base_dir: Path,
    *,
    domain: str = "product-development",
) -> list[dict]:
    """Resolve the Roadmap sidecar's member ids to their entities.

    Reads the member ids via `roadmap_members` (WP-005 — the single sidecar
    reader; this function does NOT re-read the on-disk layout) and resolves
    them to entities via the existing `where_id_in` predicate. No new
    traversal primitive (ADR-006).

    Best-effort (NFR-01): an empty / missing / malformed sidecar yields no
    members, so this returns `[]` and never raises — `roadmap_members`
    already absorbs the malformed case.

    Args:
        base_dir: the `.brain/` root (the sidecar lives under it; the entity
            instances live under `base_dir / "instances"`).
        domain: the domain whose instances the member ids resolve against.

    Returns:
        The roadmap member entities; `[]` when the sidecar is empty / absent /
        malformed.
    """
    member_ids = roadmap_members(base_dir)
    if not member_ids:
        return []
    return find_entities(
        base_dir / "instances",
        domain=domain,
        predicate=where_id_in(member_ids),
    )
