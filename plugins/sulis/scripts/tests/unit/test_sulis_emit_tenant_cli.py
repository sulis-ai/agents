"""End-to-end CLI tests for `sulis-emit-tenant`."""

from __future__ import annotations

from pathlib import Path


_VALID = """
name: Sulis AI
kind: company
state: active
"""


class TestSulisEmitTenantCli:
    def test_emits_under_foundation_domain_by_default(
        self, tmp_path: Path, run_tool
    ) -> None:
        yaml_path = tmp_path / "tenant.yaml"
        yaml_path.write_text(_VALID)
        result = run_tool(
            "sulis-emit-tenant", "--from-yaml", str(yaml_path), "--repo-root", str(tmp_path)
        )
        assert result.ok, f"stderr: {result.stderr!r}"
        assert result.data["count"] == 1
        first = Path(result.data["entities"][0]["path"])
        rel = first.relative_to(tmp_path)
        assert rel.parts[:3] == (".brain", "instances", "foundation")
        assert rel.parts[3] == "tenant"

    def test_emitted_file_exists(self, tmp_path: Path, run_tool) -> None:
        yaml_path = tmp_path / "tenant.yaml"
        yaml_path.write_text(_VALID)
        result = run_tool(
            "sulis-emit-tenant", "--from-yaml", str(yaml_path), "--repo-root", str(tmp_path)
        )
        assert result.ok
        assert Path(result.data["entities"][0]["path"]).exists()

    def test_returns_error_for_missing_path(self, tmp_path: Path, run_tool) -> None:
        result = run_tool(
            "sulis-emit-tenant",
            "--from-yaml", str(tmp_path / "missing.yaml"),
            "--repo-root", str(tmp_path),
        )
        assert not result.ok
        assert "not found" in result.error.lower()
