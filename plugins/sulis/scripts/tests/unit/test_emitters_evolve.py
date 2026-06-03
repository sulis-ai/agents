"""WP-012 — the apply-evolve refactor: Product / Opportunity emitters now call
``evolve_entity`` (WP-009) instead of ``repo.save``, turning bitemporal
evolution ON for the live emit paths.

This is the *behaviour* contract for the REORGANISE-Refactor gated by the
WP-011 characterisation baseline (which pins the pre-refactor current-snapshot
behaviour and is updated in lockstep at Blue). Per ADR-003 + ADR-002:

  - **Product** (``_product_emission``) and **Opportunity**
    (``_opportunity_emission``) are ``prov:Entity`` living types. After the
    refactor each emit:
      * opens a bitemporal window (first emit) or closes the prior + opens a
        new one (re-emit of a changed body) — delegating to ``evolve_entity``,
        NOT re-implementing window logic (EP-03);
      * carries the conditional ``wasGeneratedBy`` edge on the new window when
        the caller supplies the producing LifecycleRun ref
        (``generated_by=<dna:lifecyclerun:…>``).

  - **Project** is a ``prov:Plan`` living type — it gets windows but NO
    ``wasGeneratedBy`` (``generated_by=None``). Its emit path (the
    ``_discovery`` minter → ``.sulis/projects`` bag) does NOT yet route through
    the ``EntityRepository`` port, so *applying* evolve to the Project emit
    path is the ADR-006 reconciliation owned by **WP-015** (gated by WP-014's
    minter characterisation test). WP-012 pins the windows-only / NO-prov
    semantics at the ``evolve_entity`` seam (``generated_by=None``) so the
    contract Project will inherit at WP-015 is locked in now; the Project
    emit-path swap itself is deferred (see the WP-012 journal scope note).

  - **Graceful degradation** is preserved: a failing evolve must NOT raise into
    the host operation — emission stays best-effort.

These run against a **real** ``LocalFileEntityAdapter`` over a temp dir
(MEA-09 — no mocks at the store seam). The on-disk shape an evolved entity
takes is the history *envelope* (``{"windows": [...]}``), read back via
``find_by_id``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _entity_evolve import evolve_entity
from _opportunity_emission import emit_opportunity_from_srd
from _product_emission import emit_product_from_yaml

# The producing LifecycleRun ref the emit context threads in as ``generated_by``
# for prov:Entity types (Product, Opportunity). After the refactor it lands on
# the new window's ``wasGeneratedBy`` edge.
_RUN_ID = "dna:lifecyclerun:01JX0RUNRUNRUNRUNRUNRUNRUN"


# ─── fixtures / helpers ──────────────────────────────────────────────────────


@pytest.fixture
def adapter(tmp_path: Path) -> LocalFileEntityAdapter:
    """A real file-backed adapter over a temp dir, resolving the vendored
    product-development schemas (no mock — MEA-09)."""
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances",
        domain="product-development",
    )


@pytest.fixture
def foundation_adapter(tmp_path: Path) -> LocalFileEntityAdapter:
    """A real file-backed adapter resolving the vendored ``foundation`` schemas
    — Project's ``project.schema.json`` lives there, not under
    product-development."""
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances",
        domain="foundation",
    )


def _read_windows(
    adapter: LocalFileEntityAdapter, entity_type: str, entity_id: str
) -> list[dict]:
    """Read the persisted history-envelope's ordered window list (ADR-003).

    One file per entity holding an ordered ``windows`` list; the current open
    window is the last element (the only one with ``valid_to`` null).
    """
    envelope = adapter.find_by_id(entity_type, entity_id)
    assert envelope is not None, f"no envelope persisted for {entity_id}"
    windows = envelope.get("windows")
    assert isinstance(windows, list), (
        f"evolved entity must persist a history envelope with a `windows` list; "
        f"got {type(windows)} — the emitter is still calling repo.save"
    )
    return windows


def _write_product_yaml(tmp_path: Path, *, state: str = "active") -> Path:
    product_yaml = tmp_path / ".sulis" / "products" / "acme-billing.yaml"
    product_yaml.parent.mkdir(parents=True, exist_ok=True)
    product_yaml.write_text(
        "name: Acme Billing\n"
        "description: One invoice for every team\n"
        "category: saas\n"
        f"state: {state}\n"
        "belongs_to_tenant: dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT\n",
        encoding="utf-8",
    )
    return product_yaml


def _write_srd(tmp_path: Path, *, summary: str) -> Path:
    srd = tmp_path / "SRD.md"
    srd.write_text(
        "---\n"
        "title: Fast Close\n"
        "---\n"
        "## Summary\n"
        f"{summary}\n"
        "\n"
        "## Scope\n"
        "Out of scope: payroll.\n",
        encoding="utf-8",
    )
    return srd


# ─── 1 · Product — first emit opens one window ───────────────────────────────


class TestProductEmitOpensWindow:
    """First Product emit → exactly one OPEN bitemporal window (evolve is ON)."""

    def test_product_emit_opens_window(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        product_yaml = _write_product_yaml(tmp_path)

        emitted = emit_product_from_yaml(
            product_yaml, adapter, generated_by=_RUN_ID
        )
        assert len(emitted) == 1
        eid = emitted[0]["id"]

        windows = _read_windows(adapter, "product", eid)
        assert len(windows) == 1, "first emit must open exactly one window"
        sole = windows[0]
        assert sole.get("valid_to") in (None, ""), (
            "the sole window must be OPEN (valid_to null)"
        )
        assert sole.get("valid_from"), "an opened window must carry valid_from"
        # Load-bearing current-state fields survive the refactor.
        assert sole["id"] == eid
        assert sole["name"] == "Acme Billing"
        assert sole["belongs_to_tenant"] == "dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT"
        assert sole["state"] == "active"
        assert sole["sys_status"] == "active"


# ─── 2 · Product — re-emit of a changed body evolves WITH prov ───────────────


class TestProductReEmitEvolvesWithProv:
    """A changed Product re-emit closes the prior window + opens a new one that
    carries ``wasGeneratedBy`` (prov:Entity)."""

    def test_product_re_emit_evolves_with_prov(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        product_yaml = _write_product_yaml(tmp_path, state="active")
        emitted = emit_product_from_yaml(
            product_yaml, adapter, generated_by=_RUN_ID
        )
        eid = emitted[0]["id"]

        # Change the body (state active → sunset) and re-emit.
        product_yaml.write_text(
            "name: Acme Billing\n"
            "description: One invoice for every team\n"
            "category: saas\n"
            "state: sunset\n"
            "belongs_to_tenant: dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT\n",
            encoding="utf-8",
        )
        emit_product_from_yaml(product_yaml, adapter, generated_by=_RUN_ID)

        windows = _read_windows(adapter, "product", eid)
        assert len(windows) == 2, "a changed re-emit must add a window"
        prior, current = windows[0], windows[1]
        assert prior.get("valid_to"), "prior window must close (valid_to set)"
        assert current.get("valid_to") in (None, ""), "new window must be open"
        # windows abut exactly — no gap, no overlap.
        assert prior["valid_to"] == current["valid_from"]
        # the new window carries the conditional prov edge (camelCase canonical).
        assert current.get("wasGeneratedBy") == _RUN_ID, (
            "prov:Entity (Product) new window must carry wasGeneratedBy"
        )
        assert "was_generated_by" not in current, (
            "no snake_case scalar; the canonical edge is camelCase wasGeneratedBy"
        )
        assert current["state"] == "sunset", "new window holds the changed state"


# ─── 3 · Opportunity — emit evolves WITH prov ────────────────────────────────


class TestOpportunityEmitEvolvesWithProv:
    """Opportunity (prov:Entity) new window carries ``wasGeneratedBy``."""

    def test_opportunity_emit_evolves_with_prov(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        srd = _write_srd(
            tmp_path,
            summary="When I close the books I want one number so I can file fast.",
        )
        emitted = emit_opportunity_from_srd(srd, adapter, generated_by=_RUN_ID)
        assert len(emitted) == 1
        oid = emitted[0]["id"]

        windows = _read_windows(adapter, "opportunity", oid)
        assert len(windows) == 1, "first emit opens one window"
        sole = windows[0]
        assert sole.get("valid_to") in (None, ""), "the window must be open"
        assert sole.get("wasGeneratedBy") == _RUN_ID, (
            "prov:Entity (Opportunity) window must carry wasGeneratedBy"
        )
        assert sole["job_statement"] == (
            "When I close the books I want one number so I can file fast."
        )
        assert sole["state"] == "hypothesis"
        assert sole["sys_status"] == "active"


# ─── 4 · Project — windows-only, NO prov (helper-level pin) ──────────────────


class TestProjectEvolvesWithoutProv:
    """Project is ``prov:Plan`` — ``evolve_entity(generated_by=None)`` moves the
    window but writes NO ``wasGeneratedBy`` edge.

    WP-012 SCOPE: the Project *emit path* (the ``_discovery`` minter →
    ``.sulis/projects`` bag) does NOT yet route through the ``EntityRepository``
    port, so swapping it to ``evolve_entity`` is the ADR-006 reconciliation
    owned by WP-015 (gated by WP-014). What WP-012 owns is locking in the
    windows-only / NO-prov CONTRACT Project will inherit — pinned here at the
    ``evolve_entity`` seam so the Project semantics are unambiguous before
    WP-015 wires the emit path.
    """

    def _valid_project(self) -> dict:
        return {
            "id": "dna:project:01JX0CCCCCCCCCCCCCCCCCCCCC",
            "name": "Sulis Agents",
            "belongs_to_tenant": "dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT",
            "type": "plugin",
            "source": json.dumps(
                {"repo": "sulis-ai/agents", "path": ".", "primary_branch": "main"}
            ),
            "version_files": ["plugins/sulis/.claude-plugin/plugin.json"],
            "branch_policy": "trunk",
            "state": "active",
            "sys_status": "active",
        }

    def test_project_evolve_without_prov(
        self, foundation_adapter: LocalFileEntityAdapter
    ) -> None:
        body = self._valid_project()
        pid = body["id"]

        # First evolve opens window 1.
        evolve_entity(
            repo=foundation_adapter,
            entity_type="project",
            entity_id=pid,
            new_fields=body,
            generated_by=None,
            at="2026-01-01T00:00:00Z",
        )
        # A changed re-evolve closes prior + opens window 2.
        changed = dict(body)
        changed["state"] = "archived"
        evolve_entity(
            repo=foundation_adapter,
            entity_type="project",
            entity_id=pid,
            new_fields=changed,
            generated_by=None,
            at="2026-02-01T00:00:00Z",
        )

        windows = _read_windows(foundation_adapter, "project", pid)
        assert len(windows) == 2, "Project gets windows (it IS a living entity)"
        prior, current = windows[0], windows[1]
        assert prior["valid_to"] == "2026-02-01T00:00:00Z", "prior closes"
        assert current.get("valid_to") in (None, ""), "new window open"
        # Project (prov:Plan) carries NO wasGeneratedBy — not on any window.
        for w in windows:
            assert "wasGeneratedBy" not in w, (
                "Project is prov:Plan — it never carries a wasGeneratedBy edge"
            )
            assert "prov_constraints" not in w


# ─── 5 · Graceful degradation — a failing evolve does not raise ──────────────


class TestEmitFailureDegradesGracefully:
    """Emission is best-effort: a failing evolve must NOT raise into the host
    operation (graceful-degradation discipline preserved across the refactor)."""

    def test_emit_failure_degrades_gracefully(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        product_yaml = _write_product_yaml(tmp_path)

        # An adapter whose validate() always blows up simulates a store fault
        # (missing schema, IO error, etc.) at the evolve persistence point.
        class _ExplodingAdapter(LocalFileEntityAdapter):
            def validate(self, entity_type: str, instance: dict) -> None:
                raise RuntimeError("simulated store fault at the persistence point")

        exploding = _ExplodingAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

        # Must NOT raise — the host operation continues even though the emit
        # failed. The emitter returns the composed list it attempted to write.
        result = emit_product_from_yaml(
            product_yaml, exploding, generated_by=_RUN_ID
        )
        assert isinstance(result, list), (
            "a failing emit must degrade gracefully (return, not raise)"
        )
