"""End-to-end CLI tests for `sulis-emit-tool` (foundation-domain ingest)."""

from __future__ import annotations

import json
from pathlib import Path


def _tools_jsonld() -> str:
    tool = {
        "id": "dna:tool:01KT1WT101G1TREM0TEREAD000",
        "name": "git-remote-read",
        "for_domain": "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM",
        "kind": "query",
        "inputs_schema_ref": "schemas/tools/x-input.schema.json",
        "outputs_schema_ref": "schemas/tools/x-output.schema.json",
        "implementation_kind": "subprocess",
        "version": "1.0.0",
        "state": "active",
        "sys_status": "active",
    }
    return json.dumps({"@context": "x", "@type": "ToolSet", "tools": [tool]})


class TestSulisEmitToolCli:
    def test_emits_under_foundation_domain_by_default(
        self, tmp_path: Path, run_tool
    ) -> None:
        src = tmp_path / "tools.jsonld"
        src.write_text(_tools_jsonld())
        result = run_tool(
            "sulis-emit-tool", "--from-instances", str(src), "--repo-root", str(tmp_path)
        )
        assert result.ok, f"stderr: {result.stderr!r}"
        assert result.data["count"] == 1
        first = Path(result.data["entities"][0]["path"])
        rel = first.relative_to(tmp_path)
        assert rel.parts[:4] == (".brain", "instances", "foundation", "tool")

    def test_emitted_file_exists(self, tmp_path: Path, run_tool) -> None:
        src = tmp_path / "tools.jsonld"
        src.write_text(_tools_jsonld())
        result = run_tool(
            "sulis-emit-tool", "--from-instances", str(src), "--repo-root", str(tmp_path)
        )
        assert result.ok
        assert Path(result.data["entities"][0]["path"]).exists()

    def test_returns_error_for_missing_path(self, tmp_path: Path, run_tool) -> None:
        result = run_tool(
            "sulis-emit-tool",
            "--from-instances", str(tmp_path / "missing.jsonld"),
            "--repo-root", str(tmp_path),
        )
        assert not result.ok
        assert "not found" in result.error.lower()
