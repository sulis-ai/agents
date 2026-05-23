"""PR vs codebase scope auto-detection.

All tier-skills accept --scope auto|pr|codebase. The auto path tries to
infer from local git state: feature branch with diverging commits → PR
scope (the diff); on main/master/trunk → codebase scope. Overridable
via --base-branch + --scope explicit flags.

Used by check-readability, check-tests, check-build, check-security.
Each skill calls resolve_scope() with its CLI args and gets back:
  (scope, base_branch, files_in_scope)
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def detect_base_branch(repo_root: Path) -> str:
    """Find the project's main-line branch. Order: main, master, trunk,
    then git's symbolic-ref for origin/HEAD."""
    for candidate in ("main", "master", "trunk"):
        rc, _, _ = _git(repo_root, ["rev-parse", "--verify", f"refs/heads/{candidate}"])
        if rc == 0:
            return candidate
    rc, out, _ = _git(repo_root, ["symbolic-ref", "refs/remotes/origin/HEAD"])
    if rc == 0 and "/" in out:
        return out.strip().split("/")[-1]
    return "main"


def detect_scope(repo_root: Path, base_branch: str) -> tuple[str, list[str]]:
    """Auto-detect PR vs codebase scope from local git state.

    Returns (scope, files). For PR scope, files is the changed-file list
    from `git diff --name-only base...HEAD`. For codebase, files is empty
    (caller walks the tree).
    """
    rc, current, _ = _git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if rc != 0:
        return "codebase", []
    current = current.strip()
    if current == base_branch:
        return "codebase", []

    rc, out, _ = _git(
        repo_root, ["diff", "--name-only", f"{base_branch}...HEAD"]
    )
    if rc != 0:
        rc, out, _ = _git(repo_root, ["diff", "--name-only", "HEAD"])

    files = [f for f in out.strip().splitlines() if f]
    if not files:
        return "codebase", []
    return "pr", files


def fetch_pr_files(pr_number: int, repo_root: Path) -> tuple[list[str], list[str]]:
    """Fetch files in a remote PR via gh CLI. Returns (files, errors)."""
    rc, out, err = _run(
        ["gh", "pr", "diff", str(pr_number), "--name-only"], repo_root
    )
    if rc != 0:
        return [], [f"gh pr diff failed (rc={rc}): {err}"]
    files = [f for f in out.strip().splitlines() if f]
    return files, []


def list_codebase_files(
    repo_root: Path, extensions: set[str] | None = None
) -> list[str]:
    """List all tracked files; filter to given extensions if provided."""
    rc, out, _ = _git(repo_root, ["ls-files"])
    if rc != 0:
        return []
    files = out.strip().splitlines()
    if extensions:
        files = [f for f in files if Path(f).suffix in extensions]
    return files


def resolve_scope(
    repo_root: Path,
    scope_arg: str,
    base_branch_arg: str | None,
    pr_number_arg: int | None,
    extensions: set[str] | None = None,
) -> tuple[str, str, list[str], list[str]]:
    """Top-level scope resolver. Returns (scope, base_branch, files, errors).

    Logic:
      1. If --pr-number passed: PR scope via gh CLI.
      2. Else if --scope=pr: local diff vs --base-branch (auto-detected if absent).
      3. Else if --scope=codebase: full tree.
      4. Else (--scope=auto): detect from git state.
    """
    errors: list[str] = []
    base_branch = base_branch_arg or detect_base_branch(repo_root)

    if pr_number_arg is not None:
        scope = "pr"
        files, fetch_errors = fetch_pr_files(pr_number_arg, repo_root)
        errors.extend(fetch_errors)
    elif scope_arg == "pr":
        scope = "pr"
        _, files = detect_scope(repo_root, base_branch)
    elif scope_arg == "codebase":
        scope = "codebase"
        files = list_codebase_files(repo_root, extensions)
    else:  # auto
        scope, files = detect_scope(repo_root, base_branch)
        if scope == "codebase":
            files = list_codebase_files(repo_root, extensions)

    if extensions and scope == "pr":
        files = [f for f in files if Path(f).suffix in extensions]

    return scope, base_branch, files, errors


# ─── git/subprocess helpers ─────────────────────────────────────────


def _git(repo_root: Path, args: list[str]) -> tuple[int, str, str]:
    return _run(["git", *args], repo_root)


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=30
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError as exc:
        return 127, "", str(exc)
