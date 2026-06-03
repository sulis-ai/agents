"""End-to-end CLI tests for `sulis-author-scenario` (the /sulis:specify intake)."""

from __future__ import annotations

import json
from pathlib import Path

from _scenario_authoring import _ulid

_TENANT = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"


def _spec() -> dict:
    return {
        "name": "A signed-in user can pay with a saved card",
        "verifies": [f"dna:requirement:{_ulid('req-pay')}"],
        "exercises": f"dna:design:{_ulid('des-checkout')}",
        "tenant": _TENANT,
        "seed": "pay-with-saved-card",
        "steps": [
            {"instruction": "Sign in as a user with a saved card",
             "asserts": ["a session is established"]},
            {"instruction": "Pay with the saved card",
             "asserts": ["the response shows payment succeeded"]},
        ],
    }


class TestAuthorScenarioCli:
    def test_assembles_writes_and_emits(self, tmp_path: Path, run_tool) -> None:
        jpath = tmp_path / "journey.json"
        jpath.write_text(json.dumps(_spec()))
        out = tmp_path / "scenarios.jsonld"
        result = run_tool(
            "sulis-author-scenario", "--journey", str(jpath), "--out", str(out),
            "--emit", "--base-dir", str(tmp_path / ".brain" / "instances"),
            "--repo-root", str(tmp_path),
        )
        assert result.ok, f"stderr: {result.stderr!r}"
        d = result.data
        assert d["step_count"] == 2
        assert d["scenario_id"].startswith("dna:scenario:")
        assert d["workflow_id"].startswith("dna:workflow:")
        assert d["emitted"] == {"scenario": 1, "workflow": 1, "step": 2}

        # durable authored bundle written
        assert out.exists()
        bundle = json.loads(out.read_text())
        assert len(bundle["steps"]) == 2

        # entities landed in the brain, scenario under product-development
        inst = tmp_path / ".brain" / "instances"
        sc_id = d["scenario_id"].rsplit(":", 1)[-1]
        wf_id = d["workflow_id"].rsplit(":", 1)[-1]
        assert (inst / "product-development" / "scenario" / f"{sc_id}.jsonld").exists()
        assert (inst / "foundation" / "workflow" / f"{wf_id}.jsonld").exists()
        assert len(list((inst / "foundation" / "step").glob("*.jsonld"))) == 2

    def test_without_emit_writes_bundle_only(self, tmp_path: Path, run_tool) -> None:
        jpath = tmp_path / "journey.json"
        jpath.write_text(json.dumps(_spec()))
        result = run_tool(
            "sulis-author-scenario", "--journey", str(jpath),
            "--out", str(tmp_path / "b.jsonld"), "--repo-root", str(tmp_path),
        )
        assert result.ok
        assert result.data["emitted"] is None
        assert not (tmp_path / ".brain").exists()

    def test_missing_required_key_errors(self, tmp_path: Path, run_tool) -> None:
        jpath = tmp_path / "bad.json"
        jpath.write_text(json.dumps({"name": "x"}))
        result = run_tool("sulis-author-scenario", "--journey", str(jpath), "--repo-root", str(tmp_path))
        assert not result.ok
        assert "missing required keys" in result.error

    def test_missing_file_errors(self, tmp_path: Path, run_tool) -> None:
        result = run_tool(
            "sulis-author-scenario", "--journey", str(tmp_path / "nope.json"),
            "--repo-root", str(tmp_path),
        )
        assert not result.ok
        assert "not found" in result.error.lower()
