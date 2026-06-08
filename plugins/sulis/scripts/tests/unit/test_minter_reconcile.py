"""WP-015 — the minter reconcile: canonical brain-store save + human mirror.

ADR-006 reclassifies ``_discovery/minter.py``'s ``write_project_entity`` from a
single ``.sulis/projects/<slug>.jsonld`` write into a **canonical-first /
mirror-second** reconcile:

  1. **Canonical** — the inner Project is saved through the ``EntityRepository``
     port via the shared bitemporal helper ``evolve_entity`` (WP-009), pointed at
     the central Tenant home (WP-013), with ``generated_by=None``. Project is
     ``prov:Plan`` (ADR-002/ADR-006): it gets bitemporal windows + the supersedes
     chain, but **no** ``wasGeneratedBy`` edge — putting an Entity→Activity edge
     on a recipe is a PROV-O type violation.
  2. **Mirror** — ``.sulis/projects/<slug>.jsonld`` is retained as the
     human-readable artifact, written by the SAME atomic-write + path-safety
     machinery (now ``write_project_mirror``), derived from the same entity dict.

Ordering is load-bearing (ADR-006): a failed canonical write writes **no**
mirror (the founder never sees a Project the store rejected); a failed mirror
after a good canonical save is a **logged best-effort degradation** (the
canonical truth is already safe). The WP-014 characterisation baseline pins the
four mirror-side safety properties — those are re-asserted here against the
post-reconcile ``write_project_entity`` to prove the reconcile preserved them.

These tests run against a **real** ``LocalFileEntityAdapter`` over a real temp
central home (no mock at the canonical write seam) and a real temp repo for the
mirror; ``consuming_repo_root`` is monkeypatched for hermetic path-safety, the
same seam the sibling minter suites use.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _discovery.minter import (
    EntityAlreadyExistsError,
    PathOutsideAllowedDirectoryError,
    write_project_entity,
    write_project_mirror,
)
from _entity_adapter_local import LocalFileEntityAdapter

# The deterministic Tenant the composed Project belongs to. The canonical save
# lands under this Tenant's central home (ADR-005), keyed by the ULID verbatim.
# IDs are valid 26-char Crockford-base32 ULIDs — the canonical port validates
# the Project body against the compiled foundation schema (the reconcile's whole
# point: Project stops being special and is reject-on-invalid like every entity).
_TENANT_ID = "dna:tenant:01KT0EXAMP1ETENANT00000000"
_PROJECT_ID = "dna:project:01KT0PR0JECT0000000000000A"

# Project lives in the foundation domain (its compiled schema is
# brain/compiled/foundation/project.schema.json), NOT product-development.
_FOUNDATION = "foundation"


# ─── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real temp repo whose ``.sulis/projects/`` is ready, with
    ``consuming_repo_root`` + the central-home base patched at the temp dir."""
    (tmp_path / ".sulis" / "projects").mkdir(parents=True)

    from _discovery import minter as minter_module

    monkeypatch.setattr(minter_module, "consuming_repo_root", lambda: tmp_path)
    # Route the central Tenant home under the temp dir so the canonical save is
    # hermetic — sulis_state_base() honours SULIS_STATE_DIR (the same seam the
    # central-home suite uses).
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "state"))
    return tmp_path


@pytest.fixture
def project_entity() -> dict:
    """A representative, schema-valid inner Project bag — the load-bearing
    multi-repo anchor fields ADR-006 requires survive the reconcile.

    ``source`` is a JSON-encoded string and ``belongs_to_product_ref`` a plain
    string, matching ``_discovery._compose_entity`` and the compiled foundation
    Project schema (``unevaluatedProperties: false``).
    """
    return {
        "id": _PROJECT_ID,
        "name": "Payments App",
        "belongs_to_tenant": _TENANT_ID,
        "type": "service",
        "source": json.dumps({"repo": "acme/payments", "path": ".", "primary_branch": "main"}),
        "version_files": ["pyproject.toml"],
        "branch_policy": "trunk",
        "belongs_to_product_ref": "dna:product:acme-billing",
        "state": "active",
        "sys_status": "active",
    }


def _projects_dir(repo_root: Path) -> Path:
    return repo_root / ".sulis" / "projects"


def _central_home(repo_root: Path) -> Path:
    from _brain_emit_helper import central_tenant_home

    return central_tenant_home(_TENANT_ID)


def _canonical_envelope(repo_root: Path) -> dict | None:
    """The persisted canonical history envelope for the Project, or None."""
    adapter = LocalFileEntityAdapter(
        base_dir=_central_home(repo_root), domain=_FOUNDATION
    )
    return adapter.find_by_id("project", _PROJECT_ID)


# ─── 1 · canonical-first, then mirror ─────────────────────────────────────


class TestCanonicalSaveThenMirror:
    def test_canonical_save_then_mirror(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        """The brain store is written (canonical) AND the human mirror lands —
        both derived from the same entity dict (ADR-006)."""
        target = _projects_dir(repo_root) / "payments-app.jsonld"

        write_project_entity(target, project_entity)

        # Canonical: the Project is a living entity in the central Tenant home,
        # one open bitemporal window carrying the body verbatim.
        envelope = _canonical_envelope(repo_root)
        assert envelope is not None, "the canonical brain-store save must persist"
        assert envelope["windows"], "the canonical save opens a bitemporal window"
        current = envelope["windows"][-1]
        assert current["valid_to"] is None, "the new window is open"
        assert current["id"] == _PROJECT_ID
        assert current["belongs_to_tenant"] == _TENANT_ID
        assert current["belongs_to_product_ref"] == "dna:product:acme-billing"

        # Mirror: the human-readable artifact lands too, carrying the same body.
        assert target.exists(), "the human mirror must be written"
        mirrored = json.loads(target.read_text())
        assert mirrored == project_entity
        assert list(_projects_dir(repo_root).glob("*.tmp")) == []

    def test_project_window_carries_no_prov_edge(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        """Project is ``prov:Plan``: the canonical window gets bitemporal fields
        but NO ``wasGeneratedBy`` edge (generated_by=None — ADR-002/ADR-006)."""
        target = _projects_dir(repo_root) / "payments-app.jsonld"
        write_project_entity(target, project_entity)

        current = _canonical_envelope(repo_root)["windows"][-1]
        assert "wasGeneratedBy" not in current, (
            "Project is prov:Plan — windows + supersedes only, never a prov edge"
        )
        assert "valid_from" in current, "the bitemporal window still opens"

    def test_re_discovery_evolves_not_duplicates(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        """A re-discovery (``--update`` → allow_overwrite) EVOLVES the canonical
        Project: the prior window closes, a new one opens — the living-entity
        contract (ADR-003/ADR-006), not a second fresh save."""
        target = _projects_dir(repo_root) / "payments-app.jsonld"
        write_project_entity(target, project_entity)

        evolved = dict(project_entity)
        evolved["state"] = "archived"
        write_project_entity(target, evolved, allow_overwrite=True)

        windows = _canonical_envelope(repo_root)["windows"]
        assert len(windows) == 2, "a changed re-discovery opens a second window"
        assert windows[0]["valid_to"] is not None, "the prior window is closed"
        assert windows[1]["valid_to"] is None, "the new window is open"
        assert windows[1]["state"] == "archived"


# ─── 2 · the four WP-014 safety properties preserved on the mirror ─────────


class TestPathSafetyPreserved:
    """The four characterisation properties WP-014 pinned still hold on the
    mirror write after the reconcile (EP-07 — verbatim safety discipline)."""

    def test_mirror_atomic_and_round_trips(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        target = _projects_dir(repo_root) / "payments-app.jsonld"
        write_project_entity(target, project_entity)
        assert json.loads(target.read_text()) == project_entity
        assert list(_projects_dir(repo_root).glob("*.tmp")) == []

    def test_path_safety_rejects_dotdot_traversal(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        evil = _projects_dir(repo_root) / ".." / "escaped.jsonld"
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_entity(evil, project_entity)

    def test_path_safety_rejects_symlink_traversal(
        self, repo_root: Path, project_entity: dict, tmp_path: Path
    ) -> None:
        outside = tmp_path / "outside-the-repo"
        outside.mkdir()
        symlink = _projects_dir(repo_root) / "escape"
        symlink.symlink_to(outside)
        evil = symlink / "evil.jsonld"
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_entity(evil, project_entity)

    def test_mirror_function_keeps_the_safety_boundary(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        """``write_project_mirror`` (the extracted human-mirror writer) carries
        the path-safety boundary verbatim — the same guard, now on the mirror."""
        evil = _projects_dir(repo_root) / ".." / "escaped.jsonld"
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_mirror(evil, project_entity)


# ─── 3 · MUC-003 refuse-on-exists preserved ───────────────────────────────


class TestMuc003Refuses:
    def test_muc003_refuses_existing_mirror(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        target = _projects_dir(repo_root) / "payments-app.jsonld"
        target.write_text('{"pre-existing": true}')
        with pytest.raises(EntityAlreadyExistsError):
            write_project_entity(target, project_entity, allow_overwrite=False)
        # Refusal is total — the existing mirror is left untouched.
        assert json.loads(target.read_text()) == {"pre-existing": True}


# ─── 4 · ordering + graceful degradation (ADR-006) ────────────────────────


class TestCanonicalFirstOrderingAndDegradation:
    def test_failed_canonical_writes_no_mirror(
        self, repo_root: Path, project_entity: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A canonical-write failure raises and writes NO mirror — the mirror can
        never show a Project the store rejected (ADR-006 ordering)."""
        from _discovery import minter as minter_module

        def boom(**_kw):  # type: ignore[no-untyped-def]
            raise RuntimeError("canonical store is down")

        monkeypatch.setattr(minter_module, "evolve_entity", boom)

        target = _projects_dir(repo_root) / "payments-app.jsonld"
        with pytest.raises(RuntimeError):
            write_project_entity(target, project_entity)

        assert not target.exists(), (
            "a failed canonical save must write no mirror"
        )

    def test_failed_mirror_after_good_save_degrades(
        self, repo_root: Path, project_entity: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A mirror failure AFTER a good canonical save is a logged best-effort
        degradation — it does not raise; the canonical truth is already safe."""
        from _discovery import minter as minter_module

        def boom(*_a, **_kw):  # type: ignore[no-untyped-def]
            raise OSError("mirror disk full")

        # Break only the mirror write; the canonical save runs for real.
        monkeypatch.setattr(minter_module, "write_project_mirror", boom)

        target = _projects_dir(repo_root) / "payments-app.jsonld"
        # Does NOT raise — graceful degradation.
        write_project_entity(target, project_entity)

        # The canonical save still happened (it precedes the mirror).
        assert _canonical_envelope(repo_root) is not None, (
            "canonical-first: the good canonical save survives a mirror failure"
        )
