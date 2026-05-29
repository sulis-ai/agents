"""Regression coverage for the repo-wide env isolation in tests/conftest.py.

Lesson #74: the autouse `_isolate_sulis_state` fixture isolated
SULIS_STATE_DIR but not SULIS_CHANGE_ID, so the suite failed inside a
change-bound session (where SULIS_CHANGE_ID is exported) — subcommands like
`sulis-change mark-shipped` that fall back to the env var picked up the real
session's change id through run_tool's `os.environ.copy()`.

These tests pin BOTH halves of the isolation. They fail (RED) if either env
var leaks into a test from the parent environment; run e.g. with
`SULIS_CHANGE_ID=01KSGFAKE... pytest tests/unit/test_conftest_env_isolation.py`
to exercise the regression directly.
"""

from __future__ import annotations

import os


def test_sulis_change_id_cleared_by_autouse_fixture():
    """SULIS_CHANGE_ID must never be visible inside a test, even when the
    parent shell exported it (a change-bound session). The autouse
    `_isolate_sulis_state` fixture clears it for every test."""
    assert os.environ.get("SULIS_CHANGE_ID") is None


def test_sulis_state_dir_redirected_to_tmp():
    """SULIS_STATE_DIR must point at a per-test tmp dir, never the real
    ~/.sulis store, so subprocess writes don't pollute the developer/CI
    runner's global change store."""
    state_dir = os.environ.get("SULIS_STATE_DIR")
    assert state_dir is not None
    assert state_dir not in ("", os.path.expanduser("~/.sulis"))
