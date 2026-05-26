"""Unit tests for _change_state.py (per-change workflow-stage persistence).

A change moves through six workflow stages:
  recon -> specify -> design -> implement -> review -> ship

The current stage is persisted as lightweight per-change LOCAL state at
~/.sulis/changes/{change_id}/state.json (alongside CONTEXT.md / session.json
/ launch.sh) — NOT the committed .changes/*.yaml manifest. Stage is local
workflow position, not shared/committed state.

write_change_stage is best-effort like write_change_context: an OSError on
an unwritable path degrades to None + a logged warning, never crashes the
caller (`sulis-change start` stamps the initial stage and must not abort if
the local state dir is unwritable).
"""

from __future__ import annotations

import json
from unittest import mock

import pytest

import _change_state as cs


_GOOD_ULID = "01HYQC71000000000000000000"


@pytest.fixture(autouse=True)
def _home_base_isolation(tmp_path_factory, monkeypatch):
    """This module exercises the ~/.sulis HOME-fallback path explicitly, so it
    opts out of the repo-wide SULIS_STATE_DIR isolation (root conftest) and
    isolates via HOME instead. Tests that set their own HOME override the
    default set here, so existing path assertions hold; tests that don't are
    still kept out of the real home."""
    monkeypatch.delenv("SULIS_STATE_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))


# ─── Canonical stages + validator ─────────────────────────────────────────


def test_workflow_stages_are_the_six_in_order():
    assert cs.WORKFLOW_STAGES == (
        "recon", "specify", "design", "implement", "review", "ship",
    )


def test_is_valid_stage_accepts_each_canonical_stage():
    for stage in cs.WORKFLOW_STAGES:
        assert cs.is_valid_stage(stage) is True


def test_is_valid_stage_rejects_unknown():
    assert cs.is_valid_stage("deploy") is False
    assert cs.is_valid_stage("") is False
    assert cs.is_valid_stage("Recon") is False  # case-sensitive


# ─── write_change_stage ───────────────────────────────────────────────────


def test_write_change_stage_creates_state_json_at_expected_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = cs.write_change_stage(_GOOD_ULID, "recon")
    expected = tmp_path / ".sulis" / "changes" / _GOOD_ULID / "state.json"
    assert path == expected
    assert path.exists()


def test_write_change_stage_returns_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = cs.write_change_stage(_GOOD_ULID, "recon")
    assert path.is_absolute()


def test_write_change_stage_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = cs.write_change_stage(_GOOD_ULID, "specify")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["change_id"] == _GOOD_ULID
    assert data["stage"] == "specify"
    # ISO-8601 UTC with trailing Z
    assert data["updated_at"].endswith("Z")
    assert "T" in data["updated_at"]


def test_write_change_stage_creates_parent_dir_if_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert not (tmp_path / ".sulis").exists()
    path = cs.write_change_stage(_GOOD_ULID, "recon")
    assert path.parent.exists()


def test_write_change_stage_rejects_unknown_stage(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(cs, "_emit_warning") as warned:
        result = cs.write_change_stage(_GOOD_ULID, "bogus")
    assert result is None
    assert warned.called


def test_write_change_stage_appends_to_stage_history(tmp_path, monkeypatch):
    """Each write appends a {stage, at} row to stage_history (dashboard use)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    cs.write_change_stage(_GOOD_ULID, "recon")
    path = cs.write_change_stage(_GOOD_ULID, "specify")
    data = json.loads(path.read_text(encoding="utf-8"))
    history = data["stage_history"]
    assert [row["stage"] for row in history] == ["recon", "specify"]
    assert all("at" in row for row in history)


# ─── write_change_stage best-effort degrade ───────────────────────────────


def test_write_change_stage_returns_none_when_write_text_raises(tmp_path, monkeypatch):
    """An unwritable state.json degrades to None, not a traceback."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(cs.Path, "write_text",
                           side_effect=PermissionError(13, "Permission denied")):
        result = cs.write_change_stage(_GOOD_ULID, "recon")
    assert result is None


def test_write_change_stage_returns_none_when_mkdir_raises(tmp_path, monkeypatch):
    """An unwritable ~/.sulis/changes dir degrades to None, not raise."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(cs.Path, "mkdir",
                           side_effect=OSError(30, "Read-only file system")):
        result = cs.write_change_stage(_GOOD_ULID, "recon")
    assert result is None


# ─── read_change_stage ────────────────────────────────────────────────────


def test_read_change_stage_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cs.write_change_stage(_GOOD_ULID, "design")
    assert cs.read_change_stage(_GOOD_ULID) == "design"


def test_read_change_stage_missing_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cs.read_change_stage(_GOOD_ULID) is None


def test_read_change_stage_corrupt_json_returns_none(tmp_path, monkeypatch):
    """A malformed state.json degrades to None, not a JSONDecodeError."""
    monkeypatch.setenv("HOME", str(tmp_path))
    state_dir = tmp_path / ".sulis" / "changes" / _GOOD_ULID
    state_dir.mkdir(parents=True)
    (state_dir / "state.json").write_text("{not valid json", encoding="utf-8")
    assert cs.read_change_stage(_GOOD_ULID) is None


def test_read_change_stage_reflects_latest_write(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cs.write_change_stage(_GOOD_ULID, "recon")
    cs.write_change_stage(_GOOD_ULID, "implement")
    assert cs.read_change_stage(_GOOD_ULID) == "implement"
