"""Characterisation baseline pinning the minter BEFORE the WP-015 reconcile.

WP-014 (REINFORCE-Test). ADR-006 reclassifies ``_discovery/minter.py``'s
``write_project_entity`` as a **REORGANISE-Refactor**: WP-015 will route the
Project save through the canonical ``EntityRepository`` port (``repo.save(
"project", entity)``) and keep ``.sulis/projects/<slug>.jsonld`` as a
human-readable *mirror* — written by the SAME atomic, path-safe machinery,
repurposed as ``write_project_mirror``. Per the Characterisation-Tests-Before-
Refactor MUST (EP-07) the minter's load-bearing safety behaviour is **pinned
first, here**, so WP-015 can prove it preserved every safety property while
adding the canonical save.

This file captures the **current** observable behaviour of the UNCHANGED
minter as four discrete safety properties — it is green-from-the-start against
today's code (the characterisation point; a faithful capture passes against
the behaviour it pins). The four properties WP-015 MUST keep alive on the
mirror write:

  1. **Atomic write into ``.sulis/projects/<slug>.jsonld``** — tmp + ``fsync``
     + ``os.replace``; the full entity lands, no ``.tmp`` residue on success.
  2. **Path-safety** — ``.resolve()`` + ``is_relative_to(<repo>/.sulis/projects)``
     refuses ``..``- and symlink-traversal *before any I/O*.
  3. **MUC-003 refuse-on-exists** — re-mint over an existing entity is refused
     unless ``allow_overwrite=True``; pre-existing content is left untouched.
  4. **Partial-write cleanup on cancel** — a SIGINT between the tmp write and
     the rename leaves only the ``.tmp`` (target absent — the atomic
     guarantee); the stale-tmp sweep then removes it (MUC-002 idempotence).

Each property is a **discrete assertion block** so WP-015 knows exactly what
must survive the move onto the mirror. The tests run against a **real** temp
repo with the real ``write_project_entity`` (no mock at the write seam,
MEA-09); ``consuming_repo_root`` is monkeypatched to the temp dir so path
safety resolves hermetically — the same seam the sibling minter unit suite
and the living-entity emit baseline use.

NB: this is the *minter* (Project bag) path, distinct from the
``EntityRepository`` adapter path the Product/Opportunity emitters use. Today
Project mints to ``.sulis/projects/`` via this path, NOT the port — that
divergence is precisely what ADR-006 / WP-015 reconcile. WP-014 pins the path
as-is so the reconcile is provably safety-preserving.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from _discovery.minter import (
    EntityAlreadyExistsError,
    PathOutsideAllowedDirectoryError,
    stale_tmp_sweep,
    write_project_entity,
)

# ─── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real temp repo whose ``.sulis/projects/`` is ready, with
    ``consuming_repo_root`` patched to it.

    ``write_project_entity`` resolves the allowed write dir via
    ``consuming_repo_root() / ".sulis" / "projects"`` (which shells out to
    ``git rev-parse`` in production). Patching the seam — not the write — keeps
    the characterisation honest: the real atomic write + real path-safety run
    against a real filesystem (MEA-09, no mock at the write seam).
    """
    projects_dir = tmp_path / ".sulis" / "projects"
    projects_dir.mkdir(parents=True)

    from _discovery import minter as minter_module

    monkeypatch.setattr(minter_module, "consuming_repo_root", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def project_entity() -> dict:
    """A representative Project bag — the load-bearing multi-repo anchor fields
    ADR-006 requires survive the reconcile (``belongs_to_tenant``, ``source``,
    plain-string ``belongs_to_product_ref``). Pinned verbatim so WP-015's
    mirror write is proven to carry them through unchanged.
    """
    return {
        "@context": "https://sulis.ai/schema/v1",
        "@type": "Project",
        "@id": "dna:project:payments-app",
        "name": "Payments App",
        "belongs_to_tenant": "dna:tenant:01KT0EX4MPLETENANT0000000",
        "belongs_to_product_ref": "dna:product:acme-billing",
        "source": {"repo": "acme/payments", "path": "."},
        "state": "active",
        "sys_status": "active",
    }


def _projects_dir(repo_root: Path) -> Path:
    return repo_root / ".sulis" / "projects"


# ─── 1 · golden behaviour — safe atomic write of the mirror ───────────────


class TestCurrentMinterSafetyPinned:
    """Property 1 (golden): the current ``write_project_entity`` writes the
    entity bag safely and atomically into ``.sulis/projects/<slug>.jsonld`` —
    full content present, JSON round-trips, no ``.tmp`` residue. This is the
    happy path WP-015's ``write_project_mirror`` must reproduce verbatim.
    """

    def test_current_minter_safety_pinned(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        target = _projects_dir(repo_root) / "payments-app.jsonld"

        write_project_entity(target, project_entity)

        # The full entity lands at the target, byte-for-byte round-trippable.
        assert target.exists(), "the minter must write the entity bag atomically"
        written = json.loads(target.read_text())
        assert written == project_entity

        # Load-bearing multi-repo anchor fields survive verbatim (ADR-006 —
        # the reconcile changes WHERE bytes live, never the Project's shape).
        assert written["belongs_to_tenant"] == "dna:tenant:01KT0EX4MPLETENANT0000000"
        assert written["belongs_to_product_ref"] == "dna:product:acme-billing"
        assert written["source"] == {"repo": "acme/payments", "path": "."}

        # Atomic-write postcondition: no ``.tmp`` residue once the rename lands.
        assert list(_projects_dir(repo_root).glob("*.tmp")) == [], (
            "a successful atomic write leaves no tmp file behind"
        )

    def test_fsync_precedes_rename(
        self,
        repo_root: Path,
        project_entity: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Durability ordering is part of the atomic-write contract WP-015
        keeps: ``os.fsync`` on the tmp file MUST precede ``os.replace`` so the
        renamed file's data is on disk before it becomes visible at the target.
        """
        call_order: list[str] = []

        real_fsync = os.fsync

        def tracking_fsync(fd: int) -> None:
            call_order.append("fsync")
            real_fsync(fd)

        real_replace = os.replace

        def tracking_replace(src, dst, *a, **k):  # type: ignore[no-untyped-def]
            call_order.append("replace")
            return real_replace(src, dst, *a, **k)

        monkeypatch.setattr(os, "fsync", tracking_fsync)
        monkeypatch.setattr(os, "replace", tracking_replace)

        target = _projects_dir(repo_root) / "payments-app.jsonld"
        write_project_entity(target, project_entity)

        assert "fsync" in call_order and "replace" in call_order
        assert call_order.index("fsync") < call_order.index("replace"), (
            "fsync must precede the rename for the durability guarantee"
        )


# ─── 2 · path safety — traversal refused before any I/O ───────────────────


class TestPathSafetyRejectsTraversal:
    """Property 2: ``_assert_path_safety`` (``.resolve()`` +
    ``is_relative_to(<repo>/.sulis/projects)``) refuses both ``..``-traversal
    and symlink-traversal out of the allowed dir, and does so BEFORE any
    filesystem write. WP-015's mirror write keeps this boundary verbatim.
    """

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
        # A symlink under .sulis/projects/ pointing OUT of the repo resolves
        # outside the allowed dir; .resolve() follows it and the check refuses.
        symlink = _projects_dir(repo_root) / "escape"
        symlink.symlink_to(outside)

        evil = symlink / "evil.jsonld"
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_entity(evil, project_entity)

    def test_path_safety_runs_before_any_io(
        self,
        repo_root: Path,
        project_entity: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A refused path triggers NO mkdir and NO write — the guard is the
        first thing in, so a hostile target never causes filesystem effects.
        """
        io_targets: list[str] = []

        real_mkdir = Path.mkdir

        def tracking_mkdir(self, *a, **k):  # type: ignore[no-untyped-def]
            io_targets.append(f"mkdir:{self}")
            return real_mkdir(self, *a, **k)

        real_write_text = Path.write_text

        def tracking_write_text(self, *a, **k):  # type: ignore[no-untyped-def]
            io_targets.append(f"write_text:{self}")
            return real_write_text(self, *a, **k)

        monkeypatch.setattr(Path, "mkdir", tracking_mkdir)
        monkeypatch.setattr(Path, "write_text", tracking_write_text)

        evil = _projects_dir(repo_root) / ".." / "escaped.jsonld"
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_entity(evil, project_entity)

        assert not any("escaped.jsonld" in t for t in io_targets), (
            "path-safety must refuse before any mkdir/write touches the target"
        )


# ─── 3 · MUC-003 — refuse-on-exists ───────────────────────────────────────


class TestMuc003RefusesExisting:
    """Property 3 (MUC-003): re-minting over an existing entity is refused
    unless ``allow_overwrite=True``; the pre-existing file is left untouched.
    WP-015's mirror write keeps this refusal — the founder reruns with
    ``--update`` to enter the per-field diff (evolve) flow.
    """

    def test_muc003_refuses_existing(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        target = _projects_dir(repo_root) / "payments-app.jsonld"
        target.write_text('{"pre-existing": true}')

        with pytest.raises(EntityAlreadyExistsError):
            write_project_entity(target, project_entity, allow_overwrite=False)

        # The existing content is untouched — the refusal is total, not partial.
        assert json.loads(target.read_text()) == {"pre-existing": True}

    def test_muc003_allows_overwrite_with_flag(
        self, repo_root: Path, project_entity: dict
    ) -> None:
        target = _projects_dir(repo_root) / "payments-app.jsonld"
        target.write_text('{"pre-existing": true}')

        write_project_entity(target, project_entity, allow_overwrite=True)

        assert json.loads(target.read_text()) == project_entity


# ─── 4 · partial-write cleanup on cancel (MUC-002) ────────────────────────


class TestPartialWriteCleanedOnCancel:
    """Property 4: a SIGINT between the tmp write and the rename leaves the
    target ABSENT (atomic guarantee) and only a ``.tmp`` behind; the stale-tmp
    sweep then removes it, so a re-run is clean (MUC-002 idempotence). WP-015's
    mirror keeps both the atomic guarantee and the sweep.
    """

    def test_partial_write_cleaned_on_cancel(
        self,
        repo_root: Path,
        project_entity: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        projects = _projects_dir(repo_root)
        target = projects / "payments-app.jsonld"
        tmp = target.with_suffix(".jsonld.tmp")

        # Chaos shim: cancel exactly at the rename — the tmp is already written
        # and fsync'd, but os.replace never lands the target.
        def chaos_replace(src, dst, *a, **k):  # type: ignore[no-untyped-def]
            raise KeyboardInterrupt("simulated SIGINT at rename")

        monkeypatch.setattr(os, "replace", chaos_replace)

        with pytest.raises(KeyboardInterrupt):
            write_project_entity(target, project_entity)

        # Atomic guarantee: the target never half-appeared; only the tmp remains.
        assert not target.exists(), (
            "the atomic write must never leave a partial target — only the tmp"
        )
        assert tmp.exists(), "the cancelled write leaves its tmp for the sweep"

        # MUC-002: the stale-tmp sweep cleans the residue, leaving a clean dir.
        removed = stale_tmp_sweep(projects)
        assert removed == 1
        assert not tmp.exists()
        assert list(projects.glob("*.tmp")) == []
