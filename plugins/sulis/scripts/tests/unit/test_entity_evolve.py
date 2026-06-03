"""Characterisation tests for `_entity_evolve.evolve_entity` (WP-009).

`evolve_entity` is the shared helper that turns ON bitemporal evolution for
living entities (ADR-003). It sits **above** the `EntityRepository` port and
owns the close-window / open-window cycle plus a **CONDITIONAL** PROV
`wasGeneratedBy` edge write.

What it does, per ADR-003 + ADR-002:
  1. reads the current open window for ``(entity_type, id)`` via the port;
  2. closes the prior window (sets ``valid_to``) and opens a new one
     (``valid_from`` == prior ``valid_to``, plus ``confidence`` +
     ``sys_status``);
  3. **only when ``generated_by`` is provided** (prov:Entity types — Product,
     Opportunity) records the ``wasGeneratedBy`` edge to the generating
     LifecycleRun Activity. ``generated_by=None`` (prov:Plan — Project) moves
     the window but writes NO edge;
  4. persists BOTH windows as a single-file history-envelope rewrite (one
     atomic write; never an instant with two open windows);
  5. a byte-identical re-emit is a no-op (opens no window — idempotent);
  6. refuses any ``entity_type`` not on the ``_LIVING_ENTITY_TYPES`` allowlist
     (Decision / LifecycleRun stay append-only).

Two orthogonal guards (ADR-003, corrected):
  - ``_LIVING_ENTITY_TYPES`` admits all three living types (product /
    opportunity / project) — all three get windows.
  - the **provenance** write is a *separate* conditional, gated by
    ``generated_by is not None``.

There is **no ``used`` parameter** (canonical v2.1.0 LifecycleRun has no
``used`` field — DR-013) and **no ``wasRevisionOf``** anywhere (lineage is the
bitemporal window chain).

These tests run against a **real** ``LocalFileEntityAdapter`` over a temp dir
(MEA-09 — no mocks at the store seam).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _entity_evolve import _LIVING_ENTITY_TYPES, evolve_entity


class _NonFileBackedRepo:
    """An `EntityRepository`-shaped stub WITHOUT `instance_path` — stands in for
    a future non-file adapter (e.g. SQLite) where the file-only history-envelope
    layout does not apply (ADR-003 OAQ-1)."""

    def save(self, entity_type: str, instance: dict) -> None:  # pragma: no cover
        ...

    def find_by_id(self, entity_type: str, instance_id: str) -> dict | None:
        return None

    def validate(self, entity_type: str, instance: dict) -> None:
        return None


_RUN_ID = "dna:lifecyclerun:01JX0RUNRUNRUNRUNRUNRUNRUN"
_RUN_ID_2 = "dna:lifecyclerun:01JX0RUNRUNRUNRUNRUNRUNRU2"


# ─── fixtures ───────────────────────────────────────────────────────────────


def _valid_product() -> dict:
    """A Product instance body that passes the vendored product.schema.json.

    No PROV edge here — the edge is the evolve helper's CONDITIONAL write, not
    part of the schema-validated body (the compiled schema is
    ``unevaluatedProperties: false``).
    """
    return {
        "id": "dna:product:01JX0AAAAAAAAAAAAAAAAAAAAA",
        "name": "Acme Billing",
        "belongs_to_tenant": "dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT",
        "state": "active",
        "sys_status": "active",
    }


def _valid_opportunity() -> dict:
    return {
        "id": "dna:opportunity:01JX0BBBBBBBBBBBBBBBBBBBBB",
        "for_product": "dna:product:01JX0AAAAAAAAAAAAAAAAAAAAA",
        "job_statement": "when I close the books I want one number so I can file fast",
        "state": "validated",
        "sys_status": "active",
    }


def _valid_project() -> dict:
    import json as _json

    return {
        "id": "dna:project:01JX0CCCCCCCCCCCCCCCCCCCCC",
        "name": "Sulis Agents",
        "belongs_to_tenant": "dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT",
        "type": "plugin",
        "source": _json.dumps(
            {"repo": "sulis-ai/agents", "path": ".", "primary_branch": "main"}
        ),
        "version_files": ["plugins/sulis/.claude-plugin/plugin.json"],
        "branch_policy": "trunk",
        "state": "active",
        "sys_status": "active",
    }


@pytest.fixture
def adapter(tmp_path: Path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances",
        domain="product-development",
    )


@pytest.fixture
def foundation_adapter(tmp_path: Path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances",
        domain="foundation",
    )


# ─── window mechanics ───────────────────────────────────────────────────────


class TestFirstEmission:
    """First emission of a never-seen entity opens exactly one open window."""

    def test_first_emission_opens_one_window(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        result = evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=_valid_product()["id"],
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        assert result is not None, "first emission must open a window"
        windows = _read_windows(adapter, "product", _valid_product()["id"])
        assert len(windows) == 1
        assert windows[0]["valid_from"] == "2026-01-01T00:00:00Z"
        assert windows[0].get("valid_to") in (None, ""), (
            "the sole window must be open (valid_to null)"
        )


class TestCloseOpenWindow:
    """Second emission closes the prior window and opens a new one that abuts
    it exactly (prior valid_to == new valid_from)."""

    def test_close_open_window(self, adapter: LocalFileEntityAdapter) -> None:
        pid = _valid_product()["id"]
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=pid,
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        changed = _valid_product()
        changed["state"] = "maintenance"
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=pid,
            new_fields=changed,
            generated_by=_RUN_ID_2,
            at="2026-02-01T00:00:00Z",
        )

        windows = _read_windows(adapter, "product", pid)
        assert len(windows) == 2, "second emission must add a window"
        prior, current = windows[0], windows[1]
        assert prior["valid_to"] == "2026-02-01T00:00:00Z", "prior window must close"
        assert current["valid_from"] == "2026-02-01T00:00:00Z"
        assert current.get("valid_to") in (None, ""), "new window must be open"
        # windows abut exactly — no gap, no overlap
        assert prior["valid_to"] == current["valid_from"]
        assert current["state"] == "maintenance", "new window carries new fields"


class TestNoopIdempotent:
    """A byte-identical re-emit opens no new window (idempotent re-runs do not
    churn history)."""

    def test_noop_idempotent(self, adapter: LocalFileEntityAdapter) -> None:
        pid = _valid_product()["id"]
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=pid,
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        result = evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=pid,
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            at="2026-03-01T00:00:00Z",
        )

        assert result is None, "byte-identical re-emit must be a no-op (returns None)"
        windows = _read_windows(adapter, "product", pid)
        assert len(windows) == 1, "no-op must not append a window"


class TestNoTwoOpenWindows:
    """At no instant does one entity have two open windows
    (valid_to IS NULL)."""

    def test_no_two_open_windows(self, adapter: LocalFileEntityAdapter) -> None:
        pid = _valid_product()["id"]
        ats = [
            "2026-01-01T00:00:00Z",
            "2026-02-01T00:00:00Z",
            "2026-03-01T00:00:00Z",
        ]
        for i, at in enumerate(ats):
            fields = _valid_product()
            fields["name"] = f"Acme Billing v{i}"
            evolve_entity(
                repo=adapter,
                entity_type="product",
                entity_id=pid,
                new_fields=fields,
                generated_by=_RUN_ID,
                at=at,
            )

        windows = _read_windows(adapter, "product", pid)
        open_windows = [w for w in windows if w.get("valid_to") in (None, "")]
        assert len(open_windows) == 1, (
            f"exactly one window may be open; found {len(open_windows)}"
        )
        assert windows[-1] is open_windows[0], "the open window must be the last"


# ─── allowlist guard ────────────────────────────────────────────────────────


class TestAppendOnlyGuard:
    """``evolve_entity`` refuses an entity type that is not on the
    ``_LIVING_ENTITY_TYPES`` allowlist — append-only event entities (Decision,
    LifecycleRun) can never be evolved."""

    @pytest.mark.parametrize("event_type", ["decision", "lifecyclerun"])
    def test_refuses_event_entity(
        self, adapter: LocalFileEntityAdapter, event_type: str
    ) -> None:
        with pytest.raises((ValueError, KeyError)):
            evolve_entity(
                repo=adapter,
                entity_type=event_type,
                entity_id=f"dna:{event_type}:01JX0EEEEEEEEEEEEEEEEEEEEE",
                new_fields={"id": f"dna:{event_type}:01JX0EEEEEEEEEEEEEEEEEEEEE"},
                generated_by=None,
                at="2026-01-01T00:00:00Z",
            )

    def test_allowlist_admits_all_three_living_types(self) -> None:
        assert _LIVING_ENTITY_TYPES == frozenset(
            {"product", "opportunity", "project"}
        )


# ─── PROV write discipline (ADR-002) ────────────────────────────────────────


class TestProvEdgeForProvEntity:
    """Product / Opportunity (prov:Entity) with a ``generated_by`` ref → the
    new open window carries the ``wasGeneratedBy`` edge to a valid
    ``dna:lifecyclerun:<ulid>``, expressed as the canonical ``prov_constraints``
    edge (NOT a snake_case scalar)."""

    def test_writes_was_generated_by_for_prov_entity(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        pid = _valid_product()["id"]
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=pid,
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        window = _read_windows(adapter, "product", pid)[-1]
        assert window.get("wasGeneratedBy") == _RUN_ID, (
            "prov:Entity window must carry the wasGeneratedBy edge"
        )
        # NOT a snake_case scalar — the canonical prov key is camelCase
        assert "was_generated_by" not in window, (
            "no snake_case scalar; the canonical edge is wasGeneratedBy"
        )

    def test_writes_was_generated_by_for_opportunity(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        oid = _valid_opportunity()["id"]
        evolve_entity(
            repo=adapter,
            entity_type="opportunity",
            entity_id=oid,
            new_fields=_valid_opportunity(),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        window = _read_windows(adapter, "opportunity", oid)[-1]
        assert window.get("wasGeneratedBy") == _RUN_ID


class TestProjectNoProvEdge:
    """Project (prov:Plan) gets the window move but NO ``wasGeneratedBy`` edge —
    putting it on a Plan is a PROV-O type violation (ADR-002, ADR-006).
    ``generated_by=None`` is the gate."""

    def test_project_evolve_writes_NO_prov_edge(
        self, foundation_adapter: LocalFileEntityAdapter
    ) -> None:
        prj = _valid_project()
        evolve_entity(
            repo=foundation_adapter,
            entity_type="project",
            entity_id=prj["id"],
            new_fields=prj,
            generated_by=None,
            at="2026-01-01T00:00:00Z",
        )

        window = _read_windows(foundation_adapter, "project", prj["id"])[-1]
        # the window moved (it exists + is open)
        assert window["valid_from"] == "2026-01-01T00:00:00Z"
        assert window.get("valid_to") in (None, "")
        # but NO prov edge — neither camelCase nor snake_case
        assert "wasGeneratedBy" not in window, (
            "Project (prov:Plan) must carry no wasGeneratedBy edge"
        )
        assert "was_generated_by" not in window


class TestNoUsedNoWasRevisionOf:
    """The helper never writes a ``used`` field (no such param; canonical
    v2.1.0 LifecycleRun has no ``used`` field — DR-013) and never a
    ``wasRevisionOf`` (lineage is the bitemporal window chain)."""

    def test_no_used_field_anywhere(self, adapter: LocalFileEntityAdapter) -> None:
        pid = _valid_product()["id"]
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=pid,
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        window = _read_windows(adapter, "product", pid)[-1]
        assert "used" not in window, "the helper writes no `used` field"
        assert "wasRevisionOf" not in window, "the helper writes no `wasRevisionOf`"

    def test_evolve_entity_has_no_used_parameter(self) -> None:
        import inspect

        params = inspect.signature(evolve_entity).parameters
        assert "used" not in params, "evolve_entity must have no `used` parameter"


class TestRequiresFileBackedRepo:
    """The history-envelope layout is file-adapter only (ADR-003 OAQ-1). A
    repository that does not expose ``instance_path`` is refused plainly — a
    wiring error, not a deep ``AttributeError``."""

    def test_non_file_backed_repo_is_refused(self) -> None:
        with pytest.raises(TypeError, match="instance_path"):
            evolve_entity(
                repo=_NonFileBackedRepo(),  # type: ignore[arg-type]
                entity_type="product",
                entity_id=_valid_product()["id"],
                new_fields=_valid_product(),
                generated_by=_RUN_ID,
                at="2026-01-01T00:00:00Z",
            )


# ─── real-adapter exercise (MEA-09) ─────────────────────────────────────────


class TestRunsAgainstRealAdapter:
    """The helper is exercised against a real temp-dir file adapter — no mock
    at the store seam (MEA-09)."""

    def test_runs_against_real_temp_adapter(
        self, tmp_path: Path
    ) -> None:
        real = LocalFileEntityAdapter(
            base_dir=tmp_path / "real" / "instances",
            domain="product-development",
        )
        pid = _valid_product()["id"]

        evolve_entity(
            repo=real,
            entity_type="product",
            entity_id=pid,
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        # the envelope is a real file on disk under the adapter's layout
        ulid = pid.rsplit(":", 1)[-1]
        envelope_path = (
            tmp_path
            / "real"
            / "instances"
            / "product-development"
            / "product"
            / f"{ulid}.jsonld"
        )
        assert envelope_path.exists(), f"expected envelope at {envelope_path}"


class TestDefaultClockAndDefensiveLoad:
    """Edge paths: the default ``at`` clock, and a pre-evolution bare snapshot
    already on disk (treated as no-history rather than crashing the evolve)."""

    def test_default_at_stamps_a_utc_window(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        pid = _valid_product()["id"]
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=pid,
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            # at omitted → defaults to now (UTC)
        )

        window = _read_windows(adapter, "product", pid)[-1]
        valid_from = window["valid_from"]
        assert valid_from.endswith("Z"), "default clock must stamp a UTC instant"
        # parseable ISO-8601
        from datetime import datetime

        datetime.fromisoformat(valid_from.replace("Z", "+00:00"))

    def test_bare_snapshot_on_disk_is_treated_as_no_history(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        """A pre-evolution current-snapshot write (no ``windows`` key) does not
        crash evolve — the helper opens a fresh envelope rather than reading a
        missing window list."""
        pid = _valid_product()["id"]
        # Place a bare snapshot at the adapter's instance path (the shape the
        # old current-snapshot emitters wrote, before evolution turned on).
        adapter.save("product", _valid_product())

        result = evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=pid,
            new_fields=_valid_product(),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        assert result is not None, "evolve over a bare snapshot must open a window"
        windows = _read_windows(adapter, "product", pid)
        assert len(windows) == 1
        assert windows[0].get("valid_to") in (None, "")


# ─── helper: read the persisted window list ─────────────────────────────────


def _read_windows(
    adapter: LocalFileEntityAdapter, entity_type: str, entity_id: str
) -> list[dict]:
    """Read the persisted history-envelope's ordered window list.

    The history layout (ADR-003) is one file per entity holding an ordered
    list of windows; the current open window is the last element. The envelope
    is the on-disk shape ``find_by_id`` returns for an evolved entity.
    """
    envelope = adapter.find_by_id(entity_type, entity_id)
    assert envelope is not None, f"no envelope persisted for {entity_id}"
    windows = envelope.get("windows")
    assert isinstance(windows, list), (
        f"history envelope must hold a `windows` list; got {type(windows)}"
    )
    return windows
