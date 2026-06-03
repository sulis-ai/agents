"""`evolve_entity` — the shared bitemporal-evolution helper (ADR-003).

This is the one place the close-window / open-window / conditional-PROV cycle
lives. When a *living* entity changes, `evolve_entity`:

  1. reads the current open window for ``(entity_type, entity_id)`` via the
     `EntityRepository` port;
  2. closes the prior window (sets ``valid_to``) and opens a new one
     (``valid_from`` == the prior window's ``valid_to`` — the windows abut
     exactly, no gap, no overlap), carrying ``confidence`` + ``sys_status``
     from the new body;
  3. **only when ``generated_by`` is supplied** (prov:Entity types — Product,
     Opportunity) records the PROV ``wasGeneratedBy`` edge to the generating
     LifecycleRun Activity (ADR-001). ``generated_by=None`` (prov:Plan types —
     Project) moves the window but writes NO edge — putting ``wasGeneratedBy``
     on a Plan is a PROV-O type violation (ADR-002, ADR-006);
  4. persists BOTH windows as a single-file history-envelope rewrite, written
     atomically (write-tmp-then-rename) so a committed window survives a crash
     and no instant ever exposes two open windows;
  5. a byte-identical re-emit is a **no-op** (returns ``None``, opens no
     window) — idempotent re-runs do not churn history;
  6. refuses any ``entity_type`` not on the ``_LIVING_ENTITY_TYPES`` allowlist
     — Decision / LifecycleRun are append-only events and MUST NOT evolve.

Two **orthogonal** guards (ADR-003, corrected):

  - ``_LIVING_ENTITY_TYPES`` is the living-vs-events split. It admits all three
    living types (product / opportunity / project); all three get windows.
  - the PROV write is a *separate* conditional, gated by
    ``generated_by is not None``. Product / Opportunity supply a ref and get
    the edge; Project supplies ``None`` and gets none.

This helper sits **above** the `EntityRepository` port (EXPAND-Create, not a
wrap — the domain owns the port): it works unchanged against the repo-local
file adapter or the central Tenant home (ADR-005), with zero adapter-specific
branches. It reuses the port's ``validate`` for reject-on-invalid and the
adapter's instance-path layout for placement.

There is **no ``used`` parameter** — canonical v2.1.0 LifecycleRun has no
``used`` field (DR-013 settled its field-set with content-addressed
``inputs_ref`` / ``outputs_ref``); modelling consumed inputs as ABox
``prov:used`` triples is a separate, later concern. ``wasRevisionOf`` is
written nowhere — version lineage is the bitemporal window chain itself.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

from _entity_repository import EntityRepository


@runtime_checkable
class _FileBackedRepository(EntityRepository, Protocol):
    """An `EntityRepository` that also exposes its on-disk instance path.

    The history-envelope layout (ADR-003) is *file-adapter only* — OAQ-1
    defers the SQLite row-based materialisation with the SQLite swap (ADR-005).
    So the evolve helper needs the on-disk path to write the envelope, but it
    gets it through this narrow public seam (``instance_path``) rather than
    reaching into a concrete adapter's internals — the helper still depends on
    a *protocol*, not on `LocalFileEntityAdapter`. When the SQLite adapter
    lands, it materialises windows as rows behind the same `EntityRepository`
    port and supplies its own evolve materialisation; this file-backed seam is
    not on its path.
    """

    def instance_path(self, entity_type: str, instance_id: str) -> Path:
        """The on-disk path where this entity's envelope is stored."""
        ...


# The living-vs-events allowlist (ADR-003): the single source of truth for
# which entity types may evolve. All three living types get bitemporal windows;
# event entities (Decision, LifecycleRun, …) stay append-only and are refused.
_LIVING_ENTITY_TYPES: Final[frozenset[str]] = frozenset(
    {"product", "opportunity", "project"}
)

# The PROV-O edge key — camelCase, the canonical `prov_constraints` convention
# (NOT a snake_case `was_generated_by` scalar; ADR-002).
_PROV_EDGE_KEY: Final[str] = "wasGeneratedBy"

# Window-level fields the helper manages on each window, on top of the
# schema-validated entity body. These are excluded when comparing two bodies
# for the no-op check (a re-emit that differs only in `valid_from` is still a
# no-op).
_WINDOW_FIELDS: Final[frozenset[str]] = frozenset(
    {"valid_from", "valid_to", _PROV_EDGE_KEY}
)


def evolve_entity(
    *,
    repo: EntityRepository,
    entity_type: str,
    entity_id: str,
    new_fields: dict,
    generated_by: str | None,
    at: str | None = None,
) -> dict | None:
    """Close the prior window, open a new one; persist both atomically.

    Args:
        repo: the `EntityRepository` port — the file adapter (repo-local OR the
            central Tenant home). The helper works unchanged against either.
        entity_type: the living entity type. MUST be in
            ``_LIVING_ENTITY_TYPES`` or the call raises ``ValueError``.
        entity_id: the stable ``dna:{entity_type}:{ulid}`` id whose history
            envelope is being evolved.
        new_fields: the changed attributes for the new window — a complete,
            schema-valid entity body (no PROV edge; the edge is this helper's
            conditional write).
        generated_by: the ``dna:lifecyclerun:<ulid>`` that produced this
            version. When supplied (prov:Entity types — Product, Opportunity),
            the new window records the ``wasGeneratedBy`` edge to it. ``None``
            (prov:Plan types — Project) writes NO edge.
        at: the instant the new window opens (ISO-8601 UTC). Defaults to now.
            The prior window's ``valid_to`` is set to the same instant, so the
            windows abut exactly.

    Returns:
        The new open window (a dict) on a real evolution; ``None`` when the
        emit is a no-op (the new body is byte-identical to the current open
        window's body — idempotent re-runs open no window).

    Raises:
        ValueError: if ``entity_type`` is not on the ``_LIVING_ENTITY_TYPES``
            allowlist (an append-only event entity must never evolve), or if
            ``new_fields`` fails schema validation at the port.
    """
    if entity_type not in _LIVING_ENTITY_TYPES:
        raise ValueError(
            f"{entity_type!r} is not a living entity type; "
            f"only {sorted(_LIVING_ENTITY_TYPES)} may evolve. "
            "Append-only event entities (Decision, LifecycleRun, …) use "
            "`save`, not `evolve_entity`."
        )

    # Reject-on-invalid at the port BEFORE touching history — never persist a
    # window for a body that does not validate. The PROV edge is NOT part of
    # the validated body (the compiled schema is `unevaluatedProperties:
    # false`), so we validate the body alone, then attach the edge to the
    # window below.
    body = dict(new_fields)
    repo.validate(entity_type, body)

    opened_at = at if at is not None else _utc_now()

    envelope = _load_envelope(repo, entity_type, entity_id)
    current = _current_window(envelope)

    # No-op: the new body is byte-identical to the current open window's body
    # (ignoring window-level fields). Idempotent re-runs do not churn history.
    if current is not None and _body_of(current) == _body_of(body):
        return None

    new_window = _open_window(body, opened_at, generated_by)

    if current is not None:
        # Close the prior window at the same instant the new one opens — the
        # two abut exactly (prior valid_to == new valid_from).
        current["valid_to"] = opened_at

    envelope["windows"].append(new_window)
    _persist_envelope(_as_file_backed(repo), entity_type, entity_id, envelope)
    return new_window


def _as_file_backed(repo: EntityRepository) -> _FileBackedRepository:
    """Narrow the port to the file-backed seam the envelope layout needs.

    The history-envelope materialisation is file-adapter only (ADR-003 OAQ-1 —
    the SQLite row-based materialisation is deferred behind the same port). A
    repository that does not expose ``instance_path`` cannot host the envelope;
    that is a wiring error, surfaced plainly rather than as an ``AttributeError``
    deep in the write.
    """
    if not isinstance(repo, _FileBackedRepository):
        raise TypeError(
            f"{type(repo).__name__} does not expose `instance_path`; "
            "the bitemporal history-envelope layout requires a file-backed "
            "EntityRepository (ADR-003 OAQ-1 — SQLite materialisation is "
            "deferred behind the same port)."
        )
    return repo


# ─── window construction ────────────────────────────────────────────────────


def _open_window(body: dict, opened_at: str, generated_by: str | None) -> dict:
    """Build a new open window from a validated body.

    Sets ``valid_from`` (the open instant) and leaves ``valid_to`` unset
    (the window is open). When ``generated_by`` is supplied, records the
    ``wasGeneratedBy`` PROV edge — the single conditional that distinguishes
    prov:Entity (Product/Opportunity) from prov:Plan (Project).
    """
    window = dict(body)
    window["valid_from"] = opened_at
    window["valid_to"] = None
    if generated_by is not None:
        window[_PROV_EDGE_KEY] = generated_by
    return window


def _body_of(window: dict) -> dict:
    """The schema-validated entity body of a window, minus the window-level
    fields the helper manages — the comparison surface for the no-op check."""
    return {k: v for k, v in window.items() if k not in _WINDOW_FIELDS}


def _current_window(envelope: dict) -> dict | None:
    """The current open window (the last with ``valid_to`` unset), or ``None``
    for a never-seen entity."""
    windows = envelope.get("windows", [])
    if not windows:
        return None
    last = windows[-1]
    return last if last.get("valid_to") in (None, "") else None


# ─── history-envelope persistence (above the port) ──────────────────────────


def _load_envelope(repo: EntityRepository, entity_type: str, entity_id: str) -> dict:
    """Read the entity's history envelope, or a fresh empty one.

    The envelope (ADR-003 history layout) is one file per entity holding an
    ordered ``windows`` list. ``find_by_id`` returns it for an already-evolved
    entity; for a never-seen id it returns ``None`` and we start fresh.
    """
    existing = repo.find_by_id(entity_type, entity_id)
    if existing is None:
        return {"id": entity_id, "entity_type": entity_type, "windows": []}
    # Defensive: an envelope must carry a windows list. A bare snapshot (no
    # `windows` key) would be a pre-evolution current-snapshot write; treat it
    # as no history rather than crashing the evolve.
    if "windows" not in existing or not isinstance(existing["windows"], list):
        return {"id": entity_id, "entity_type": entity_type, "windows": []}
    return existing


def _persist_envelope(
    repo: _FileBackedRepository,
    entity_type: str,
    entity_id: str,
    envelope: dict,
) -> None:
    """Write the history envelope atomically (write-tmp-then-rename).

    The envelope is the bitemporal history wrapper — not a single entity
    snapshot — so it bypasses ``repo.save`` (which validates + writes ONE
    schema instance) and writes directly to the adapter's instance path,
    resolved through the public ``instance_path`` seam. The per-window bodies
    were already validated through ``repo.validate`` before they entered the
    envelope. ``os.replace`` makes the swap atomic: a reader sees either the
    prior envelope or the new one, never a torn write, and a crash mid-write
    leaves no half-written file visible.
    """
    path = Path(repo.instance_path(entity_type, entity_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    # `sort_keys=True` + `indent=2` keeps git diffs stable across evolves of
    # the same entity, matching the adapter's own `save` discipline.
    payload = json.dumps(envelope, indent=2, sort_keys=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(payload)
    os.replace(tmp, path)


def _utc_now() -> str:
    """The current instant as an ISO-8601 UTC string (``…Z``)."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
