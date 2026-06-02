"""Tests for the Tool emitter (foundation domain).

Tool is the first link in the Scenario-graph emit chain
(Tool → Step → Workflow → Scenario). Unlike the compose-from-foreign-artifact
emitters (Requirement-from-SRD), Tool is an **ingest**: the authored
`instances/{name}/tools.jsonld` entries are already complete Tool entities
carrying real ULIDs; the emitter parses, validates, and persists them into the
brain store under the `foundation` domain.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _tool_emission import (
    compose_tools_from_jsonld,
    emit_tools_from_jsonld,
    skipped_tools,
)


def _tool(ulid: str, name: str) -> dict:
    """A minimal valid Tool entity (matches the foundation tool.schema.json
    required set), modelled on the real discover-project tools.jsonld shape."""
    return {
        "id": f"dna:tool:{ulid}",
        "name": name,
        "for_domain": "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM",
        "kind": "query",
        "inputs_schema_ref": "schemas/tools/x-input.schema.json",
        "outputs_schema_ref": "schemas/tools/x-output.schema.json",
        "implementation_kind": "subprocess",
        "version": "1.0.0",
        "state": "active",
        "sys_status": "active",
    }


_T1 = _tool("01KT1WT101G1TREM0TEREAD000", "git-remote-read")
_T2 = _tool("01KT1WT102RDPKGJS0N000000A", "read-package-json")


class TestComposeIngest:
    def test_reads_tools_key(self) -> None:
        text = json.dumps({"@context": "x", "@type": "ToolSet", "tools": [_T1, _T2]})
        out = compose_tools_from_jsonld(text, source_path="tools.jsonld")
        assert [t["name"] for t in out] == ["git-remote-read", "read-package-json"]

    def test_tolerates_bare_list(self) -> None:
        out = compose_tools_from_jsonld(json.dumps([_T1]), source_path="x")
        assert len(out) == 1 and out[0]["id"] == _T1["id"]

    def test_tolerates_graph_key(self) -> None:
        out = compose_tools_from_jsonld(json.dumps({"@graph": [_T1]}), source_path="x")
        assert len(out) == 1

    def test_empty_or_malformed_returns_empty_not_raise(self) -> None:
        assert compose_tools_from_jsonld("not json", source_path="x") == []
        assert compose_tools_from_jsonld(json.dumps({"tools": []}), source_path="x") == []

    def test_drops_entries_without_id(self) -> None:
        bad = {"name": "no-id"}
        out = compose_tools_from_jsonld(json.dumps({"tools": [_T1, bad]}), source_path="x")
        assert [t["id"] for t in out] == [_T1["id"]]

    def test_skipped_tools_reports_idless_stubs(self) -> None:
        # "no silent truncation" — id-less stub entries are surfaced, not dropped quietly
        text = json.dumps({"tools": [_T1, {"name": "drift-detector", "kind": None}]})
        assert [s["name"] for s in skipped_tools(text)] == ["drift-detector"]
        assert skipped_tools("not json") == []


class TestEmitPersists:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="foundation",
        )

    def test_persists_authored_tools_with_real_ulids(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        src = tmp_path / "tools.jsonld"
        src.write_text(json.dumps({"tools": [_T1, _T2]}))
        emitted = emit_tools_from_jsonld(src, adapter)
        assert len(emitted) == 2

        tool_dir = tmp_path / ".brain" / "instances" / "foundation" / "tool"
        files = sorted(p.name for p in tool_dir.glob("*.jsonld"))
        # real authored ULIDs preserved as the storage key — no derivation
        assert files == [
            "01KT1WT101G1TREM0TEREAD000.jsonld",
            "01KT1WT102RDPKGJS0N000000A.jsonld",
        ]

    def test_idempotent_reemit(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        src = tmp_path / "tools.jsonld"
        src.write_text(json.dumps({"tools": [_T1]}))
        emit_tools_from_jsonld(src, adapter)
        emit_tools_from_jsonld(src, adapter)  # same id → same file, no dup
        tool_dir = tmp_path / ".brain" / "instances" / "foundation" / "tool"
        assert len(list(tool_dir.glob("*.jsonld"))) == 1
