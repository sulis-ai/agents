"""Integration tests for #142 — wpx-step12 wrap is idempotent on replay.

CH-01KT48 trigger: wpx-step12 wrap failed twice in a row — first because
flip-status `--expected in_progress` rejected a pending WP (the single-WP
run-wp path hadn't pre-flipped), then, after a manual flip, because
append-evidence rejected the now-already-present `## Acceptance Evidence`
section. The wrap had no `--force` so the second attempt left the WP in a
partial state requiring hand cleanup.

The fix:
  - `wpx-wp append-evidence` → success no-op (already_present=True) when the
    section already exists, instead of erroring.
  - `wpx-index flip-status` → success early-return (already=True) when the
    row is already at the target status, regardless of --expected.

These two changes make a second wrap call land cleanly without -force flags.
"""

from __future__ import annotations

import json


def _common(tmp_project):
    return [
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
    ]


def _seed_pipeline_result(tmp_path):
    p = tmp_path / "pipeline-result.json"
    p.write_text(json.dumps({"result": {
        "outcome": "success",
        "merge_sha": "deadbeef1234",
        "deploy_url": "https://staging.example.com",
        "health_status": "healthy",
        "smoke_verdict": "PASS",
    }}))
    return p


def test_step12_wrap_is_idempotent_on_replay(
    tmp_project, seed_index, seed_wp, run_tool, tmp_path,
):
    """A second `wpx-step12 wrap` call on a WP already wrapped once must
    succeed: append-evidence sees the existing section + no-ops; flip-status
    sees the row already at 'done' + no-ops; worktree remove is already
    tolerant. The whole call returns ok with each step reporting the
    already-done shape."""
    seed_index("INDEX-minimal.md")
    seed_wp("WP-001-template.md", wp_id="WP-001", slug="replay")
    pipeline = _seed_pipeline_result(tmp_path)

    # WP-001 starts as `done` in INDEX-minimal — flip to in_progress for the
    # first wrap call.
    flip = run_tool(
        "wpx-index", "set-status",
        "--wp", "WP-001", "--to", "in_progress",
        *_common(tmp_project),
    )
    assert flip.ok

    # First wrap — normal happy path.
    first = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-replay",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    assert first.ok, f"first wrap failed: {first.error}"

    # Second wrap — must succeed idempotently.
    second = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-replay",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    assert second.ok, f"replay wrap failed: {second.error}"

    steps = second.data["steps"]
    assert steps["append_evidence"].get("already_present") is True, (
        f"append-evidence not idempotent on replay; got {steps}"
    )
    assert steps["flip_status"].get("already") is True, (
        f"flip-status not idempotent on replay; got {steps}"
    )

    # WP file still has exactly ONE evidence section (not two appended).
    wp_text = (tmp_project.wp_dir / "WP-001-replay.md").read_text()
    assert wp_text.count("## Acceptance Evidence") == 1, (
        f"replay re-appended evidence; full text:\n{wp_text}"
    )


def test_step12_wrap_retries_after_pending_state(
    tmp_project, seed_index, seed_wp, run_tool, tmp_path,
):
    """L2 trigger: the first wrap call lands evidence but flip-status fails
    because the WP was at 'pending' (run-wp single-WP path didn't flip).
    After a manual flip to in_progress, the second wrap call must land
    cleanly — append-evidence no-ops on the existing section."""
    seed_index("INDEX-minimal.md")
    seed_wp("WP-001-template.md", wp_id="WP-001", slug="pending-retry")
    pipeline = _seed_pipeline_result(tmp_path)

    # Force WP-001 to pending — emulate the single-WP run-wp path that
    # didn't flip.
    flip_pending = run_tool(
        "wpx-index", "set-status",
        "--wp", "WP-001", "--to", "pending",
        *_common(tmp_project),
    )
    assert flip_pending.ok

    # First wrap — append-evidence succeeds, flip-status fails (still pending).
    first = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-pending-retry",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    # The whole call fails fast on the flip-status sub-call (existing
    # behaviour) — that's correct: pending → done with --expected in_progress
    # must surface as a misuse.
    assert not first.ok

    # WP file has the evidence block now (Step 12.1 ran before Step 12.2 hit
    # the misuse).
    wp_text_after_first = (tmp_project.wp_dir / "WP-001-pending-retry.md").read_text()
    assert "## Acceptance Evidence" in wp_text_after_first

    # Operator manually flips pending → in_progress.
    flip_inprog = run_tool(
        "wpx-index", "set-status",
        "--wp", "WP-001", "--to", "in_progress",
        *_common(tmp_project),
    )
    assert flip_inprog.ok

    # Second wrap — must succeed. append-evidence sees the existing section
    # and no-ops; flip-status flips in_progress → done.
    second = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-pending-retry",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    assert second.ok, f"retry wrap failed: {second.error}"
    assert second.data["steps"]["append_evidence"].get("already_present") is True
    # Exactly one evidence section.
    wp_text_final = (tmp_project.wp_dir / "WP-001-pending-retry.md").read_text()
    assert wp_text_final.count("## Acceptance Evidence") == 1
