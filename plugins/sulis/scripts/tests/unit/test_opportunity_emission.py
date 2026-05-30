"""Tests for `_opportunity_emission.py` — fifth worked entity emission.

Closes the synthetic-placeholder loop CH-01KSWQ opened: Opportunity emitter
produces the SAME id that Requirement emitter generates as a synthetic
source for the same SRD. The graph self-resolves.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _opportunity_emission import (
    compose_opportunity_from_srd,
    emit_opportunity_from_srd,
    _opportunity_id_for_srd,
)
from _requirement_emission import compose_requirements_from_srd
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_repository import EntityValidationError


_SRD = """---
title: Sample SRD
---

# Software Requirements Document: Sample

## Summary

Teams need a shared todo list so collaboration on small tasks doesn't get
buried in email threads. Today, a team of 5 loses ~15 mins per day to
"who's doing X?" pings.

## 4. Functional Requirements

**FR-01: Authenticate the user**

The system MUST authenticate the user via OAuth.

**Acceptance criteria:** Valid signed request grants access.
"""

_SRD_NO_SUMMARY = """# A Plain Document

No summary, no introduction, no body section labels. Nothing for the
extractor to lock onto.
"""

_SRD_INTRODUCTION = """# Software Requirements Document

## Introduction

A pricing engine for B2B SaaS where customers self-serve their plan.
"""


class TestComposeOpportunity:
    def test_extracts_one_opportunity_per_srd(self) -> None:
        result = compose_opportunity_from_srd(_SRD, srd_path="/srd/sample.md")
        assert len(result) == 1

    def test_id_matches_schema_pattern(self) -> None:
        result = compose_opportunity_from_srd(_SRD, srd_path="/srd/sample.md")
        assert re.fullmatch(
            r"^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$", result[0]["id"]
        )

    def test_job_statement_extracted_from_summary(self) -> None:
        result = compose_opportunity_from_srd(_SRD, srd_path="/srd/sample.md")
        js = result[0]["job_statement"]
        assert "Teams need a shared todo list" in js
        # And NOT the FR content (proves the section-boundary stops at the
        # next H2)
        assert "Authenticate" not in js

    def test_state_defaults_to_hypothesis(self) -> None:
        result = compose_opportunity_from_srd(_SRD, srd_path="/srd/sample.md")
        assert result[0]["state"] == "hypothesis"

    def test_introduction_synonym_works(self) -> None:
        # SRDs that use `## Introduction` instead of `## Summary` should also work.
        result = compose_opportunity_from_srd(_SRD_INTRODUCTION, srd_path="/srd/x.md")
        assert len(result) == 1
        assert "pricing engine" in result[0]["job_statement"]

    def test_srd_with_no_summary_returns_empty(self) -> None:
        assert compose_opportunity_from_srd(_SRD_NO_SUMMARY, srd_path="/srd/x.md") == []

    def test_id_is_deterministic_from_srd_path(self) -> None:
        a = compose_opportunity_from_srd(_SRD, srd_path="/srd/x.md")
        b = compose_opportunity_from_srd(_SRD, srd_path="/srd/x.md")
        assert a[0]["id"] == b[0]["id"]

    def test_for_product_passes_pattern(self) -> None:
        result = compose_opportunity_from_srd(_SRD, srd_path="/srd/x.md")
        assert re.fullmatch(
            r"^dna:product:[0-9A-HJKMNP-TV-Z]{26}$", result[0]["for_product"]
        )

    def test_optional_impact_pulled_from_frontmatter_title(self) -> None:
        result = compose_opportunity_from_srd(_SRD, srd_path="/srd/x.md")
        assert result[0]["impact"] == "Sample SRD"


# ─── critical cross-emitter ID coordination ───────────────────────────────


class TestRequirementOpportunityIdAlignment:
    """The synthetic Opportunity ID that the Requirement emitter generates
    for an SRD MUST equal the real Opportunity ID this emitter produces for
    the same SRD. Otherwise the graph never resolves and Requirements remain
    forever-orphaned from their Opportunity.
    """

    def test_opportunity_id_matches_requirement_emitter_synthetic_id(self) -> None:
        srd_path = "/some/srd/path.md"

        reqs = compose_requirements_from_srd(_SRD, srd_path=srd_path)
        opps = compose_opportunity_from_srd(_SRD, srd_path=srd_path)

        assert len(opps) == 1
        opp_id = opps[0]["id"]

        # Every Requirement's `source` should be the Opportunity we'd emit
        # from the same SRD. Now that Opportunity emission is real, the
        # Requirement's "synthetic" placeholder becomes the real entity's id.
        for r in reqs:
            assert r["source"] == opp_id, (
                "Requirement.source should equal real Opportunity.id for the "
                "same SRD — cross-emitter ID coordination broken"
            )


class TestEmitOpportunity:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists_opportunity_jsonld(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        srd_path = tmp_path / "SRD.md"
        srd_path.write_text(_SRD)
        emitted = emit_opportunity_from_srd(srd_path, adapter)
        assert len(emitted) == 1
        ulid = emitted[0]["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "opportunity" / f"{ulid}.jsonld"
        ).exists()

    def test_emit_no_summary_returns_empty_no_error(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        srd_path = tmp_path / "SRD.md"
        srd_path.write_text(_SRD_NO_SUMMARY)
        emitted = emit_opportunity_from_srd(srd_path, adapter)
        assert emitted == []
