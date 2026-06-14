"""Unit tests for #266 + #265 — wpx-train keeps the LOCAL change worktree in
sync with origin so gate reviewers never read stale state.

#266: the commit phase squash-merges each WP into origin's change branch (via
the GitHub API) but the local change worktree HEAD stays at the pre-batch
tip. Gate reviewers read the local worktree → stale state ('code not present').
Fix: `_sync_local_change_worktree_after_train` fast-forwards the local worktree
to the pushed origin tip, inside both finalise paths, before emit_result.

#265: Step 0's back-integration is a LOCAL merge commit that was never pushed;
the commit phase rebases onto `origin/{base}` (the old tip), so the local
branch diverged from origin. Fix: Step 0 pushes the back-integration on
`merged_ok`, so the rebase base includes it and the post-train ff is a true
fast-forward.

These tests load `scripts/wpx-train` as a module (no .py extension) and
monkeypatch the helpers on the loaded module to capture behaviour without a
real git repo or GitHub API.
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
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    loader = importlib.machinery.SourceFileLoader(
        "wpx_train_module", str(_SCRIPTS_DIR / "wpx-train"),
    )
    spec = importlib.util.spec_from_loader("wpx_train_module", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["wpx_train_module"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wpx_train():
    return _load_wpx_train_module()


# ─── #266 — _sync_local_change_worktree_after_train ───────────────────────


def test_sync_skipped_outside_change_context(wpx_train, monkeypatch):
    """No --change-worktree-path (or a non-change base) → skipped, no ff call."""
    called = {"n": 0}
    monkeypatch.setattr(
        wpx_train, "ff_local_change_branch_from_origin",
        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or {"status": "x"},
    )
    record: dict = {}
    # base is a change branch but no worktree path → skip
    wpx_train._sync_local_change_worktree_after_train(
        SimpleNamespace(change_worktree_path=None), "change/feat-x", "t", record,
    )
    assert record["local_worktree_sync"] == "skipped"
    # non-change base with a worktree path → also skip
    wpx_train._sync_local_change_worktree_after_train(
        SimpleNamespace(change_worktree_path="/wt"), "main", "t", record,
    )
    assert record["local_worktree_sync"] == "skipped"
    assert called["n"] == 0


def test_sync_fast_forwards_local_worktree(wpx_train, monkeypatch):
    """In a change context, the helper ff's the local worktree and records the
    status returned by the ff helper."""
    captured = {}

    def fake_ff(worktree, branch, **kw):
        captured["worktree"] = str(worktree)
        captured["branch"] = branch
        return {"status": "fast_forwarded", "advanced_commits": 3,
                "change_branch": branch}

    monkeypatch.setattr(wpx_train, "ff_local_change_branch_from_origin", fake_ff)
    record: dict = {}
    wpx_train._sync_local_change_worktree_after_train(
        SimpleNamespace(change_worktree_path="/wt/change"),
        "change/feat-x", "train-1", record,
    )
    assert record["local_worktree_sync"] == "fast_forwarded"
    assert captured == {"worktree": "/wt/change", "branch": "change/feat-x"}


def test_sync_non_fatal_on_divergence(wpx_train, monkeypatch, capsys):
    """If the ff is not possible (diverged), the helper records the status,
    logs a recovery hint, and does NOT raise (non-fatal)."""
    monkeypatch.setattr(
        wpx_train, "ff_local_change_branch_from_origin",
        lambda *a, **k: {"status": "ff_not_possible", "error": "diverged"},
    )
    record: dict = {}
    wpx_train._sync_local_change_worktree_after_train(
        SimpleNamespace(change_worktree_path="/wt/change"),
        "change/feat-x", "train-1", record,
    )
    assert record["local_worktree_sync"] == "ff_not_possible"
    err = capsys.readouterr().err
    assert "merge --ff-only" in err  # the recovery hint is surfaced


# ─── #265 — Step 0 pushes the back-integration on merged_ok ───────────────


def _fake_paths(tmp_path):
    runs = tmp_path / "train-runs"
    runs.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(train_runs_dir=runs)


def test_step_0_pushes_back_integration_on_merged_ok(
    wpx_train, tmp_path, monkeypatch,
):
    """When Step 0 actually merges main in (merged_ok), it pushes the change
    branch to origin so the commit phase's rebase base includes the
    back-integration (prevents the #265 divergence)."""
    monkeypatch.setattr(
        wpx_train, "back_integrate_change_branch",
        lambda wt, br, **kw: {"status": "merged_ok", "merged_commits": 2,
                              "change_branch": br},
    )
    pushes: list = []

    def fake_run(cmd, **kw):
        if cmd[:2] == ["git", "-C"] and "push" in cmd:
            pushes.append(cmd)
            return (0, "", "")
        return (0, "", "")

    monkeypatch.setattr(wpx_train, "_run", fake_run)

    args = SimpleNamespace(change_worktree_path=str(tmp_path / "wt"))
    record: dict = {}
    wpx_train._step_0_arrival_check(
        args, _fake_paths(tmp_path), "train-x", "change/feat-x", record,
    )
    assert record.get("step_0_back_integration_pushed") is True
    assert pushes, "Step 0 must push the back-integration to origin on merged_ok"
    pushed_cmd = pushes[0]
    assert pushed_cmd[-2:] == ["push", "origin"] or pushed_cmd[-1] == "change/feat-x"
    assert "change/feat-x" in pushed_cmd


def test_step_0_no_push_when_already_current(wpx_train, tmp_path, monkeypatch):
    """No back-integration merge (already_current) → nothing to push."""
    monkeypatch.setattr(
        wpx_train, "back_integrate_change_branch",
        lambda wt, br, **kw: {"status": "already_current", "change_branch": br},
    )
    pushes: list = []
    monkeypatch.setattr(
        wpx_train, "_run",
        lambda cmd, **kw: (pushes.append(cmd) if "push" in cmd else None) or (0, "", ""),
    )
    args = SimpleNamespace(change_worktree_path=str(tmp_path / "wt"))
    record: dict = {}
    wpx_train._step_0_arrival_check(
        args, _fake_paths(tmp_path), "train-x", "change/feat-x", record,
    )
    assert "step_0_back_integration_pushed" not in record
    assert not pushes


def test_step_0_push_failure_is_non_fatal(wpx_train, tmp_path, monkeypatch, capsys):
    """A failed back-integration push records False + warns, but does not raise
    (the train proceeds; it may diverge as before)."""
    monkeypatch.setattr(
        wpx_train, "back_integrate_change_branch",
        lambda wt, br, **kw: {"status": "merged_ok", "merged_commits": 1,
                              "change_branch": br},
    )
    monkeypatch.setattr(
        wpx_train, "_run",
        lambda cmd, **kw: (1, "", "rejected: non-fast-forward") if "push" in cmd
        else (0, "", ""),
    )
    args = SimpleNamespace(change_worktree_path=str(tmp_path / "wt"))
    record: dict = {}
    wpx_train._step_0_arrival_check(
        args, _fake_paths(tmp_path), "train-x", "change/feat-x", record,
    )
    assert record.get("step_0_back_integration_pushed") is False
    assert "could not push" in capsys.readouterr().err
