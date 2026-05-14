"""
Filesystem walk with `.gitignore` awareness, depth ceiling, and exclude
patterns.

Strategy:
- If the directory is inside a git repo, shell out to `git check-ignore --stdin`
  to authoritatively decide whether a path is gitignored. This is the most
  accurate approach (git's own ignore parser).
- If git isn't available or the path isn't in a repo, fall back to a simple
  exclude-list match.
- Always exclude paths matching `EXTRA_EXCLUDE_DIRS` (venv, node_modules,
  etc.) regardless of .gitignore.

Used by every runner that needs to discover files for processing.
"""

from __future__ import annotations

import fnmatch
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .config import DEFAULT_MAX_DEPTH, EXTRA_EXCLUDE_DIRS


@dataclass(frozen=True)
class WalkConfig:
    root: Path                       # absolute
    max_depth: int = DEFAULT_MAX_DEPTH
    extra_excludes: tuple[str, ...] = ()
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    follow_symlinks: bool = False
    use_gitignore: bool = True


def is_in_git_repo(path: Path) -> bool:
    """Return True if `path` is inside a git work tree."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            timeout=5,
            check=False,
            text=True,
        )
        return completed.returncode == 0 and completed.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def git_ignored(paths: list[Path], repo_root: Path) -> set[Path]:
    """
    Return the subset of `paths` that git considers ignored.

    Uses `git check-ignore --stdin` for an authoritative answer. Paths must
    be inside `repo_root`. Returns absolute paths.
    """
    if not paths:
        return set()

    rel_paths = [str(p.relative_to(repo_root)) for p in paths]
    stdin_text = "\n".join(rel_paths)

    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "--stdin"],
            input=stdin_text,
            capture_output=True,
            timeout=30,
            check=False,
            text=True,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()

    # check-ignore exits 0 if any ignored, 1 if none, 128 on error.
    if completed.returncode not in (0, 1):
        return set()

    ignored_rel = {line.strip() for line in completed.stdout.splitlines() if line.strip()}
    return {repo_root / rel for rel in ignored_rel}


def _matches_any_glob(path: Path, patterns: tuple[str, ...]) -> bool:
    """Check whether any path component (or the full path) matches any glob."""
    path_str = str(path)
    name = path.name
    for pat in patterns:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(path_str, pat):
            return True
    return False


def _component_in_excludes(path: Path, root: Path, excludes: tuple[str, ...]) -> bool:
    """True if any directory component along path-from-root is in `excludes`."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    return any(part in excludes for part in rel.parts)


def walk_files(cfg: WalkConfig) -> Iterator[Path]:
    """
    Yield absolute paths to files under `cfg.root` respecting all filters.

    Order: depth-first by `os.walk` defaults. For deterministic ordering
    in tests, callers should sort the result.
    """
    root = cfg.root.resolve()
    all_excludes = tuple(EXTRA_EXCLUDE_DIRS) + tuple(cfg.extra_excludes)

    # Determine gitignore strategy once
    use_git = cfg.use_gitignore and is_in_git_repo(root)
    repo_root = root if use_git else None
    if use_git:
        # find the actual repo root for accurate check-ignore
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                capture_output=True, timeout=5, check=False, text=True,
            )
            if completed.returncode == 0:
                repo_root = Path(completed.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # Collect all candidate files first so we can batch-check gitignore
    candidates: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=cfg.follow_symlinks):
        current = Path(dirpath)

        # depth check
        try:
            rel_depth = len(current.relative_to(root).parts)
        except ValueError:
            rel_depth = 0
        if rel_depth >= cfg.max_depth:
            dirnames.clear()
            continue

        # prune dirs matching extra-excludes (component-based)
        dirnames[:] = [d for d in dirnames if d not in all_excludes]

        # prune via exclude-patterns (glob)
        if cfg.exclude_patterns:
            dirnames[:] = [
                d for d in dirnames
                if not _matches_any_glob(current / d, cfg.exclude_patterns)
            ]

        for fname in filenames:
            fpath = current / fname

            # extra-excludes can match files too (e.g. lockfiles)
            if _component_in_excludes(fpath, root, all_excludes):
                continue

            # explicit exclude patterns
            if cfg.exclude_patterns and _matches_any_glob(fpath, cfg.exclude_patterns):
                continue

            # explicit include patterns: if set, file must match at least one
            if cfg.include_patterns and not _matches_any_glob(fpath, cfg.include_patterns):
                continue

            candidates.append(fpath)

    # Batch gitignore filter
    if use_git and repo_root is not None and candidates:
        # Only candidates under repo_root can be checked
        in_repo = [p for p in candidates if str(p).startswith(str(repo_root))]
        if in_repo:
            ignored = git_ignored(in_repo, repo_root)
            candidates = [p for p in candidates if p not in ignored]

    yield from candidates


def find_first_manifest(start: Path, manifest_names: tuple[str, ...]) -> Path | None:
    """
    Look for the first file matching any of `manifest_names` at `start`,
    walking up to the filesystem root. Returns absolute path or None.
    """
    current = start.resolve()
    while True:
        for name in manifest_names:
            candidate = current / name
            if candidate.exists() and candidate.is_file():
                return candidate
        if current.parent == current:
            return None
        current = current.parent


def files_for_language(workspace_path: Path, language: str) -> list[Path]:
    """
    Return source files for a given language under `workspace_path`,
    respecting .gitignore and exclusions.

    Language → extensions mapping is intentionally narrow — we use this for
    ast-grep / lizard invocations that need explicit file lists.
    """
    ext_map: dict[str, tuple[str, ...]] = {
        "ts": (".ts",),
        "tsx": (".tsx",),
        "javascript": (".js", ".mjs", ".cjs"),
        "python": (".py",),
        "go": (".go",),
        "rust": (".rs",),
        "java": (".java",),
        "csharp": (".cs",),
        "ruby": (".rb",),
        "php": (".php",),
        "swift": (".swift",),
        "kotlin": (".kt", ".kts"),
    }
    exts = ext_map.get(language, ())
    if not exts:
        return []

    cfg = WalkConfig(
        root=workspace_path.resolve(),
        include_patterns=tuple(f"*{e}" for e in exts),
    )
    return list(walk_files(cfg))
