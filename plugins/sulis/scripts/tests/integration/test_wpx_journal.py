"""Integration tests for wpx-journal.

Focuses on the v0.10.0 plan-generation surface (seed-plan / mark-plan-item /
add-plan-item / read --field plan) since those are the newest moving parts.
Basic lifecycle ops (init, start-step, complete-step) covered briefly.
"""

from __future__ import annotations

import json


def _common(tmp_project):
    return [
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
    ]


def test_journal_init_creates_file_with_all_sections(tmp_project, run_tool):
    r = run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    assert r.ok
    text = tmp_project.journal("WP-001").read_text()
    assert "## Pre-flight checks" in text
    assert "## Plan" in text
    assert "## Step trace" in text
    assert "## Self-heal attempts" in text
    assert "## Post-deploy verification" in text
    assert "## Notes" in text


def test_journal_step_trace_round_trip(tmp_project, run_tool):
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    r1 = run_tool("wpx-journal", "start-step", "--wp", "WP-001", "--step", "2", *_common(tmp_project))
    assert r1.ok
    r2 = run_tool(
        "wpx-journal", "complete-step",
        "--wp", "WP-001", "--step", "2", "--outcome", "3 tests written",
        *_common(tmp_project),
    )
    assert r2.ok
    # Read back via wpx-journal read
    r3 = run_tool(
        "wpx-journal", "read",
        "--wp", "WP-001", "--field", "step-2-status",
        *_common(tmp_project),
    )
    assert r3.ok
    assert r3.data["value"] == "completed"


# ─── Loud-failure on a missing prerequisite step row (#63) ────────────────
#
# A skipped `start-step` must be caught the moment the next step-dependent
# call runs, not pages later. `complete-step` already errored for this case;
# the fix makes every step-trace-dependent command (complete-step,
# record-attempt) consistent via a single shared prerequisite check.


def test_complete_step_fails_loudly_on_missing_start_step(tmp_project, run_tool):
    """complete-step --step N must exit non-zero with a clear message naming
    the missing prerequisite when start-step --step N was never recorded."""
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    # No start-step for step 3 — go straight to complete-step.
    r = run_tool(
        "wpx-journal", "complete-step",
        "--wp", "WP-001", "--step", "3", "--outcome", "done",
        *_common(tmp_project),
    )
    assert not r.ok, "complete-step on a missing step row must fail"
    assert r.returncode != 0, "exit code must be non-zero"
    assert "3" in r.error and "start-step" in r.error, (
        f"error must name the missing prerequisite step + remedy; got: {r.error}"
    )


def test_record_attempt_fails_loudly_on_missing_start_step(tmp_project, run_tool):
    """record-attempt --step N presumes a prior start-step row for step N.
    When that row is missing it must fail loudly (consistent with
    complete-step) rather than silently appending an orphan attempt row."""
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    # No start-step for step 4 — record-attempt should refuse.
    r = run_tool(
        "wpx-journal", "record-attempt",
        "--wp", "WP-001", "--step", "4", "--attempt", "1",
        "--failure", "import error", "--root-cause", "wrong path",
        "--change", "fixed import", "--outcome", "still-failing",
        *_common(tmp_project),
    )
    assert not r.ok, "record-attempt on a missing step row must fail"
    assert r.returncode != 0, "exit code must be non-zero"
    assert "4" in r.error and "start-step" in r.error, (
        f"error must name the missing prerequisite step + remedy; got: {r.error}"
    )


def test_record_attempt_succeeds_after_start_step(tmp_project, run_tool):
    """Happy path: with the prerequisite start-step row present,
    record-attempt succeeds."""
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    run_tool(
        "wpx-journal", "start-step", "--wp", "WP-001", "--step", "4",
        *_common(tmp_project),
    )
    r = run_tool(
        "wpx-journal", "record-attempt",
        "--wp", "WP-001", "--step", "4", "--attempt", "1",
        "--failure", "import error", "--root-cause", "wrong path",
        "--change", "fixed import", "--outcome", "passed",
        *_common(tmp_project),
    )
    assert r.ok, f"record-attempt after start-step should succeed; got {r.error}"


def test_step_trace_accepts_half_step_six_point_five(tmp_project, run_tool):
    """v0.20.1+: --step 6.5 is accepted (used by the executor's Step 6.5
    code-review gate). Pre-v0.20.1 the script rejected 6.5 because --step
    was type=int — which may have driven executors to substitute inline
    judgement rather than invoke /sulis:code-review at all.

    The half-step renders as "6.5" in the trace (not "6.5.0" or "6").
    """
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    r1 = run_tool(
        "wpx-journal", "start-step",
        "--wp", "WP-001", "--step", "6.5",
        *_common(tmp_project),
    )
    assert r1.ok, f"start-step --step 6.5 should succeed; got {r1.stderr}"
    r2 = run_tool(
        "wpx-journal", "complete-step",
        "--wp", "WP-001", "--step", "6.5",
        "--outcome", "addressed: 0 findings (bundle at PR-feat-wp-001-...)",
        *_common(tmp_project),
    )
    assert r2.ok
    # Round-trip through read --field
    r3 = run_tool(
        "wpx-journal", "read",
        "--wp", "WP-001", "--field", "step-6.5-status",
        *_common(tmp_project),
    )
    assert r3.ok
    assert r3.data["value"] == "completed", (
        f"Step 6.5 should be completed; got {r3.data}"
    )


def test_step_trace_integer_step_renders_without_trailing_zero(tmp_project, run_tool):
    """v0.20.1+ flips --step to type=float; integer steps must still
    render as "6", not "6.0", or existing journals would diverge."""
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    run_tool(
        "wpx-journal", "start-step",
        "--wp", "WP-001", "--step", "6",
        *_common(tmp_project),
    )
    r = run_tool(
        "wpx-journal", "complete-step",
        "--wp", "WP-001", "--step", "6",
        "--outcome", "lint clean",
        *_common(tmp_project),
    )
    assert r.ok
    # Look at the journal file: the row's first column must be "6", not "6.0"
    text = tmp_project.journal("WP-001").read_text()
    # The trace table row: | 6 | <started> | <completed> | lint clean |
    assert "| 6 |" in text, (
        f"Integer step must render as '6' (no trailing .0); "
        f"journal text was:\n{text}"
    )
    assert "| 6.0 |" not in text, (
        f"Integer step accidentally rendered as '6.0'; "
        f"journal text was:\n{text}"
    )


def test_seed_plan_populates_plan_section(tmp_project, run_tool, tmp_path):
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([
        {"description": "Write test_foo", "step": "2 (RED)"},
        {"description": "Implement foo()", "step": "3 (GREEN)"},
    ]))
    r = run_tool(
        "wpx-journal", "seed-plan", "--wp", "WP-001",
        "--approach", "Create primitive; new foo() with 1 test",
        "--plan-json", f"@{plan}",
        *_common(tmp_project),
    )
    assert r.ok
    assert r.data["item_count"] == 2
    text = tmp_project.journal("WP-001").read_text()
    assert "Create primitive; new foo() with 1 test" in text
    assert "Write test_foo" in text


def test_mark_plan_item_atomic_check(tmp_project, run_tool, tmp_path):
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([{"description": "x", "step": "2"}]))
    run_tool(
        "wpx-journal", "seed-plan", "--wp", "WP-001",
        "--approach", "x", "--plan-json", f"@{plan}",
        *_common(tmp_project),
    )
    # Atomic flip with correct --expected
    r1 = run_tool(
        "wpx-journal", "mark-plan-item",
        "--wp", "WP-001", "--item", "1",
        "--status", "in-progress", "--expected", "pending",
        *_common(tmp_project),
    )
    assert r1.ok
    # Atomic flip with WRONG --expected should fail
    r2 = run_tool(
        "wpx-journal", "mark-plan-item",
        "--wp", "WP-001", "--item", "1",
        "--status", "done", "--expected", "pending",
        *_common(tmp_project),
    )
    assert not r2.ok
    assert "expected 'pending'" in r2.error


def test_read_field_plan_returns_structured_json(tmp_project, run_tool, tmp_path):
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([
        {"description": "Item 1", "step": "2"},
        {"description": "Item 2", "step": "3", "notes": "conditional"},
    ]))
    run_tool(
        "wpx-journal", "seed-plan", "--wp", "WP-001",
        "--approach", "test", "--plan-json", f"@{plan}",
        *_common(tmp_project),
    )
    r = run_tool(
        "wpx-journal", "read",
        "--wp", "WP-001", "--field", "plan",
        *_common(tmp_project),
    )
    assert r.ok
    items = r.data["value"]["items"]
    assert len(items) == 2
    assert items[0]["description"] == "Item 1"
    assert items[1]["notes"] == "conditional"
