"""Unit tests for wpx-preflight dev-clean (HD-002 / WP-003).

`wpx-preflight dev-clean --repo <org/repo> --branch <branch=dev>` reads the
base branch HEAD's CURRENT recorded CI conclusion (via WP-001's
`_wpxlib._preflight_ci_conclusion`, no polling) and emits the same JSON
envelope shape as `wpx-arrival-check` (`{"ok", "errors", "warnings"}`) + an
exit code, so `/sulis:run-all`'s Step 0 gate can parse it with the pattern it
already uses.

Verdict -> envelope mapping (WP Contract):

| verdict (WP-001)        | ok    | exit | errors / warnings                  |
|-------------------------|-------|------|------------------------------------|
| green                   | true  | 0    | -                                  |
| unknown (no runs)       | true  | 0    | advisory warning                   |
| pending (in-flight)     | true  | 0    | advisory warning (reads, no wait)  |
| failed                  | false | 2    | error rule:"PRE-01", names count   |

The PRE-01 blocker is a hard stop (no override); absence of evidence
(unknown/pending) does NOT block — the pre-flight reads recorded state, it
never waits/polls.

gh is mocked via the mock_gh fixture (substring dispatch). The check-runs
endpoint is `repos/<repo>/commits/<branch>/check-runs`, so the match string
`commits/dev/check-runs` selects it.
"""

from __future__ import annotations

import json


def test_preflight_red_dev_emits_blocker_with_count(tmp_path, run_tool, mock_gh):
    """A recorded failure on dev HEAD → ok:false, exit 2, a PRE-01 error whose
    `actual` names the count (1) and the failing check name (web)."""
    mock_gh([{"match": "commits/dev/check-runs", "stdout": json.dumps({
        "check_runs": [
            {"name": "branch-ci", "status": "completed", "conclusion": "success"},
            {"name": "web",       "status": "completed", "conclusion": "failure"},
        ]})}])

    result = run_tool("wpx-preflight", "dev-clean",
                      "--repo", "sulis-ai/agents", "--branch", "dev")

    assert result.json["ok"] is False
    assert result.returncode == 2
    blocker = next(e for e in result.json["errors"] if e["rule"] == "PRE-01")
    assert "1" in blocker["actual"]                 # names the count
    assert "web" in (blocker.get("detail", "") + blocker.get("actual", ""))
    assert blocker.get("expected") == "green"


def test_preflight_green_dev_is_ok(tmp_path, run_tool, mock_gh):
    """All completed runs green → ok:true, exit 0, no errors."""
    mock_gh([{"match": "commits/dev/check-runs", "stdout": json.dumps({
        "check_runs": [
            {"name": "branch-ci", "status": "completed", "conclusion": "success"},
        ]})}])

    result = run_tool("wpx-preflight", "dev-clean",
                      "--repo", "sulis-ai/agents", "--branch", "dev")

    assert result.json["ok"] is True
    assert result.returncode == 0
    assert result.json["errors"] == []


def test_preflight_reads_conclusion_explicitly(tmp_path, run_tool, mock_gh):
    """status:completed + conclusion:failure → red (lesson #59 guard,
    end-to-end through the CLI). A completed status must NOT mask a failure
    conclusion."""
    mock_gh([{"match": "commits/dev/check-runs", "stdout": json.dumps({
        "check_runs": [{"name": "web", "status": "completed", "conclusion": "failure"}]})}])

    result = run_tool("wpx-preflight", "dev-clean",
                      "--repo", "sulis-ai/agents", "--branch", "dev")

    assert result.json["ok"] is False
    assert result.returncode == 2


def test_preflight_unknown_no_runs_is_ok_with_warning(tmp_path, run_tool, mock_gh):
    """No check-runs recorded for dev HEAD yet → ok:true, exit 0, plus an
    advisory warning (absence of evidence is not red — do not false-block)."""
    mock_gh([{"match": "commits/dev/check-runs", "stdout": json.dumps({
        "check_runs": []})}])

    result = run_tool("wpx-preflight", "dev-clean",
                      "--repo", "sulis-ai/agents", "--branch", "dev")

    assert result.json["ok"] is True
    assert result.returncode == 0
    assert result.json["errors"] == []
    assert result.json["warnings"], "unknown (no runs recorded) should surface an advisory warning"


def test_preflight_pending_in_flight_is_ok_with_warning(tmp_path, run_tool, mock_gh):
    """A run still in_progress → ok:true, exit 0, plus an advisory warning.
    The pre-flight reads recorded state; it does not block on (or poll) an
    in-flight run."""
    mock_gh([{"match": "commits/dev/check-runs", "stdout": json.dumps({
        "check_runs": [
            {"name": "branch-ci", "status": "in_progress", "conclusion": None},
        ]})}])

    result = run_tool("wpx-preflight", "dev-clean",
                      "--repo", "sulis-ai/agents", "--branch", "dev")

    assert result.json["ok"] is True
    assert result.returncode == 0
    assert result.json["errors"] == []
    assert result.json["warnings"], "pending (in-flight) should surface an advisory warning"
