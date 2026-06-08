"""CLI tests for `sulis-resolve-scenario-design` (resolve the Design placeholder)."""

from __future__ import annotations

import json
from pathlib import Path

from _scenario_authoring import _ulid, assemble_scenario_graph

_TENANT = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"


def _write_bundle(tmp_path: Path) -> tuple[Path, str]:
    bundle = assemble_scenario_graph(
        name="pay with saved card", verifies=[f"dna:requirement:{_ulid('rq')}"],
        exercises=f"dna:design:{_ulid('placeholder')}", tenant=_TENANT, seed="pay",
        steps=[{"instruction": "Sign in"}, {"instruction": "Pay"}],
        require_verifiable=False,  # this test exercises design re-pointing, not verifiability
    )
    path = tmp_path / "x.scenarios.jsonld"
    path.write_text(json.dumps(bundle))
    return path, bundle["scenarios"][0]["id"]


class TestResolveScenarioDesignCli:
    def test_repoints_and_emits(self, tmp_path: Path, run_tool) -> None:
        bundle_path, scenario_id = _write_bundle(tmp_path)
        real_design = f"dna:design:{_ulid('real-design')}"
        base = tmp_path / ".brain" / "instances"
        result = run_tool(
            "sulis-resolve-scenario-design", "--scenarios", str(bundle_path),
            "--design", real_design, "--emit", "--base-dir", str(base),
            "--repo-root", str(tmp_path),
        )
        assert result.ok, f"stderr: {result.stderr!r}"
        assert result.data["repointed"] == 1
        assert result.data["emitted"] == 1

        # durable bundle rewritten with the real design
        rewritten = json.loads(bundle_path.read_text())
        assert rewritten["scenarios"][0]["exercises"] == real_design
        # emitted scenario entity carries the real design
        sc_file = base / "product-development" / "scenario" / f"{scenario_id.rsplit(':', 1)[-1]}.jsonld"
        assert json.loads(sc_file.read_text())["exercises"] == real_design

    def test_rejects_non_design_id(self, tmp_path: Path, run_tool) -> None:
        bundle_path, _ = _write_bundle(tmp_path)
        result = run_tool(
            "sulis-resolve-scenario-design", "--scenarios", str(bundle_path),
            "--design", "dna:requirement:01KT1WT101000000000000000A", "--repo-root", str(tmp_path),
        )
        assert not result.ok
        assert "dna:design" in result.error

    def test_missing_bundle_errors(self, tmp_path: Path, run_tool) -> None:
        result = run_tool(
            "sulis-resolve-scenario-design", "--scenarios", str(tmp_path / "nope.jsonld"),
            "--design", f"dna:design:{_ulid('d')}", "--repo-root", str(tmp_path),
        )
        assert not result.ok
        assert "not found" in result.error.lower()
