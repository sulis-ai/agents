"""CLI test for `sulis-verify-acceptance --scenario <id>` (bundle-from-graph).

The loop, through the executable: a Scenario emitted to the brain store is
loaded by id and run with NO hand-built bundle. Human-only journeys resolve to
manual-pending (the gate blocks, exit 1) — what matters here is that the CLI
loaded the journey from the graph and ran it, vs erroring on a missing one.
"""

from __future__ import annotations

import json
from pathlib import Path

from _brain_query import iter_entities
from _entity_adapter_local import LocalFileEntityAdapter
from _scenario_authoring import _ulid, assemble_scenario_graph

_TENANT = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"


def _seed_store(base: Path) -> str:
    bundle = assemble_scenario_graph(
        name="A signed-in user can pay with a saved card",
        verifies=[f"dna:requirement:{_ulid('req-pay')}"],
        exercises=f"dna:design:{_ulid('des-checkout')}",
        tenant=_TENANT, seed="pay-with-saved-card",
        steps=[
            {"instruction": "Sign in as a user with a saved card",
             "asserts": ["a session is established"]},
            {"instruction": "Pay with the saved card",
             "asserts": ["the response shows payment succeeded"]},
        ],
    )
    foundation = LocalFileEntityAdapter(base_dir=base, domain="foundation")
    product = LocalFileEntityAdapter(base_dir=base, domain="product-development")
    for step in bundle["steps"]:
        foundation.save("step", step)
    for wf in bundle["workflows"]:
        foundation.save("workflow", wf)
    for sc in bundle["scenarios"]:
        product.save("scenario", sc)
    return bundle["scenarios"][0]["id"]


def _write_contract(tmp_path: Path) -> None:
    (tmp_path / ".sulis").mkdir(exist_ok=True)
    (tmp_path / ".sulis" / "repo-contract.yml").write_text(
        "targets:\n  local: http://localhost:9\n", encoding="utf-8")


class TestVerifyAcceptanceFromGraph:
    def test_loads_and_runs_from_graph(self, tmp_path: Path, run_tool) -> None:
        base = tmp_path / ".brain" / "instances"
        scenario_id = _seed_store(base)
        _write_contract(tmp_path)

        result = run_tool(
            "sulis-verify-acceptance", "--scenario", scenario_id,
            "--base-dir", str(base), "--repo-root", str(tmp_path), "--json",
        )
        # human journey → manual-pending → gate blocks (exit 1), but it RAN
        assert result.returncode == 1, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        env = json.loads(result.stdout)
        assert env["scenario"] == "A signed-in user can pay with a saved card"
        assert env["verdict"] == "manual-pending"
        assert len(env["steps"]) == 2

    def test_run_deposits_verification_evidence(self, tmp_path: Path, run_tool) -> None:
        # A run leaves a TestRun + TestResult the requirement-coverage gate
        # reads. The human journey resolves to manual-pending → a `skip`
        # record (honest: not a pass, so not coverage — but the run is logged).
        base = tmp_path / ".brain" / "instances"
        scenario_id = _seed_store(base)
        _write_contract(tmp_path)

        result = run_tool(
            "sulis-verify-acceptance", "--scenario", scenario_id,
            "--base-dir", str(base), "--repo-root", str(tmp_path), "--json",
        )
        env = json.loads(result.stdout)
        assert env["evidence"] is not None
        assert env["evidence"]["outcome"] == "skip"

        results = list(iter_entities(base, domain="product-development", entity_type="testresult"))
        assert len(results) == 1
        assert results[0]["scenario"] == scenario_id
        assert results[0]["verifies"] == [f"dna:requirement:{_ulid('req-pay')}"]

    def test_no_emit_evidence_suppresses_the_record(self, tmp_path: Path, run_tool) -> None:
        base = tmp_path / ".brain" / "instances"
        scenario_id = _seed_store(base)
        _write_contract(tmp_path)

        result = run_tool(
            "sulis-verify-acceptance", "--scenario", scenario_id,
            "--base-dir", str(base), "--repo-root", str(tmp_path), "--json",
            "--no-emit-evidence",
        )
        env = json.loads(result.stdout)
        assert env["evidence"] is None
        assert list(iter_entities(base, domain="product-development", entity_type="testresult")) == []

    def test_missing_scenario_is_invocation_error(self, tmp_path: Path, run_tool) -> None:
        base = tmp_path / ".brain" / "instances"
        _seed_store(base)
        _write_contract(tmp_path)
        result = run_tool(
            "sulis-verify-acceptance", "--scenario", f"dna:scenario:{_ulid('ghost')}",
            "--base-dir", str(base), "--repo-root", str(tmp_path),
        )
        assert result.returncode == 2
        assert "couldn't load the scenario" in result.stderr.lower()
