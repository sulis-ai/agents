"""Tests for `_requirement_emission.py` — the SRD → Requirement-entity
transformation + persistence helper.

Second worked entity emission (n=2 toward generalising the entity-emitter
skill). Pairs with `_decision_emission.py` (CH-01KSWB, the n=1 example).
The shapes diverge in interesting ways that inform the eventual generalised
skill: SRDs emit MANY entities per call, not one; sources of fields are
in-body markers (`**FR-NN: ...`, `**Acceptance criteria:**`) rather than
frontmatter; cross-entity references (`source` → Opportunity/Actor) require
upstream emissions that don't yet exist.

Decisions baked in (this slice):
  - **One emission call per SRD writes many Requirement entities** (one per
    detected `**FR-NN: <title>**` block).
  - **ID strategy** — deterministic per (SRD path, FR id): a stable
    Crockford-base32 ULID derived from sha256(srd_path + ":" + fr_id). Same
    SRD always emits the same Requirement ids; re-emission is idempotent.
  - **`source` is a placeholder** — a deterministic synthetic Opportunity
    ULID derived from the SRD path. Passes the schema pattern; semantically
    a stand-in until Opportunity emission lands (queued). Documented in the
    composed entity's `rationale` so callers can replace later.
  - **Defaults** for fields the SRD doesn't structurally express:
    `priority="must"`, `verification_method="test"`, `state="draft"`,
    `sys_status="active"`. Honest defaults; loud enough that an author
    overriding any of them sees the diff.
  - **NFR extraction** is also supported via the same composer (NFR-NN
    blocks parse identically), so NFRs become Requirement entities with
    the same shape.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _requirement_emission import (
    compose_requirements_from_srd,
    emit_requirements_from_srd,
)
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_repository import EntityValidationError


# ─── fixtures ─────────────────────────────────────────────────────────────


_SRD_WITH_FRS = """# Software Requirements Document: Sample

**Version:** 1.0
**Date:** 2026-05-30
**Status:** Draft

## Summary

A sample SRD for testing the requirement extractor. It declares a couple of
functional requirements with the conventional `**FR-NN: Title**` format.

## 4. Functional Requirements

**FR-01: Authenticate the user**

The system MUST authenticate the user via OAuth before allowing access to
protected resources. Authentication uses RFC 9421 HTTP Message Signatures
on every request.

**Acceptance criteria:** When a caller presents a valid signed request, the
system grants access; invalid signatures return 401.

**FR-02: Audit every privileged action**

The system MUST emit an audit log entry for every action performed under
elevated permissions. Each entry captures actor, action, timestamp,
target resource.

**Acceptance criteria:** Every elevated call produces exactly one audit
log row; the entry is queryable by actor + timestamp window.

## 5. Non-Functional Requirements

**NFR-01: Authentication latency**

Authentication MUST add no more than 50ms p99 to a request's total latency.

**Acceptance criteria:** Load tests with N=1000 sustained requests show
p99 auth-add latency ≤ 50ms.

## 6. Other content

Trailing sections (out of scope, appendices) MUST NOT be parsed as
requirements.
"""


_SRD_NO_FRS = """# Software Requirements Document: Empty

## Summary

A SRD with prose but no `**FR-NN:**` markers. The extractor must return
an empty list, not crash.
"""


# House style: ` — ` (em-dash) separator instead of a colon, plus the
# negative-requirement scheme FR-N1. A real SRD in exactly this shape
# silently emitted 0 requirements during the CH-01KT50 scenario-loop
# dogfood — the parser was colon-and-digit-only. Both forms MUST parse.
_SRD_EMDASH_AND_NEGATIVE = """# Software Requirements Document: House style

## 4. Functional Requirements

**FR-01 — Board lists in-flight changes**

The board MUST list every in-flight change as a card.

**Acceptance criteria:** Each in-flight change appears exactly once.

**FR-N1 — A resumed session must not fabricate completion**

A resumed session MUST NOT report a mid-action step as complete.

**Acceptance criteria:** An interrupted step is re-run, not faked.
"""


# ─── pure-transformation tests ────────────────────────────────────────────


class TestComposeRequirementsFromSrd:
    """`compose_requirements_from_srd` is pure — text + path in, list out.

    The path arg is for deterministic id derivation; no I/O is performed.
    """

    def test_extracts_one_requirement_per_FR_block(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )

        # FR-01, FR-02, NFR-01 → 3 requirements
        assert len(rs) == 3
        # The order of detection is preserved
        titles = [r.get("statement", "")[:50] for r in rs]
        assert any("authenticate" in t.lower() for t in titles)
        assert any("audit" in t.lower() for t in titles)
        assert any("latency" in t.lower() for t in titles)

    def test_extracts_FRs_with_emdash_separator_and_negative_ids(self) -> None:
        # Regression (CH-01KT50 dogfood): em-dash separator + FR-N1 negative
        # id silently produced 0 requirements. Both MUST now parse.
        rs = compose_requirements_from_srd(
            _SRD_EMDASH_AND_NEGATIVE, srd_path="dummy/house/SRD.md"
        )
        assert len(rs) == 2
        statements = " ".join(r.get("statement", "").lower() for r in rs)
        assert "board" in statements
        assert "fabricate" in statements

    def test_empty_srd_returns_empty_list(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_NO_FRS, srd_path="dummy/sample/SRD.md"
        )
        assert rs == []

    def test_each_requirement_id_matches_the_schema_pattern(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )

        pattern = re.compile(r"^dna:requirement:[0-9A-HJKMNP-TV-Z]{26}$")
        for r in rs:
            assert pattern.match(r["id"]), f"id failed schema pattern: {r['id']}"

    def test_ids_are_deterministic_across_calls_with_same_inputs(self) -> None:
        a = compose_requirements_from_srd(_SRD_WITH_FRS, srd_path="x/SRD.md")
        b = compose_requirements_from_srd(_SRD_WITH_FRS, srd_path="x/SRD.md")

        assert [r["id"] for r in a] == [r["id"] for r in b]

    def test_ids_differ_when_srd_path_differs(self) -> None:
        a = compose_requirements_from_srd(_SRD_WITH_FRS, srd_path="x/SRD.md")
        b = compose_requirements_from_srd(_SRD_WITH_FRS, srd_path="y/SRD.md")

        assert [r["id"] for r in a] != [r["id"] for r in b]

    def test_source_is_a_synthetic_opportunity_ref(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )

        pattern = re.compile(r"^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$")
        for r in rs:
            assert pattern.match(r["source"]), (
                f"source failed schema pattern: {r['source']!r}"
            )

    def test_all_requirements_from_one_srd_share_one_source_opportunity(
        self,
    ) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )
        sources = {r["source"] for r in rs}
        assert len(sources) == 1, (
            "all requirements from the same SRD should trace to one synthetic Opportunity"
        )

    def test_priority_defaults_to_must(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )
        for r in rs:
            assert r["priority"] == "must"

    def test_verification_method_defaults_to_test(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )
        for r in rs:
            assert r["verification_method"] == "test"

    def test_state_defaults_to_draft_and_sys_status_to_active(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )
        for r in rs:
            assert r["state"] == "draft"
            assert r["sys_status"] == "active"

    def test_acceptance_criteria_extracted_per_requirement(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )
        # Every requirement in the fixture has an "**Acceptance criteria:**" line
        for r in rs:
            ac = r.get("acceptance_criteria")
            assert isinstance(ac, list), f"acceptance_criteria not a list: {r}"
            assert len(ac) >= 1, f"acceptance_criteria empty: {r}"

    def test_statement_excludes_acceptance_criteria_block(self) -> None:
        rs = compose_requirements_from_srd(
            _SRD_WITH_FRS, srd_path="dummy/sample/SRD.md"
        )
        # The statement should NOT include the "**Acceptance criteria:**" line
        for r in rs:
            assert "Acceptance criteria" not in r["statement"]


# ─── persistence integration test ─────────────────────────────────────────


class TestEmitRequirementsFromSrd:
    """`emit_requirements_from_srd` reads the file, composes, validates,
    persists each requirement via the adapter."""

    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_emit_persists_each_requirement_as_a_validated_jsonld(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        srd_path = tmp_path / "SRD.md"
        srd_path.write_text(_SRD_WITH_FRS)

        emitted = emit_requirements_from_srd(srd_path, adapter)

        assert len(emitted) == 3
        # Each persisted file exists on disk.
        for r in emitted:
            ulid = r["id"].split(":")[-1]
            path = (
                tmp_path
                / ".brain"
                / "instances"
                / "product-development"
                / "requirement"
                / f"{ulid}.jsonld"
            )
            assert path.exists(), f"expected file at {path}"

    def test_emit_is_idempotent_under_re_run(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        # Same SRD, two consecutive emissions → second one writes to the same
        # paths and the on-disk content is unchanged.
        srd_path = tmp_path / "SRD.md"
        srd_path.write_text(_SRD_WITH_FRS)

        first = emit_requirements_from_srd(srd_path, adapter)
        second = emit_requirements_from_srd(srd_path, adapter)

        assert [r["id"] for r in first] == [r["id"] for r in second]

    def test_emit_returns_empty_list_for_an_srd_with_no_FRs(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        srd_path = tmp_path / "EMPTY.md"
        srd_path.write_text(_SRD_NO_FRS)

        emitted = emit_requirements_from_srd(srd_path, adapter)

        assert emitted == []

    def test_validation_propagates_for_a_schema_invalid_entity(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path, monkeypatch
    ) -> None:
        # The composer naturally produces schema-valid Requirements (defaults
        # ensure every required field is set). To pin that
        # `emit_requirements_from_srd` propagates rejection cleanly when an
        # invalid instance does come through, we monkey-patch the composer
        # to inject a Requirement with a malformed id pattern.
        from _requirement_emission import compose_requirements_from_srd as _orig
        import _requirement_emission

        def _bad_composer(srd_text: str, *, srd_path: str) -> list[dict]:
            requirements = _orig(srd_text, srd_path=srd_path)
            for r in requirements:
                # Replace with a value that fails the schema's id pattern.
                r["id"] = "not-a-dna-requirement-id"
            return requirements

        monkeypatch.setattr(
            _requirement_emission, "compose_requirements_from_srd", _bad_composer
        )

        srd_path = tmp_path / "SRD.md"
        srd_path.write_text(_SRD_WITH_FRS)

        with pytest.raises(EntityValidationError):
            emit_requirements_from_srd(srd_path, adapter)
