"""
Phase 1.11 — git history signals: churn, age, authors, co-change.

Uses only `git log`. Computes:
- Per-file commit count in the lookback window
- Distinct author count per file
- File age (first-commit date)
- Co-change pairs (files changed together in the same commit)

Recommendations downstream:
- High churn × high CCN → top Refactor priority
- bus_factor=1 in critical paths → REINFORCE-Document
- Strong co-change pairs that import-graph doesn't capture → hidden coupling
"""

from __future__ import annotations

import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import GIT_BUS_FACTOR_LOW, GIT_CHURN_HIGH_THRESHOLD, GIT_COCHANGE_MIN_PAIRS
from ..models import CoChangePair, FileChurn, HistoryPayload, RunnerInput, RunnerResult
from .base import make_result, now_iso, run_tool, ToolMissingError


class GitHistoryRunner:
    PHASE: str = "1.11"
    TOOL: str = "git"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []

        workspace_path = Path(inp.workspace_path)

        # Verify this is a git repo
        if not _is_git_repo(workspace_path):
            warnings.append("Not a git repo; history signals unavailable")
            payload = HistoryPayload(
                lookback_days=inp.git_lookback_days,
                file_churn=[], high_churn_files=[],
                bus_factor_one=[], co_change_pairs=[],
                repo_first_commit_iso=None, repo_last_commit_iso=None,
            )
            return make_result(
                phase=self.PHASE, tool=self.TOOL,
                started_at=started_at, started_monotonic=started_monotonic,
                payload=payload.__dict__, warnings=warnings,
            )

        since_date = (
            datetime.now(timezone.utc) - timedelta(days=inp.git_lookback_days)
        ).strftime("%Y-%m-%d")

        # Get per-file commit/author data
        file_data = _collect_file_history(workspace_path, since_date)

        # Get co-change pairs
        co_change = _collect_co_changes(workspace_path, since_date)

        # Repo boundaries
        first_iso, last_iso = _repo_boundaries(workspace_path)

        # Build payload
        file_churn = [
            FileChurn(
                file=f,
                commits_in_lookback=d["commits"],
                age_days=d["age_days"],
                distinct_authors=d["authors"],
                last_commit_iso=d["last_commit"],
            )
            for f, d in sorted(
                file_data.items(),
                key=lambda kv: -kv[1]["commits"],
            )
        ]
        high_churn = [
            fc.file for fc in file_churn
            if fc.commits_in_lookback > GIT_CHURN_HIGH_THRESHOLD
        ]
        bus_factor_one = [
            fc.file for fc in file_churn
            if fc.distinct_authors <= GIT_BUS_FACTOR_LOW and fc.commits_in_lookback > 0
        ]

        payload = HistoryPayload(
            lookback_days=inp.git_lookback_days,
            file_churn=[fc.__dict__ for fc in file_churn],
            high_churn_files=high_churn,
            bus_factor_one=bus_factor_one,
            co_change_pairs=[c.__dict__ for c in co_change],
            repo_first_commit_iso=first_iso,
            repo_last_commit_iso=last_iso,
        )

        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings,
        )


def _is_git_repo(path: Path) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, timeout=5, check=False, text=True,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _collect_file_history(
    workspace_path: Path,
    since_date: str,
) -> dict[str, dict]:
    """For each file changed since `since_date`, collect commits/authors."""
    # `git log --name-only --pretty=format:%H|%aI|%an --since=<date>`
    # produces sections like:
    #   abc123|2026-05-01T12:00:00+00:00|Alice
    #   path/to/file.py
    #   path/to/other.py
    #   <blank line>
    cmd = [
        "git", "-C", str(workspace_path),
        "log",
        "--name-only",
        f"--since={since_date}",
        "--pretty=format:%H%x09%aI%x09%an",
        "--no-merges",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60, check=False, text=True)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    if r.returncode != 0:
        return {}

    data: dict[str, dict] = defaultdict(
        lambda: {"commits": 0, "authors": set(), "last_commit": "", "first_commit": ""}
    )

    current_author: str = ""
    current_date: str = ""
    for line in r.stdout.splitlines():
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 3:
                current_date = parts[1]
                current_author = parts[2]
            continue
        if not line.strip():
            continue
        f = line.strip()
        entry = data[f]
        entry["commits"] += 1
        entry["authors"].add(current_author)
        if not entry["last_commit"] or current_date > entry["last_commit"]:
            entry["last_commit"] = current_date
        if not entry["first_commit"] or current_date < entry["first_commit"]:
            entry["first_commit"] = current_date

    # Compute age in days
    now = datetime.now(timezone.utc)
    out: dict[str, dict] = {}
    for f, entry in data.items():
        age_days = 0
        if entry["first_commit"]:
            try:
                first_dt = datetime.fromisoformat(entry["first_commit"])
                age_days = max(0, (now - first_dt).days)
            except ValueError:
                age_days = 0
        out[f] = {
            "commits": entry["commits"],
            "authors": len(entry["authors"]),
            "last_commit": entry["last_commit"],
            "age_days": age_days,
        }
    return out


def _collect_co_changes(
    workspace_path: Path,
    since_date: str,
) -> list[CoChangePair]:
    """
    Find file pairs that changed together. Uses `git log --name-only` and
    counts pair occurrences within each commit. Returns pairs above the
    threshold sorted by count.
    """
    cmd = [
        "git", "-C", str(workspace_path), "log",
        "--name-only", f"--since={since_date}",
        "--pretty=format:%H", "--no-merges",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60, check=False, text=True)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []

    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    current_files: list[str] = []

    def flush_commit():
        nonlocal current_files
        files = sorted(set(current_files))
        # Cap pairs per commit to avoid quadratic blowup on huge merges
        if len(files) <= 20:
            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    pair_counts[(files[i], files[j])] += 1
        current_files = []

    for line in r.stdout.splitlines():
        if not line.strip():
            flush_commit()
            continue
        # Commit-hash lines have exactly 40 hex chars (sha-1) or 64 (sha-256)
        is_commit_hash = (
            len(line) in (40, 64)
            and all(ch in "0123456789abcdef" for ch in line.lower())
        )
        if is_commit_hash:
            flush_commit()
            continue
        current_files.append(line.strip())
    flush_commit()

    pairs = [
        CoChangePair(file_a=a, file_b=b, pair_count=count)
        for (a, b), count in pair_counts.items()
        if count >= GIT_COCHANGE_MIN_PAIRS
    ]
    pairs.sort(key=lambda p: -p.pair_count)
    # Cap to top 50 pairs to keep JSON manageable
    return pairs[:50]


def _repo_boundaries(workspace_path: Path) -> tuple[str | None, str | None]:
    """Return (first-commit-iso, last-commit-iso) for the repo."""
    def _date_query(args: list[str]) -> str | None:
        try:
            r = subprocess.run(
                ["git", "-C", str(workspace_path)] + args,
                capture_output=True, timeout=10, check=False, text=True,
            )
            if r.returncode == 0:
                return r.stdout.strip() or None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    last = _date_query(["log", "-1", "--pretty=format:%aI"])
    first = _date_query(["log", "--reverse", "--pretty=format:%aI", "--all"])
    if first:
        first = first.splitlines()[0]
    return first, last
