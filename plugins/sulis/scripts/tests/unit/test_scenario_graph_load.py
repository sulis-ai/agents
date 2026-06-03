"""Tests for the flat brain-store journey loader (bundle-from-graph).

Closes the testable-state loop: a Scenario authored + emitted to the brain is
loaded BACK from the store — by scenario id → its journey Workflow → the
Workflow's Steps (resolved from `workflow.steps` names) → the Steps' Tools —
and run, with no hand-built bundle. The round-trip (emit → load → run) is the
acid test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _scenario_authoring import _ulid, assemble_scenario_graph
from _scenario_graph_load import JourneyNotFound, load_scenario_journey
from _scenario_runner import run_scenario

_TENANT = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"


def _emit(base: Path, bundle: dict, *, tools: list[dict] | None = None) -> None:
    foundation = LocalFileEntityAdapter(base_dir=base, domain="foundation")
    product = LocalFileEntityAdapter(base_dir=base, domain="product-development")
    for tool in tools or []:
        foundation.save("tool", tool)
    for step in bundle["steps"]:
        foundation.save("step", step)
    for wf in bundle["workflows"]:
        foundation.save("workflow", wf)
    for sc in bundle["scenarios"]:
        product.save("scenario", sc)


def _human_journey() -> dict:
    return assemble_scenario_graph(
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


class TestLoadFromStore:
    def test_round_trip_load_then_run(self, tmp_path: Path) -> None:
        base = tmp_path / ".brain" / "instances"
        bundle = _human_journey()
        _emit(base, bundle)
        scenario_id = bundle["scenarios"][0]["id"]

        loaded = load_scenario_journey(base, scenario_id)
        # scenario + workflow resolve by id; journey ref matches
        assert loaded.scenario["id"] == scenario_id
        assert loaded.workflow["id"] == bundle["workflows"][0]["id"]
        # steps resolved by the names in workflow.steps
        assert set(loaded.steps_by_name) == set(bundle["workflows"][0]["steps"])
        assert loaded.missing_steps == []

        # the loaded graph actually runs (human steps → manual-pending)
        result = run_scenario(
            loaded.scenario, loaded.workflow, loaded.steps_by_name, loaded.tools_by_id
        )
        assert result.scenario_id == scenario_id
        assert result.verdict == "manual-pending"
        assert len(result.steps) == 2

    def test_tool_ref_resolves_to_real_tool(self, tmp_path: Path) -> None:
        base = tmp_path / ".brain" / "instances"
        tool_id = f"dna:tool:{_ulid('http-pay-tool')}"
        tool = {
            "id": tool_id, "name": "pay-call", "for_domain": _TENANT, "kind": "mutation",
            "inputs_schema_ref": "schemas/x-in.json", "outputs_schema_ref": "schemas/x-out.json",
            "implementation_kind": "http_call", "version": "1.0.0",
            "state": "active", "sys_status": "active",
        }
        bundle = assemble_scenario_graph(
            name="pay via API", verifies=[f"dna:requirement:{_ulid('rq')}"],
            exercises=f"dna:design:{_ulid('ds')}", tenant=_TENANT, seed="pay-api",
            steps=[{"instruction": "POST a payment", "mechanism": "mixed", "tool_ref": tool_id}],
        )
        _emit(base, bundle, tools=[tool])

        loaded = load_scenario_journey(base, bundle["scenarios"][0]["id"])
        assert tool_id in loaded.tools_by_id
        assert loaded.tools_by_id[tool_id]["implementation_kind"] == "http_call"

    def test_missing_scenario_raises(self, tmp_path: Path) -> None:
        base = tmp_path / ".brain" / "instances"
        with pytest.raises(JourneyNotFound):
            load_scenario_journey(base, f"dna:scenario:{_ulid('nope')}")

    def test_dangling_step_name_is_surfaced_not_silent(self, tmp_path: Path) -> None:
        base = tmp_path / ".brain" / "instances"
        bundle = _human_journey()
        # drop one step from the store but leave it referenced in workflow.steps
        dropped = bundle["steps"].pop()
        _emit(base, bundle)
        loaded = load_scenario_journey(base, bundle["scenarios"][0]["id"])
        assert dropped["name"] in loaded.missing_steps
