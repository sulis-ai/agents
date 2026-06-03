"""Shared instance-ingest primitive (EP-03 — one pattern, many entities).

Tool / Step / Workflow / Scenario are emitted identically: their authored
`instances/{name}/{plural}.jsonld` entries are ALREADY complete entities
(real ULIDs, full required fields) — unlike the compose-from-foreign-artifact
emitters (`_requirement_emission`, `_decision_emission`). So the emitter is an
**ingest**: parse → keep id-bearing entries → persist (the adapter validates
each against its compiled schema on save, rejecting-without-persisting on
failure). No deterministic-id derivation: the authored ULID IS the identity,
so re-emission is idempotent.

This module owns that pattern once. Each entity's thin `_X_emission.py` and
`sulis-emit-X` parameterise it with `entity_type` + `list_key` (the plural
envelope key the authored file uses, e.g. `tools` / `steps` / `workflows`).

Envelope shapes tolerated:
  - `{"@context": ..., "<list_key>": [ {entity}, ... ]}`   (the authored shape)
  - `{"@graph": [ {entity}, ... ]}`
  - `[ {entity}, ... ]`                                     (a bare list)
  - `{ ...entity... }`                                      (a lone entity, has `id`)
"""

from __future__ import annotations

import json
from pathlib import Path

from _entity_repository import EntityRepository


def entity_entries(data: object, *, list_key: str) -> list[dict]:
    """Pull the entity dicts out of whichever envelope shape was authored."""
    if isinstance(data, list):
        items: object = data
    elif isinstance(data, dict):
        items = data.get(list_key) or data.get("@graph")
        if items is None:
            # a lone entity object (no envelope) counts iff it has an id
            items = [data] if data.get("id") else []
    else:
        items = []
    if not isinstance(items, list):
        return []
    return [e for e in items if isinstance(e, dict)]


def compose_instances(jsonld_text: str, *, list_key: str) -> list[dict]:
    """Authored JSON-LD text → list of id-bearing entity dicts.

    Returns `[]` (never raises) on malformed JSON or an empty/absent list.
    Drops entries without an `id` (an identity-less entry can't be an entity
    and would only fail schema validation downstream) — see `skipped_instances`
    to surface what was dropped.
    """
    try:
        data = json.loads(jsonld_text)
    except (json.JSONDecodeError, ValueError):
        return []
    return [e for e in entity_entries(data, list_key=list_key) if e.get("id")]


def skipped_instances(jsonld_text: str, *, list_key: str) -> list[dict]:
    """The complement of `compose_instances`: entries dropped for lacking an
    `id`. Surfaced by the CLI so a skip is never silent ("no silent
    truncation") — an incomplete stub entry is reported by name."""
    try:
        data = json.loads(jsonld_text)
    except (json.JSONDecodeError, ValueError):
        return []
    return [e for e in entity_entries(data, list_key=list_key) if not e.get("id")]


def ingest_instances(
    source_path: Path,
    repo: EntityRepository,
    *,
    entity_type: str,
    list_key: str,
) -> list[dict]:
    """Read an authored `{list_key}.jsonld` and persist each entity through
    `repo` under `entity_type`. Persists into whatever domain `repo` was
    constructed for. Returns the persisted dicts. Propagates
    `EntityValidationError` from the adapter on a malformed entity (the
    adapter persists nothing in that case)."""
    text = Path(source_path).read_text(encoding="utf-8")
    entities = compose_instances(text, list_key=list_key)
    for entity in entities:
        repo.save(entity_type, entity)
    return entities
