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


# ─── As-of-time window read (bitemporal; ADR-003) ──────────────────────


def _window_contains(window: dict, as_of: str) -> bool:
    """Whether `as_of` falls inside this window's half-open interval.

    The interval is ``[valid_from, valid_to)`` — the lower bound is
    **inclusive**, the upper bound **exclusive**. An open window
    (``valid_to`` null or empty) is treated as ``valid_to == +∞``, so any
    `as_of` at or after ``valid_from`` is contained.

    The half-open shape is what makes abutting windows partition time without
    overlap: when window N closes at the same instant window N+1 opens
    (``N.valid_to == N+1.valid_from`` — exactly how ``evolve_entity`` chains
    them), that shared instant belongs to N+1 alone. ISO-8601 UTC timestamps
    are lexicographically ordered, so string comparison is the correct (and
    boring) ordering — no datetime parse needed.
    """
    if as_of < window.get("valid_from", ""):
        return False
    valid_to = window.get("valid_to")
    if not valid_to:
        # Open window (``valid_to`` null or empty) — no upper bound (+∞).
        # ``not valid_to`` covers both sentinels (None and "") and narrows
        # ``valid_to`` to a non-empty string for the comparison below.
        return True
    return as_of < valid_to


def read_as_of(
    *,
    entity_type: str,
    entity_id: str,
    as_of: str,
    base_dir: Path,
) -> dict | None:
    """Return the window whose ``[valid_from, valid_to)`` contains `as_of`.

    The read side of the bitemporal window chain (ADR-003): `evolve_entity`
    writes the history envelope (an ordered ``windows`` list, one file per
    entity id); this answers *"which version was true at `as_of`?"*.

    Half-open interval semantics: ``valid_from <= as_of < valid_to``. An open
    window has ``valid_to == None`` (treated as +∞), so an `as_of` after the
    latest window opens returns that open window. An `as_of` before the first
    window's ``valid_from`` returns ``None`` (the entity did not exist yet).
    The boundary is half-open, so ``as_of == valid_to`` of window N returns
    window N+1, not N — the single source of the boundary rule is
    ``_window_contains``.

    Reuses the existing ``iter_entities`` flat-file walk — no new traversal
    code. The signature carries no ``domain``: the walk spans every domain, so
    a Product/Opportunity (``product-development``) and a Project
    (``foundation``) are found the same way.

    Args:
        entity_type: the living entity type (``product`` / ``opportunity`` /
            ``project``) — selects the per-type subtree of the walk.
        entity_id: the stable ``dna:{entity_type}:{ulid}`` id whose history
            envelope is queried.
        as_of: an ISO-8601 UTC timestamp. Compared lexicographically against
            the window bounds (ISO-8601 UTC sorts correctly as strings).
        base_dir: the ``.brain/instances/`` root — repo-local OR the central
            Tenant home (ADR-005). The same function serves both; the walk is
            identical. A non-existent ``base_dir`` yields no entities → ``None``.

    Returns:
        The matching window dict, or ``None`` when no window contains `as_of`
        (entity unknown, or `as_of` before its first window).
    """
    for envelope in iter_entities(base_dir, entity_type=entity_type):
        if envelope.get("id") != entity_id:
            continue
        windows = envelope.get("windows")
        if not isinstance(windows, list):
            return None
        for window in windows:
            if _window_contains(window, as_of):
                return window
        return None  # envelope found, but no window contains as_of
    return None  # no envelope for this entity id


# ─── Central Tenant home: cross-repo current-version read (ADR-005) ─────


def _current_open_window(envelope: dict) -> dict | None:
    """The current OPEN window of a history envelope, or ``None``.

    The current version is the last window whose ``valid_to`` is unset (an open
    window — ``valid_to`` null or empty, == +∞). This is the read-side mirror of
    the open-window invariant ``evolve_entity`` maintains on the write side: at
    most one window is open at a time, and it is the last one. A bare snapshot
    (no ``windows`` list) yields ``None`` — it has no open-window contract.
    """
    windows = envelope.get("windows")
    if not isinstance(windows, list) or not windows:
        return None
    last = windows[-1]
    return last if last.get("valid_to") in (None, "") else None


def find_current_for_tenant(
    *,
    tenant_id: str,
    entity_type: str,
) -> list[dict]:
    """Every CURRENT (open-window) entity of ``entity_type`` for ``tenant_id``,
    read from the central Tenant home (ADR-005).

    The cross-repo Tenant read: the central home
    (``central_tenant_home(tenant_id)`` == ``~/.sulis/instances/{tenant_id}/``)
    is the single subtree a Tenant's living-entity emits are *designed* to land
    in, so one walk of it returns the Tenant's whole current view across repos —
    something no single repo-local ``.brain/instances`` tree can do.

    Wiring status (ADR-005, reconciled): this central home is *wired-but-not-yet-
    defaulted* for Product/Opportunity — the seam is proven by
    ``test_central_tenant_home.py``, but the production emit CLIs still default
    ``base_dir`` to the repo-local ``.brain/instances`` (nothing invokes them
    yet), so in production the central home is reached only by the minter (the
    Project entity, ADR-006). This read serves whatever a caller has written to
    the home; flipping the Product/Opportunity CLI default is a follow-on slice.

    Built entirely on the EXISTING ``iter_entities`` flat-file walk and the
    open-window invariant — no new traversal code, no new adapter, no new query
    class (the ADR-005 reuse proof is the ABSENCE of new persistence code). The
    same walk serves the repo-local tree and the central home; only the
    ``base_dir`` differs, and here it is resolved from the Tenant id.

    Args:
        tenant_id: the deterministic ``dna:tenant:<ulid>`` whose central home is
            read. The home is resolved via ``central_tenant_home`` (which routes
            through ``sulis_state_base()`` — honouring ``SULIS_STATE_DIR``).
        entity_type: the living entity type to scope to (``product`` /
            ``opportunity`` / ``project``) — selects the per-type subtree.

    Returns:
        One dict per entity that has an OPEN window — the current window body.
        Entities whose latest window is closed (fully evolved past, no open
        window) are excluded. Empty list when the home does not exist yet or
        holds no open windows of ``entity_type``.
    """
    # Validate `tenant_id` against the tenant-ULID shape BEFORE deriving the
    # path: this id is joined into the central-home filesystem path, so an
    # unvalidated value (e.g. one bearing `..`) is a path-traversal seam. The
    # write path validates via schema; the read path must validate here too.
    # Reuse the single source of truth for the shape (`_tenant_emission`'s
    # `_TENANT_ID_RE`) — no second pattern. Imported lazily, mirroring the
    # `central_tenant_home` import below (read-seam → emit-side, no cycle).
    from _tenant_emission import _TENANT_ID_RE

    if not _TENANT_ID_RE.match(tenant_id):
        raise ValueError(
            f"tenant_id must match dna:tenant:<ulid>; got {tenant_id!r}"
        )

    # Imported here (not at module top) to avoid a read-seam → emit-helper import
    # cycle: the home resolver lives with the emit wiring; the read seam consumes
    # it lazily. central_tenant_home is pure path arithmetic — no side effects.
    from _brain_emit_helper import central_tenant_home

    base_dir = central_tenant_home(tenant_id)
    current: list[dict] = []
    for envelope in iter_entities(base_dir, entity_type=entity_type):
        window = _current_open_window(envelope)
        if window is not None:
            current.append(window)
    return current


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


# ─── Scenario-set enumeration + state (journey-rigor #84) ────────────────────
# The journey-walk (design) + scenario-coverage check (plan) need to pull the
# COMPLETE set of scenarios for a journey — to check ALL of them even when only
# some are being built — and to ask each one's verification state. Built on the
# same iter_entities + predicate primitives; no new traversal mechanism.


def find_scenarios_for_journey(
    base_dir: Path,
    journey_workflow_id: str,
    *,
    domain: str = "product-development",
) -> list[dict]:
    """All Scenarios whose `journey` is `journey_workflow_id` (a Workflow id).

    The "all scenarios in THIS journey" enumeration: a journey is a Workflow,
    and each Scenario carries `journey -> dna:workflow:<ulid>`. Group by it to
    get the journey's full scenario set, so the journey-walk / coverage check
    can account for every one even if only some are in the current change.
    """
    if not _ENTITY_ID_RE.match(journey_workflow_id):
        raise ValueError(
            f"journey_workflow_id must match dna:<type>:<ulid>; got {journey_workflow_id!r}"
        )
    return find_entities(
        base_dir,
        domain=domain,
        entity_type="scenario",
        predicate=where_field_equals("journey", journey_workflow_id),
    )


def find_scenarios_verifying(
    base_dir: Path,
    requirement_id: str,
    *,
    domain: str = "product-development",
) -> list[dict]:
    """All Scenarios whose `verifies` array contains `requirement_id`.

    The other grouping key: the scenario set for a change's requirements.
    """
    if not _ENTITY_ID_RE.match(requirement_id):
        raise ValueError(
            f"requirement_id must match dna:<type>:<ulid>; got {requirement_id!r}"
        )
    return find_entities(
        base_dir,
        domain=domain,
        entity_type="scenario",
        predicate=where_list_field_contains("verifies", requirement_id),
    )


def find_passing_testresults_for_scenario(
    base_dir: Path,
    scenario_id: str,
    *,
    domain: str = "product-development",
) -> list[dict]:
    """All passing TestResults back-linked to `scenario_id` (`scenario` field).

    "Is this Scenario currently observed-green?" — the per-scenario state the
    coverage check uses to classify an already-built scenario as still-green
    (vs needing a re-run). Uses the `TestResult.scenario` back-link the
    acceptance run deposits (see `_scenario_evidence`)."""
    if not _ENTITY_ID_RE.match(scenario_id):
        raise ValueError(
            f"scenario_id must match dna:<type>:<ulid>; got {scenario_id!r}"
        )
    return [
        r for r in find_entities(
            base_dir, domain=domain, entity_type="testresult",
            predicate=where_field_equals("scenario", scenario_id),
        )
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
