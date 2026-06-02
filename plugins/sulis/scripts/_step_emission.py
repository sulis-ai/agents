"""Authored `steps.jsonld` → Step entity (foundation) — INGEST emitter (thin).

Delegates to the shared `_instance_ingest` primitive (EP-03). Link 2 in the
Scenario-graph emit chain. Step IS the IDEF0/ICOM box (input_artifacts,
controls, output_artifacts, mechanism/tool_ref).
"""

from __future__ import annotations

from pathlib import Path

from _entity_repository import EntityRepository
from _instance_ingest import compose_instances, ingest_instances, skipped_instances

_LIST_KEY = "steps"


def compose_steps_from_jsonld(jsonld_text: str, *, source_path: str) -> list[dict]:
    return compose_instances(jsonld_text, list_key=_LIST_KEY)


def skipped_steps(jsonld_text: str) -> list[dict]:
    return skipped_instances(jsonld_text, list_key=_LIST_KEY)


def emit_steps_from_jsonld(source_path: Path, repo: EntityRepository) -> list[dict]:
    return ingest_instances(source_path, repo, entity_type="step", list_key=_LIST_KEY)
