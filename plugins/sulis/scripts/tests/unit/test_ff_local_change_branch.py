"""Unit tests for #141 — `ff_local_change_branch_from_origin`.

After wpx-pipeline squash-merges a WP into the change branch via the GitHub
API, the squash commit lands on origin/<change_branch> but the LOCAL change
worktree is still at the pre-merge SHA. The next agent (e.g. Step 11
security-review) reads stale files and returns a false "CANNOT REVIEW"
verdict. The helper here closes that gap.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_ff_already_current(monkeypatch, tmp_path):
    """Origin is at or behind HEAD → no fetch-merge work, status reports it."""
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        calls.append(list(cmd))
        if cmd[:2] == ["git", "fetch"]:
            return (0, "", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (0, "", "")  # origin/<branch> IS ancestor → already current
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import ff_local_change_branch_from_origin
    result = ff_local_change_branch_from_origin(tmp_path, "change/fix-x")
    assert result["status"] == "already_current"
    assert result["change_branch"] == "change/fix-x"
    # No merge invocation expected
    assert not any(
        c[:3] == ["git", "merge", "--ff-only"] for c in calls
    )


def test_ff_fast_forwarded_with_advance_count(monkeypatch, tmp_path):
    """Origin is ahead → ff merge succeeds, advanced_commits reported."""
    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            return (0, "", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (1, "", "")  # NOT ancestor → origin ahead
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return (0, "1\n", "")
        if cmd[:3] == ["git", "merge", "--ff-only"]:
            return (0, "", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import ff_local_change_branch_from_origin
    result = ff_local_change_branch_from_origin(tmp_path, "change/fix-x")
    assert result["status"] == "fast_forwarded"
    assert result["advanced_commits"] == 1


def test_ff_fetch_failed(monkeypatch, tmp_path):
    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            return (1, "", "Could not resolve host: github.com")
        return (0, "", "")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import ff_local_change_branch_from_origin
    result = ff_local_change_branch_from_origin(tmp_path, "change/fix-x")
    assert result["status"] == "fetch_failed"
    assert "Could not resolve" in result["error"]


def test_ff_not_possible_when_local_diverged(monkeypatch, tmp_path):
    """If --ff-only refuses, surface ff_not_possible instead of silently
    creating a merge commit (preserves CW-04's no-rebase + intentful merges
    rule)."""
    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            return (0, "", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (1, "", "")
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return (0, "2\n", "")
        if cmd[:3] == ["git", "merge", "--ff-only"]:
            return (
                1,
                "",
                "fatal: Not possible to fast-forward, aborting.",
            )
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import ff_local_change_branch_from_origin
    result = ff_local_change_branch_from_origin(tmp_path, "change/fix-x")
    assert result["status"] == "ff_not_possible"
    assert "fast-forward" in result["error"]
