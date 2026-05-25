"""Unit tests for wpx-arrival-check (RC-11 arrival check).

The script verifies the Repository Contract (RC-01..RC-10) against a live
repo via `gh api`, and emits the RC-11 JSON contract:
    {"ok": bool, "errors": [...], "warnings": [...]}
Exit 0 = all MUST pass; exit 2 = a MUST failed; exit 1 = tooling error.

Deploy-related MUSTs (RC-05 secrets / RC-06 / RC-08 signing) downgrade to
WARN when .sulis/repo-contract.yml declares `deploy_target: none`
(marketplace profile — see repo-contract.yml).

gh is mocked via the mock_gh fixture (fake binary on PATH, substring dispatch).
Workflow-file presence (RC-04) is a real filesystem check against --repo-root.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ─── helpers ──────────────────────────────────────────────────────────────


def _write_contract(repo_root: Path, deploy_target: str = "none") -> None:
    sulis = repo_root / ".sulis"
    sulis.mkdir(parents=True, exist_ok=True)
    (sulis / "repo-contract.yml").write_text(
        f"repo: sulis-ai/agents\nprofile: plugin-marketplace\ndeploy_target: {deploy_target}\n"
    )


def _write_workflows(repo_root: Path, names: list[str]) -> None:
    wf = repo_root / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    triggers = {
        "branch-ci": "on:\n  pull_request:\n    branches: [dev]\n  push:\n    branches: ['feat/wp-*', 'change/*']\n",
        "merge-queue-ci": "on:\n  merge_group:\n",
        "deploy-staging": "on:\n  push:\n    branches: [dev]\n",
        "health-and-smoke": "on:\n  workflow_run:\n    workflows: [deploy-staging]\n",
        "promote-dev-to-main": "on:\n  workflow_dispatch:\n",
        "release-prod": "on:\n  push:\n    tags: ['v*.*.*']\n",
    }
    default_trigger = "on: push\n"
    for n in names:
        body = triggers.get(n, default_trigger)
        (wf / f"{n}.yml").write_text(f"name: {n}\n{body}")


def _conformant_gh_responses() -> list[dict]:
    """Mock gh responses for a fully-conformant repo. Specific matches first."""
    # Ordered most-specific first — the mock matches the first response whose
    # `match` is a substring of the gh args. `rules/branches/dev` must precede
    # `branches/dev` (the latter is a substring of the former).
    return [
        {"match": "rules/branches/dev", "stdout": json.dumps([
            {"type": "merge_queue", "parameters": {"merge_method": "SQUASH"}},
        ])},
        {"match": "branches/dev/protection", "stdout": json.dumps({
            "required_status_checks": {"contexts": ["branch-ci", "merge-queue-ci"]},
            "required_linear_history": {"enabled": True},
        })},
        {"match": "branches/main/protection", "stdout": json.dumps({
            "required_linear_history": {"enabled": True},
        })},
        {"match": "branches/dev", "stdout": json.dumps({"name": "dev"})},
        {"match": "branches/main", "stdout": json.dumps({"name": "main"})},
        {"match": "/environments", "stdout": json.dumps({
            "environments": [{"name": "staging"}, {"name": "production"}],
        })},
        # repo settings / default branch — least specific, matched last
        {"match": "repos/sulis-ai/agents", "stdout": json.dumps({
            "default_branch": "dev",
            "allow_squash_merge": True,
            "allow_merge_commit": False,
            "allow_rebase_merge": False,
            "delete_branch_on_merge": True,
        })},
    ]


# ─── tests ────────────────────────────────────────────────────────────────


def test_conformant_repo_passes(tmp_path, run_tool, mock_gh):
    """A fully-conformant repo → ok:true, exit 0."""
    _write_contract(tmp_path, deploy_target="none")
    _write_workflows(tmp_path, [
        "branch-ci", "merge-queue-ci", "deploy-staging",
        "health-and-smoke", "promote-dev-to-main", "release-prod",
    ])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_conformant_gh_responses())

    result = run_tool("wpx-arrival-check", "--repo", "sulis-ai/agents",
                      "--repo-root", str(tmp_path))

    assert result.json is not None, f"non-JSON output: {result.stdout!r} / {result.stderr!r}"
    assert result.json["ok"] is True, f"errors: {result.json.get('errors')}"
    assert result.returncode == 0


def test_missing_dev_branch_fails_rc01(tmp_path, run_tool, mock_gh):
    """No dev branch → RC-01 error, exit 2."""
    _write_contract(tmp_path)
    _write_workflows(tmp_path, [
        "branch-ci", "merge-queue-ci", "deploy-staging",
        "health-and-smoke", "promote-dev-to-main", "release-prod",
    ])
    responses = _conformant_gh_responses()
    # dev branch lookup fails (404)
    responses.insert(0, {"match": "branches/dev", "exit_code": 1,
                         "stderr": "Not Found"})
    mock_gh(responses)

    result = run_tool("wpx-arrival-check", "--repo", "sulis-ai/agents",
                      "--repo-root", str(tmp_path))

    assert result.json is not None
    assert result.json["ok"] is False
    rules_failed = {e["rule"] for e in result.json["errors"]}
    assert "RC-01" in rules_failed
    assert result.returncode == 2


def test_missing_workflow_fails_rc04(tmp_path, run_tool, mock_gh):
    """A missing required workflow file → RC-04 error, exit 2."""
    _write_contract(tmp_path)
    _write_workflows(tmp_path, ["branch-ci", "merge-queue-ci"])  # 4 missing
    mock_gh(_conformant_gh_responses())

    result = run_tool("wpx-arrival-check", "--repo", "sulis-ai/agents",
                      "--repo-root", str(tmp_path))

    assert result.json["ok"] is False
    rules_failed = {e["rule"] for e in result.json["errors"]}
    assert "RC-04" in rules_failed
    assert result.returncode == 2


def test_deploy_target_none_downgrades_secrets_to_warning(tmp_path, run_tool, mock_gh):
    """deploy_target: none → absent deploy secrets are WARN, not ERROR."""
    _write_contract(tmp_path, deploy_target="none")
    _write_workflows(tmp_path, [
        "branch-ci", "merge-queue-ci", "deploy-staging",
        "health-and-smoke", "promote-dev-to-main", "release-prod",
    ])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    responses = _conformant_gh_responses()
    # secret list returns empty (no deploy tokens)
    responses.insert(0, {"match": "secret list", "stdout": "[]"})
    mock_gh(responses)

    result = run_tool("wpx-arrival-check", "--repo", "sulis-ai/agents",
                      "--repo-root", str(tmp_path))

    assert result.json["ok"] is True, f"errors: {result.json.get('errors')}"
    warn_rules = {w["rule"] for w in result.json["warnings"]}
    assert "RC-06" in warn_rules
    assert result.returncode == 0


def test_missing_codeowners_is_warning_not_error(tmp_path, run_tool, mock_gh):
    """CODEOWNERS is SHOULD (RC-10) → WARN, not a MUST failure."""
    _write_contract(tmp_path)
    _write_workflows(tmp_path, [
        "branch-ci", "merge-queue-ci", "deploy-staging",
        "health-and-smoke", "promote-dev-to-main", "release-prod",
    ])
    # no CODEOWNERS written
    mock_gh(_conformant_gh_responses())

    result = run_tool("wpx-arrival-check", "--repo", "sulis-ai/agents",
                      "--repo-root", str(tmp_path))

    assert result.json["ok"] is True
    warn_rules = {w["rule"] for w in result.json["warnings"]}
    assert "RC-10" in warn_rules
