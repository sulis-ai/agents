"""End-to-end CLI tests for `sulis-emit-requirements` — exercises the JSON
envelope shape callers rely on.
"""

from __future__ import annotations

import json
from pathlib import Path


_SRD = """# Software Requirements Document: Sample

## Summary

A sample SRD for the CLI smoke test.

## 4. Functional Requirements

**FR-01: Authenticate the user**

The system MUST authenticate via OAuth before granting access.

**Acceptance criteria:** Valid signatures grant access; invalid signatures
return 401.

**FR-02: Audit privileged actions**

The system MUST emit an audit log entry for every elevated action.

**Acceptance criteria:** Every elevated call produces one log row.
"""


class TestSulisEmitRequirementsCli:
    def test_emits_one_jsonld_per_FR_via_cli(
        self, tmp_path: Path, run_tool
    ) -> None:
        srd_path = tmp_path / "SRD.md"
        srd_path.write_text(_SRD)

        result = run_tool(
            "sulis-emit-requirements",
            "--from-srd", str(srd_path),
            "--repo-root", str(tmp_path),
        )

        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        assert result.data["count"] == 2
        assert len(result.data["requirements"]) == 2

        # Every emitted requirement file is on disk.
        for entry in result.data["requirements"]:
            assert Path(entry["path"]).exists()
            # And validates against the vendored schema (round-trip via the
            # adapter would have rejected otherwise; we exercise that path
            # in test_entity_adapter_local.py).

    def test_emits_under_repo_root_brain_instances_by_default(
        self, tmp_path: Path, run_tool
    ) -> None:
        srd_path = tmp_path / "SRD.md"
        srd_path.write_text(_SRD)

        result = run_tool(
            "sulis-emit-requirements",
            "--from-srd", str(srd_path),
            "--repo-root", str(tmp_path),
        )

        assert result.ok
        first_path = Path(result.data["requirements"][0]["path"])
        rel = first_path.relative_to(tmp_path)
        assert rel.parts[:3] == (".brain", "instances", "product-development")
        assert rel.parts[3] == "requirement"
        assert rel.name.endswith(".jsonld")

    def test_empty_srd_returns_count_zero_not_error(
        self, tmp_path: Path, run_tool
    ) -> None:
        srd_path = tmp_path / "EMPTY.md"
        srd_path.write_text("# Just prose, no FRs\n\nSome text.")

        result = run_tool(
            "sulis-emit-requirements",
            "--from-srd", str(srd_path),
            "--repo-root", str(tmp_path),
        )

        # An SRD with no FRs is not a failure — it's a 0-count success.
        assert result.ok, (
            f"empty-SRD should be ok=true (count=0); got {result.stderr!r}"
        )
        assert result.data["count"] == 0
        assert result.data["requirements"] == []

    def test_returns_error_for_missing_srd_path(
        self, tmp_path: Path, run_tool
    ) -> None:
        result = run_tool(
            "sulis-emit-requirements",
            "--from-srd", str(tmp_path / "does-not-exist.md"),
            "--repo-root", str(tmp_path),
        )

        assert not result.ok
        assert result.error is not None
        assert "not found" in result.error.lower()
