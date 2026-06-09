"""End-to-end integration test for the Brain↔OS golden-thread.

This is the real proof of the cross-emitter ID coordination. Six emitters
exist today; this test exercises them in their natural sequence against a
synthetic project layout, then validates that the emitted entity graph
**resolves** — every cross-entity ref points at a real, persisted entity
of the right type.

The test stands in for what `/sulis:specify` → `/sulis:draft-architecture`
will eventually produce when wired end-to-end. Until those skill wirings
ship, this test is the closest demonstration of the substrate working as
one coherent thing.

The chain it validates:

    Tenant (foundation)
      ↑ Product.belongs_to_tenant
      Product
        ↑ Opportunity.for_product
        Opportunity
          ↑ Requirement.source (via the synthetic-id-now-real-id alignment)
          Requirement (existing CH-01KSWQ emitter)

Plus standalone:
    Decision (from ADR; no required cross-refs)
    Finding (free-standing; observed_in optional)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _tenant_emission import emit_tenant_from_yaml
from _product_emission import emit_product_from_yaml
from _opportunity_emission import emit_opportunity_from_srd
from _requirement_emission import emit_requirements_from_srd
from _decision_emission import emit_decision_from_adr
from _finding_emission import emit_finding


_TENANT_YAML = """
name: Sulis AI
kind: company
legal_name: Sulis AI Ltd
state: active
"""

_PRODUCT_YAML = """
name: Team Todo App
description: A shared todo list for teams
category: saas
state: active
"""

_SRD = """---
title: Team Todo App SRD
---

# Software Requirements Document

## Summary

Teams need a shared todo list so collaboration on small tasks doesn't get
buried in email threads.

## 4. Functional Requirements

**FR-01: Authenticate user**

The system MUST authenticate users via OAuth.

**Acceptance criteria:** A valid signed request grants access.

**FR-02: Create todos**

The system MUST allow users to create todos visible to their team.

**Acceptance criteria:** A POST to /todos persists and notifies the team.
"""

_ADR = """---
id: ADR-001
title: Pick PostgreSQL for the todo store
status: accepted
change_id: 01ABCDEFGHJKMNPQRSTVWXYZ12
date: 2026-05-30
---

# ADR-001 — PostgreSQL

## Decision

Use PostgreSQL with logical replication.

## Context

We need durable, queryable storage for shared todos.

## Options Considered

- PostgreSQL — chosen, proven.
- DynamoDB — rejected, eventual consistency conflicts with team-visibility expectations.

## Consequences

Higher ops overhead, better durability and queryability.
"""


def _layout(tmp_path: Path) -> dict:
    """Build a realistic project layout under tmp_path."""
    sulis = tmp_path / ".sulis"
    products_dir = sulis / "products"
    products_dir.mkdir(parents=True)
    arch_dir = tmp_path / ".architecture" / "team-todo" / "adrs"
    arch_dir.mkdir(parents=True)
    spec_dir = tmp_path / ".specifications" / "team-todo"
    spec_dir.mkdir(parents=True)

    paths = {
        "tenant_yaml": sulis / "tenant.yaml",
        "product_yaml": products_dir / "team-todo-app.yaml",
        "srd": spec_dir / "SRD.md",
        "adr": arch_dir / "ADR-001-postgres.md",
    }
    paths["tenant_yaml"].write_text(_TENANT_YAML)
    paths["product_yaml"].write_text(_PRODUCT_YAML)
    paths["srd"].write_text(_SRD)
    paths["adr"].write_text(_ADR)
    return paths


@pytest.fixture
def foundation_adapter(tmp_path: Path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances",
        domain="foundation",
    )


@pytest.fixture
def pd_adapter(tmp_path: Path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances",
        domain="product-development",
    )


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _instance_path(tmp_path: Path, domain: str, entity_type: str, entity_id: str) -> Path:
    ulid = entity_id.rsplit(":", 1)[-1]
    return tmp_path / ".brain" / "instances" / domain / entity_type / f"{ulid}.jsonld"


class TestGoldenThreadEndToEnd:
    """One project; six emitters in sequence; the graph resolves."""

    def test_full_chain_resolves(
        self,
        tmp_path: Path,
        foundation_adapter: LocalFileEntityAdapter,
        pd_adapter: LocalFileEntityAdapter,
    ) -> None:
        paths = _layout(tmp_path)

        # ── Emit each entity ────────────────────────────────────────────

        tenants = emit_tenant_from_yaml(paths["tenant_yaml"], foundation_adapter)
        products = emit_product_from_yaml(paths["product_yaml"], pd_adapter)
        opportunities = emit_opportunity_from_srd(paths["srd"], pd_adapter)
        requirements = emit_requirements_from_srd(paths["srd"], pd_adapter)
        decision = emit_decision_from_adr(paths["adr"], pd_adapter)
        finding = emit_finding(
            repo=pd_adapter,
            kind="security",
            severity="high",
            summary="SSRF risk in /api/proxy (apps/api/src/proxy.py:42)",
        )

        # ── Every emitted file exists on disk ───────────────────────────

        assert _instance_path(tmp_path, "foundation", "tenant", tenants[0]["id"]).exists()
        assert _instance_path(tmp_path, "product-development", "product", products[0]["id"]).exists()
        assert _instance_path(tmp_path, "product-development", "opportunity", opportunities[0]["id"]).exists()
        for r in requirements:
            assert _instance_path(tmp_path, "product-development", "requirement", r["id"]).exists()
        assert _instance_path(tmp_path, "product-development", "decision", decision["id"]).exists()
        assert _instance_path(tmp_path, "product-development", "finding", finding["id"]).exists()

        # ── The graph resolves — each cross-ref points at a real entity ─

        # Product.belongs_to_tenant → Tenant.id
        product = _load(_instance_path(tmp_path, "product-development", "product", products[0]["id"]))
        assert product["belongs_to_tenant"] == tenants[0]["id"], (
            "Product.belongs_to_tenant should equal the emitted Tenant.id"
        )

        # Requirement.source → Opportunity.id (the critical alignment that
        # closes the CH-01KSWQ synthetic-placeholder loop)
        opp = _load(_instance_path(tmp_path, "product-development", "opportunity", opportunities[0]["id"]))
        for r in requirements:
            r_jsonld = _load(_instance_path(tmp_path, "product-development", "requirement", r["id"]))
            assert r_jsonld["source"] == opp["id"], (
                f"Requirement {r['id']}.source should equal Opportunity.id — "
                "cross-emitter ID coordination broken if this fires"
            )

        # And the count of expected entities
        assert len(tenants) == 1
        assert len(products) == 1
        assert len(opportunities) == 1
        assert len(requirements) == 2  # FR-01, FR-02

    def test_chain_is_idempotent_under_re_run(
        self,
        tmp_path: Path,
        foundation_adapter: LocalFileEntityAdapter,
        pd_adapter: LocalFileEntityAdapter,
    ) -> None:
        """Re-running each emitter on the same source confirms its ID
        strategy. Four emitters (tenant, product, opportunity, requirement)
        are deterministic — same source ⇒ same IDs, no duplicates. The
        decision emitter is intentionally NOT idempotent by @id (WP-012): each
        emission mints a fresh ULID so two decisions from the same change
        never collide on one @id, so a re-run yields a distinct decision @id.
        """
        paths = _layout(tmp_path)

        # First pass
        t1 = emit_tenant_from_yaml(paths["tenant_yaml"], foundation_adapter)
        p1 = emit_product_from_yaml(paths["product_yaml"], pd_adapter)
        o1 = emit_opportunity_from_srd(paths["srd"], pd_adapter)
        r1 = emit_requirements_from_srd(paths["srd"], pd_adapter)
        d1 = emit_decision_from_adr(paths["adr"], pd_adapter)

        # Second pass
        t2 = emit_tenant_from_yaml(paths["tenant_yaml"], foundation_adapter)
        p2 = emit_product_from_yaml(paths["product_yaml"], pd_adapter)
        o2 = emit_opportunity_from_srd(paths["srd"], pd_adapter)
        r2 = emit_requirements_from_srd(paths["srd"], pd_adapter)
        d2 = emit_decision_from_adr(paths["adr"], pd_adapter)

        assert t1[0]["id"] == t2[0]["id"]
        assert p1[0]["id"] == p2[0]["id"]
        assert o1[0]["id"] == o2[0]["id"]
        assert [r["id"] for r in r1] == [r["id"] for r in r2]
        # Decision is intentionally per-emission distinct (WP-012 collision
        # fix): a re-run mints a fresh ULID, so the @ids differ.
        assert d1["id"] != d2["id"]
