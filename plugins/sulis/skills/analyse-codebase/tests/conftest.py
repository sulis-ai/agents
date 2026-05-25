"""
Test configuration for /sulis:analyse-codebase.

- Adds the probe package to sys.path so tests can import it.
- Gates integration tests on tool availability (skip-not-install).
- Provides fixture factory helpers.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent / "scripts"

# Make the probe package importable
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ─── Tool availability ────────────────────────────────────────────────────


def _is_available(tool: str) -> bool:
    return shutil.which(tool) is not None


@pytest.fixture(scope="session")
def has_astgrep() -> bool:
    return _is_available("ast-grep")


@pytest.fixture(scope="session")
def has_lizard() -> bool:
    if not _is_available("lizard"):
        return False
    # Sanity: make sure it's the McCabe lizard, not the compression utility
    try:
        r = subprocess.run(
            ["lizard", "--help"], capture_output=True, timeout=5, check=False, text=True
        )
        return "cyclomatic complexity" in (r.stdout + r.stderr).lower()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="session")
def has_scc() -> bool:
    return _is_available("scc")


@pytest.fixture(scope="session")
def has_git() -> bool:
    return _is_available("git")


@pytest.fixture
def integration_tools(has_astgrep, has_lizard, has_scc, has_git):
    """Skip the test if any required tool is missing.

    Use as a fixture parameter for any test that calls real tool binaries.
    """
    missing = []
    if not has_astgrep: missing.append("ast-grep")
    if not has_lizard: missing.append("lizard")
    if not has_scc: missing.append("scc")
    if not has_git: missing.append("git")
    if missing:
        pytest.skip(
            f"Required tools missing: {', '.join(missing)}. "
            f"Run plugins/sulis/skills/analyse-codebase/scripts/install-probe-tools.sh."
        )
    return True


# ─── Fixture path resolver ────────────────────────────────────────────────


FIXTURES_DIR = _HERE / "fixtures"


@pytest.fixture(scope="session")
def fixtures_root() -> Path:
    """Absolute path to the fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def make_workspace(tmp_path: Path):
    """
    Factory: copy a fixture into tmp_path, optionally as a git repo.

    Returns a Path to the copied workspace.
    """
    def _make(fixture_name: str, as_git_repo: bool = True) -> Path:
        src = FIXTURES_DIR / fixture_name
        if not src.exists():
            pytest.skip(f"Fixture {fixture_name} not found at {src}")
        dst = tmp_path / fixture_name
        shutil.copytree(src, dst)
        if as_git_repo:
            subprocess.run(["git", "init", "-q"], cwd=dst, check=True)
            subprocess.run(["git", "add", "."], cwd=dst, check=True)
            # Allow empty for fixtures with no files (e.g. empty/)
            subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=Test",
                 "commit", "-q", "--allow-empty", "-m", "initial"],
                cwd=dst, check=True,
            )
        return dst
    return _make
