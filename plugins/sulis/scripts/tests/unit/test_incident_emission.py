"""Tests for `_incident_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _incident_emission import compose_incident, emit_incident


class TestComposeIncident:
    def test_minimum_valid(self) -> None:
        i = compose_incident(severity="sev2")
        assert re.fullmatch(r"^dna:incident:[0-9A-HJKMNP-TV-Z]{26}$", i["id"])
        assert i["severity"] == "sev2"
        assert isinstance(i["detected_at"], str) and len(i["detected_at"]) >= 10
        assert i["sys_status"] == "active"

    def test_with_resolution(self) -> None:
        i = compose_incident(
            severity="sev1",
            detected_at="2026-05-30T10:00:00Z",
            resolved_at="2026-05-30T10:45:00Z",
            mttr="PT45M",
        )
        assert i["resolved_at"] == "2026-05-30T10:45:00Z"
        assert i["mttr"] == "PT45M"

    def test_invalid_severity_raises(self) -> None:
        with pytest.raises(ValueError, match="severity"):
            compose_incident(severity="critical")

    def test_invalid_mttr_raises(self) -> None:
        with pytest.raises(ValueError, match="mttr"):
            compose_incident(severity="sev2", mttr="45 minutes")

    def test_deterministic_id(self) -> None:
        a = compose_incident(severity="sev1", detected_at="2026-05-30T10:00:00Z")
        b = compose_incident(severity="sev1", detected_at="2026-05-30T10:00:00Z",
                              resolved_at="2026-05-30T10:45:00Z")
        # Same severity + detected_at → same ID (resolution updates same record)
        assert a["id"] == b["id"]


class TestEmitIncident:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        i = emit_incident(repo=adapter, severity="sev2")
        ulid = i["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "incident" / f"{ulid}.jsonld"
        ).exists()
