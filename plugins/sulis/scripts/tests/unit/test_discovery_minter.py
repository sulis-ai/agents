"""Tests for ``_discovery.minter`` — Mint phase atomic write contract.

Covers TDD §Armor §Atomic write semantics + §Path-safety check, and
MUC-002 (cancel mid-flow) / MUC-003 (entity already exists).

The atomic-write pattern is POSIX-guaranteed (``os.replace`` is atomic
on the same filesystem). Cross-filesystem moves are out of scope —
``.sulis/projects/`` is inside the repo.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from _discovery.minter import (
    EntityAlreadyExistsError,
    PathOutsideAllowedDirectoryError,
    install_sigint_handler,
    stale_tmp_sweep,
    write_project_entity,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake ``consuming_repo_root`` with ``.sulis/projects/`` ready.

    ``write_project_entity`` resolves the repo root via
    ``git rev-parse --show-toplevel``. Patch ``_discovery.minter.consuming_repo_root``
    so tests run hermetically against tmp_path.
    """
    projects_dir = tmp_path / ".sulis" / "projects"
    projects_dir.mkdir(parents=True)

    from _discovery import minter as minter_module

    monkeypatch.setattr(minter_module, "consuming_repo_root", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def sample_entity() -> dict:
    return {
        "@context": "https://sulis.ai/schema/v1",
        "@type": "Project",
        "@id": "dna:project:payments-app",
        "name": "Payments App",
        "belongs_to_tenant": "dna:tenant:01KT0EX4MPLETENANT0000000",
    }


# ---------------------------------------------------------------------------
# Atomic-write semantics
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    def test_atomic_write_produces_target_on_success(
        self, fake_repo_root: Path, sample_entity: dict
    ) -> None:
        target = fake_repo_root / ".sulis" / "projects" / "payments-app.jsonld"
        write_project_entity(target, sample_entity)
        assert target.exists()
        loaded = json.loads(target.read_text())
        assert loaded == sample_entity

    def test_atomic_write_leaves_no_tmp_on_success(
        self, fake_repo_root: Path, sample_entity: dict
    ) -> None:
        target = fake_repo_root / ".sulis" / "projects" / "payments-app.jsonld"
        write_project_entity(target, sample_entity)
        projects_dir = target.parent
        tmp_files = list(projects_dir.glob("*.tmp"))
        assert tmp_files == []

    def test_atomic_write_calls_fsync_before_rename(
        self,
        fake_repo_root: Path,
        sample_entity: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Durability: ``os.fsync`` must be called before the rename so the
        renamed file's data is guaranteed on disk before it becomes visible
        at the target path.
        """
        call_order: list[str] = []

        original_fsync = os.fsync

        def tracking_fsync(fd: int) -> None:
            call_order.append("fsync")
            original_fsync(fd)

        original_replace = os.replace

        def tracking_replace(src, dst, *args, **kwargs):  # type: ignore[no-untyped-def]
            call_order.append("replace")
            return original_replace(src, dst, *args, **kwargs)

        monkeypatch.setattr(os, "fsync", tracking_fsync)
        monkeypatch.setattr(os, "replace", tracking_replace)

        target = fake_repo_root / ".sulis" / "projects" / "payments-app.jsonld"
        write_project_entity(target, sample_entity)

        # fsync must precede the rename
        assert "fsync" in call_order
        assert "replace" in call_order
        assert call_order.index("fsync") < call_order.index("replace")

    def test_sigint_between_write_and_rename_leaves_only_tmp(
        self,
        fake_repo_root: Path,
        sample_entity: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Chaos shim: raise ``KeyboardInterrupt`` after the .tmp file is
        written but before ``os.replace`` happens. Expected state:
        target file absent, .tmp file present.
        """

        def chaos_replace(src, dst, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise KeyboardInterrupt("simulated SIGINT")

        monkeypatch.setattr(os, "replace", chaos_replace)

        target = fake_repo_root / ".sulis" / "projects" / "payments-app.jsonld"
        tmp = target.with_suffix(".jsonld.tmp")

        with pytest.raises(KeyboardInterrupt):
            write_project_entity(target, sample_entity)

        assert not target.exists()
        assert tmp.exists()  # mid-flow cancellation leaves only the .tmp

    def test_stale_tmp_sweep_removes_dot_tmp_files(self, fake_repo_root: Path) -> None:
        """Sweep removes ``*.tmp`` and leaves non-tmp files alone."""
        projects = fake_repo_root / ".sulis" / "projects"
        stale = projects / "foo.jsonld.tmp"
        keep = projects / "bar.jsonld"
        stale.write_text('{"stale": true}')
        keep.write_text('{"real": true}')

        removed = stale_tmp_sweep(projects)

        assert removed == 1
        assert not stale.exists()
        assert keep.exists()

    def test_idempotent_after_cancellation(
        self, fake_repo_root: Path, sample_entity: dict
    ) -> None:
        """After a cancelled run leaves a .tmp file, the sweep + re-run
        produces the same outcome as a first-time run (NFR-003).
        """
        projects = fake_repo_root / ".sulis" / "projects"
        target = projects / "payments-app.jsonld"
        leftover_tmp = target.with_suffix(".jsonld.tmp")

        # Simulate a cancelled previous run
        leftover_tmp.write_text('{"partial": true}')

        # Sweep + re-mint
        stale_tmp_sweep(projects)
        assert not leftover_tmp.exists()

        write_project_entity(target, sample_entity)

        assert target.exists()
        assert json.loads(target.read_text()) == sample_entity
        assert list(projects.glob("*.tmp")) == []


# ---------------------------------------------------------------------------
# Path-safety check
# ---------------------------------------------------------------------------


class TestPathSafety:
    def test_path_safety_blocks_symlink_traversal(
        self, fake_repo_root: Path, sample_entity: dict, tmp_path: Path
    ) -> None:
        """A symlink under ``.sulis/projects/`` pointing at an outside
        location resolves outside the allowed dir and is refused.
        """
        # Create an outside target dir
        outside = tmp_path / "outside-the-repo"
        outside.mkdir()

        # Create a symlink from .sulis/projects/escape → outside/
        symlink = fake_repo_root / ".sulis" / "projects" / "escape"
        symlink.symlink_to(outside)

        evil = symlink / "evil.jsonld"
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_entity(evil, sample_entity)

    def test_path_safety_blocks_dotdot_traversal(
        self, fake_repo_root: Path, sample_entity: dict
    ) -> None:
        """``..`` traversal out of ``.sulis/projects/`` is refused after resolve()."""
        evil = fake_repo_root / ".sulis" / "projects" / ".." / "evil.jsonld"
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_entity(evil, sample_entity)

    def test_path_safety_blocks_marketplace_projects_write(
        self, fake_repo_root: Path, sample_entity: dict
    ) -> None:
        """Writing to a marketplace-managed location is refused (the
        ``plugins/sulis/instances/release-train/projects.jsonld``
        corruption case from TDD §Armor §Path-safety check).
        """
        # The fake_repo_root is the consuming repo; an attempt to write
        # to a sibling top-level dir like plugins/... is refused.
        evil = (
            fake_repo_root
            / "plugins"
            / "sulis"
            / "instances"
            / "release-train"
            / "projects.jsonld"
        )
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_entity(evil, sample_entity)

    def test_path_safety_runs_before_any_io(
        self,
        fake_repo_root: Path,
        sample_entity: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If path safety fails, no mkdir / write / fsync / rename runs."""
        io_calls: list[str] = []

        original_mkdir = Path.mkdir

        def tracking_mkdir(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            io_calls.append(f"mkdir:{self}")
            return original_mkdir(self, *args, **kwargs)

        original_write_text = Path.write_text

        def tracking_write_text(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            io_calls.append(f"write_text:{self}")
            return original_write_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", tracking_mkdir)
        monkeypatch.setattr(Path, "write_text", tracking_write_text)

        evil = fake_repo_root / ".sulis" / "projects" / ".." / "evil.jsonld"
        with pytest.raises(PathOutsideAllowedDirectoryError):
            write_project_entity(evil, sample_entity)

        # No write/mkdir should have happened on the evil path
        assert not any("evil.jsonld" in c for c in io_calls)


# ---------------------------------------------------------------------------
# Pre-existing entity (MUC-003)
# ---------------------------------------------------------------------------


class TestPreExistingEntity:
    def test_refuses_overwrite_without_allow_flag(
        self, fake_repo_root: Path, sample_entity: dict
    ) -> None:
        target = fake_repo_root / ".sulis" / "projects" / "payments-app.jsonld"
        target.write_text('{"pre-existing": true}')

        with pytest.raises(EntityAlreadyExistsError):
            write_project_entity(target, sample_entity, allow_overwrite=False)

        # Existing content untouched
        assert json.loads(target.read_text()) == {"pre-existing": True}

    def test_allows_overwrite_with_flag(
        self, fake_repo_root: Path, sample_entity: dict
    ) -> None:
        target = fake_repo_root / ".sulis" / "projects" / "payments-app.jsonld"
        target.write_text('{"pre-existing": true}')

        write_project_entity(target, sample_entity, allow_overwrite=True)

        assert json.loads(target.read_text()) == sample_entity


# ---------------------------------------------------------------------------
# Signal handler installation idempotence
# ---------------------------------------------------------------------------


class TestSignalHandlerInstallation:
    def test_install_sigint_handler_is_idempotent(self, fake_repo_root: Path) -> None:
        """Calling ``install_sigint_handler`` twice for the same projects_dir
        does not double-register.
        """
        import signal

        projects = fake_repo_root / ".sulis" / "projects"
        try:
            install_sigint_handler(projects)
            handler_after_first = signal.getsignal(signal.SIGINT)
            install_sigint_handler(projects)
            handler_after_second = signal.getsignal(signal.SIGINT)
            # Idempotence: the second call did not swap the handler
            assert handler_after_first is handler_after_second
        finally:
            signal.signal(signal.SIGINT, signal.default_int_handler)
            # Reset registry so other tests can re-install
            from _discovery import minter as _m

            _m._INSTALLED_HANDLERS.clear()

    def test_install_sigint_handler_fires_sweep_and_reraises(
        self, fake_repo_root: Path
    ) -> None:
        """When the installed handler is invoked (simulating SIGINT
        delivery), it sweeps stale ``.tmp`` files and re-raises
        ``KeyboardInterrupt`` so the operator sees a clean stack-top
        cancellation.
        """
        import signal as signal_module

        projects = fake_repo_root / ".sulis" / "projects"
        stale = projects / "leftover.jsonld.tmp"
        stale.write_text('{"partial": true}')

        try:
            install_sigint_handler(projects)
            handler = signal_module.getsignal(signal_module.SIGINT)
            assert callable(handler)
            with pytest.raises(KeyboardInterrupt):
                handler(signal_module.SIGINT, None)
            # Sweep ran
            assert not stale.exists()
            # Default handler restored so the next ^C surfaces cleanly
            assert (
                signal_module.getsignal(signal_module.SIGINT)
                is signal_module.default_int_handler
            )
        finally:
            signal_module.signal(
                signal_module.SIGINT, signal_module.default_int_handler
            )
            from _discovery import minter as _m

            _m._INSTALLED_HANDLERS.clear()
