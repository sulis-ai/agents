"""Characterisation tests for the living-entity emit paths — UPDATED by WP-012
(apply-evolve) to the POST-refactor behaviour.

History (EP-07 characterisation discipline): WP-011 first authored this file to
pin the *pre-refactor* current-snapshot behaviour (the safety net) and confirmed
it green against unchanged code. WP-012 then performed the refactor and, per the
Characterisation-Tests-Before-Refactor MUST, UPDATES the golden assertions here
in lockstep with the behaviour change — keeping the load-bearing emit fields
pinned (what must NOT change) and re-pointing the window / provenance assertions
to the new, correct shape (what the refactor deliberately adds). The diff between
the WP-011 baseline and this file IS the documented proof the behaviour change is
intentional and matches ADR-002 / ADR-003 / ADR-006.

What changed at WP-012:

  1. **Product** (``_product_emission``) — NOW a *living* ``prov:Entity``. The
     emit delegates to ``evolve_entity`` instead of ``repo.save``: the on-disk
     file is a history *envelope* (``{"windows": [...]}``); the current open
     window carries ``valid_from`` (``valid_to`` null while open), the
     load-bearing current-state fields (id / name / belongs_to_tenant / state /
     sys_status), and — when the emit context supplies the producing LifecycleRun
     ref via ``generated_by`` — the conditional ``wasGeneratedBy`` edge.

  2. **Opportunity** (``_opportunity_emission``) — same: a history envelope
     whose open window carries the load-bearing fields + the conditional
     ``wasGeneratedBy`` (``prov:Entity``).

  3. **Project** (``_discovery._compose_entity`` + ``minter.write_project_entity``):
     **UNCHANGED at WP-012.** Project's mint still writes a ``project-instances``
     *bag* atomically at ``.sulis/projects/{slug}.jsonld``, NOT through the
     EntityRepository port — so the WP-012 evolve refactor does not touch it.
     Routing Project through the port (so ``evolve_entity`` applies) is the
     ADR-006 reconciliation owned by **WP-015** (gated by WP-014's minter
     characterisation test). The Project baseline below therefore still pins the
     CURRENT single-snapshot bag: ``valid_from`` + ``confidence`` but NO
     ``valid_to`` window-close and NO ``wasGeneratedBy`` (Project is
     ``prov:Plan`` — it never carries a prov edge, even after WP-015; it gains
     windows + supersedes only). See ADR-006.

These run against a **real** ``LocalFileEntityAdapter`` over a temp dir, and a
**real** atomic ``write_project_entity`` over a temp dir (MEA-09 — no mocks at
the store seam).
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

# The LifecycleRun id the emit context threads in via ``generated_by``. AFTER
# WP-012 it lands on the current open window's ``wasGeneratedBy`` edge for the
# prov:Entity types (Product / Opportunity).
_RUN_ID = "dna:lifecyclerun:01JX0RVNRVNRVNRVNRVNRVNRVN"


# ─── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def adapter(tmp_path: Path) -> LocalFileEntityAdapter:
    """A real file-backed adapter over a temp dir, resolving the vendored
    product-development schemas (no mock — MEA-09)."""
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances",
        domain="product-development",
    )


def _read_current_window(
    adapter: LocalFileEntityAdapter, entity_type: str, eid: str
) -> dict:
    """Read the current OPEN window from the on-disk history envelope.

    Post-WP-012 the living emit writes a history envelope
    (``{"windows": [...]}``) via ``evolve_entity``; the current state is the
    last window (the only one with ``valid_to`` null). This is the observable
    output the characterisation now pins.
    """
    path = adapter.instance_path(entity_type, eid)
    assert path.exists(), f"emitter must have written {entity_type} at {path}"
    envelope = json.loads(path.read_text())
    windows = envelope.get("windows")
    assert isinstance(windows, list) and windows, (
        f"evolved {entity_type} must persist a non-empty history envelope; "
        f"got {envelope!r} — the emit is not delegating to evolve_entity"
    )
    return windows[-1]


# ─── 1 · Product baseline ────────────────────────────────────────────────────


class TestProductEmitBaseline:
    """Pins the POST-WP-012 Product emit: ``_product_emission`` delegates to
    ``evolve_entity``, persisting a history envelope whose current OPEN window
    carries the load-bearing current-state fields (id / name /
    belongs_to_tenant / state / sys_status), an open ``valid_from`` window, and
    — when ``generated_by`` is supplied — the conditional ``wasGeneratedBy``
    edge (Product is ``prov:Entity``).
    """

    def test_product_emit_writes_open_window_with_prov(
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

        emitted = emit_product_from_yaml(
            product_yaml, adapter, generated_by=_RUN_ID
        )

        # The emitter returns exactly the one composed dict it emitted.
        assert len(emitted) == 1
        product = emitted[0]
        eid = product["id"]

        # The on-disk history envelope's current open window is the observable
        # contract. Load-bearing current-state fields must survive the refactor.
        window = _read_current_window(adapter, "product", eid)
        assert window["id"] == eid
        assert window["id"].startswith("dna:product:")
        assert window["name"] == "Acme Billing"
        assert window["belongs_to_tenant"] == "dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT"
        assert window["state"] == "active"
        assert window["sys_status"] == "active"

        # POST-REFACTOR: the window is OPEN (valid_from set, valid_to null) and
        # carries the conditional wasGeneratedBy edge to the producing run.
        assert window.get("valid_from"), "an opened window carries valid_from"
        assert window.get("valid_to") in (None, ""), (
            "the sole/current window must be open (valid_to null)"
        )
        assert window.get("wasGeneratedBy") == _RUN_ID, (
            "Product is prov:Entity — when generated_by is supplied the window "
            "records the canonical wasGeneratedBy edge"
        )
        assert "was_generated_by" not in window, (
            "no snake_case scalar — the canonical edge is camelCase wasGeneratedBy"
        )


# ─── 2 · Opportunity baseline ────────────────────────────────────────────────


class TestOpportunityEmitBaseline:
    """Pins the POST-WP-012 Opportunity emit: ``_opportunity_emission``
    delegates to ``evolve_entity``, persisting a history envelope whose current
    open window carries the load-bearing fields + the conditional
    ``wasGeneratedBy`` edge (Opportunity is ``prov:Entity``).
    """

    def test_opportunity_emit_writes_open_window_with_prov(
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

        emitted = emit_opportunity_from_srd(srd, adapter, generated_by=_RUN_ID)

        assert len(emitted) == 1
        opp = emitted[0]
        eid = opp["id"]

        window = _read_current_window(adapter, "opportunity", eid)

        # Load-bearing fields of the current state (now carried on the window).
        assert window["id"] == eid
        assert window["id"].startswith("dna:opportunity:")
        assert window["for_product"].startswith("dna:product:")
        assert window["job_statement"] == (
            "When I close the books I want one number so I can file fast."
        )
        assert window["state"] == "hypothesis"
        assert window["sys_status"] == "active"

        # POST-REFACTOR: open window + conditional prov edge (same as Product).
        assert window.get("valid_from"), "an opened window carries valid_from"
        assert window.get("valid_to") in (None, ""), "the window must be open"
        assert window.get("wasGeneratedBy") == _RUN_ID, (
            "Opportunity is prov:Entity — the window records wasGeneratedBy"
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
