"""Authored `scenarios.jsonld` → Scenario entity (product-development) — INGEST.

Delegates to the shared `_instance_ingest` primitive (EP-03). Link 4 (final) in
the Scenario-graph emit chain — here every ref (verifies → Requirement[],
exercises → Design, journey → Workflow) resolves to a real entity emitted by
the earlier links. Scenario is a PRODUCT-DEVELOPMENT entity (not foundation),
so the CLI defaults `--domain product-development`.

There is no authored scenarios.jsonld in the repo yet — real instances come
from the `/sulis:specify` intake (the founder authors the verification journey,
drafted from acceptance criteria). This emitter is ready to ingest them.
"""

from __future__ import annotations

from pathlib import Path

from _entity_repository import EntityRepository
from _instance_ingest import compose_instances, ingest_instances, skipped_instances

_LIST_KEY = "scenarios"


def compose_scenarios_from_jsonld(jsonld_text: str, *, source_path: str) -> list[dict]:
    return compose_instances(jsonld_text, list_key=_LIST_KEY)


def skipped_scenarios(jsonld_text: str) -> list[dict]:
    return skipped_instances(jsonld_text, list_key=_LIST_KEY)


def emit_scenarios_from_jsonld(source_path: Path, repo: EntityRepository) -> list[dict]:
    return ingest_instances(source_path, repo, entity_type="scenario", list_key=_LIST_KEY)
