"""Tests for the scenario-authoring assembler (the /sulis:specify intake).

A founder authors a verification journey in PLAIN ENGLISH (a list of numbered
steps, drafted from the SRD's acceptance criteria). `assemble_scenario_graph`
turns that into the IDEF0 graph underneath — a Scenario + a Workflow + its
Steps — with all the schema machinery the founder never sees. The acid test:
the assembled entities persist through the REAL emitters (validating against the
compiled Step/Workflow/Scenario schemas) without error.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _scenario_authoring import (
    _ulid,
    assemble_scenario_graph,
    repoint_scenarios_exercises,
)

_TENANT = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"


def _ref(kind: str, seed: str) -> str:
    return f"dna:{kind}:{_ulid(seed)}"


def _journey() -> dict:
    return assemble_scenario_graph(
        name="A signed-in user can pay with a saved card",
        verifies=[_ref("requirement", "req-pay")],
        exercises=_ref("design", "des-checkout"),
        tenant=_TENANT,
        seed="pay-with-saved-card",
        steps=[
            {"instruction": "Sign in as a user with a saved card",
             "asserts": ["a session is established"]},
            {"instruction": "Pay with the saved card",
             "asserts": ["the response shows payment succeeded"]},
        ],
    )


class TestAssembleStructure:
    def test_returns_one_scenario_one_workflow_n_steps(self) -> None:
        g = _journey()
        assert len(g["scenarios"]) == 1
        assert len(g["workflows"]) == 1
        assert len(g["steps"]) == 2

    def test_scenario_journey_points_at_the_workflow(self) -> None:
        g = _journey()
        assert g["scenarios"][0]["journey"] == g["workflows"][0]["id"]
        assert g["scenarios"][0]["verifies"] == [_ref("requirement", "req-pay")]

    def test_workflow_references_steps_by_name_in_order(self) -> None:
        g = _journey()
        wf, steps = g["workflows"][0], g["steps"]
        names = [s["name"] for s in steps]
        assert wf["steps"] == names
        assert wf["initial_steps"] == [names[0]]
        assert wf["terminal_steps"] == [names[-1]]
        # linear transitions: s0 -> s1
        assert wf["transitions"] == [f"{names[0]} -> {names[1]}"]

    def test_step_names_are_globally_unique_namespaced(self) -> None:
        # two journeys with identical step wording must NOT collide on step names
        # (flat-store reconstruction resolves workflow.steps names → Step entities)
        # name-uniqueness is orthogonal to verifiability — opt out of the gate
        a = assemble_scenario_graph(
            name="A", verifies=[_ref("requirement", "rqa")], exercises=_ref("design", "da"),
            tenant=_TENANT, seed="journey-a",
            steps=[{"instruction": "Sign in"}, {"instruction": "Pay"}],
            require_verifiable=False,
        )
        b = assemble_scenario_graph(
            name="B", verifies=[_ref("requirement", "rqb")], exercises=_ref("design", "db"),
            tenant=_TENANT, seed="journey-b",
            steps=[{"instruction": "Sign in"}, {"instruction": "Pay"}],
            require_verifiable=False,
        )
        names_a = {s["name"] for s in a["steps"]}
        names_b = {s["name"] for s in b["steps"]}
        assert names_a.isdisjoint(names_b)
        # and the workflow references its own namespaced names
        assert a["workflows"][0]["steps"] == [s["name"] for s in a["steps"]]

    def test_verification_discriminator(self) -> None:
        g = _journey()
        wf = g["workflows"][0]
        assert wf["type"] == "review"
        assert wf["for_process"] == "verification"

    def test_plain_english_preserved_and_asserts_become_postconditions(self) -> None:
        g = _journey()
        s0 = g["steps"][0]
        assert "saved card" in s0["agent_instructions"].lower()
        assert g["steps"][1]["postconditions"] == ["the response shows payment succeeded"]
        # founder-authored journeys default to human-run (tool_ref deferred)
        assert s0["mechanism"] == "human"
        assert "tool_ref" not in s0


class TestVerifiabilityGate:
    """Journey-rigor #5 — a verification journey must be verifiable.

    A journey with no observable check is a description of clicks; it can report
    green while the feature is broken (the green-but-broken-login class). The
    gate is on by default at authoring time.
    """

    def test_journey_with_no_checks_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="observable check"):
            assemble_scenario_graph(
                name="no checks", verifies=[_ref("requirement", "r")],
                exercises=_ref("design", "d"), tenant=_TENANT, seed="nc",
                steps=[{"instruction": "Sign in"}, {"instruction": "Land somewhere"}],
            )

    def test_unobservable_outcome_is_rejected(self) -> None:
        # has a check mid-journey, but the OUTCOME (final step) isn't observable
        with pytest.raises(ValueError, match="outcome"):
            assemble_scenario_graph(
                name="blind outcome", verifies=[_ref("requirement", "r")],
                exercises=_ref("design", "d"), tenant=_TENANT, seed="bo",
                steps=[
                    {"instruction": "Sign in", "asserts": ["a session is established"]},
                    {"instruction": "Do the thing"},  # no assert on the outcome
                ],
            )

    def test_verifiable_journey_passes(self) -> None:
        g = assemble_scenario_graph(
            name="verifiable", verifies=[_ref("requirement", "r")],
            exercises=_ref("design", "d"), tenant=_TENANT, seed="ok",
            steps=[
                {"instruction": "Sign in", "asserts": ["a session is established"]},
                {"instruction": "See the dashboard", "asserts": ["the dashboard is shown"]},
            ],
        )
        assert g["steps"][-1]["postconditions"] == ["the dashboard is shown"]

    def test_opt_out_allows_checkless_journey(self) -> None:
        # the escape hatch for structural tests orthogonal to verifiability
        g = assemble_scenario_graph(
            name="structural", verifies=[_ref("requirement", "r")],
            exercises=_ref("design", "d"), tenant=_TENANT, seed="so",
            steps=[{"instruction": "Sign in"}], require_verifiable=False,
        )
        assert len(g["steps"]) == 1


class TestRepointExercises:
    def test_repoints_every_scenario_to_the_real_design(self) -> None:
        g = _journey()
        placeholder = g["scenarios"][0]["exercises"]
        real_design = f"dna:design:{_ulid('real-checkout-design')}"
        assert placeholder != real_design

        out = repoint_scenarios_exercises(g, real_design)
        assert all(s["exercises"] == real_design for s in out["scenarios"])
        # workflows + steps untouched; inputs not mutated
        assert out["workflows"] == g["workflows"]
        assert g["scenarios"][0]["exercises"] == placeholder  # original unchanged

    def test_repointed_scenario_still_validates(self, tmp_path: Path) -> None:
        g = _journey()
        real_design = f"dna:design:{_ulid('real-design')}"
        out = repoint_scenarios_exercises(g, real_design)
        adapter = LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances", domain="product-development"
        )
        adapter.save("scenario", out["scenarios"][0])  # must not raise

    def test_empty_design_raises(self) -> None:
        with pytest.raises(ValueError):
            repoint_scenarios_exercises(_journey(), "")


class TestAssembledEntitiesValidate:
    """The acid test: assembled entities persist through the real schema-
    validating adapters without error."""

    def test_steps_and_workflow_persist_under_foundation(self, tmp_path: Path) -> None:
        g = _journey()
        adapter = LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances", domain="foundation"
        )
        for step in g["steps"]:
            adapter.save("step", step)        # raises EntityValidationError on bad shape
        adapter.save("workflow", g["workflows"][0])
        wf_id = g["workflows"][0]["id"].rsplit(":", 1)[-1]
        assert (tmp_path / ".brain" / "instances" / "foundation" / "workflow"
                / f"{wf_id}.jsonld").exists()

    def test_scenario_persists_under_product_development(self, tmp_path: Path) -> None:
        g = _journey()
        adapter = LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances", domain="product-development"
        )
        adapter.save("scenario", g["scenarios"][0])
        sc_id = g["scenarios"][0]["id"].rsplit(":", 1)[-1]
        assert (tmp_path / ".brain" / "instances" / "product-development" / "scenario"
                / f"{sc_id}.jsonld").exists()


class TestSurfaceTag:
    """WP-007 (FR-10, ADR-005) — a scenario carries a first-class `surface`
    tag (ui | tool) so the verification set can be partitioned by the consumer
    surface it exercises.

    Additive-optional (DESIGN.md §9.1): absent reads as `ui` (the current
    single-surface default), so existing scenarios + their seed-derived IDs are
    unchanged (NFR-05). The tag persists on the Scenario node and round-trips
    through the real schema-validating adapter (NFR-D01 — brain is truth).
    No new driver mechanism is introduced (FR-14).
    """

    def _surface_journey(self, surface: str | None) -> dict:
        kwargs: dict = dict(
            name="A user can run a tool against the brain",
            verifies=[_ref("requirement", "req-tool")],
            exercises=_ref("design", "des-tool"),
            tenant=_TENANT,
            seed="tool-surface-journey",
            steps=[
                {"instruction": "Invoke the tool",
                 "asserts": ["the tool returns a result"]},
            ],
        )
        if surface is not None:
            kwargs["surface"] = surface
        return assemble_scenario_graph(**kwargs)

    def test_assemble_scenario_graph_tags_surface(self, tmp_path: Path) -> None:
        # surface="tool" => the Scenario node carries surface: tool, and the
        # tagged scenario still validates through the real adapter (brain truth).
        g = self._surface_journey("tool")
        assert g["scenarios"][0]["surface"] == "tool"
        adapter = LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances", domain="product-development"
        )
        adapter.save("scenario", g["scenarios"][0])  # must not raise

    def test_surface_defaults_to_ui(self) -> None:
        # omit surface => reads "ui" (back-compat with the single-surface default)
        g = self._surface_journey(None)
        assert g["scenarios"][0]["surface"] == "ui"

    def test_seed_stability_preserved(self) -> None:
        # NFR-05: the same seed yields an identical scenario id whether or not a
        # surface is supplied — surface must not feed any _ulid seed.
        without = self._surface_journey(None)
        with_tool = self._surface_journey("tool")
        assert without["scenarios"][0]["id"] == with_tool["scenarios"][0]["id"]
        assert without["workflows"][0]["id"] == with_tool["workflows"][0]["id"]
        assert [s["id"] for s in without["steps"]] == [
            s["id"] for s in with_tool["steps"]
        ]

    def test_invalid_surface_is_rejected(self) -> None:
        # the tag is a closed enum (ui | tool); anything else is a typo, not a
        # third surface — fail loud at authoring rather than persist a bad tag.
        with pytest.raises(ValueError, match="surface"):
            self._surface_journey("api")


def test_single_step_journey_has_no_transitions_issue(tmp_path: Path) -> None:
    # a 1-step journey: terminal==initial, transitions may be empty BUT schema
    # requires minItems:1 on transitions — assembler must emit a self/sentinel edge.
    g = assemble_scenario_graph(
        name="health check", verifies=[_ref("requirement", "req-health")],
        exercises=_ref("design", "des-health"), tenant=_TENANT, seed="hc",
        steps=[{"instruction": "Hit the health endpoint", "asserts": ["200 OK"]}],
    )
    adapter = LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances", domain="foundation"
    )
    adapter.save("workflow", g["workflows"][0])  # must not raise (transitions minItems:1)
