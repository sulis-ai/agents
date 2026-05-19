"""
Test configuration for sulis-execution's wpx-* CLI tools.

- Adds the scripts directory to sys.path so unit tests can import _wpxlib.
- Provides shared fixtures: tmp_project, run_tool, mock_gh, local_git_repo.
- Provides helpers for seeding INDEX.md, WP files, journals from fixtures.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent
_FIXTURES_DIR = _HERE / "fixtures"

# Make _wpxlib importable for unit tests
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ─── Project path helpers ─────────────────────────────────────────────────


@dataclass
class ProjectPaths:
    """Convenience handle for a tmp test project's layout."""

    repo_root: Path
    project: str

    @property
    def arch_root(self) -> Path:
        return self.repo_root / ".architecture" / self.project

    @property
    def wp_dir(self) -> Path:
        return self.arch_root / "work-packages"

    @property
    def index_md(self) -> Path:
        return self.wp_dir / "INDEX.md"

    @property
    def security_dir(self) -> Path:
        return self.repo_root / ".security" / self.project

    @property
    def findings_dir(self) -> Path:
        return self.security_dir / "findings"

    @property
    def findings_register(self) -> Path:
        return self.security_dir / "findings-register.md"

    def journal(self, wp: str) -> Path:
        return self.wp_dir / f".executor-{wp}.md"

    def blocker(self, wp: str) -> Path:
        return self.wp_dir / f"BLOCKER-{wp}.md"


@pytest.fixture
def scripts_dir() -> Path:
    """Absolute path to the wpx-* scripts directory."""
    return _SCRIPTS_DIR


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to the tests/fixtures/ directory."""
    return _FIXTURES_DIR


@pytest.fixture
def tmp_project(tmp_path) -> ProjectPaths:
    """Create a tmp project with .architecture/<slug>/work-packages/ etc."""
    project = "test-project"
    paths = ProjectPaths(repo_root=tmp_path, project=project)
    paths.wp_dir.mkdir(parents=True, exist_ok=True)
    paths.findings_dir.mkdir(parents=True, exist_ok=True)
    return paths


def _copy_fixture(name: str, dest: Path) -> Path:
    """Copy a fixture file into the destination path."""
    src = _FIXTURES_DIR / name
    if not src.exists():
        raise FileNotFoundError(f"Fixture not found: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest)
    return dest


@pytest.fixture
def seed_index(tmp_project):
    """Returns a function that copies a fixture INDEX.md into the project."""
    def _seed(fixture_name: str) -> Path:
        return _copy_fixture(fixture_name, tmp_project.index_md)
    return _seed


@pytest.fixture
def seed_wp(tmp_project):
    """Returns a function that copies a fixture WP file into the project."""
    def _seed(fixture_name: str, wp_id: str = None, slug: str = "test") -> Path:
        wp_id = wp_id or fixture_name.split("-template")[0]
        dest_name = f"{wp_id}-{slug}.md"
        return _copy_fixture(fixture_name, tmp_project.wp_dir / dest_name)
    return _seed


# ─── Tool invocation ──────────────────────────────────────────────────────


@dataclass
class ToolResult:
    """The result of invoking a wpx-* tool via subprocess."""

    returncode: int
    stdout: str
    stderr: str
    json: dict | None  # parsed stdout if it's valid JSON, else None

    @property
    def ok(self) -> bool:
        return self.json is not None and self.json.get("ok") is True

    @property
    def error(self) -> str | None:
        return self.json.get("error") if self.json else None

    @property
    def data(self) -> dict:
        return self.json.get("data", {}) if self.json else {}


def _run_tool_impl(scripts_dir: Path, tool: str, *args, env: dict | None = None) -> ToolResult:
    cmd = [str(scripts_dir / tool), *args]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
        timeout=60,
    )
    parsed = None
    try:
        parsed = json.loads(proc.stdout.strip()) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        parsed = None
    return ToolResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        json=parsed,
    )


@pytest.fixture
def run_tool(scripts_dir):
    """Returns a function that invokes a wpx-* tool via subprocess.

    Usage:
        result = run_tool("wpx-journal", "init", "--wp", "WP-001",
                          "--project", "x", "--repo-root", str(tmp_path))
        assert result.ok
        assert result.data["wp"] == "WP-001"
    """
    def _run(tool: str, *args, env: dict | None = None) -> ToolResult:
        return _run_tool_impl(scripts_dir, tool, *args, env=env)
    return _run


# ─── mock_gh: fake gh binary on PATH ──────────────────────────────────────


_GH_STUB_TEMPLATE = """#!/usr/bin/env bash
# Fake gh binary for tests. Dispatches based on argv against a JSON
# response map stored at $GH_MOCK_CONFIG.
set -e
if [ -z "${GH_MOCK_CONFIG:-}" ]; then
  echo "gh mock: GH_MOCK_CONFIG env var not set" >&2
  exit 2
fi
ARGS="$*"
python3 - "$ARGS" <<'PYEOF'
import json, os, sys, re
args = sys.argv[1]
config_path = os.environ["GH_MOCK_CONFIG"]
with open(config_path) as f:
    config = json.load(f)

# Find the first response whose 'match' pattern is a substring of args.
# Responses can also explicitly set 'exit_code' (default 0) and 'stderr'.
for entry in config.get("responses", []):
    match = entry.get("match", "")
    if not match or match in args:
        if entry.get("stdout"):
            print(entry["stdout"], end="")
        if entry.get("stderr"):
            print(entry["stderr"], end="", file=sys.stderr)
        sys.exit(entry.get("exit_code", 0))

# Fallthrough: unmatched gh call. Default to error.
print(f"gh mock: no matching response for args: {args}", file=sys.stderr)
sys.exit(1)
PYEOF
"""


@pytest.fixture
def mock_gh(tmp_path, monkeypatch):
    """Installs a fake `gh` binary at the front of PATH.

    Usage:
        mock_gh([
            {"match": "compare", "stdout": '{"status": "identical"}'},
            {"match": "merges", "stdout": '{"sha": "deadbeef"}'},
        ])

    The fixture returns a function. Each call ADDS or REPLACES the gh
    mock config. The fake gh dispatches based on substring match of the
    arguments string.
    """
    gh_dir = tmp_path / "_mock_bin"
    gh_dir.mkdir(parents=True, exist_ok=True)
    gh_path = gh_dir / "gh"
    gh_path.write_text(_GH_STUB_TEMPLATE)
    gh_path.chmod(gh_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    config_path = tmp_path / "_gh_mock_config.json"

    monkeypatch.setenv("PATH", f"{gh_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("GH_MOCK_CONFIG", str(config_path))

    def _configure(responses: list[dict]) -> None:
        config_path.write_text(json.dumps({"responses": responses}))

    # Default: no responses configured (any gh call errors)
    _configure([])
    return _configure


# ─── mock_curl: fake curl binary on PATH (for _poll_health tests) ────────


_CURL_STUB_TEMPLATE = """#!/usr/bin/env bash
# Fake curl binary for tests. Inspects the URL argument and returns
# a canned HTTP status code per a JSON config at $CURL_MOCK_CONFIG.
set -e
if [ -z "${CURL_MOCK_CONFIG:-}" ]; then
  echo "curl mock: CURL_MOCK_CONFIG env var not set" >&2
  exit 2
fi
ARGS="$*"
python3 - "$ARGS" <<'PYEOF'
import json, os, sys
args = sys.argv[1]
config_path = os.environ["CURL_MOCK_CONFIG"]
with open(config_path) as f:
    config = json.load(f)

# Find the response whose 'url_substring' is in args.
for entry in config.get("responses", []):
    needle = entry.get("url_substring", "")
    if not needle or needle in args:
        # Print the status code on stdout (mimics curl -w "%{http_code}").
        status = str(entry.get("status", "200"))
        print(status, end="")
        # `curl -sf` returns 22 (HTTP error) on 4xx/5xx; replicate.
        if entry.get("status", 200) >= 400 and "-f" in args.split():
            sys.exit(22)
        sys.exit(0)

# Fallthrough: 404 + non-zero exit (matches curl -sf semantics)
print("404", end="")
sys.exit(22)
PYEOF
"""


@pytest.fixture
def mock_curl(tmp_path, monkeypatch):
    """Installs a fake `curl` binary at the front of PATH.

    Usage:
        mock_curl([
            {"url_substring": "/health", "status": 200},
            {"url_substring": "",        "status": 404},  # fallback
        ])

    Each response matches by URL substring; the first match wins.
    `curl -sf` semantics replicated: 4xx returns exit 22 with the
    status code printed on stdout (which the wpx-pipeline parser
    reads via the `-w "%{http_code}"` flag).
    """
    curl_dir = tmp_path / "_mock_curl_bin"
    curl_dir.mkdir(parents=True, exist_ok=True)
    curl_path = curl_dir / "curl"
    curl_path.write_text(_CURL_STUB_TEMPLATE)
    curl_path.chmod(curl_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    config_path = tmp_path / "_curl_mock_config.json"

    # Prepend to PATH; preserve any prior PATH manipulation from mock_gh
    current_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{curl_dir}:{current_path}")
    monkeypatch.setenv("CURL_MOCK_CONFIG", str(config_path))

    def _configure(responses: list[dict]) -> None:
        config_path.write_text(json.dumps({"responses": responses}))

    _configure([])
    return _configure


# ─── local_git_repo: real local git for git operations ────────────────────


@pytest.fixture
def local_git_repo(tmp_path):
    """Initialise a real local git repo with a dev branch + initial commit.

    Returns the repo path. Tests that exercise git operations (wpx-worktree,
    rebase logic) use this fixture instead of mocking git — git is fast
    and deterministic enough to use directly.
    """
    repo = tmp_path / "_local_repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "dev"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True,
    )
    (repo / "README.md").write_text("# test repo\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"],
        cwd=repo, check=True,
    )
    # Set up a "remote" by adding a second clone as origin
    remote = tmp_path / "_origin.git"
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(repo), str(remote)],
        check=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote)],
        cwd=repo, check=True,
    )
    subprocess.run(
        ["git", "push", "-q", "-u", "origin", "dev"],
        cwd=repo, check=True,
    )
    return repo


# ─── Tool availability gates ──────────────────────────────────────────────


@pytest.fixture(scope="session")
def has_git() -> bool:
    return shutil.which("git") is not None


@pytest.fixture
def requires_git(has_git):
    if not has_git:
        pytest.skip("git binary not available")
    return True
