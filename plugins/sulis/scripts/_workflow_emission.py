"""Authored `workflow.jsonld` → Workflow entity (foundation) — INGEST emitter.

Delegates to the shared `_instance_ingest` primitive (EP-03). Link 3 in the
Scenario-graph emit chain. A Workflow is the process graph (steps /
initial_steps / terminal_steps / transitions). The authored file uses the
`workflows` envelope key.
"""

from __future__ import annotations

from pathlib import Path

from _entity_repository import EntityRepository
from _instance_ingest import compose_instances, ingest_instances, skipped_instances

_LIST_KEY = "workflows"


def compose_workflows_from_jsonld(jsonld_text: str, *, source_path: str) -> list[dict]:
    return compose_instances(jsonld_text, list_key=_LIST_KEY)


def skipped_workflows(jsonld_text: str) -> list[dict]:
    return skipped_instances(jsonld_text, list_key=_LIST_KEY)


def emit_workflows_from_jsonld(source_path: Path, repo: EntityRepository) -> list[dict]:
    return ingest_instances(source_path, repo, entity_type="workflow", list_key=_LIST_KEY)
