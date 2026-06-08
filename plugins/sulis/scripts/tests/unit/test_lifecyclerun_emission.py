"""Tests for `_lifecyclerun_emission.py` (v2 — `step` ref).

Migrated to the v2 contract (WP-002): `compose_lifecyclerun`/`emit_lifecyclerun`
take a resolved `step` ref (a `dna:step:<ulid>`), not a free `step_name`
string. The deeper v2 behaviour (run_id, schema validation) is exercised in
`test_lifecyclerun_emission_v2.py`; this file keeps the original happy-path +
guard coverage, re-pointed at `step`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _lifecyclerun_emission import compose_lifecyclerun, emit_lifecyclerun
from _entity_adapter_local import LocalFileEntityAdapter


_ACTOR = "dna:actor:01ABCDEFGHJKMNPQRSTVWXYZ12"
_STEP = "dna:step:01KT61X5ST01CHANGESTART00A"


class TestComposeLifecycleRun:
    def test_minimum_valid(self) -> None:
        r = compose_lifecyclerun(step=_STEP, outcome="completed")
        assert re.fullmatch(r"^dna:lifecyclerun:[0-9A-HJKMNP-TV-Z]{26}$", r["id"])
        assert r["step"] == _STEP
        assert r["outcome"] == "completed"
        assert isinstance(r["at"], str) and len(r["at"]) >= 10
        assert r["sys_status"] == "active"

    def test_with_actor(self) -> None:
        r = compose_lifecyclerun(
            step=_STEP, outcome="completed", by_actor=_ACTOR
        )
        assert r["by_actor"] == _ACTOR

    def test_invalid_outcome_raises(self) -> None:
        with pytest.raises(ValueError, match="outcome"):
            compose_lifecyclerun(step=_STEP, outcome="exploded")

    def test_empty_step_raises(self) -> None:
        with pytest.raises(ValueError, match="step"):
            compose_lifecyclerun(step="", outcome="completed")

    def test_non_step_ref_raises(self) -> None:
        with pytest.raises(ValueError, match="step"):
            compose_lifecyclerun(step="change-started:fix:x", outcome="completed")

    def test_invalid_by_actor_raises(self) -> None:
        with pytest.raises(ValueError, match="by_actor"):
            compose_lifecyclerun(
                step=_STEP, outcome="completed", by_actor="not-an-actor"
            )


class TestEmitLifecycleRun:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        r = emit_lifecyclerun(repo=adapter, step=_STEP, outcome="completed")
        ulid = r["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "lifecyclerun" / f"{ulid}.jsonld"
        ).exists()
