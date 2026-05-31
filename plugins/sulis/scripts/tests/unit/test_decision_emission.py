"""Tests for `_decision_emission.py` — the ADR → Decision-entity transformation
+ persistence helper.

This is the D1 wire-up: when `/sulis:draft-architecture` writes an ADR file,
the same flow emits a structured Decision entity through the EntityRepository
port (validated against the vendored compiled schema).

Decisions taken (confirmed by founder):
  - ID strategy: reuse the ADR's `change_id` frontmatter (→
    `dna:decision:{change_id}`) when present; generate a fresh ULID otherwise.
  - Section extraction: parse `## Context` / `## Decision` /
    `## Options Considered` (with `Alternatives considered` synonym) /
    `## Consequences` from the markdown body.
  - Status→state translation: ADR's `status: accepted` → entity's
    `state: accepted` (the schema's two-lifecycle model means `status` is
    storage-lifecycle now; we translate the ADR's old vocabulary at the
    emitter boundary, not by changing the ADR convention).
  - `sys_status` is always `"active"` on emission.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _decision_emission import (
    compose_decision_from_adr,
    emit_decision_from_adr,
)
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_repository import EntityValidationError


# ─── fixtures ─────────────────────────────────────────────────────────────


_ADR_WITH_CHANGE_ID = """---
id: ADR-001
title: Decouple integration from release via changesets
status: accepted
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
date: 2026-05-28
closes: 66
---

# ADR-001 — Decouple integration from release via changesets

## Decision

Integration and release are separated into two distinct acts. Each change
writes a changeset; release batches them into one deterministic bump.

## Context

`/sulis:change ship` couples integration with release and leaves the release
half to agent discipline. There is no mandated, enforced bump step.

## Options Considered

- Per-change bump as a required ship step — rejected; keeps the version race.
- Manual bump, better-documented — rejected; docs don't enforce.
- Changeset-based release-train — chosen; eliminates the per-change bump race.

## Consequences

The bump becomes deterministic and enforced; the version race is structurally
impossible.
"""

_ADR_NO_CHANGE_ID = """---
id: ADR-099
title: Pick PostgreSQL for the order store
status: proposed
date: 2026-05-30
---

# ADR-099 — Pick PostgreSQL for the order store

## Decision

PostgreSQL with logical replication.

## Context

We need durable, queryable order storage.

## Options Considered

- PostgreSQL with logical replication.
- DynamoDB.
- MySQL.

## Consequences

Higher operational complexity, better durability.
"""

_ADR_ALTERNATIVES_HEADING = """---
id: ADR-002
title: Sample with alternates heading
status: accepted
change_id: 01KSWBWMCFTVB52NGGVAAQBA7R
date: 2026-05-30
---

# ADR-002 — Sample

## Decision

Choose A.

## Context

Reason for the choice.

## Alternatives considered

1. **Option A (chosen).** Best fit.
2. **Option B.** Rejected because reasons.

## Consequences

Mostly positive.
"""


# ─── pure-transformation tests ────────────────────────────────────────────


class TestComposeDecisionFromAdr:
    """`compose_decision_from_adr` is pure — text in, Decision dict out. No I/O."""

    def test_reuses_change_id_from_frontmatter_when_present(self) -> None:
        d = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        assert d["id"] == "dna:decision:01KSQNPBPN7W74QVAZ25F79RNH"

    def test_generates_fresh_ulid_when_change_id_missing(self) -> None:
        d = compose_decision_from_adr(_ADR_NO_CHANGE_ID)

        # Schema pattern: dna:decision:<26 Crockford-base32 chars>
        import re

        assert re.fullmatch(
            r"^dna:decision:[0-9A-HJKMNP-TV-Z]{26}$", d["id"]
        ), f"id failed schema pattern: {d['id']}"

    def test_extracts_title_and_translates_status_to_state(self) -> None:
        d = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        assert d["title"] == "Decouple integration from release via changesets"
        # ADR's `status: accepted` → entity's `state: accepted` (two-lifecycle
        # translation at the emitter boundary)
        assert d["state"] == "accepted"

    def test_sys_status_is_always_active_on_emission(self) -> None:
        d = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        assert d["sys_status"] == "active"

    def test_extracts_context_decision_consequences_prose_sections(self) -> None:
        d = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        # Context, decision, consequences are joined-prose strings.
        assert "Integration and release are separated" in d["decision"]
        assert "/sulis:change ship" in d["context"]
        assert "structurally" in d["consequences"]

    def test_extracts_options_considered_as_array_of_at_least_one_item(
        self,
    ) -> None:
        d = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        # Schema: text[1..*]
        assert isinstance(d["options_considered"], list)
        assert len(d["options_considered"]) >= 1
        # The bullet item content should be in there somewhere
        joined = " | ".join(d["options_considered"])
        assert "Per-change bump" in joined
        assert "Changeset-based" in joined

    def test_options_considered_tolerant_of_alternatives_synonym(self) -> None:
        # The real ADR-001 we shipped used `## Alternatives considered` —
        # extractor must accept that synonym too.
        d = compose_decision_from_adr(_ADR_ALTERNATIVES_HEADING)

        assert isinstance(d["options_considered"], list)
        assert len(d["options_considered"]) >= 1
        joined = " | ".join(d["options_considered"])
        assert "Option A" in joined


# ─── persistence integration test ─────────────────────────────────────────


class TestEmitDecisionFromAdr:
    """`emit_decision_from_adr` reads the file, composes, validates, persists."""

    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_emit_writes_a_validated_jsonld_file(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        adr_path = tmp_path / "ADR-001.md"
        adr_path.write_text(_ADR_WITH_CHANGE_ID)

        decision = emit_decision_from_adr(adr_path, adapter)

        # Returned decision dict matches what got persisted.
        assert decision["id"] == "dna:decision:01KSQNPBPN7W74QVAZ25F79RNH"

        # And the file is on disk under the canonical path.
        written = (
            tmp_path
            / ".brain"
            / "instances"
            / "product-development"
            / "decision"
            / "01KSQNPBPN7W74QVAZ25F79RNH.jsonld"
        )
        assert written.exists(), f"expected file at {written}"

    def test_emit_rejects_malformed_adr_with_no_decision_section(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        bad_adr = """---
id: ADR-099
title: Missing the decision section
status: proposed
date: 2026-05-30
---

# ADR-099

## Context
Something.
"""
        adr_path = tmp_path / "ADR-099.md"
        adr_path.write_text(bad_adr)

        with pytest.raises(EntityValidationError) as exc_info:
            emit_decision_from_adr(adr_path, adapter)

        # The error must surface that the required `decision` field is missing.
        assert "decision" in str(exc_info.value).lower()
