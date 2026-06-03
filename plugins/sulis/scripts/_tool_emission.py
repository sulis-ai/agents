"""Authored `tools.jsonld` → Tool entity (foundation domain) — INGEST emitter.

First link in the Scenario-graph emit chain (Tool → Step → Workflow →
Scenario). The ingest pattern is shared across all four (`_instance_ingest`);
this module is the thin Tool-specific binding (`entity_type="tool"`,
`list_key="tools"`). Public names kept stable for the existing Tool tests +
the `sulis-emit-tool` CLI.
"""

from __future__ import annotations

from pathlib import Path

from _entity_repository import EntityRepository
from _instance_ingest import compose_instances, ingest_instances, skipped_instances

_LIST_KEY = "tools"


def compose_tools_from_jsonld(jsonld_text: str, *, source_path: str) -> list[dict]:
    return compose_instances(jsonld_text, list_key=_LIST_KEY)


def skipped_tools(jsonld_text: str) -> list[dict]:
    return skipped_instances(jsonld_text, list_key=_LIST_KEY)


def emit_tools_from_jsonld(source_path: Path, repo: EntityRepository) -> list[dict]:
    return ingest_instances(source_path, repo, entity_type="tool", list_key=_LIST_KEY)
