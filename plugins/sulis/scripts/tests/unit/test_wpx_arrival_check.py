"""Unit tests for wpx-arrival-check (RC-11 arrival check, v0.3.0 profile model).

The script verifies the Repository Contract against a live repo via `gh api`
+ filesystem, applying the v0.3.0 profile-applicability matrix
(repository-contract-standard.md): a repo declares a single `profile:`
(deployable-web-app | published-artifact | internal-tool) XOR an `artifacts:`
list, plus an orthogonal `contribution_model:` (team | solo). The matrix
decides, per rule, whether an absent/wrong resource is an error, a warning,
or skipped.

Key v0.3.0 behaviours under test:
- RC-02 deadlock fix: classic required checks on dev = `branch-ci` ONLY;
  `merge-queue-ci` must NOT be a classic required check.
- RC-03 keys on contribution_model: team → queue MUST exist; solo → queue
  MUST be absent.
- RC-05/06/08 vary by profile (deployable strict; published relaxed;
  internal N/A).
- Multi-artifact: union — a deployable artifact keeps the strict set.
- Defaults: no profile + no artifacts → deployable-web-app; no
  contribution_model → team (backward-compat = strict v0.2.0).

gh is mocked via the mock_gh fixture (substring dispatch, most-specific first).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ─── helpers ──────────────────────────────────────────────────────────────


def _write_contract(repo_root: Path, body: str) -> None:
    sulis = repo_root / ".sulis"
    sulis.mkdir(parents=True, exist_ok=True)
    (sulis / "repo-contract.yml").write_text(body)


def _write_workflows(repo_root: Path, names: list[str]) -> None:
    wf = repo_root / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    for n in names:
        (wf / f"{n}.yml").write_text(f"name: {n}\non: push\n")


def _gh_base(*, queue_present: bool, default_branch: str = "dev",
             environments: list[str] | None = None) -> list[dict]:
    """Conformant gh responses. Most-specific match first.

    queue_present toggles whether the dev rules include a merge_queue rule.
    """
    envs = environments if environments is not None else ["staging", "production"]
    rules = [{"type": "merge_queue"}] if queue_present else []
    return [
        {"match": "rules/branches/dev", "stdout": json.dumps(rules)},
        {"match": "branches/dev/protection", "stdout": json.dumps({
            "required_status_checks": {"contexts": ["branch-ci"]},
        })},
        {"match": "branches/main/protection", "stdout": json.dumps({})},
        {"match": "branches/dev", "stdout": json.dumps({"name": "dev"})},
        {"match": "branches/main", "stdout": json.dumps({"name": "main"})},
        {"match": "/environments", "stdout": json.dumps({
            "environments": [{"name": e} for e in envs],
        })},
        {"match": "secret list", "stdout": "[]"},
        {"match": "repos/sulis-ai/agents", "stdout": json.dumps({
            "default_branch": default_branch,
            "allow_squash_merge": True, "allow_merge_commit": False,
            "allow_rebase_merge": False, "delete_branch_on_merge": True,
        })},
    ]


def _run(run_tool, repo_root: Path):
    return run_tool("wpx-arrival-check", "--repo", "sulis-ai/agents",
                    "--repo-root", str(repo_root))


SINGLE_WF = ["branch-ci", "merge-queue-ci", "deploy-staging",
             "health-and-smoke", "promote-dev-to-main", "release-prod"]


# ─── RC-02 deadlock fix ─────────────────────────────────────────────────────


def test_rc02_requires_branch_ci_only_not_merge_queue_ci(tmp_path, run_tool, mock_gh):
    """v0.3.0 RC-02 fix: classic required checks = branch-ci ONLY.

    A dev branch whose classic required checks are exactly [branch-ci] must
    PASS RC-02 — the old code demanded merge-queue-ci too (the deadlock).
    """
    _write_contract(tmp_path, "profile: deployable-web-app\ncontribution_model: team\n")
    _write_workflows(tmp_path, SINGLE_WF)
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=True))

    result = _run(run_tool, tmp_path)

    rc02_errors = [e for e in result.json["errors"] if e["rule"] == "RC-02"]
    assert rc02_errors == [], f"RC-02 should pass with branch-ci-only: {rc02_errors}"


def test_rc02_fails_if_merge_queue_ci_is_a_classic_required_check(tmp_path, run_tool, mock_gh):
    """The inverse: merge-queue-ci present as a classic check is now an ERROR
    (it re-introduces the deadlock)."""
    _write_contract(tmp_path, "profile: deployable-web-app\ncontribution_model: team\n")
    _write_workflows(tmp_path, SINGLE_WF)
    responses = _gh_base(queue_present=True)
    responses[1] = {"match": "branches/dev/protection", "stdout": json.dumps({
        "required_status_checks": {"contexts": ["branch-ci", "merge-queue-ci"]},
    })}
    mock_gh(responses)

    result = _run(run_tool, tmp_path)

    rc02_errors = [e for e in result.json["errors"] if e["rule"] == "RC-02"]
    assert rc02_errors, "merge-queue-ci as a classic required check must fail RC-02"


# ─── RC-03 keyed on contribution_model ──────────────────────────────────────


def test_rc03_solo_requires_queue_absent(tmp_path, run_tool, mock_gh):
    """solo → merge queue MUST be absent. Queue present = error."""
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main",
                                "deploy-staging", "health-and-smoke", "release-prod"])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=True))  # queue present — wrong for solo

    result = _run(run_tool, tmp_path)

    rc03 = [e for e in result.json["errors"] if e["rule"] == "RC-03"]
    assert rc03, "solo repo with a merge queue present must fail RC-03"


def test_rc03_solo_passes_with_no_queue(tmp_path, run_tool, mock_gh):
    """solo + no queue = RC-03 clean."""
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main",
                                "deploy-staging", "health-and-smoke", "release-prod"])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=False))

    result = _run(run_tool, tmp_path)

    rc03 = [e for e in result.json["errors"] if e["rule"] == "RC-03"]
    assert rc03 == [], f"solo + no queue should pass RC-03: {rc03}"


def test_rc03_team_requires_queue_present(tmp_path, run_tool, mock_gh):
    """team → merge queue MUST exist. Absent = error."""
    _write_contract(tmp_path, "profile: deployable-web-app\ncontribution_model: team\n")
    _write_workflows(tmp_path, SINGLE_WF)
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=False))  # no queue — wrong for team

    result = _run(run_tool, tmp_path)

    rc03 = [e for e in result.json["errors"] if e["rule"] == "RC-03"]
    assert rc03, "team repo with no merge queue must fail RC-03"


# ─── this repo: published-artifact + solo ───────────────────────────────────


def test_published_solo_repo_passes(tmp_path, run_tool, mock_gh):
    """The marketplace's own profile: published-artifact + solo.

    branch-ci + promote + deploy/health/release (repurposed) required;
    merge-queue-ci NOT required (solo); RC-05 warn; RC-06 skip; RC-08 warn.
    """
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    # note: no merge-queue-ci.yml (solo doesn't need it)
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main",
                                "deploy-staging", "health-and-smoke", "release-prod"])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=False))

    result = _run(run_tool, tmp_path)

    assert result.json["ok"] is True, f"errors: {result.json['errors']}"
    assert result.returncode == 0
    # RC-06 should be skipped (no error, no requirement); RC-05 warn allowed
    rc06_errors = [e for e in result.json["errors"] if e["rule"] == "RC-06"]
    assert rc06_errors == []


def test_published_solo_does_not_require_merge_queue_ci_workflow(tmp_path, run_tool, mock_gh):
    """solo → merge-queue-ci.yml is not a required workflow file."""
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main",
                                "deploy-staging", "health-and-smoke", "release-prod"])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=False))

    result = _run(run_tool, tmp_path)

    rc04 = [e for e in result.json["errors"]
            if e["rule"] == "RC-04" and "merge-queue-ci" in e["check"]]
    assert rc04 == [], "merge-queue-ci.yml must not be required for solo"


# ─── deployable-web-app default (backward-compat = strict v0.2.0) ────────────


def test_default_profile_is_deployable_team_strict(tmp_path, run_tool, mock_gh):
    """No profile + no contribution_model → deployable-web-app + team.

    Missing environments → RC-05 ERROR (strict), not warn.
    """
    _write_contract(tmp_path, "repo: sulis-ai/agents\n")  # no profile, no model
    _write_workflows(tmp_path, SINGLE_WF)
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=True, environments=[]))  # no envs

    result = _run(run_tool, tmp_path)

    rc05 = [e for e in result.json["errors"] if e["rule"] == "RC-05"]
    assert rc05, "deployable default with no environments must ERROR on RC-05 (strict)"


def test_published_missing_env_is_warn_not_error(tmp_path, run_tool, mock_gh):
    """published-artifact: missing environment is WARN, not error."""
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main",
                                "deploy-staging", "health-and-smoke", "release-prod"])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=False, environments=[]))

    result = _run(run_tool, tmp_path)

    rc05_errors = [e for e in result.json["errors"] if e["rule"] == "RC-05"]
    rc05_warns = [w for w in result.json["warnings"] if w["rule"] == "RC-05"]
    assert rc05_errors == [], "published missing env must not be an error"
    assert rc05_warns, "published missing env should be a warning"


# ─── multi-artifact union ───────────────────────────────────────────────────


def test_multi_artifact_deployable_keeps_strict_set(tmp_path, run_tool, mock_gh):
    """artifacts: [api: deployable-web-app, sdk: published-artifact], team.

    Per-artifact namespaced workflows required: deploy-api-staging.yml,
    health-api-staging.yml, release-api-prod.yml, publish-sdk.yml +
    shared branch-ci/merge-queue-ci/promote. Union: the api artifact's
    deploy workflows are MUST (the sdk can't cancel them).
    """
    _write_contract(tmp_path, (
        "repo: acme/widget\ncontribution_model: team\n"
        "artifacts:\n"
        "  - name: api\n    type: deployable-web-app\n"
        "  - name: sdk\n    type: published-artifact\n"
    ))
    # deliberately MISSING deploy-api-staging.yml to prove it's required
    _write_workflows(tmp_path, ["branch-ci", "merge-queue-ci", "promote-dev-to-main",
                                "health-api-staging", "release-api-prod", "publish-sdk"])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    mock_gh(_gh_base(queue_present=True))

    result = _run(run_tool, tmp_path)

    rc04 = [e for e in result.json["errors"]
            if e["rule"] == "RC-04" and "deploy-api-staging" in e["check"]]
    assert rc04, "deployable artifact's deploy-<name>-staging.yml must be required (union)"


def test_profile_and_artifacts_both_present_is_error(tmp_path, run_tool, mock_gh):
    """A repo declaring BOTH profile and artifacts is malformed."""
    _write_contract(tmp_path, (
        "profile: deployable-web-app\n"
        "artifacts:\n  - name: api\n    type: deployable-web-app\n"
    ))
    _write_workflows(tmp_path, SINGLE_WF)
    mock_gh(_gh_base(queue_present=True))

    result = _run(run_tool, tmp_path)

    assert result.json["ok"] is False
    contract_errs = [e for e in result.json["errors"] if e["rule"] == "contract"]
    assert contract_errs, "profile + artifacts both present must be a contract error"


# ─── invariant rules still enforced ─────────────────────────────────────────


def test_missing_dev_branch_still_fails_rc01(tmp_path, run_tool, mock_gh):
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main"])
    responses = _gh_base(queue_present=False)
    responses.insert(0, {"match": "branches/dev", "exit_code": 1, "stderr": "Not Found"})
    mock_gh(responses)

    result = _run(run_tool, tmp_path)

    assert result.json["ok"] is False
    assert "RC-01" in {e["rule"] for e in result.json["errors"]}
    assert result.returncode == 2


def test_missing_codeowners_is_warning(tmp_path, run_tool, mock_gh):
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main",
                                "deploy-staging", "health-and-smoke", "release-prod"])
    mock_gh(_gh_base(queue_present=False))

    result = _run(run_tool, tmp_path)

    assert "RC-10" in {w["rule"] for w in result.json["warnings"]}
