"""Integration tests for wpx-step12.

Locks down the v0.10.2 regressions: (a) multi-line JSON parse from
sub-tool stdout, (b) ok:false propagation from sub-tools as fail-fast,
(c) --repo-root propagation to sub-tool invocations.

These tests use real subprocess calls to sibling wpx-* tools — the
whole point of wpx-step12 is cross-tool dispatch, so mocking would
defeat the purpose.
"""

from __future__ import annotations

import json


def _common(tmp_project):
    return [
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
    ]


def _seed_pipeline_result(tmp_path, outcome="success"):
    p = tmp_path / "pipeline-result.json"
    p.write_text(json.dumps({"result": {
        "outcome": outcome,
        "merge_sha": "deadbeef1234",
        "deploy_url": "https://staging.example.com",
        "health_status": "healthy",
        "smoke_verdict": "PASS",
    }}))
    return p


def test_step12_wrap_happy_path(tmp_project, seed_index, seed_wp, run_tool, tmp_path):
    """End-to-end: all three sub-calls succeed; final state is correct."""
    seed_index("INDEX-minimal.md")
    seed_wp("WP-001-template.md", wp_id="WP-001", slug="happy")
    pipeline = _seed_pipeline_result(tmp_path)

    # WP-001 in INDEX-minimal is `done`, need to flip back to in_progress first
    flip = run_tool(
        "wpx-index", "set-status",
        "--wp", "WP-001", "--to", "in_progress",
        *_common(tmp_project),
    )
    assert flip.ok

    result = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-test",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    assert result.ok, f"wrap failed: {result.error}"

    # All three steps recorded in the summary
    steps = result.data["steps"]
    assert "append_evidence" in steps
    assert "flip_status" in steps
    assert "worktree_remove" in steps
    assert "skipped" in steps["worktree_remove"]  # no --worktree-path passed

    # Side effects on disk:
    wp_text = (tmp_project.wp_dir / "WP-001-happy.md").read_text()
    assert "## Acceptance Evidence" in wp_text
    index_text = tmp_project.index_md.read_text()
    assert "| WP-001 | First | Create | done |" in index_text


def test_step12_multi_line_json_parse(tmp_project, seed_index, seed_wp, run_tool, tmp_path):
    """v0.10.2 regression: wpx-step12._call_tool must parse the whole
    multi-line JSON, not just the last line (which would be `}`).

    This test exercises the same code path that crashed pre-v0.10.2. If
    the parse logic regresses, this fails fast.
    """
    seed_index("INDEX-minimal.md")
    seed_wp("WP-001-template.md", wp_id="WP-001", slug="parse")
    pipeline = _seed_pipeline_result(tmp_path)

    run_tool(
        "wpx-index", "set-status",
        "--wp", "WP-001", "--to", "in_progress",
        *_common(tmp_project),
    )

    result = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-parse",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    assert result.ok
    # Specifically: append_evidence sub-call must have been parsed
    # correctly — its data field should be a non-empty dict.
    assert result.data["steps"]["append_evidence"], "sub-tool JSON parse failed"
    assert "path" in result.data["steps"]["append_evidence"]


def test_step12_propagates_ok_false_from_subtool(
    tmp_project, seed_index, run_tool, tmp_path,
):
    """v0.10.2 regression: if a sub-tool returns ok:false (structured
    failure), wpx-step12 must fail-fast — NOT silently continue past the
    failed step.

    Scenario: WP file doesn't exist on disk → wpx-wp append-evidence
    returns ok:false → wpx-step12 must propagate the error and NOT flip
    INDEX.
    """
    seed_index("INDEX-minimal.md")
    pipeline = _seed_pipeline_result(tmp_path)

    # No seed_wp call — WP-999 file doesn't exist
    result = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-999",
        "--branch", "feat/wp-999",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    # Must fail-fast (NOT proceed to flip INDEX)
    assert not result.ok
    assert "wpx-wp" in result.error or "No WP file" in result.error
    # INDEX must be untouched (no WP-999 added)
    assert "WP-999" not in tmp_project.index_md.read_text()


def test_step12_repo_root_propagation(
    tmp_project, seed_index, seed_wp, run_tool, tmp_path,
):
    """v0.10.2 regression: wpx-step12 must pass --repo-root through to
    every sub-tool. If --repo-root is missing on a sub-call, the sub-tool
    resolves paths against its own cwd (not the project root) and fails
    to find the WP file.

    Test: run wpx-step12 from a cwd that's NOT the project root. If the
    --repo-root propagation is broken, wpx-wp can't find WP-001 even
    though it's there.
    """
    seed_index("INDEX-minimal.md")
    seed_wp("WP-001-template.md", wp_id="WP-001", slug="repo-root")
    pipeline = _seed_pipeline_result(tmp_path)

    run_tool(
        "wpx-index", "set-status",
        "--wp", "WP-001", "--to", "in_progress",
        *_common(tmp_project),
    )

    # The --repo-root is explicit (tmp_project.repo_root). If sub-calls
    # don't get it propagated, they'd resolve paths against the scripts
    # dir's cwd and fail. This is the test from v0.10.2's commit message.
    result = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-repo-root",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    assert result.ok, (
        f"wpx-step12 failed despite --repo-root: {result.error}. "
        f"This indicates --repo-root is not being propagated to "
        f"sub-tools."
    )


# ─── #267 — gate-handoff path: WP prior status is step-7-complete ──────────


def test_step12_wrap_from_gate_handoff_accepts_step_7_complete(
    tmp_project, seed_index, seed_wp, run_tool, tmp_path,
):
    """#267 — the --enable-gate-handoff train path leaves WPs at
    `step-7-complete` (not `in_progress`). With --from-gate-handoff the wrap's
    12.2 flip must expect step-7-complete and succeed; without the flag it
    rejects (the bug the operator hit, doing the wrap by hand per WP)."""
    seed_index("INDEX-minimal.md")
    seed_wp("WP-001-template.md", wp_id="WP-001", slug="gatehandoff")
    pipeline = _seed_pipeline_result(tmp_path)

    # Emulate the gate-handoff state: WP at step-7-complete.
    flip = run_tool(
        "wpx-index", "set-status",
        "--wp", "WP-001", "--to", "step-7-complete",
        *_common(tmp_project),
    )
    assert flip.ok

    # WITHOUT --from-gate-handoff → the legacy expected (in_progress) is wrong
    # for this state, so the wrap fails (the #267 symptom).
    bad = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-gatehandoff",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    assert not bad.ok, "wrap should reject step-7-complete without --from-gate-handoff"

    # WITH --from-gate-handoff → the flip expects step-7-complete and succeeds.
    good = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-gatehandoff",
        "--pipeline-result", f"@{pipeline}",
        "--from-gate-handoff",
        *_common(tmp_project),
    )
    assert good.ok, f"gate-handoff wrap failed: {good.error}"
    index_text = tmp_project.index_md.read_text()
    assert "| WP-001 | First | Create | done |" in index_text


def test_step12_wrap_default_still_expects_in_progress(
    tmp_project, seed_index, seed_wp, run_tool, tmp_path,
):
    """Regression — without the flag, the legacy per-WP path (prior status
    in_progress) still works unchanged."""
    seed_index("INDEX-minimal.md")
    seed_wp("WP-001-template.md", wp_id="WP-001", slug="legacy")
    pipeline = _seed_pipeline_result(tmp_path)

    flip = run_tool(
        "wpx-index", "set-status",
        "--wp", "WP-001", "--to", "in_progress",
        *_common(tmp_project),
    )
    assert flip.ok
    result = run_tool(
        "wpx-step12", "wrap",
        "--wp", "WP-001",
        "--branch", "feat/wp-001-legacy",
        "--pipeline-result", f"@{pipeline}",
        *_common(tmp_project),
    )
    assert result.ok, f"legacy wrap failed: {result.error}"
    assert "| WP-001 | First | Create | done |" in tmp_project.index_md.read_text()
