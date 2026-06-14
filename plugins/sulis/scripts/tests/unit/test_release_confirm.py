"""Unit tests for the race-free release-run confirm (#121).

The bug: confirming a release after merge by `gh run list
--workflow=release-on-merge --limit 1` can return the PREVIOUS run — the new
run for the merge commit isn't created the instant the merge lands, so "the
latest run" is a race. A confirm built on it reports success against a stale
release (caught manually via the Definition-of-Done git-log check when no new
release commit appeared on main).

The fix: select the run by matching its `headSha` to the merge commit — never
"the latest". `select_release_run` is the pure decision; the CLI polls + feeds
it. Tested here.
"""

from __future__ import annotations

from _release_confirm import select_release_run

_MERGE = "c42eeaab8f926a85992497049766d785ca082e94"
_OTHER = "5d62cdf2f80b9da39e8a1742be9a095e9b98013b"


def _run(sha, status="completed", conclusion="success", rid=1):
    return {"headSha": sha, "status": status, "conclusion": conclusion,
            "databaseId": rid}


def test_selects_the_run_for_the_merge_sha_not_the_latest():
    # The previous run is listed first (most-recent-first) but belongs to a
    # DIFFERENT merge — selecting it would confirm a stale release.
    runs = [_run(_OTHER, rid=2), _run(_MERGE, rid=1)]
    got = select_release_run(runs, _MERGE)
    assert got is not None
    assert got["databaseId"] == 1
    assert got["headSha"] == _MERGE


def test_matches_short_sha_against_full_run_sha():
    # The caller may hold a short (8-char) merge sha; the run carries the full.
    runs = [_run(_MERGE, rid=1)]
    assert select_release_run(runs, _MERGE[:8])["databaseId"] == 1


def test_returns_none_when_no_run_for_the_sha_yet():
    # The new run hasn't been created yet → None (caller keeps polling), NOT
    # a wrong-run match. This is the exact race the bug exploited.
    runs = [_run(_OTHER, rid=2)]
    assert select_release_run(runs, _MERGE) is None


def test_returns_none_on_empty_list():
    assert select_release_run([], _MERGE) is None


def test_ignores_runs_missing_headsha():
    runs = [{"status": "queued", "databaseId": 9}, _run(_MERGE, rid=1)]
    assert select_release_run(runs, _MERGE)["databaseId"] == 1
