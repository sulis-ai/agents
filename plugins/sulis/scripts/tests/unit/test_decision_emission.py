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

# A business decision (BDR). The body shape matches an ADR — the
# discriminator is the `kind`, supplied by the caller (`--from-bdr` /
# `--kind bdr`), not inferred from the markdown. ADR-006: `kind` is a
# discriminator on the existing decision entity, not a new entity type.
_BDR_BODY = """---
id: BDR-001
title: Ship the three phases in sequence
status: accepted
change_id: 01KSWBWMCFTVB52NGGVAAQBA7R
date: 2026-05-30
---

# BDR-001 — Ship the three phases in sequence

## Decision

Ship P1, then P2, then P3 — each phase independently reversible.

## Context

A single big-bang cutover couples three unrelated risk surfaces.

## Options Considered

- Big-bang all three phases at once — rejected; couples risk.
- Phased P1 → P2 → P3 — chosen; each phase reverts independently.

## Consequences

Slower to full feature, but each phase de-risks the next.
"""


# ─── pure-transformation tests ────────────────────────────────────────────


class TestComposeDecisionFromAdr:
    """`compose_decision_from_adr` is pure — text in, Decision dict out. No I/O."""

    def test_mints_a_fresh_ulid_id_even_when_change_id_present(self) -> None:
        # WP-012 collision fix: the @id used to be derived from `change_id`
        # (`dna:decision:{change_id}`), so two decisions in the same change
        # collapsed to the same @id and overwrote each other on disk. Each
        # emitted decision now gets its OWN fresh ULID — distinctness is the
        # invariant, change-traceability moves off the primary id.
        d = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        # The @id is a fresh ULID, NOT the change_id verbatim.
        assert d["id"] != "dna:decision:01KSQNPBPN7W74QVAZ25F79RNH"
        # Schema pattern: dna:decision:<26 Crockford-base32 chars>
        import re

        assert re.fullmatch(
            r"^dna:decision:[0-9A-HJKMNP-TV-Z]{26}$", d["id"]
        ), f"id failed schema pattern: {d['id']}"

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

        # The @id is a fresh ULID (WP-012 collision fix), not the change_id.
        import re

        assert re.fullmatch(
            r"^dna:decision:[0-9A-HJKMNP-TV-Z]{26}$", decision["id"]
        ), f"id failed schema pattern: {decision['id']}"

        # And the file is on disk under the canonical path derived from that id.
        ulid = decision["id"].rsplit(":", 1)[-1]
        written = (
            tmp_path
            / ".brain"
            / "instances"
            / "product-development"
            / "decision"
            / f"{ulid}.jsonld"
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


# ─── WP-012 — ADR/BDR kind discriminator (FR-17, ADR-006) ──────────────────


class TestKindDiscriminator:
    """A decision carries `kind ∈ {adr, bdr}`; absent reads as `adr` (§9.1)."""

    def test_emit_bdr_carries_kind_bdr(self) -> None:
        # SC-17 core: a business decision composed with kind=bdr carries
        # `kind: bdr`, distinct from a technical ADR (kind defaults to adr).
        bdr = compose_decision_from_adr(_BDR_BODY, kind="bdr")
        adr = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        assert bdr["kind"] == "bdr"
        assert adr["kind"] == "adr"
        assert bdr["kind"] != adr["kind"]

    def test_explicit_kind_adr_round_trips(self) -> None:
        adr = compose_decision_from_adr(_ADR_WITH_CHANGE_ID, kind="adr")

        assert adr["kind"] == "adr"

    def test_absent_kind_reads_as_adr(self) -> None:
        # Migration §9.1: a decision composed without a kind defaults to `adr`,
        # so existing decision/*.jsonld need no rewrite.
        d = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        assert d["kind"] == "adr"

    def test_out_of_enum_kind_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="kind must be one of"):
            compose_decision_from_adr(_ADR_WITH_CHANGE_ID, kind="strategy")

    def test_emitted_bdr_persists_and_validates_against_schema(
        self, tmp_path: Path
    ) -> None:
        # The additive-optional `kind` enum must pass the vendored compiled
        # schema's validation (the validating adapter reads it on save).
        adapter = LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )
        bdr_path = tmp_path / "BDR-001.md"
        bdr_path.write_text(_BDR_BODY)

        decision = emit_decision_from_adr(bdr_path, adapter, kind="bdr")

        assert decision["kind"] == "bdr"
        ulid = decision["id"].rsplit(":", 1)[-1]
        written = (
            tmp_path
            / ".brain"
            / "instances"
            / "product-development"
            / "decision"
            / f"{ulid}.jsonld"
        )
        assert written.exists(), f"expected persisted BDR at {written}"


class TestMultiDecisionNoIdCollision:
    """The bundled fix: ≥2 decisions in one run get distinct `@id`s."""

    def test_multi_decision_emit_no_id_collision(self, tmp_path: Path) -> None:
        # Two ADRs sharing the SAME change_id used to collapse to one @id
        # (`dna:decision:{change_id}`) and overwrite each other on disk. After
        # the fix each emission mints its own ULID, so both persist distinctly.
        adapter = LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

        # Both ADRs carry the SAME change_id frontmatter (a change that
        # produced two ADRs) — the exact pre-fix collision trigger.
        shared_change_id_adr_a = _ADR_WITH_CHANGE_ID
        shared_change_id_adr_b = _ADR_WITH_CHANGE_ID.replace(
            "title: Decouple integration from release via changesets",
            "title: A second decision in the same change",
        )
        assert "01KSQNPBPN7W74QVAZ25F79RNH" in shared_change_id_adr_b

        adr_a = tmp_path / "ADR-A.md"
        adr_a.write_text(shared_change_id_adr_a)
        adr_b = tmp_path / "ADR-B.md"
        adr_b.write_text(shared_change_id_adr_b)

        d_a = emit_decision_from_adr(adr_a, adapter)
        d_b = emit_decision_from_adr(adr_b, adapter)

        # Distinct @ids.
        assert d_a["id"] != d_b["id"], "two decisions collided on the same @id"

        # Both files survive on disk (no overwrite).
        decision_dir = (
            tmp_path / ".brain" / "instances" / "product-development" / "decision"
        )
        persisted = sorted(decision_dir.glob("*.jsonld"))
        assert len(persisted) == 2, (
            f"expected 2 distinct decision files, found {len(persisted)}: "
            f"{[p.name for p in persisted]}"
        )

    def test_compose_twice_same_source_yields_distinct_ids(self) -> None:
        # Even composing the identical ADR text twice yields distinct @ids —
        # id minting is per-emission, never a function of the source content.
        first = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)
        second = compose_decision_from_adr(_ADR_WITH_CHANGE_ID)

        assert first["id"] != second["id"]
