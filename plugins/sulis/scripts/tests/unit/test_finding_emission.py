"""Tests for `_finding_emission.py` — sixth worked entity emission.

Replaces the `findings-register.md` danger-class artifact. Two source
modes — single per-finding (called by check skills) and bulk-from-register
(migration of existing legacy findings).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _finding_emission import (
    compose_finding,
    compose_findings_from_register,
    emit_finding,
    emit_findings_from_register,
)
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_repository import EntityValidationError


class TestComposeFindingSingle:
    def test_minimum_valid_finding(self) -> None:
        f = compose_finding(
            kind="security",
            severity="high",
            summary="SSRF in /api/proxy",
        )
        assert re.fullmatch(r"^dna:finding:[0-9A-HJKMNP-TV-Z]{26}$", f["id"])
        assert f["kind"] == "security"
        assert f["severity"] == "high"
        assert f["summary"] == "SSRF in /api/proxy"
        assert f["state"] == "open"
        assert f["sys_status"] == "active"
        # observed_at defaults to "now" — at minimum it's a non-empty ISO-ish string
        assert isinstance(f["observed_at"], str) and len(f["observed_at"]) >= 10
        # No observed_in unless a real typed ref was passed
        assert "observed_in" not in f

    def test_free_form_locator_folded_into_summary_not_observed_in(self) -> None:
        # observed_in is a TYPED ref to Component/Release/Deployment per the
        # schema. Free-form locators (file:line) get folded into the summary
        # so they're not lost; observed_in stays empty until Component
        # emission lands and call sites can pass real refs.
        f = compose_finding(
            kind="security",
            severity="high",
            summary="SSRF in /api/proxy",
            observed_in="apps/api/src/proxy.py:42",
        )
        assert "apps/api/src/proxy.py:42" in f["summary"]
        assert "observed_in" not in f

    def test_typed_observed_in_ref_is_preserved(self) -> None:
        component_id = "dna:component:01ABCDEFGHJKMNPQRSTVWXYZ12"
        f = compose_finding(
            kind="security",
            severity="high",
            summary="SSRF",
            observed_in=component_id,
        )
        assert f["observed_in"] == component_id

    def test_id_is_deterministic_from_signature(self) -> None:
        a = compose_finding(kind="security", severity="high", summary="X", observed_in="a:1")
        b = compose_finding(kind="security", severity="high", summary="X", observed_in="a:1")
        assert a["id"] == b["id"]

    def test_id_differs_for_different_summary(self) -> None:
        a = compose_finding(kind="security", severity="high", summary="X")
        b = compose_finding(kind="security", severity="high", summary="Y")
        assert a["id"] != b["id"]

    def test_id_differs_for_different_locator(self) -> None:
        # Locator folds into summary; two locators → two summaries → two ids.
        a = compose_finding(kind="security", severity="high", summary="X", observed_in="file_a:1")
        b = compose_finding(kind="security", severity="high", summary="X", observed_in="file_b:1")
        assert a["id"] != b["id"]

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="kind"):
            compose_finding(kind="not-a-kind", severity="high", summary="X")

    def test_invalid_severity_raises(self) -> None:
        with pytest.raises(ValueError, match="severity"):
            compose_finding(kind="security", severity="EXTREME", summary="X")

    def test_empty_summary_raises(self) -> None:
        with pytest.raises(ValueError, match="summary"):
            compose_finding(kind="security", severity="high", summary="   ")

    def test_omits_observed_in_when_empty(self) -> None:
        f = compose_finding(kind="other", severity="info", summary="generic")
        assert "observed_in" not in f


class TestComposeFindingsFromRegister:
    def test_parses_a_legacy_register(self, tmp_path: Path) -> None:
        register = tmp_path / "findings-register.md"
        register.write_text(
            "# Findings register\n"
            "\n"
            "| ID | kind | severity | observed_in | summary | signature |\n"
            "|---|---|---|---|---|---|\n"
            "| SF-001 | security | high | apps/api/src/proxy.py:42 | SSRF in /api/proxy | sig1 |\n"
            "| SF-002 | code-quality | medium | apps/api/src/login.py:88 | nested try/except hides errors | sig2 |\n"
            "| SF-003 | accessibility | low | apps/web/src/Dialog.tsx:12 | missing aria-label on close button | sig3 |\n"
        )

        findings = compose_findings_from_register(register)
        assert len(findings) == 3
        assert findings[0]["kind"] == "security"
        assert findings[1]["severity"] == "medium"
        assert "aria-label" in findings[2]["summary"]

    def test_skips_malformed_rows_silently(self, tmp_path: Path) -> None:
        register = tmp_path / "findings-register.md"
        register.write_text(
            "| SF-001 | invalid-kind | high | a:1 | X | sig |\n"
            "| SF-002 | security | high | b:1 | Y | sig |\n"
        )

        findings = compose_findings_from_register(register)
        # First row has invalid kind → skipped. Second row valid → emitted.
        assert len(findings) == 1
        assert findings[0]["kind"] == "security"


class TestEmitFinding:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists_finding_jsonld(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        f = emit_finding(
            repo=adapter,
            kind="security",
            severity="high",
            summary="SSRF in /api/proxy at apps/api/src/proxy.py:42",
        )
        ulid = f["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "finding" / f"{ulid}.jsonld"
        ).exists()

    def test_bulk_persists_all_findings(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        register = tmp_path / "register.md"
        register.write_text(
            "| SF-001 | security | high | file_a:1 | First | sig1 |\n"
            "| SF-002 | code-quality | low | file_b:1 | Second | sig2 |\n"
        )
        emitted = emit_findings_from_register(register, adapter)
        assert len(emitted) == 2

    def test_validation_propagates(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path, monkeypatch
    ) -> None:
        # Inject a Finding with a malformed id to exercise the adapter's
        # rejection path.
        from _finding_emission import compose_finding as _orig
        import _finding_emission

        def _bad(**kwargs):
            f = _orig(**kwargs)
            f["id"] = "not-a-valid-dna-id"
            return f

        monkeypatch.setattr(_finding_emission, "compose_finding", _bad)

        with pytest.raises(EntityValidationError):
            emit_finding(
                repo=adapter, kind="security", severity="high", summary="X"
            )
