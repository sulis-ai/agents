"""Unit tests for the Phase 2 train-run primitives.

Covers:
- check_train_trigger: force / size / staleness / nothing-fires
- write_train_run_record: shape round-trip

The full happy-path integration test (rebase chain → bundled-tip CI →
sequential merge → deploy/health/smoke) requires substantial subprocess
mocking (gh repo clone, git rebase against a fake origin, multi-step
mock_gh responses). It is deferred to a follow-up commit; for now the
happy-path is exercised end-to-end manually via /sulis-execution:run-all
in real sessions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from _wpxlib import (
    EligibilityResult,
    TRAIN_TRIGGER_MIN_SIZE,
    TRAIN_TRIGGER_STALENESS_SECONDS,
    check_train_trigger,
    write_train_run_record,
)


def _make_eligible(*wp_ids: str) -> list[EligibilityResult]:
    return [
        EligibilityResult(wp=wp, branch=f"feat/wp-{wp.lower()}-x",
                          eligible=True, reason="ready")
        for wp in wp_ids
    ]


# ─── check_train_trigger ──────────────────────────────────────────────────


def test_trigger_force_fires_even_with_empty_eligible():
    """--force fires regardless of queue."""
    fire, reason = check_train_trigger([], force=True)
    assert fire is True
    assert reason == "force"


def test_trigger_force_fires_with_one_eligible():
    """--force with 1 eligible WP fires (degenerate train = single WP)."""
    fire, reason = check_train_trigger(_make_eligible("WP-001"), force=True)
    assert fire is True


def test_trigger_no_eligible_no_force_does_not_fire():
    fire, reason = check_train_trigger([], force=False)
    assert fire is False
    assert reason == "no eligible WPs"


def test_trigger_size_fires_at_min_size():
    """Reaching TRAIN_TRIGGER_MIN_SIZE fires the size trigger."""
    eligible = _make_eligible(*[f"WP-{i:03d}" for i in range(TRAIN_TRIGGER_MIN_SIZE)])
    fire, reason = check_train_trigger(eligible)
    assert fire is True
    assert "size trigger" in reason


def test_trigger_below_min_size_does_not_fire():
    """One fewer than min size waits (no force, no staleness)."""
    eligible = _make_eligible(
        *[f"WP-{i:03d}" for i in range(TRAIN_TRIGGER_MIN_SIZE - 1)]
    )
    fire, reason = check_train_trigger(eligible)
    assert fire is False
    assert "need" in reason


def test_trigger_staleness_fires_with_one_old_wp():
    """One WP queued past the staleness threshold fires the trigger."""
    eligible = _make_eligible("WP-001")
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(seconds=TRAIN_TRIGGER_STALENESS_SECONDS + 60)
              ).strftime("%Y-%m-%dT%H:%M:%SZ")
    lookup = {"WP-001": old_ts}
    fire, reason = check_train_trigger(eligible, queued_at_lookup=lookup, now=now)
    assert fire is True
    assert "staleness trigger" in reason


def test_trigger_staleness_does_not_fire_with_fresh_wps():
    """Queued WPs younger than the threshold don't fire staleness."""
    eligible = _make_eligible("WP-001")
    now = datetime.now(timezone.utc)
    fresh_ts = (now - timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    lookup = {"WP-001": fresh_ts}
    fire, _ = check_train_trigger(eligible, queued_at_lookup=lookup, now=now)
    assert fire is False


def test_trigger_staleness_tolerates_missing_or_malformed_timestamps():
    """Missing / malformed queued_at entries don't crash; just no staleness."""
    eligible = _make_eligible("WP-001")
    fire, _ = check_train_trigger(eligible, queued_at_lookup={"WP-001": "garbage"})
    assert fire is False


# ─── write_train_run_record ───────────────────────────────────────────────


def test_write_train_run_record_creates_parent_dir(tmp_path):
    """Parent dir doesn't exist → emit creates it."""
    record_path = tmp_path / "train-runs" / "train-2026-05-21T120000Z.yaml"
    write_train_run_record(record_path, {
        "train_id": "train-2026-05-21T120000Z",
        "started_at": "2026-05-21T12:00:00Z",
        "completed_at": "2026-05-21T12:30:00Z",
        "outcome": "success",
        "batch_size": 2,
        "bundle": [
            {"wp": "WP-001", "branch": "feat/wp-001-x",
             "pre_train_sha": "aaa111", "rebased_to_sha": "bbb222",
             "merge_sha_on_dev": "ccc333"},
            {"wp": "WP-002", "branch": "feat/wp-002-y",
             "pre_train_sha": "ddd444", "rebased_to_sha": "eee555",
             "merge_sha_on_dev": "fff666"},
        ],
        "deploy_url": "https://github.com/acme/x/actions/runs/1",
        "health_status": "healthy",
        "smoke_verdict": "PASS",
    })
    assert record_path.exists()
    text = record_path.read_text()
    assert "train_id: \"train-2026-05-21T120000Z\"" in text
    assert "outcome: \"success\"" in text
    assert "batch_size: 2" in text
    assert "wp: WP-001" in text
    assert "merge_sha_on_dev: ccc333" in text


def test_write_train_run_record_handles_null_fields(tmp_path):
    """None values in the record are emitted as YAML `null`."""
    record_path = tmp_path / "train.yaml"
    write_train_run_record(record_path, {
        "train_id": "train-x",
        "outcome": "pending",
        "deploy_url": None,
        "health_status": None,
        "smoke_verdict": None,
        "bundle": [
            {"wp": "WP-001", "branch": "feat/wp-001-x",
             "pre_train_sha": "abc", "rebased_to_sha": "def",
             "merge_sha_on_dev": None},  # null until merged
        ],
    })
    text = record_path.read_text()
    assert "deploy_url: null" in text
    assert "merge_sha_on_dev: null" in text


def test_write_train_run_record_blocker_outcome(tmp_path):
    """Blocker outcome with outcome_reason field included."""
    record_path = tmp_path / "train-blocker.yaml"
    write_train_run_record(record_path, {
        "train_id": "train-y",
        "outcome": "blocker",
        "outcome_reason": "bundled-tip CI failed",
        "batch_size": 3,
        "bundle": [],
    })
    text = record_path.read_text()
    assert "outcome: \"blocker\"" in text
    assert "outcome_reason: \"bundled-tip CI failed\"" in text
