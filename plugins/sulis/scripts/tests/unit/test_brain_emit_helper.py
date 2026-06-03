"""Tests for `_brain_emit_helper.py`.

The helper's contract is two-part:

1. **Happy path:** when the brain is usable, helpers emit the right entity
   and return its payload (a dict).
2. **Graceful degradation:** when anything goes wrong (missing schemas,
   bad input, unwritable path, opted out via env var), helpers return
   `None` and do NOT raise — the host script must not be broken by the
   side-effect.

We test both halves explicitly. The host script's perspective is what
matters: it always sees `dict | None`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _brain_emit_helper import (
    _brain_emit_enabled,
    emit_change_shipped_event,
    emit_change_started_event,
    emit_decisions_from_adrs,
    emit_deployment_event,
    emit_lifecycle_step_event,
    emit_release_event,
    emit_requirements_from_srd,
)


_REL = "dna:release:01ABCDEFGHJKMNPQRSTVWXYZ12"
_ENV = "dna:environment:01BCDEFGHJKMNPQRSTVWXYZ123"
_COMP = "dna:component:01CDEFGHJKMNPQRSTVWXYZ1234"


# ─── Env-var gate ───────────────────────────────────────────────────────


class TestEnabledFlag:
    def test_default_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SULIS_BRAIN_EMIT", raising=False)
        assert _brain_emit_enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "off"])
    def test_explicit_off(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv("SULIS_BRAIN_EMIT", value)
        assert _brain_emit_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", "anything-else"])
    def test_explicit_on(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv("SULIS_BRAIN_EMIT", value)
        assert _brain_emit_enabled() is True


# ─── Change lifecycle events ────────────────────────────────────────────


class TestChangeStartedEvent:
    def test_happy_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_change_started_event(
            tmp_path, change_id="01ABC", handle="CH-01ABC",
            slug="fix-login-bug", primitive="fix",
        )
        assert result is not None
        assert result["step"] == "dna:step:01KT61X5ST01CHANGESTART00A"
        assert result.get("run_id") == "change-started:fix:fix-login-bug"
        assert result["outcome"] == "completed"
        # Persisted to disk
        ulid = result["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "lifecyclerun" / f"{ulid}.jsonld"
        ).exists()

    def test_opt_out_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_EMIT", "0")
        assert emit_change_started_event(
            tmp_path, change_id="x", handle="x", slug="x", primitive="x",
        ) is None

    def test_unwritable_base_dir_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Point base_dir at a path under a non-existent parent that's read-only
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", "/nonexistent-readonly-1234/x")
        assert emit_change_started_event(
            tmp_path, change_id="x", handle="x", slug="x", primitive="x",
        ) is None


class TestChangeShippedEvent:
    def test_happy_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_change_shipped_event(
            tmp_path, change_id="01ABC", handle="CH-01ABC",
            slug="fix-login-bug", primitive="fix",
            shipped_sha="abc1234",
        )
        assert result is not None
        assert result["step"] == "dna:step:01KT61X5ST02CHANGESH1PP00A"
        assert result.get("run_id") == "change-shipped:fix:fix-login-bug"
        assert result["outcome"] == "completed"


# ─── Generic lifecycle step event ───────────────────────────────────────


class TestLifecycleStepEvent:
    def test_happy_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_lifecycle_step_event(
            tmp_path, step_name="wpx-pipeline-success:WP-012", outcome="completed",
        )
        assert result is not None
        assert result["step"] == "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"
        assert result.get("run_id") == "wpx-pipeline-success:WP-012"
        assert result["outcome"] == "completed"

    def test_bad_outcome_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_lifecycle_step_event(
            tmp_path, step_name="x", outcome="exploded",  # not in enum
        )
        assert result is None


# ─── Deploy event ───────────────────────────────────────────────────────


class TestDeploymentEvent:
    def test_happy_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_deployment_event(
            tmp_path, release_id=_REL, environment_id=_ENV,
            outcome="succeeded",
        )
        assert result is not None
        assert result["of_release"] == _REL
        assert result["to_environment"] == _ENV
        assert result["outcome"] == "succeeded"

    def test_bad_release_ref_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_deployment_event(
            tmp_path, release_id="not-a-release",
            environment_id=_ENV, outcome="succeeded",
        )
        assert result is None  # _safely catches the ValueError


# ─── Release event ──────────────────────────────────────────────────────


class TestReleaseEvent:
    def test_happy_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_release_event(
            tmp_path, version="v0.34.0", component_ids=[_COMP],
            sbom_uri="urn:sbom:none-yet",
        )
        assert result is not None
        assert result["version"] == "v0.34.0"
        assert result["comprises"] == [_COMP]

    def test_empty_component_ids_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Don't even try to emit — schema requires minItems=1
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_release_event(
            tmp_path, version="v0.34.0", component_ids=[],
            sbom_uri="urn:sbom:x",
        )
        assert result is None


# ─── Spec-ingestion helpers ─────────────────────────────────────────────


class TestRequirementsFromSrd:
    def test_happy_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        srd_path = tmp_path / "SRD.md"
        srd_path.write_text(
            "# SRD\n\n"
            "**FR-001: Login**\n\n"
            "The system shall authenticate users.\n\n"
            "**Acceptance criteria:**\n- Valid credentials → 200.\n\n"
            "**FR-002: Logout**\n\n"
            "Users may log out.\n\n"
            "**Acceptance criteria:**\n- Logout clears session.\n"
        )
        result = emit_requirements_from_srd(tmp_path, srd_path=srd_path)
        assert result is not None
        assert len(result) == 2
        assert all(r["id"].startswith("dna:requirement:") for r in result)

    def test_missing_srd_returns_none_or_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_requirements_from_srd(tmp_path, srd_path=tmp_path / "nope.md")
        # _safely catches FileNotFoundError → returns None
        assert result is None


class TestDecisionsFromAdrs:
    def test_happy_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        adr_dir = tmp_path / "adrs"
        adr_dir.mkdir()
        # Decision emitter reads ADR frontmatter — minimum valid shape
        _ADR_BODY = (
            "## Decision\n\nUse Redis for the session cache.\n\n"
            "## Options Considered\n\n- Redis — chosen\n- Memcached — rejected\n\n"
            "## Consequences\n\nFast reads; an extra service to operate.\n"
        )
        (adr_dir / "ADR-001-cache.md").write_text(
            "---\nid: ADR-001\ntitle: Use Redis\nstatus: accepted\n---\n\n" + _ADR_BODY
        )
        (adr_dir / "ADR-002-hashing.md").write_text(
            "---\nid: ADR-002\ntitle: Argon2id\nstatus: accepted\n---\n\n" + _ADR_BODY
        )
        result = emit_decisions_from_adrs(tmp_path, adr_dir=adr_dir)
        assert result is not None
        assert len(result) == 2

    def test_missing_dir_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        result = emit_decisions_from_adrs(tmp_path, adr_dir=tmp_path / "nope")
        assert result is None

    def test_empty_dir_returns_empty_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        adr_dir = tmp_path / "adrs"
        adr_dir.mkdir()
        # No ADR files → empty list (different from None — the dir exists)
        result = emit_decisions_from_adrs(tmp_path, adr_dir=adr_dir)
        assert result == []
