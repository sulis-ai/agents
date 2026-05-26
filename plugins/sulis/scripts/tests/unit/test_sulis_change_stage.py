"""Unit tests for `sulis-change stage` (cmd_stage).

`stage` stamps the workflow stage a change has reached into the
branch-independent local store (`{state_base}/changes/{id}/state.json`),
so the dashboard reflects where each change sits in the six-stage workflow
(recon -> specify -> design -> implement -> review -> ship).

Change-id resolution: `--change-id` if given, else the `SULIS_CHANGE_ID`
env var. Invalid stages and a missing change-id are honest errors, not
silent no-ops.

State isolation: the repo-wide autouse `_isolate_sulis_state` fixture
(tests/conftest.py) points SULIS_STATE_DIR at a per-test tmp dir, so these
writes never touch the real ~/.sulis store.
"""

from __future__ import annotations

import argparse
import importlib.util
from contextlib import ExitStack
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
_SC_PATH = _SCRIPTS / "sulis-change"


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SC_PATH))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


sc = _load_sulis_change()

import _change_state  # noqa: E402  (scripts dir is on sys.path after the load)

_GOOD_ULID = "01HYQC71000000000000000000"


# ─── emit capture harness ─────────────────────────────────────────────────


class _ExitOK(Exception):
    def __init__(self, data):
        self.data = data


class _ExitErr(Exception):
    def __init__(self, message, context=None):
        self.message = message
        self.context = context


def _capture_emit():
    captured: dict = {}

    def _ok(data=None, warnings=None, exit_code=0):
        captured["ok"] = True
        captured["data"] = data
        raise _ExitOK(data)

    def _err(message, context=None):
        captured["ok"] = False
        captured["error"] = message
        captured["context"] = context
        raise _ExitErr(message, context)

    patches = [
        mock.patch.object(sc, "emit_ok", side_effect=_ok),
        mock.patch.object(sc, "emit_error", side_effect=_err),
    ]
    return captured, patches


def _run_stage(args, captured, patches):
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with pytest.raises((_ExitOK, _ExitErr)):
            sc.cmd_stage(args)
    return captured


def _args(stage, *, change_id=None) -> argparse.Namespace:
    return argparse.Namespace(stage=stage, change_id=change_id)


# ─── happy path: explicit --change-id ──────────────────────────────────────


def test_stage_with_change_id_writes_state(monkeypatch):
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    captured, patches = _capture_emit()
    _run_stage(_args("design", change_id=_GOOD_ULID), captured, patches)

    assert captured["ok"] is True
    assert captured["data"]["stage"] == "design"
    assert captured["data"]["change_id"] == _GOOD_ULID
    # The write is real (in the isolated tmp store) — read it back.
    assert _change_state.read_change_stage(_GOOD_ULID) == "design"


# ─── happy path: resolve change-id from the environment ────────────────────


def test_stage_resolves_change_id_from_env(monkeypatch):
    monkeypatch.setenv("SULIS_CHANGE_ID", _GOOD_ULID)
    captured, patches = _capture_emit()
    _run_stage(_args("implement"), captured, patches)

    assert captured["ok"] is True
    assert captured["data"]["change_id"] == _GOOD_ULID
    assert _change_state.read_change_stage(_GOOD_ULID) == "implement"


def test_stage_each_workflow_stage_is_accepted(monkeypatch):
    for stage in _change_state.WORKFLOW_STAGES:
        captured, patches = _capture_emit()
        _run_stage(_args(stage, change_id=_GOOD_ULID), captured, patches)
        assert captured["ok"] is True, stage
        assert _change_state.read_change_stage(_GOOD_ULID) == stage


# ─── error: unknown stage ──────────────────────────────────────────────────


def test_stage_rejects_unknown_stage(monkeypatch):
    captured, patches = _capture_emit()
    _run_stage(_args("deploy", change_id=_GOOD_ULID), captured, patches)

    assert captured["ok"] is False
    assert "deploy" in captured["error"]
    # Lists the valid stages so the caller can correct.
    assert captured["context"]["valid_stages"] == list(_change_state.WORKFLOW_STAGES)
    # Nothing was written for the bad stage.
    assert _change_state.read_change_stage(_GOOD_ULID) is None


# ─── error: no change to stamp ─────────────────────────────────────────────


def test_stage_errors_when_no_change_id(monkeypatch):
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    captured, patches = _capture_emit()
    _run_stage(_args("recon"), captured, patches)

    assert captured["ok"] is False
    assert "SULIS_CHANGE_ID" in captured["error"]
