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
    """Single-root loader behaviour. These cases emit a complete brain (scenario
    + foundation) to one `tmp_path` root and read it back, so they pass
    `library_root=None` to opt out of the plugin-relative library root — keeping
    each case isolated to its own `tmp_path` and exercising the historical
    single-root contract (the library/captures split is covered by
    `TestLibraryCapturesSplit`)."""

    def test_round_trip_load_then_run(self, tmp_path: Path) -> None:
        base = tmp_path / ".brain" / "instances"
        bundle = _human_journey()
        _emit(base, bundle)
        scenario_id = bundle["scenarios"][0]["id"]

        loaded = load_scenario_journey(base, scenario_id, library_root=None)
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
            steps=[{"instruction": "POST a payment", "mechanism": "mixed", "tool_ref": tool_id,
                    "asserts": ["the payment is accepted"]}],
        )
        _emit(base, bundle, tools=[tool])

        loaded = load_scenario_journey(
            base, bundle["scenarios"][0]["id"], library_root=None
        )
        assert tool_id in loaded.tools_by_id
        assert loaded.tools_by_id[tool_id]["implementation_kind"] == "http_call"

    def test_missing_scenario_raises(self, tmp_path: Path) -> None:
        base = tmp_path / ".brain" / "instances"
        with pytest.raises(JourneyNotFound):
            load_scenario_journey(
                base, f"dna:scenario:{_ulid('nope')}", library_root=None
            )

    def test_dangling_step_name_is_surfaced_not_silent(self, tmp_path: Path) -> None:
        base = tmp_path / ".brain" / "instances"
        bundle = _human_journey()
        # drop one step from the store but leave it referenced in workflow.steps
        dropped = bundle["steps"].pop()
        _emit(base, bundle)
        loaded = load_scenario_journey(
            base, bundle["scenarios"][0]["id"], library_root=None
        )
        assert dropped["name"] in loaded.missing_steps


def _emit_captures_scenario(base: Path, bundle: dict) -> None:
    """Emit ONLY the product-development scenario to a captures root.

    Mirrors the post-migration world (WP-005): captures hold
    `product-development/*`; the `foundation/workflow|step|tool` library ships
    plugin-relative and is NOT in the captures root.
    """
    product = LocalFileEntityAdapter(base_dir=base, domain="product-development")
    for sc in bundle["scenarios"]:
        product.save("scenario", sc)


def _emit_foundation_library(
    base: Path, bundle: dict, *, tools: list[dict] | None = None
) -> None:
    """Emit ONLY the foundation library (workflow/steps/tools) to a library root."""
    foundation = LocalFileEntityAdapter(base_dir=base, domain="foundation")
    for tool in tools or []:
        foundation.save("tool", tool)
    for step in bundle["steps"]:
        foundation.save("step", step)
    for wf in bundle["workflows"]:
        foundation.save("workflow", wf)


class TestLibraryCapturesSplit:
    """ADR-001 / WP-002: foundation reads come from the plugin-relative library
    root; product-development reads come from the captures root (base_dir).

    The two roots are disjoint by entity type — the library ships
    `foundation/workflow|step|tool`, captures hold `product-development/*` — so
    a fresh install (empty captures) still loads the shipped library, and a
    captures root carrying only the scenario resolves its journey from the
    library."""

    def test_foundation_and_captures_share_one_root(self, tmp_path: Path) -> None:
        """RED (gap, pre-WP-002): a captures root that holds the scenario but
        NOT the foundation workflow cannot resolve the journey from a single
        root — `load_scenario_journey` raises `JourneyNotFound`. Post-WP-002
        the foundation read comes from the library root, so the SAME captures
        root resolves cleanly (the GREEN twin below)."""
        captures = tmp_path / "central" / ".brain" / "instances"
        bundle = _human_journey()
        # Only the scenario lands in captures; the foundation library is absent
        # from this root (it ships plugin-relative).
        _emit_captures_scenario(captures, bundle)

        with pytest.raises(JourneyNotFound):
            load_scenario_journey(captures, bundle["scenarios"][0]["id"])

    def test_split_roots_load_scenario_from_captures_foundation_from_library(
        self, tmp_path: Path
    ) -> None:
        """GREEN: scenario from the captures root, workflow/steps/tools from the
        library root — the two unioned by `load_scenario_journey` via WP-001's
        multi-root seam."""
        captures = tmp_path / "central" / ".brain" / "instances"
        library = tmp_path / "plugin" / ".brain" / "instances"
        tool_id = f"dna:tool:{_ulid('lib-tool')}"
        tool = {
            "id": tool_id, "name": "lib-call", "for_domain": _TENANT,
            "kind": "mutation", "inputs_schema_ref": "schemas/x-in.json",
            "outputs_schema_ref": "schemas/x-out.json",
            "implementation_kind": "http_call", "version": "1.0.0",
            "state": "active", "sys_status": "active",
        }
        bundle = assemble_scenario_graph(
            name="pay via the shipped library", verifies=[f"dna:requirement:{_ulid('rq')}"],
            exercises=f"dna:design:{_ulid('ds')}", tenant=_TENANT, seed="lib-pay",
            steps=[{"instruction": "POST a payment", "mechanism": "mixed",
                    "tool_ref": tool_id, "asserts": ["the payment is accepted"]}],
        )
        _emit_captures_scenario(captures, bundle)
        _emit_foundation_library(library, bundle, tools=[tool])

        loaded = load_scenario_journey(
            captures, bundle["scenarios"][0]["id"], library_root=library
        )
        assert loaded.scenario["id"] == bundle["scenarios"][0]["id"]
        assert loaded.workflow["id"] == bundle["workflows"][0]["id"]
        assert set(loaded.steps_by_name) == set(bundle["workflows"][0]["steps"])
        assert loaded.missing_steps == []
        assert tool_id in loaded.tools_by_id

    def test_fresh_install_library_loads_without_central_brain(
        self, tmp_path: Path
    ) -> None:
        """GREEN (spec acceptance #3/#4): an empty central captures root still
        resolves the journey, because the foundation library ships plugin-
        relative. The scenario itself is a capture, so it lives in captures;
        everything the workflow needs comes from the library root."""
        captures = tmp_path / "empty-central" / ".brain" / "instances"
        library = tmp_path / "plugin" / ".brain" / "instances"
        bundle = _human_journey()
        # Captures holds ONLY the scenario (a fresh install has no other
        # captured records); the foundation library is the shipped baseline.
        _emit_captures_scenario(captures, bundle)
        _emit_foundation_library(library, bundle)

        loaded = load_scenario_journey(
            captures, bundle["scenarios"][0]["id"], library_root=library
        )
        assert loaded.workflow["id"] == bundle["workflows"][0]["id"]
        assert set(loaded.steps_by_name) == set(bundle["workflows"][0]["steps"])
        assert loaded.missing_steps == []

    def test_single_root_with_no_library_still_raises_when_workflow_absent(
        self, tmp_path: Path
    ) -> None:
        """`library_root=None` collapses to a single-root read: a captures root
        holding only the scenario (no foundation workflow) cannot resolve the
        journey, so `JourneyNotFound` is raised — preserving the historical
        single-root contract for callers that opt out of the library root."""
        captures = tmp_path / ".brain" / "instances"
        bundle = _human_journey()
        _emit_captures_scenario(captures, bundle)

        with pytest.raises(JourneyNotFound):
            load_scenario_journey(
                captures, bundle["scenarios"][0]["id"], library_root=None
            )

    def test_default_library_root_is_plugin_relative_constant(self) -> None:
        """BLUE-supporting: the library root is a single plugin-relative
        constant derived like `_DEFAULT_SCHEMAS_DIR` (`Path(__file__).parent`
        anchor), not a hard-coded `.brain` path string."""
        from _scenario_graph_load import LIBRARY_ROOT

        # Anchored at the scripts dir, reaching the shipped `.brain/instances`.
        assert LIBRARY_ROOT.is_absolute()
        assert LIBRARY_ROOT.name == "instances"
        assert LIBRARY_ROOT.parent.name == ".brain"
