"""Unit tests for the global change store (slice A.5 of the dashboard work).

The local store under {state_base}/changes/ is the branch-independent global
index of all changes — what the dashboard + `sulis-change list` + nuke read.
git is per-branch, so a committed manifest on a change branch can't be
enumerated from dev; these records (change.json) can.

Covers:
  - sulis_state_base(): SULIS_STATE_DIR override vs ~/.sulis fallback.
  - write_change_record / read_change_record: full record, round-trip.
  - list_all_changes: enumerates records, skips record-less dirs, orders
    most-recent-first, overlays the live stage from state.json.
"""

from __future__ import annotations

import json

import _change_state as cs


_GOOD_ULID = "01HYQC71000000000000000000"
_ULID_B = "01HYQC72000000000000000000"
_ULID_C = "01HYQC73000000000000000000"


def _record(change_id: str, **overrides) -> dict:
    base = {
        "change_id": change_id,
        "handle": "CH-" + change_id[3:9],
        "slug": "introduce-payments",
        "primitive": "create",
        "branch": "change/create-introduce-payments",
        "worktree_path": "/tmp/wt",
        "intent": "add subscription billing",
        "base_branch": "dev",
        "base_sha": "abc1234def5678",
        "created_at": "2026-05-26T11:00:00Z",
        "stage": "recon",
    }
    base.update(overrides)
    return base


# ─── sulis_state_base resolver ─────────────────────────────────────────────


def test_state_base_honours_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "isolated"))
    assert cs.sulis_state_base() == tmp_path / "isolated"


def test_state_base_falls_back_to_home(tmp_path, monkeypatch):
    monkeypatch.delenv("SULIS_STATE_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cs.sulis_state_base() == tmp_path / ".sulis"


def test_changes_base_under_state_base(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    assert cs.changes_base() == tmp_path / "changes"


def test_change_dir_under_changes_base(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    assert cs.change_dir(_GOOD_ULID) == tmp_path / "changes" / _GOOD_ULID


def test_state_path_honours_override(tmp_path, monkeypatch):
    """write_change_stage routes through the resolver too."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    path = cs.write_change_stage(_GOOD_ULID, "recon")
    assert path == (tmp_path / "changes" / _GOOD_ULID / "state.json")


# ─── write_change_record / read_change_record ──────────────────────────────


def test_write_change_record_creates_change_json(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    path = cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID))
    assert path == (tmp_path / "changes" / _GOOD_ULID / "change.json")
    assert path.exists()


def test_write_change_record_returns_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    path = cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID))
    assert path.is_absolute()


def test_change_record_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID))
    record = cs.read_change_record(_GOOD_ULID)
    assert record["change_id"] == _GOOD_ULID
    assert record["slug"] == "introduce-payments"
    assert record["primitive"] == "create"
    assert record["branch"] == "change/create-introduce-payments"
    assert record["intent"] == "add subscription billing"
    assert record["base_branch"] == "dev"
    # L-11 / #44: base_sha must persist — the cockpit diff route needs it as
    # the git ref to diff the worktree against. Dropping it left diffs dead.
    assert record["base_sha"] == "abc1234def5678"
    assert record["stage"] == "recon"


def test_change_record_has_all_canonical_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    path = cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID))
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in cs._CHANGE_RECORD_FIELDS:
        assert field in data, f"missing field {field!r}"


# ─── #38: shipped terminal stage + shipped_at + mark_change_shipped ─────────


def test_shipped_is_a_valid_terminal_stage():
    assert cs.is_valid_stage("shipped")
    # And it's distinct from the 6 workflow stages
    assert "shipped" not in cs.WORKFLOW_STAGES


def test_shipped_at_round_trips_in_record(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID,
                           _record(_GOOD_ULID, shipped_at="2026-05-27T16:00:00Z"))
    record = cs.read_change_record(_GOOD_ULID)
    assert record["shipped_at"] == "2026-05-27T16:00:00Z"


def test_mark_change_shipped_sets_stage_and_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID))
    cs.write_change_stage(_GOOD_ULID, "ship")  # active in ship stage

    result = cs.mark_change_shipped(_GOOD_ULID, now="2026-05-27T16:00:00Z")
    assert result is not None
    # The PERSISTED record must carry the shipped stage (not just the overlay)
    # — direct readers like `cmd_nuke` use read_change_record without the
    # overlay, and they must see 'shipped' to enforce the audit-trail guard.
    record = cs.read_change_record(_GOOD_ULID)
    assert record["shipped_at"] == "2026-05-27T16:00:00Z"
    assert record["stage"] == "shipped"
    # The overlay store agrees (list_all_changes reads state.json over the record)
    rows = cs.list_all_changes()
    assert rows[0]["stage"] == "shipped"


def test_mark_change_shipped_is_idempotent_preserves_first_timestamp(
    tmp_path, monkeypatch,
):
    """A second mark-shipped (e.g. re-running the ship flow) MUST NOT
    overwrite the original shipped_at — the audit trail is the first event."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID))
    cs.mark_change_shipped(_GOOD_ULID, now="2026-05-27T16:00:00Z")
    cs.mark_change_shipped(_GOOD_ULID, now="2026-05-27T17:00:00Z")  # later
    record = cs.read_change_record(_GOOD_ULID)
    assert record["shipped_at"] == "2026-05-27T16:00:00Z"


def test_mark_change_shipped_returns_none_for_missing_record(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    assert cs.mark_change_shipped("01HYQC79000000000000000000",
                                  now="2026-05-27T16:00:00Z") is None


def test_write_change_record_defaults_missing_fields(tmp_path, monkeypatch):
    """Missing keys default to "" (str); stage defaults to recon."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    path = cs.write_change_record(_GOOD_ULID, {"change_id": _GOOD_ULID})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["slug"] == ""
    assert data["intent"] == ""
    assert data["stage"] == "recon"


def test_read_change_record_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    assert cs.read_change_record(_GOOD_ULID) is None


def test_read_change_record_corrupt_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    d = tmp_path / "changes" / _GOOD_ULID
    d.mkdir(parents=True)
    (d / "change.json").write_text("{not json", encoding="utf-8")
    with mock_warning(cs):
        assert cs.read_change_record(_GOOD_ULID) is None


# ─── change_record_is_unreadable (#22 safety-check predicate) ──────────────
#
# `read_change_record` collapses two distinct states to None: "file absent"
# (benign) and "file exists but is unreadable" (load-bearing for safety
# checks). `change_record_is_unreadable` is the predicate that
# distinguishes the second case — used by `sulis-change nuke` so the #38
# shipped-protection guard can't silently fail open on a corrupt record.


def test_change_record_is_unreadable_returns_false_when_record_absent(
    tmp_path, monkeypatch,
):
    """File doesn't exist on disk → not unreadable, just absent (benign)."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    assert cs.change_record_is_unreadable(_GOOD_ULID) is False


def test_change_record_is_unreadable_returns_false_when_record_ok(
    tmp_path, monkeypatch,
):
    """File exists and parses cleanly → not unreadable."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID))
    assert cs.change_record_is_unreadable(_GOOD_ULID) is False


def test_change_record_is_unreadable_returns_true_on_corrupt_json(
    tmp_path, monkeypatch,
):
    """File exists but JSON is malformed → unreadable. This is the case the
    #22 fix exists to surface — the shipped-protection check at the nuke
    call site keys off this to refuse loudly instead of failing open."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    d = tmp_path / "changes" / _GOOD_ULID
    d.mkdir(parents=True)
    (d / "change.json").write_text("{not valid json", encoding="utf-8")
    with mock_warning(cs):
        assert cs.change_record_is_unreadable(_GOOD_ULID) is True


def test_change_record_is_unreadable_returns_true_on_empty_file(
    tmp_path, monkeypatch,
):
    """An empty file exists but parses to nothing → unreadable. Catches the
    truncated-write failure mode (e.g. process killed mid-write)."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    d = tmp_path / "changes" / _GOOD_ULID
    d.mkdir(parents=True)
    (d / "change.json").write_text("", encoding="utf-8")
    with mock_warning(cs):
        assert cs.change_record_is_unreadable(_GOOD_ULID) is True


# ─── list_all_changes ──────────────────────────────────────────────────────


def test_list_all_changes_enumerates_records(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID, slug="a-change"))
    cs.write_change_record(_ULID_B, _record(_ULID_B, slug="b-change"))
    records = cs.list_all_changes()
    slugs = sorted(r["slug"] for r in records)
    assert slugs == ["a-change", "b-change"]


def test_list_all_changes_empty_when_no_store(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "nope"))
    assert cs.list_all_changes() == []


def test_list_all_changes_skips_record_less_dirs(tmp_path, monkeypatch):
    """A dir with state.json/CONTEXT.md but no change.json is skipped."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    # One proper record
    cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID))
    # A legacy/partial dir without change.json
    legacy = tmp_path / "changes" / _ULID_B
    legacy.mkdir(parents=True)
    (legacy / "state.json").write_text('{"stage": "implement"}', encoding="utf-8")
    records = cs.list_all_changes()
    ids = [r["change_id"] for r in records]
    assert ids == [_GOOD_ULID]


def test_list_all_changes_orders_most_recent_first(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID, _record(
        _GOOD_ULID, slug="oldest", created_at="2026-05-26T09:00:00Z"))
    cs.write_change_record(_ULID_B, _record(
        _ULID_B, slug="newest", created_at="2026-05-26T13:00:00Z"))
    cs.write_change_record(_ULID_C, _record(
        _ULID_C, slug="middle", created_at="2026-05-26T11:00:00Z"))
    records = cs.list_all_changes()
    assert [r["slug"] for r in records] == ["newest", "middle", "oldest"]


def test_list_all_changes_overlays_live_stage(tmp_path, monkeypatch):
    """change.json seeds stage=recon; state.json's live stage wins in the view."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID, stage="recon"))
    cs.write_change_stage(_GOOD_ULID, "implement")  # advance the live cursor
    records = cs.list_all_changes()
    assert len(records) == 1
    assert records[0]["stage"] == "implement"


def test_list_all_changes_keeps_seed_stage_without_state_json(tmp_path, monkeypatch):
    """No state.json → the record's own stage is reported as-is."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    cs.write_change_record(_GOOD_ULID, _record(_GOOD_ULID, stage="recon"))
    records = cs.list_all_changes()
    assert records[0]["stage"] == "recon"


# ─── helpers ────────────────────────────────────────────────────────────────


class mock_warning:
    """Context manager that silences (and tolerates) _emit_warning calls."""

    def __init__(self, module):
        from unittest import mock
        self._patch = mock.patch.object(module, "_emit_warning")

    def __enter__(self):
        return self._patch.__enter__()

    def __exit__(self, *exc):
        return self._patch.__exit__(*exc)
