"""The change-lifecycle Workflow + the Change.journey link (#129 B1).

A Change runs a Workflow (recon→ship), executed by its session. This pins the
authored Workflow + Step instances are schema-valid, the journey is forward-
connected, and the new Change.journey link validates — all against the REAL
schemas (no mock).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_lifecycle import (  # noqa: E402
    STAGES, WORKFLOW_ID, author, step_instances, workflow_instance)
from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402

_REPO = Path(__file__).resolve().parents[5]
_COMPILED = _REPO / "plugins" / "sulis" / "brain" / "compiled"


def _validator(domain: str, entity: str) -> Draft202012Validator:
    return Draft202012Validator(
        json.loads((_COMPILED / domain / f"{entity}.schema.json").read_text()))


# ─── the Workflow + Step instances are schema-valid ─────────────────────────


def test_workflow_instance_is_schema_valid():
    _validator("foundation", "workflow").validate(workflow_instance())


def test_step_instances_are_schema_valid():
    v = _validator("foundation", "step")
    steps = step_instances()
    assert len(steps) == 6
    for s in steps:
        v.validate(s)
        assert s["mechanism"] == "mixed"   # the session is the human+agent executor


# ─── the journey is the six stages, forward-connected ───────────────────────


def test_workflow_is_the_six_stage_journey():
    wf = workflow_instance()
    assert wf["steps"] == ["recon", "specify", "design", "implement", "review", "ship"]
    assert wf["initial_steps"] == ["recon"]
    assert wf["terminal_steps"] == ["ship"]
    assert wf["transitions"] == [
        "recon -> specify", "specify -> design", "design -> implement",
        "implement -> review", "review -> ship"]


def test_workflow_id_is_stable():
    assert workflow_instance()["id"] == WORKFLOW_ID == "dna:workflow:" + WORKFLOW_ID.split(":")[-1]


# ─── Change.journey link validates against the (extended) Change schema ──────


def _base_change() -> dict:
    u = "0123456789ABCDEFGHJKMNPQRS"
    return {"id": f"dna:change:{u}", "handle": "CH-X", "slug": "s", "intent": "i",
            "primitive": "fix", "state": "in-flight", "started_at": "2026-06-12T09:00:00Z",
            "sys_status": "active"}


def test_change_accepts_a_journey_link():
    v = _validator("product-development", "change")
    c = _base_change()
    c["journey"] = WORKFLOW_ID
    assert v.is_valid(c)


def test_change_rejects_a_malformed_journey():
    v = _validator("product-development", "change")
    c = _base_change()
    c["journey"] = "dna:workflow:bad"
    assert not v.is_valid(c)


# ─── author() persists them through the real adapter ────────────────────────


def test_author_persists_workflow_and_steps(tmp_path):
    repo = LocalFileEntityAdapter(base_dir=tmp_path / ".brain" / "instances", domain="foundation")
    author(repo)
    assert repo.find_by_id("workflow", WORKFLOW_ID)["name"] == "change-lifecycle"
    saved_steps = {s["name"] for s in repo.iter_entities("step")}
    assert saved_steps == set(STAGES)
