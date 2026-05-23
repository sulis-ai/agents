"""Tier-namespaced baseline read/write.

All tier skills share `.checkup/{project}/baseline.json` but use distinct
sub-keys to avoid collision:

  tier_1_systems       — check-build: build-system → pass/fail
  tier_1_captured_at   — timestamp
  tier_2_findings      — check-security: signature set
  tier_2_captured_at   — timestamp
  tier_3_tests         — check-tests: full Baseline shape
  tier_5_findings      — check-readability: (future) signature set

Each tier reads/writes only its own sub-key; other tiers' data passes
through unchanged.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any


def baseline_path(repo_root: Path, project: str) -> Path:
    return repo_root / ".checkup" / project / "baseline.json"


def load_namespace(repo_root: Path, project: str, namespace: str, default: Any) -> Any:
    """Load a single tier's sub-key from the shared baseline file."""
    path = baseline_path(repo_root, project)
    if not path.is_file():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get(namespace, default)
    except (json.JSONDecodeError, OSError):
        return default


def save_namespace(repo_root: Path, project: str, namespace: str, value: Any) -> None:
    """Write a single tier's sub-key, preserving other tiers' data."""
    path = baseline_path(repo_root, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
    existing[namespace] = value
    existing[f"{namespace}_captured_at"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
    )
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def current_sha(repo_root: Path) -> str:
    """Short HEAD SHA, or 'unknown' if git unavailable."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
