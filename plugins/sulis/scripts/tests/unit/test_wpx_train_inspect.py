"""Unit tests for v0.17.0 — wpx-train inspect subcommand (Phase 1.2).

Tests the inspect command + its supporting helpers:
- render_train_state_plain_english: founder-friendly rendering for
  each named phase (pending, rebasing, ci_running, merging, deploying,
  verifying, success, failed, paused, aborted)
- list_train_runs: enumerates in-flight + historical trains;
  most-recent-first ordering
- cmd_inspect-level behaviour (verified via the helpers; the cmd_*
  function is a thin wrapper around them)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

from _wpxlib import (  # noqa: E402
    init_train_state,
    list_train_runs,
    render_train_state_plain_english,
    train_state_path,
    update_train_phase,
    update_wp_phase_outcome,
)


# ─── render_train_state_plain_english ────────────────────────────────────


def _make_state(phase: str, tmp_path: Path, **extras) -> dict:
    """Helper: build a state dict at a named phase."""
    bundle = extras.pop("bundle", [
        {"wp": "WP-001", "branch": "feat/wp-001", "pre_train_sha": "abc"},
    ])
    init_train_state(tmp_path, "train-test", bundle, {"project": "demo"})
    state_path = train_state_path(tmp_path, "train-test")
    if phase != "pending":
        update_train_phase(state_path, phase, **{
            k: v for k, v in extras.items()
            if k in ("pause_reason", "recovery_hint")
        })
    from _wpxlib import read_train_state
    return read_train_state(state_path)


@pytest.mark.parametrize("phase,expected_phrase", [
    ("pending", "Selected the bundle"),
    ("rebasing", "Rebasing the feature branches"),
    ("ci_running", "Waiting for the bundled-tip CI"),
    ("merging", "Squash-merging"),
    ("deploying", "Waiting for the deploy workflow"),
    ("verifying", "health + smoke"),
    ("success", "All work merged"),
    ("failed", "revert path ran"),
    ("paused", "Needs attention"),
    ("aborted", "Aborted by founder"),
])
def test_render_each_phase_has_descriptive_translation(tmp_path, phase, expected_phrase):
    """Every phase has a founder-friendly description in the renderer."""
    state = _make_state(phase, tmp_path)
    rendered = render_train_state_plain_english(state)
    assert expected_phrase in rendered, (
        f"Phase {phase!r} rendering missing expected phrase {expected_phrase!r}.\n"
        f"Rendered:\n{rendered}"
    )


def test_render_shows_pause_reason_and_recovery_hint(tmp_path):
    """Paused state surfaces both pause_reason and recovery_hint."""
    state = _make_state(
        "paused", tmp_path,
        pause_reason="bundled-tip-ci-red",
        recovery_hint="Fix CI on feat/wp-001; run wpx-train resume train-test",
    )
    rendered = render_train_state_plain_english(state)
    assert "bundled-tip-ci-red" in rendered
    assert "wpx-train resume" in rendered
    assert "Pause reason:" in rendered
    assert "What to do:" in rendered


def test_render_shows_bundle_with_per_wp_outcomes(tmp_path):
    """Bundle section shows per-WP outcomes after phase advances."""
    bundle = [
        {"wp": "WP-001", "branch": "feat/wp-001", "pre_train_sha": "a"},
        {"wp": "WP-002", "branch": "feat/wp-002", "pre_train_sha": "b"},
    ]
    state = _make_state("rebasing", tmp_path, bundle=bundle)
    state_path = train_state_path(tmp_path, "train-test")
    update_wp_phase_outcome(state_path, "WP-001", "rebasing", "rebased")
    update_wp_phase_outcome(state_path, "WP-002", "rebasing", "conflict")
    from _wpxlib import read_train_state
    state = read_train_state(state_path)
    rendered = render_train_state_plain_english(state)
    assert "WP-001" in rendered
    assert "rebased" in rendered
    assert "WP-002" in rendered
    assert "conflict" in rendered


def test_render_shows_merged_sha_for_completed_wps(tmp_path):
    """Bundle entries with merge_sha_on_dev populated show the short SHA."""
    state = _make_state("merging", tmp_path)
    state_path = train_state_path(tmp_path, "train-test")
    # Manually set merge_sha_on_dev for testing
    from _wpxlib import read_train_state, write_train_state
    s = read_train_state(state_path)
    s["bundle"][0]["merge_sha_on_dev"] = "abc12345def67890"
    write_train_state(state_path, s)
    state = read_train_state(state_path)
    rendered = render_train_state_plain_english(state)
    # Short SHA (first 8 chars)
    assert "abc12345" in rendered
    assert "merged as" in rendered


def test_render_includes_phase_history(tmp_path):
    """Phase history section appears when there's >1 phase."""
    state = _make_state("rebasing", tmp_path)
    rendered = render_train_state_plain_english(state)
    assert "Phase history" in rendered
    assert "pending" in rendered
    assert "rebasing" in rendered


def test_render_omits_phase_history_for_single_phase(tmp_path):
    """Phase history section is omitted when only pending phase exists."""
    state = _make_state("pending", tmp_path)
    rendered = render_train_state_plain_english(state)
    assert "Phase history" not in rendered


# ─── list_train_runs ────────────────────────────────────────────────────


def test_list_returns_empty_for_missing_dir(tmp_path):
    """No train_runs dir → empty list."""
    assert list_train_runs(tmp_path / "nope") == []


def test_list_returns_empty_for_empty_dir(tmp_path):
    """Existing but empty dir → empty list."""
    tmp_path.mkdir(exist_ok=True)
    assert list_train_runs(tmp_path) == []


def test_list_returns_in_flight_trains(tmp_path):
    """In-flight train (state.json present) shows up with in_flight=True."""
    init_train_state(tmp_path, "train-001", [], {"project": "x"})
    runs = list_train_runs(tmp_path)
    assert len(runs) == 1
    assert runs[0]["train_id"] == "train-001"
    assert runs[0]["in_flight"] is True
    assert runs[0]["phase"] == "pending"


def test_list_returns_historical_yaml_records(tmp_path):
    """Terminal train (.yaml only, no state.json) shows up with in_flight=False."""
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "train-historical.yaml").write_text(
        'train_id: "train-historical"\n'
        'started_at: "2026-01-01T00:00:00Z"\n'
        'outcome: "success"\n'
    )
    runs = list_train_runs(tmp_path)
    assert len(runs) == 1
    assert runs[0]["train_id"] == "train-historical"
    assert runs[0]["in_flight"] is False
    assert runs[0]["phase"] == "success"


def test_list_orders_most_recent_first(tmp_path):
    """Multiple trains: most recent started_at first."""
    init_train_state(tmp_path, "train-old", [], {"project": "x"})
    # Manually backdate the state file's started_at
    from _wpxlib import read_train_state, write_train_state
    old_state = read_train_state(train_state_path(tmp_path, "train-old"))
    old_state["started_at"] = "2025-01-01T00:00:00Z"
    write_train_state(train_state_path(tmp_path, "train-old"), old_state)

    init_train_state(tmp_path, "train-new", [], {"project": "x"})
    new_state = read_train_state(train_state_path(tmp_path, "train-new"))
    new_state["started_at"] = "2026-12-31T23:59:59Z"
    write_train_state(train_state_path(tmp_path, "train-new"), new_state)

    runs = list_train_runs(tmp_path)
    assert len(runs) == 2
    assert runs[0]["train_id"] == "train-new"
    assert runs[1]["train_id"] == "train-old"


def test_list_prefers_in_flight_state_over_yaml(tmp_path):
    """If a train has both state.json + yaml, the in-flight state wins."""
    init_train_state(tmp_path, "train-dup", [], {"project": "x"})
    (tmp_path / "train-dup.yaml").write_text(
        'train_id: "train-dup"\n'
        'started_at: "2026-01-01T00:00:00Z"\n'
        'outcome: "success"\n'
    )
    runs = list_train_runs(tmp_path)
    # Only one entry (in-flight wins; yaml shadowed)
    train_dups = [r for r in runs if r["train_id"] == "train-dup"]
    assert len(train_dups) == 1
    assert train_dups[0]["in_flight"] is True
    assert train_dups[0]["phase"] == "pending"


def test_list_includes_pause_reason_for_paused_trains(tmp_path):
    """Paused trains surface pause_reason in the listing."""
    init_train_state(tmp_path, "train-paused", [], {"project": "x"})
    update_train_phase(
        train_state_path(tmp_path, "train-paused"),
        "paused",
        pause_reason="ci-flaked",
        recovery_hint="re-run CI",
    )
    runs = list_train_runs(tmp_path)
    assert len(runs) == 1
    assert runs[0]["phase"] == "paused"
    assert runs[0]["pause_reason"] == "ci-flaked"


# ─── JSON round-trip via inspect ─────────────────────────────────────────


def test_state_can_be_json_serialised_for_inspect_json_output(tmp_path):
    """The state dict serialises cleanly to JSON (for --json mode)."""
    bundle = [{"wp": "WP-001", "branch": "feat/wp-001", "pre_train_sha": "a"}]
    state = _make_state("ci_running", tmp_path, bundle=bundle)
    # Should not raise
    serialised = json.dumps(state, indent=2)
    parsed = json.loads(serialised)
    assert parsed["train_id"] == "train-test"
    assert parsed["phase"] == "ci_running"


# ─── HD-011 — phase_descriptions ↔ PHASES consistency ─────────────────


def test_phase_descriptions_covers_every_non_terminal_phase(tmp_path):
    """HD-011 RED — render_train_state_plain_english must produce a
    description line (the ``  → ...`` row) for every phase in PHASES.

    Catches the verifying_gates case where HD-007 added the phase to
    PHASES but forgot to extend the phase_descriptions dict in
    render_train_state_plain_english — founders running `wpx-train
    inspect` saw the phase name with no explanation.
    """
    from _wpxlib import PHASES
    for phase in PHASES:
        state = _make_state(phase, tmp_path)
        rendered = render_train_state_plain_english(state)
        assert " → " in rendered, (
            f"HD-011: phase {phase!r} has no description in "
            f"render_train_state_plain_english.phase_descriptions. "
            f"Founder running `wpx-train inspect` would see the phase "
            f"name with no explanation.\nRendered:\n{rendered}"
        )


def test_phase_descriptions_has_no_dead_keys_outside_phases():
    """HD-011 RED — phase_descriptions must not contain keys that are
    not in PHASES.

    Catches the dead ``code_review`` key left over from a rejected HD-007
    design alternative (Option A — pause-then-resume; superseded by
    Option B — verifying_gates + mark-gates-complete). Dead keys mislead
    future contributors into thinking the phase exists.
    """
    import inspect as inspect_mod
    from _wpxlib import PHASES, render_train_state_plain_english
    src = inspect_mod.getsource(render_train_state_plain_english)
    # The dead key from the rejected pause-then-resume design.
    assert "code_review" not in src, (
        "HD-011: render_train_state_plain_english still references the "
        "dead `code_review` phase from HD-007's rejected design. The "
        "chosen design uses `verifying_gates` + the mark-gates-complete "
        "subcommand instead."
    )
    # Defensive: any non-PHASES key would mislead the reader.
    known_phases = set(PHASES)
    # Extract any quoted phase keys from the dict literal in src.
    # We look for `        "key": ` to avoid false positives in
    # description text (which uses different leading whitespace).
    import re
    keys_in_dict = set(re.findall(r'^        "([a-z_]+)":\s', src, re.MULTILINE))
    unknown = keys_in_dict - known_phases
    assert not unknown, (
        f"HD-011: phase_descriptions contains keys not in PHASES: "
        f"{sorted(unknown)}. Either add them to PHASES or remove them "
        f"from phase_descriptions."
    )
