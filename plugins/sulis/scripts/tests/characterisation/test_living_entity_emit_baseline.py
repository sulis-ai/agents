"""Characterisation tests pinning the CURRENT living-entity emit behaviour
(WP-011) — the safety net for the WP-012 apply-evolve refactor.

Per the Characterisation-Tests-Before-Refactor MUST (CLAUDE.md EP-07 +
ADR-003 §4 apply-evolve): before WP-012 moves the Product / Opportunity /
Project emit paths from a plain ``repo.save(...)`` / atomic-write to
``evolve_entity(...)``, this test FIRST captures what those emit paths do
*today*. It is "Red" only in the written-first sense — it goes GREEN against
**unchanged** code, which is exactly the EP-07 confirm-passes step. WP-012's
refactor must keep these golden assertions true (where the observable contract
is unchanged) and extend them (where evolve adds bitemporal windows).

What is pinned today — the three living-entity emit paths:

  1. **Product** (``_product_emission``): ``compose_*`` builds a current-
     snapshot dict; ``emit_*`` writes it via ``repo.save("product", ...)``
     through ``LocalFileEntityAdapter``. One file at
     ``{base}/product-development/product/{ulid}.jsonld``. **No** bitemporal
     window chain (no ``valid_to``, no window list) and **no**
     ``wasGeneratedBy`` edge — evolution is OFF today (ADR-003 §Context).

  2. **Opportunity** (``_opportunity_emission``): same shape — a current
     snapshot via ``repo.save("opportunity", ...)``. No windows, no prov.

  3. **Project** (``_discovery._compose_entity`` + ``minter.write_project_entity``):
     mints a ``project-instances`` *bag* (NOT through the EntityRepository
     adapter — a different, atomic-file write path) at
     ``.sulis/projects/{slug}.jsonld``. The inner project dict already carries
     a single ``valid_from`` + ``confidence`` snapshot, but **no** ``valid_to``,
     **no** window list, and **no** ``wasGeneratedBy`` — the supersedes /
     window chain WP-012 + WP-015 add is NOT here yet.

These run against a **real** ``LocalFileEntityAdapter`` over a temp dir, and a
**real** atomic ``write_project_entity`` over a temp dir (MEA-09 — no mocks at
the store seam). Each test documents the observable contract it pins so WP-012
knows what must survive the refactor.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _discovery import _compose_entity
from _discovery.minter import write_project_entity
from _entity_adapter_local import LocalFileEntityAdapter
from _opportunity_emission import emit_opportunity_from_srd
from _product_emission import emit_product_from_yaml

# A LifecycleRun id that, AFTER the WP-012 refactor, will become the
# ``generated_by`` argument and produce a ``wasGeneratedBy`` edge on
# Product / Opportunity. Today it is unused by the emitters — pinning its
# ABSENCE is the point.
_RUN_ID = "dna:lifecyclerun:01JX0RUNRUNRUNRUNRUNRUNRUN"


# ─── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def adapter(tmp_path: Path) -> LocalFileEntityAdapter:
    """A real file-backed adapter over a temp dir, resolving the vendored
    product-development schemas (no mock — MEA-09)."""
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances",
        domain="product-development",
    )


def _read_saved(adapter: LocalFileEntityAdapter, entity_type: str, eid: str) -> dict:
    """Read the raw on-disk JSON the adapter wrote — the observable output."""
    path = adapter.instance_path(entity_type, eid)
    assert path.exists(), f"emitter must have written {entity_type} at {path}"
    return json.loads(path.read_text())


# ─── 1 · Product baseline ────────────────────────────────────────────────────


class TestProductEmitBaseline:
    """Pins: ``_product_emission`` composes a current-snapshot Product dict and
    writes it via ``repo.save("product", ...)`` to one file — NO bitemporal
    window chain and NO ``wasGeneratedBy`` edge today.

    WP-012 contract: after the refactor, the same load-bearing fields
    (id / name / belongs_to_tenant / state / sys_status) must still be the
    current state, and a ``wasGeneratedBy`` edge + a window chain are ADDED.
    """

    def test_current_save_behaviour_pinned(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        product_yaml = tmp_path / ".sulis" / "products" / "acme-billing.yaml"
        product_yaml.parent.mkdir(parents=True, exist_ok=True)
        product_yaml.write_text(
            "name: Acme Billing\n"
            "description: One invoice for every team\n"
            "category: saas\n"
            "state: active\n"
            "belongs_to_tenant: dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT\n",
            encoding="utf-8",
        )

        emitted = emit_product_from_yaml(product_yaml, adapter)

        # The emitter returns exactly the one composed dict it saved.
        assert len(emitted) == 1
        product = emitted[0]
        eid = product["id"]

        # The on-disk file is the observable contract WP-012 must preserve.
        saved = _read_saved(adapter, "product", eid)

        # Load-bearing fields — the current snapshot WP-012 must keep current.
        assert saved["id"] == eid
        assert saved["id"].startswith("dna:product:")
        assert saved["name"] == "Acme Billing"
        assert saved["belongs_to_tenant"] == "dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT"
        assert saved["state"] == "active"
        assert saved["sys_status"] == "active"

        # CURRENT-SNAPSHOT-ONLY pin: today there is NO bitemporal window chain
        # and NO provenance edge. WP-012 ADDS these — so their ABSENCE is the
        # baseline the refactor changes deliberately.
        assert "valid_to" not in saved, (
            "today's Product snapshot does not close a window (no valid_to) — "
            "WP-012's evolve_entity introduces the window chain"
        )
        assert "wasGeneratedBy" not in saved and "prov_constraints" not in saved, (
            "today's Product emit writes NO wasGeneratedBy edge — WP-012 adds "
            "the CONDITIONAL prov edge for this prov:Entity type"
        )
        assert _RUN_ID not in json.dumps(saved), (
            "the LifecycleRun is not referenced by today's emit — pinned absent"
        )


# ─── 2 · Opportunity baseline ────────────────────────────────────────────────


class TestOpportunityEmitBaseline:
    """Pins: ``_opportunity_emission`` composes a current-snapshot Opportunity
    dict from an SRD's ``## Summary`` and writes it via
    ``repo.save("opportunity", ...)`` — NO window chain, NO prov edge today.
    """

    def test_opportunity_emit_baseline(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        srd = tmp_path / "SRD.md"
        srd.write_text(
            "---\n"
            "title: Fast Close\n"
            "---\n"
            "## Summary\n"
            "When I close the books I want one number so I can file fast.\n"
            "\n"
            "## Scope\n"
            "Out of scope: payroll.\n",
            encoding="utf-8",
        )

        emitted = emit_opportunity_from_srd(srd, adapter)

        assert len(emitted) == 1
        opp = emitted[0]
        eid = opp["id"]

        saved = _read_saved(adapter, "opportunity", eid)

        # Load-bearing fields of the current snapshot.
        assert saved["id"] == eid
        assert saved["id"].startswith("dna:opportunity:")
        assert saved["for_product"].startswith("dna:product:")
        assert saved["job_statement"] == (
            "When I close the books I want one number so I can file fast."
        )
        assert saved["state"] == "hypothesis"
        assert saved["sys_status"] == "active"

        # CURRENT-SNAPSHOT-ONLY pin — same as Product.
        assert "valid_to" not in saved, (
            "today's Opportunity snapshot does not close a window — WP-012 adds it"
        )
        assert "wasGeneratedBy" not in saved and "prov_constraints" not in saved, (
            "today's Opportunity emit writes NO wasGeneratedBy edge — WP-012 adds "
            "the CONDITIONAL prov edge for this prov:Entity type"
        )


# ─── 3 · Project baseline ────────────────────────────────────────────────────


class TestProjectEmitBaseline:
    """Pins: the Project mint path (``_discovery._compose_entity`` +
    ``minter.write_project_entity``) — distinct from the adapter path. It builds
    a ``project-instances`` *bag* and atomically writes it under
    ``.sulis/projects/``. The inner project dict carries a single ``valid_from``
    + ``confidence`` SNAPSHOT but NO ``valid_to`` window-close, NO window list,
    and NO ``wasGeneratedBy`` (Project is a ``prov:Plan`` — it never gets a prov
    edge, even after WP-012/WP-015; it gets windows + supersedes only).
    """

    def test_project_emit_baseline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # write_project_entity enforces path-safety against
        # <consuming_repo_root>/.sulis/projects/. Patch the repo root to tmp so
        # the real atomic write runs hermetically (mirrors the minter test).
        from _discovery import minter as minter_module

        monkeypatch.setattr(minter_module, "consuming_repo_root", lambda: tmp_path)

        bag = _compose_entity(
            composed_fields={
                "name": "Sulis Agents",
                "type": "plugin",
                "version_files": ["plugins/sulis/.claude-plugin/plugin.json"],
                "branch_policy": "trunk",
                "description": "The agents plugin.",
            },
            source_repo="sulis-ai/agents",
            primary_branch="main",
            release_workflow_ref="dna:workflow:01KT0RTRA1NWFW00000000000A",
        )

        target = tmp_path / ".sulis" / "projects" / "sulis-agents.jsonld"
        write_project_entity(target, bag)

        assert target.exists(), "Project mint must write the entity bag"
        written = json.loads(target.read_text())

        # The bag is the observable contract — a project-instances envelope
        # wrapping a list of project dicts (NOT a single entity at the adapter
        # path). WP-015 reconciles this to the canonical store; pin the shape.
        assert written["@type"] == "project-instances"
        assert written["@id"] == "dna:Sulis Agents:projects"
        assert isinstance(written["projects"], list) and len(written["projects"]) == 1

        proj = written["projects"][0]
        # Load-bearing fields of the current project snapshot.
        assert proj["id"].startswith("dna:project:")
        assert proj["name"] == "Sulis Agents"
        assert proj["belongs_to_tenant"].startswith("dna:tenant:")
        assert proj["type"] == "plugin"
        assert proj["state"] == "active"
        assert proj["sys_status"] == "active"

        # Project carries a SINGLE snapshot's valid_from + confidence today —
        # NOT a closed window and NOT a window list.
        assert proj["valid_from"] == "2026-06-01T00:00:00Z"
        assert proj["confidence"] == 1.0
        assert "valid_to" not in proj, (
            "today's Project snapshot does not close a window — WP-015 adds the "
            "window chain + supersedes"
        )

        # Project is a prov:Plan — it gets NO wasGeneratedBy, today OR after the
        # refactor (ADR-002 / ADR-006). Pin its permanent absence.
        assert "wasGeneratedBy" not in proj and "prov_constraints" not in proj, (
            "Project is prov:Plan — it never carries a wasGeneratedBy edge"
        )
