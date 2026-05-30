"""Tests for `_lifecyclerun_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _lifecyclerun_emission import compose_lifecyclerun, emit_lifecyclerun
from _entity_adapter_local import LocalFileEntityAdapter


_ACTOR = "dna:actor:01ABCDEFGHJKMNPQRSTVWXYZ12"


class TestComposeLifecycleRun:
    def test_minimum_valid(self) -> None:
        r = compose_lifecyclerun(step_name="run-all Step 7", outcome="completed")
        assert re.fullmatch(r"^dna:lifecyclerun:[0-9A-HJKMNP-TV-Z]{26}$", r["id"])
        assert r["step_name"] == "run-all Step 7"
        assert r["outcome"] == "completed"
        assert isinstance(r["at"], str) and len(r["at"]) >= 10
        assert r["sys_status"] == "active"

    def test_with_actor(self) -> None:
        r = compose_lifecyclerun(
            step_name="ship", outcome="completed", by_actor=_ACTOR
        )
        assert r["by_actor"] == _ACTOR

    def test_invalid_outcome_raises(self) -> None:
        with pytest.raises(ValueError, match="outcome"):
            compose_lifecyclerun(step_name="x", outcome="exploded")

    def test_empty_step_name_raises(self) -> None:
        with pytest.raises(ValueError, match="step_name"):
            compose_lifecyclerun(step_name="", outcome="completed")

    def test_invalid_by_actor_raises(self) -> None:
        with pytest.raises(ValueError, match="by_actor"):
            compose_lifecyclerun(
                step_name="x", outcome="completed", by_actor="not-an-actor"
            )


class TestEmitLifecycleRun:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        r = emit_lifecyclerun(repo=adapter, step_name="run-all", outcome="completed")
        ulid = r["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "lifecyclerun" / f"{ulid}.jsonld"
        ).exists()
