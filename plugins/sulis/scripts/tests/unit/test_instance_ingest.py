"""Tests for the shared instance-ingest primitive.

Tool / Step / Workflow / Scenario are all emitted the SAME way: their authored
`instances/{name}/{plural}.jsonld` entries are already complete entities, so
the emitter parses → keeps id-bearing entries → persists. Rather than four
copy-paste emitters (EP-03), that pattern lives here once, parameterised by
`entity_type` + `list_key`.
"""

from __future__ import annotations

import json
from pathlib import Path

from _instance_ingest import (
    compose_instances,
    entity_entries,
    ingest_instances,
    skipped_instances,
)


def _ent(ulid: str, **extra: object) -> dict:
    return {"id": f"dna:tool:{ulid}", "name": ulid, **extra}


class _FakeRepo:
    """Captures save calls; entity-type-agnostic (the primitive under test is)."""

    def __init__(self) -> None:
        self.saved: list[tuple[str, dict]] = []

    def save(self, entity_type: str, instance: dict) -> None:
        self.saved.append((entity_type, instance))

    def find_by_id(self, entity_type: str, instance_id: str):  # unused here
        return None


class TestEntityEntries:
    def test_plural_list_key(self) -> None:
        data = {"steps": [_ent("A"), _ent("B")]}
        assert len(entity_entries(data, list_key="steps")) == 2

    def test_graph_fallback(self) -> None:
        data = {"@graph": [_ent("A")]}
        assert len(entity_entries(data, list_key="steps")) == 1

    def test_bare_list(self) -> None:
        assert len(entity_entries([_ent("A")], list_key="steps")) == 1

    def test_single_object_with_id(self) -> None:
        # a lone entity (no envelope) is treated as a one-item list
        assert len(entity_entries(_ent("A"), list_key="workflows")) == 1

    def test_single_object_without_id_is_not_an_entity(self) -> None:
        assert entity_entries({"name": "no-id"}, list_key="workflows") == []

    def test_ignores_non_dict_items(self) -> None:
        assert entity_entries({"steps": [_ent("A"), "junk", 7]}, list_key="steps") == [_ent("A")]


class TestComposeAndSkip:
    def test_compose_keeps_id_bearing(self) -> None:
        text = json.dumps({"tools": [_ent("A"), {"name": "stub"}]})
        out = compose_instances(text, list_key="tools")
        assert [e["id"] for e in out] == ["dna:tool:A"]

    def test_skipped_returns_idless(self) -> None:
        text = json.dumps({"tools": [_ent("A"), {"name": "stub"}]})
        assert [e["name"] for e in skipped_instances(text, list_key="tools")] == ["stub"]

    def test_malformed_json_returns_empty_not_raise(self) -> None:
        assert compose_instances("not json", list_key="tools") == []
        assert skipped_instances("not json", list_key="tools") == []


class TestIngest:
    def test_persists_each_under_entity_type(self, tmp_path: Path) -> None:
        src = tmp_path / "steps.jsonld"
        src.write_text(json.dumps({"steps": [_ent("A"), _ent("B")]}))
        repo = _FakeRepo()
        out = ingest_instances(src, repo, entity_type="step", list_key="steps")
        assert len(out) == 2
        assert [t for (t, _) in repo.saved] == ["step", "step"]
