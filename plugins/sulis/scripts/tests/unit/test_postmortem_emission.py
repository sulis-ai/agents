"""Tests for `_postmortem_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _postmortem_emission import compose_postmortem, emit_postmortem


_INC = "dna:incident:01ABCDEFGHJKMNPQRSTVWXYZ12"
_REQ = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"
_OPP = "dna:opportunity:01CDEFGHJKMNPQRSTVWXYZ1234"


class TestComposePostmortem:
    def test_minimum_valid(self) -> None:
        p = compose_postmortem(
            for_incident=_INC, findings="Rate-limit exhaustion at edge.",
        )
        assert re.fullmatch(r"^dna:postmortem:[0-9A-HJKMNP-TV-Z]{26}$", p["id"])
        assert p["for_incident"] == _INC
        assert p["findings"] == "Rate-limit exhaustion at edge."
        assert p["blameless"] is True
        assert p["sys_status"] == "active"

    def test_with_actions(self) -> None:
        p = compose_postmortem(
            for_incident=_INC, findings="X",
            actions=[_REQ, _OPP],
        )
        assert p["actions"] == [_REQ, _OPP]

    def test_blameful(self) -> None:
        p = compose_postmortem(for_incident=_INC, findings="X", blameless=False)
        assert p["blameless"] is False

    def test_invalid_incident_raises(self) -> None:
        with pytest.raises(ValueError, match="for_incident"):
            compose_postmortem(for_incident="not-an-incident", findings="X")

    def test_empty_findings_raises(self) -> None:
        with pytest.raises(ValueError, match="findings"):
            compose_postmortem(for_incident=_INC, findings="")

    def test_invalid_action_raises(self) -> None:
        with pytest.raises(ValueError, match="actions"):
            compose_postmortem(for_incident=_INC, findings="X", actions=["not-a-ref"])

    def test_deterministic_id_one_per_incident(self) -> None:
        a = compose_postmortem(for_incident=_INC, findings="First draft.")
        b = compose_postmortem(for_incident=_INC, findings="Updated draft.")
        # One incident → one postmortem; findings update lands on same record
        assert a["id"] == b["id"]


class TestEmitPostmortem:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        p = emit_postmortem(repo=adapter, for_incident=_INC, findings="X")
        ulid = p["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "postmortem" / f"{ulid}.jsonld"
        ).exists()
