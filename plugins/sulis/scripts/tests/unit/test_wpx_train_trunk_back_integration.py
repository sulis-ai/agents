"""Unit tests for issue #228 — wpx-train Step-0 / Step-12.5 back-integration
must target the trunk (``origin/main``), not the retired ``dev`` branch.

Background (the bug):

  The repo migrated dev→main (#177); there is no ``dev`` branch. But
  ``wpx-train``'s change-branch back-integration (Step 0 arrival check and
  Step 12.5 post-batch) still passed ``dev_ref="origin/dev"`` to
  ``back_integrate_change_branch`` and logged "...from origin/dev". Shipping
  into a change branch failed with::

      Step 0 fetch_failed: fatal: couldn't find remote ref dev

  Note ``back_integrate_change_branch`` ALREADY defaults
  ``dev_ref="origin/main"`` and derives the fetch ref from the param — the
  bug was purely the CALLER overriding the good default with a stale string.

The fix:

  Both ``_step_0_arrival_check`` and ``_step_12_5_back_integration`` target
  the trunk (``origin/main``), consistent with wpx-train's own
  ``base_branch or "main"`` convention used everywhere else in the file, and
  with ``wpx-pipeline`` which already passes ``dev_ref="origin/main"``.

These tests load ``scripts/wpx-train`` as a module (no .py extension) and
monkeypatch ``back_integrate_change_branch`` on the loaded module to capture
the ``dev_ref`` the caller actually passes.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent


def _load_wpx_train_module():
    """Load scripts/wpx-train as ``wpx_train_module`` (no .py extension)."""
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    script_path = _SCRIPTS_DIR / "wpx-train"
    loader = importlib.machinery.SourceFileLoader(
        "wpx_train_module", str(script_path),
    )
    spec = importlib.util.spec_from_loader("wpx_train_module", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["wpx_train_module"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wpx_train():
    return _load_wpx_train_module()


def _fake_paths(tmp_path):
    """Minimal WpxPaths-like stub: only train_runs_dir is touched on success."""
    runs = tmp_path / "train-runs"
    runs.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(train_runs_dir=runs)


# ─── Step 0 arrival check ─────────────────────────────────────────────────


def test_step_0_back_integration_targets_trunk_not_dev(
    wpx_train, tmp_path, monkeypatch, capsys,
):
    """Step 0 passes ``dev_ref="origin/main"`` (trunk), never ``origin/dev``."""
    captured_kwargs: dict = {}

    def fake_back_integrate(worktree, branch, dev_ref="origin/main", **kw):
        captured_kwargs["dev_ref"] = dev_ref
        return {"status": "already_current", "change_branch": branch}

    monkeypatch.setattr(
        wpx_train, "back_integrate_change_branch", fake_back_integrate,
    )

    args = SimpleNamespace(change_worktree_path=str(tmp_path / "wt"))
    record: dict = {}
    wpx_train._step_0_arrival_check(
        args, _fake_paths(tmp_path), "train-x",
        "change/feat-dark-mode", record,
    )

    assert captured_kwargs["dev_ref"] == "origin/main", (
        "Step 0 must back-integrate the change branch from the trunk "
        "(origin/main), not the retired dev branch."
    )
    # The Step-0 log line must reference the trunk, not dev.
    err = capsys.readouterr().err
    assert "origin/dev" not in err
    assert "origin/main" in err


def test_step_12_5_back_integration_targets_trunk_not_dev(
    wpx_train, tmp_path, monkeypatch, capsys,
):
    """Step 12.5 post-batch back-integration also targets the trunk."""
    captured_kwargs: dict = {}

    def fake_back_integrate(worktree, branch, dev_ref="origin/main", **kw):
        captured_kwargs["dev_ref"] = dev_ref
        return {"status": "already_current", "change_branch": branch}

    monkeypatch.setattr(
        wpx_train, "back_integrate_change_branch", fake_back_integrate,
    )

    args = SimpleNamespace(change_worktree_path=str(tmp_path / "wt"))
    record: dict = {}
    wpx_train._step_12_5_back_integration(
        args, "train-x", "change/feat-dark-mode", record,
    )

    assert captured_kwargs["dev_ref"] == "origin/main"
    err = capsys.readouterr().err
    assert "origin/dev" not in err
    assert "origin/main" in err


# ─── default base-branch target + source-level guard ─────────────────────


def test_no_stale_origin_dev_in_back_integration_callers():
    """Source-level guard: the change-branch back-integration callers and
    their default must reference the trunk, never the retired dev branch."""
    train_src = (_SCRIPTS_DIR / "wpx-train").read_text(encoding="utf-8")
    # The two back-integration call sites must not pass dev_ref="origin/dev".
    assert 'dev_ref="origin/dev"' not in train_src, (
        "back_integrate_change_branch callers must pass origin/main, not "
        "origin/dev (#228 — dev branch retired in #177)."
    )
    # The default ship target must be the trunk.
    assert 'args.base_branch or "dev"' not in train_src, (
        "Default ship target must be the trunk (main), not the retired dev."
    )
