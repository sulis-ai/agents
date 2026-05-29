"""Regression coverage for the TOCTOU edge in `_rollback_pre_merge_train_state`.

Lesson #68: the rollback helper guards its `read_train_state` call with
`except RuntimeError`, after a top-level `state_path.exists()` check. But
`read_train_state` raises `FileNotFoundError` (not `RuntimeError`) when the
state file vanishes in the window between the `exists()` check and the read.
Under `TrainLock` the window is effectively unreachable in practice, but an
unhandled `FileNotFoundError` in `cmd_run`'s terminal error handlers would add
noise to an already-failing path. Widening the catch to
`(RuntimeError, FileNotFoundError)` makes the helper degrade cleanly (return
False, leave state for manual inspection).

This test loads `wpx-train` as a module (it has no .py extension and is
invoked via shebang in production) and simulates the vanish by making
`read_train_state` raise `FileNotFoundError` while the state file passes the
top-level `exists()` guard.
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
    module = _load_wpx_train_module()
    yield module
    sys.modules.pop("wpx_train_module", None)


def test_rollback_returns_false_when_state_vanishes_in_toctou_window(
    wpx_train, tmp_path, monkeypatch,
):
    """The state file passes the top-level exists() guard, but read_train_state
    raises FileNotFoundError because the file vanished in the TOCTOU window.
    The helper must return False without propagating the exception."""
    train_id = "train-toctou"
    runs_dir = tmp_path / "train-runs"
    runs_dir.mkdir(parents=True)
    paths = SimpleNamespace(train_runs_dir=runs_dir)

    # Create the state file so the helper's top-of-body `exists()` guard passes.
    state_path = wpx_train.train_state_path(runs_dir, train_id)
    state_path.write_text("{}")

    # Simulate the vanish: read_train_state re-checks existence and raises
    # FileNotFoundError (its real behaviour for a missing file).
    def _raise_fnf(_state_path):
        raise FileNotFoundError(f"vanished in the toctou window: {_state_path}")

    monkeypatch.setattr(wpx_train, "read_train_state", _raise_fnf)

    # Before the fix (`except RuntimeError`), this propagates FileNotFoundError.
    # After widening to (RuntimeError, FileNotFoundError), it returns False.
    assert (
        wpx_train._rollback_pre_merge_train_state(paths, train_id) is False
    )


def test_rollback_returns_false_on_corrupt_state_runtimeerror(
    wpx_train, tmp_path, monkeypatch,
):
    """The pre-existing RuntimeError path (corrupt JSON) must keep degrading
    cleanly — widening the catch must not regress it."""
    train_id = "train-corrupt"
    runs_dir = tmp_path / "train-runs"
    runs_dir.mkdir(parents=True)
    paths = SimpleNamespace(train_runs_dir=runs_dir)

    state_path = wpx_train.train_state_path(runs_dir, train_id)
    state_path.write_text("{}")

    def _raise_runtime(_state_path):
        raise RuntimeError("corrupt state json")

    monkeypatch.setattr(wpx_train, "read_train_state", _raise_runtime)

    assert (
        wpx_train._rollback_pre_merge_train_state(paths, train_id) is False
    )
