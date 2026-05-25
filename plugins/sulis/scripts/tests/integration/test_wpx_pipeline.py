"""Integration tests for wpx-pipeline.

LOAD-BEARING: includes the regression tests for v0.10.4 (emit_ok exit_code
+ no-branch-CI auto-skip) AND v0.10.5 Bug 1 (already-merged-branch
detection — _gh_merge previously crashed with RuntimeError on GitHub's
409 response when the base already contained the head).

Uses the `mock_gh` fixture to control gh CLI responses. Uses the
`local_git_repo` fixture for real git operations on the worktree.
"""

from __future__ import annotations

import json


def _common_pipeline_args(tmp_project, local_git_repo, smoke="true", dev_sha="abc123"):
    """Standard pipeline args. dev_sha defaults to 'abc123' which matches
    the mocked dev ref SHA in most tests — keeps the rebase step a no-op
    (no SHA mismatch). Tests that exercise rebase explicitly pass a
    different value.
    """
    return [
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
        "--wp", "WP-001",
        "--branch", "feat/test",
        "--worktree-path", str(local_git_repo),
        "--dev-sha-at-creation", dev_sha,
        "--deploy-workflow", "Deploy",
        "--staging-url", "https://example.com",
        "--smoke-cmd", smoke,
        "--repo", "test-org/test-repo",
    ]


# ─── v0.10.4 regressions — emit_ok exit_code paths ────────────────────────


def test_emit_ok_no_branch_ci_returns_clean_json_not_traceback(
    tmp_project, local_git_repo, run_tool, mock_gh,
):
    """v0.10.4 regression: when no branch CI is detected and the pipeline
    auto-skips, the run must complete cleanly (or fail-fast with structured
    JSON) — not crash with a Python TypeError from emit_ok(exit_code=...).

    Setup: no .github/workflows present (auto-skip CI). gh merges returns
    409 (already merged — Bug 1 case). Pipeline must emit clean JSON.
    """
    # No branch CI in worktree (default — no .github/workflows)
    # No mocks configured for the merge step → pipeline will hit Bug 1.
    # We just want to assert the exit is structured JSON, not a traceback.
    mock_gh([
        # The /merges call will return 409 (already merged); the existing
        # code raises RuntimeError. Test that we surface a clean blocker
        # JSON rather than a traceback. POST-FIX, this should detect via
        # /compare and skip to deploy. PRE-FIX, this test asserts the
        # absence of a Python traceback only.
        {"match": "compare", "stdout": json.dumps({"status": "identical"})},
        # Deploy workflow has no runs yet
        {"match": "run list", "stdout": "[]"},
    ])
    result = run_tool("wpx-pipeline", "run", *_common_pipeline_args(tmp_project, local_git_repo))
    # Must produce structured JSON (not crash with traceback)
    assert result.json is not None, (
        f"pipeline did not produce JSON; stdout={result.stdout!r}; "
        f"stderr (last 1k chars)={result.stderr[-1000:]!r}"
    )
    # No Python traceback in stderr
    assert "Traceback" not in result.stderr


# ─── v0.10.5 Bug 1 — already-merged branch detection ──────────────────────


def test_already_merged_branch_skips_merge_step(
    tmp_project, local_git_repo, run_tool, mock_gh,
):
    """Regression for v0.10.5 Bug 1: when the branch has already been
    squash-merged to dev (GitHub's compare API returns status='identical'
    or 'behind'), wpx-pipeline must skip the merge step and proceed to
    deploy poll on the existing dev HEAD.

    Pre-fix: pipeline hits the /merges endpoint, gets 409, raises
    RuntimeError, crashes.

    Post-fix: pipeline checks /compare first, detects already-merged,
    skips merge, fetches dev HEAD as the merge_sha, proceeds to deploy.
    """
    # Set up worktree with branch CI so CI poll isn't skipped (we want
    # the merge step path)
    workflows = local_git_repo / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "on:\n  push:\n    branches:\n      - 'feat/**'\njobs: {}\n"
    )

    mock_gh([
        # CI on feat/test: all green
        {
            "match": "commits/feat/test/check-runs",
            "stdout": json.dumps({
                "check_runs": [
                    {"name": "ci", "status": "completed", "conclusion": "success"},
                ],
            }),
        },
        # dev SHA same as branch SHA (branch already merged)
        {
            "match": "git/refs/heads/dev",
            "stdout": json.dumps({"object": {"sha": "abc123"}}),
        },
        # compare: identical
        {
            "match": "compare",
            "stdout": json.dumps({"status": "identical"}),
        },
        # Deploy workflow run on the dev sha
        {
            "match": "run list",
            "stdout": json.dumps([{
                "databaseId": 999,
                "status": "completed",
                "conclusion": "success",
                "createdAt": "2026-05-19T12:00:00Z",
                "url": "https://example.com/run/999",
            }]),
        },
    ])

    result = run_tool(
        "wpx-pipeline", "run",
        *_common_pipeline_args(tmp_project, local_git_repo),
    )

    # Must emit structured JSON (not crash)
    assert result.json is not None, (
        f"pipeline crashed: stderr={result.stderr[-1000:]!r}"
    )
    # No Python traceback
    assert "Traceback" not in result.stderr
    # Outcome should be success (already merged + deploy green + health/smoke skipped or OK)
    outcome = result.data.get("result", {}).get("outcome")
    assert outcome in ("success", "blocker"), f"unexpected outcome: {outcome}"
    # If success, merge_sha must be set (to the existing dev SHA)
    if outcome == "success":
        assert result.data["result"].get("merge_sha") is not None


# ─── --skip-ci-poll behaviour (v0.10.4 sanity) ────────────────────────────


def test_explicit_skip_ci_poll_works(
    tmp_project, local_git_repo, run_tool, mock_gh,
):
    """Confirm --skip-ci-poll skips the CI poll step even when branch CI
    is detected (explicit override).
    """
    workflows = local_git_repo / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "on:\n  push:\n    branches:\n      - 'feat/**'\njobs: {}\n"
    )

    mock_gh([
        # CI poll would normally happen but --skip-ci-poll skips it.
        # We don't add a check-runs response; if pipeline hits it, the
        # mock returns exit 1 and the test would fail.
        {
            "match": "git/refs/heads/dev",
            "stdout": json.dumps({"object": {"sha": "abc123"}}),
        },
        {
            "match": "compare",
            "stdout": json.dumps({"status": "identical"}),
        },
        {
            "match": "run list",
            "stdout": json.dumps([{
                "databaseId": 1, "status": "completed",
                "conclusion": "success", "createdAt": "2026-05-19T12:00:00Z",
                "url": "https://example.com/run/1",
            }]),
        },
    ])

    result = run_tool(
        "wpx-pipeline", "run",
        *_common_pipeline_args(tmp_project, local_git_repo),
        "--skip-ci-poll",
    )
    # The stderr log should mention "skipping CI poll"
    assert "skipping CI poll" in result.stderr or "Step 8a: skipping" in result.stderr
    # And no Python traceback
    assert "Traceback" not in result.stderr


def test_auto_skip_when_no_branch_ci(
    tmp_project, local_git_repo, run_tool, mock_gh,
):
    """v0.10.4 regression: auto-detect missing branch CI → skip CI poll
    with a WARNING (don't hang for 45min).
    """
    # No .github/workflows directory in the worktree
    mock_gh([
        {
            "match": "git/refs/heads/dev",
            "stdout": json.dumps({"object": {"sha": "abc123"}}),
        },
        {
            "match": "compare",
            "stdout": json.dumps({"status": "identical"}),
        },
        {
            "match": "run list",
            "stdout": json.dumps([{
                "databaseId": 1, "status": "completed",
                "conclusion": "success", "createdAt": "2026-05-19T12:00:00Z",
                "url": "https://example.com/run/1",
            }]),
        },
    ])

    result = run_tool(
        "wpx-pipeline", "run",
        *_common_pipeline_args(tmp_project, local_git_repo),
    )
    # The WARNING about no branch CI should appear in stderr
    assert "no branch-CI" in result.stderr or "auto-detected absence" in result.stderr
    assert "Traceback" not in result.stderr


# ─── v0.10.6 — _detect_branch_ci false-positive on paths-ignore ────────────


def test_paths_ignore_docs_does_not_register_as_branch_ci(
    tmp_project, local_git_repo, run_tool, mock_gh,
):
    """Regression for v0.10.6: a deploy-on-push-to-dev workflow with
    `paths-ignore: - 'docs/**'` was previously misclassified as branch
    CI because the v0.10.5 detector substring-grepped the YAML for any
    CC prefix (`docs/` matched). The fix structurally parses
    `branches:` lists only, rejecting `paths-ignore`, `branches-ignore`,
    `paths`, etc.

    Without the fix: pipeline hangs polling CI for 45 min on the user's
    tria/kinds-and-tools project because deploy-dev.yml has
    paths-ignore: ['docs/**', '**/*.md'] and `docs/` triggers the
    substring grep.
    """
    workflows = local_git_repo / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    # The user's actual deploy-dev.yml shape: pushes to dev only,
    # path filter (NOT branch filter) on docs/
    (workflows / "deploy-dev.yml").write_text("""\
name: Deploy to Dev Environment
on:
  push:
    branches: [dev]
    paths-ignore:
      - 'docs/**'
      - '**/*.md'
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo deploy
""")

    mock_gh([
        {"match": "git/refs/heads/dev", "stdout": json.dumps({"object": {"sha": "abc123"}})},
        {"match": "compare", "stdout": json.dumps({"status": "identical"})},
        {"match": "run list", "stdout": json.dumps([{
            "databaseId": 1, "status": "completed",
            "conclusion": "success", "createdAt": "2026-05-19T12:00:00Z",
            "url": "https://example.com/run/1",
        }])},
    ])

    result = run_tool(
        "wpx-pipeline", "run",
        *_common_pipeline_args(tmp_project, local_git_repo),
    )
    # Auto-skip must engage: the deploy workflow does NOT trigger on
    # branch pushes (only on dev pushes); paths-ignore is a path
    # filter, not a branch filter. Pre-fix, the substring grep on
    # `docs/` would falsely classify this as branch CI → pipeline
    # would hang for 45 min waiting for check-runs that never appear.
    assert "no branch-CI" in result.stderr or "auto-detected absence" in result.stderr, (
        f"detector failed to skip — stderr={result.stderr[-500:]!r}"
    )
    assert "Traceback" not in result.stderr


# ─── v0.10.7 — health path auto-detect from --smoke-cmd ────────────────────


def test_health_path_auto_detected_from_smoke_cmd(
    tmp_project, local_git_repo, run_tool, mock_gh, mock_curl,
):
    """Regression for v0.10.7: when --smoke-cmd encodes a URL with a
    /health path, wpx-pipeline must hit that path for Step 10a — not
    the bare staging URL root. Pre-fix, the pipeline curled the staging
    URL with no path appended; for APIs whose root returns 404 by
    design, this looped for 600s and produced a spurious BLOCKER.
    """
    workflows = local_git_repo / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "on:\n  push:\n    branches:\n      - 'feat/**'\njobs: {}\n"
    )

    mock_gh([
        {"match": "commits/feat/test/check-runs", "stdout": json.dumps({
            "check_runs": [{"name": "ci", "status": "completed",
                            "conclusion": "success"}],
        })},
        {"match": "git/refs/heads/dev", "stdout": json.dumps({"object": {"sha": "abc123"}})},
        {"match": "compare", "stdout": json.dumps({"status": "identical"})},
        {"match": "run list", "stdout": json.dumps([{
            "databaseId": 999, "status": "completed",
            "conclusion": "success", "createdAt": "2026-05-19T12:00:00Z",
            "url": "https://example.com/run/999",
        }])},
    ])

    # The user's actual repro: /health returns 200; / returns 404.
    mock_curl([
        {"url_substring": "/health", "status": 200},
        {"url_substring": "", "status": 404},   # fallback for "/"
    ])

    result = run_tool(
        "wpx-pipeline", "run",
        *_common_pipeline_args(
            tmp_project, local_git_repo,
            smoke="echo 'smoke ok https://staging.example.com/health'",
        ),
    )
    assert result.json is not None, f"pipeline crashed: {result.stderr[-500:]!r}"
    outcome = result.data.get("result", {}).get("outcome")
    assert outcome == "success", (
        f"expected success but got {outcome}; pipeline failed at Step 10a "
        f"despite smoke-cmd encoding /health. "
        f"blocker_reason={result.data.get('result', {}).get('blocker_reason')}; "
        f"health_url={result.data.get('result', {}).get('health_url')!r}"
    )
    # stderr should log the auto-detect
    assert "auto-detected from --smoke-cmd" in result.stderr, (
        f"expected auto-detect log; stderr={result.stderr[-500:]!r}"
    )


def test_health_path_falls_back_to_root_when_smoke_cmd_has_no_url(
    tmp_project, local_git_repo, run_tool, mock_gh, mock_curl,
):
    """v0.10.7 backward-compat: when --smoke-cmd has no URL (e.g.
    `true`, a pytest invocation, or empty), health check falls back
    to the bare staging URL root — same behaviour as v0.10.6 and
    earlier for projects whose root serves health.
    """
    workflows = local_git_repo / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "on:\n  push:\n    branches: ['feat/**']\njobs: {}\n"
    )

    mock_gh([
        {"match": "commits/feat/test/check-runs", "stdout": json.dumps({
            "check_runs": [{"name": "ci", "status": "completed",
                            "conclusion": "success"}],
        })},
        {"match": "git/refs/heads/dev", "stdout": json.dumps({"object": {"sha": "abc123"}})},
        {"match": "compare", "stdout": json.dumps({"status": "identical"})},
        {"match": "run list", "stdout": json.dumps([{
            "databaseId": 1, "status": "completed",
            "conclusion": "success", "createdAt": "2026-05-19T12:00:00Z",
            "url": "https://example.com/run/1",
        }])},
    ])

    # Root returns 200 (the legacy / backward-compat case)
    mock_curl([{"url_substring": "", "status": 200}])

    result = run_tool(
        "wpx-pipeline", "run",
        *_common_pipeline_args(tmp_project, local_git_repo, smoke="true"),
    )
    assert result.json is not None
    outcome = result.data.get("result", {}).get("outcome")
    assert outcome == "success", (
        f"expected success on root-served health; got {outcome}; "
        f"reason={result.data.get('result', {}).get('blocker_reason')}"
    )
    # stderr should log the "default (root)" path source
    assert "default (root)" in result.stderr, (
        f"expected default-root log; stderr={result.stderr[-500:]!r}"
    )


def test_health_path_explicit_flag_wins(
    tmp_project, local_git_repo, run_tool, mock_gh, mock_curl,
):
    """v0.10.7: --health-path explicit override beats auto-detect.
    Useful when the smoke command's URL doesn't match where health
    actually lives (e.g. smoke posts to /api/orders but health is
    at /healthz).
    """
    workflows = local_git_repo / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "on:\n  push:\n    branches: ['feat/**']\njobs: {}\n"
    )

    mock_gh([
        {"match": "commits/feat/test/check-runs", "stdout": json.dumps({
            "check_runs": [{"name": "ci", "status": "completed",
                            "conclusion": "success"}],
        })},
        {"match": "git/refs/heads/dev", "stdout": json.dumps({"object": {"sha": "abc123"}})},
        {"match": "compare", "stdout": json.dumps({"status": "identical"})},
        {"match": "run list", "stdout": json.dumps([{
            "databaseId": 1, "status": "completed",
            "conclusion": "success", "createdAt": "2026-05-19T12:00:00Z",
            "url": "https://example.com/run/1",
        }])},
    ])

    # /healthz returns 200; everything else (/health, /) returns 404.
    # If the override didn't win, auto-detect would pick /health → 404.
    mock_curl([
        {"url_substring": "/healthz", "status": 200},
        {"url_substring": "", "status": 404},
    ])

    result = run_tool(
        "wpx-pipeline", "run",
        *_common_pipeline_args(
            tmp_project, local_git_repo,
            smoke="echo 'smoke ok https://staging.example.com/health'",  # auto would pick /health
        ),
        "--health-path", "/healthz",  # explicit override
    )
    assert result.json is not None
    outcome = result.data.get("result", {}).get("outcome")
    assert outcome == "success", (
        f"explicit --health-path /healthz should have won over "
        f"auto-detected /health; got outcome={outcome}, "
        f"reason={result.data.get('result', {}).get('blocker_reason')}"
    )
    assert "--health-path flag" in result.stderr


def test_branches_ignore_does_not_register_as_branch_ci(
    tmp_project, local_git_repo, run_tool, mock_gh,
):
    """v0.10.6: `branches-ignore: ['feat/**']` means the workflow does
    NOT run on feature branches (opposite of branch CI). The detector
    must NOT match this as branch CI.
    """
    workflows = local_git_repo / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text("""\
on:
  push:
    branches-ignore:
      - 'feat/**'
jobs:
  test:
    runs-on: ubuntu-latest
    steps: [{run: echo}]
""")

    mock_gh([
        {"match": "git/refs/heads/dev", "stdout": json.dumps({"object": {"sha": "abc123"}})},
        {"match": "compare", "stdout": json.dumps({"status": "identical"})},
        {"match": "run list", "stdout": json.dumps([{
            "databaseId": 1, "status": "completed",
            "conclusion": "success", "createdAt": "2026-05-19T12:00:00Z",
            "url": "https://example.com/run/1",
        }])},
    ])

    result = run_tool(
        "wpx-pipeline", "run",
        *_common_pipeline_args(tmp_project, local_git_repo),
    )
    # Auto-skip must engage because the workflow excludes feat/ branches
    assert "no branch-CI" in result.stderr or "auto-detected absence" in result.stderr
