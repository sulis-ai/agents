"""Race-free confirm of the release-on-merge run for a merge commit (#121).

The bug this closes: confirming a release after merge by "the latest
release-on-merge run" (`gh run list --limit 1`) races. The run for the
just-merged commit is not created the instant the merge lands, so the
most-recent run can belong to a PREVIOUS merge — and a confirm built on it
reports success against a stale release. (Caught manually when no new
`release: sulis v…` commit appeared on main despite a "success" watch.)

The race-free signal is the merge commit's sha: select the run whose
``headSha`` matches it, never "the latest". ``select_release_run`` is the pure
decision; ``poll_release_run`` wraps it with polling. Stdlib only. 3.11-safe.
"""

from __future__ import annotations

import json
import subprocess
import time


def select_release_run(runs, merge_sha):
    """Return the run whose ``headSha`` matches ``merge_sha`` (full or short
    prefix, either direction), or ``None`` if no run for that commit exists in
    ``runs`` yet.

    NEVER returns "the latest" run — that is the race the bug exploited.
    ``None`` means "no run for this commit yet, keep polling", NOT "wrong run".
    """
    sha = (merge_sha or "").strip()
    if not sha:
        return None
    for run in runs:
        head = str((run or {}).get("headSha", "") or "").strip()
        if not head:
            continue
        if head == sha or head.startswith(sha) or sha.startswith(head):
            return run
    return None


def _list_release_runs(repo: str, workflow: str = "release-on-merge.yml",
                       limit: int = 20, *, run=None) -> list[dict]:
    """The most-recent release runs (headSha/status/conclusion/databaseId).
    Best-effort: any gh/parse error returns ``[]``. ``run`` is injectable."""
    runner = run or (lambda cmd: subprocess.run(
        cmd, capture_output=True, text=True, timeout=30))
    try:
        res = runner([
            "gh", "run", "list", "--repo", repo, "--workflow", workflow,
            "--limit", str(limit),
            "--json", "headSha,status,conclusion,databaseId",
        ])
    except (OSError, subprocess.SubprocessError):
        return []
    if res.returncode != 0:
        return []
    try:
        data = json.loads(res.stdout)
    except (ValueError, TypeError):
        return []
    return data if isinstance(data, list) else []


def poll_release_run(repo: str, merge_sha: str, *, attempts: int = 20,
                     sleep_s: float = 6.0, run=None, sleep=None):
    """Poll until the release run for ``merge_sha`` exists AND has completed;
    return ``(found: bool, conclusion: str | None, run: dict | None)``.

    Race-free: each poll re-lists and selects by sha (never latest). Returns
    ``found=False`` if no run for the commit appears within the budget — the
    honest "couldn't confirm", never a stale-run false success. ``run`` and
    ``sleep`` seams are injectable for tests."""
    _sleep = sleep or time.sleep
    for _ in range(max(1, attempts)):
        match = select_release_run(_list_release_runs(repo, run=run), merge_sha)
        if match is not None and str(match.get("status")) == "completed":
            return (True, str(match.get("conclusion") or ""), match)
        _sleep(sleep_s)
    # Final read after the last sleep (so attempts==1 still gets one check post-wait).
    match = select_release_run(_list_release_runs(repo, run=run), merge_sha)
    if match is not None and str(match.get("status")) == "completed":
        return (True, str(match.get("conclusion") or ""), match)
    return (False, None, match)
