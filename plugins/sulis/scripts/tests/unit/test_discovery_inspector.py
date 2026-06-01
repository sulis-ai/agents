"""Contract + adapter tests for `_discovery.inspector`.

Covers the `RepoInspector` Protocol and the `LocalFilesystemInspector`
concrete adapter per TDD §Form §Ports & Adapters — Port 1 (RepoInspector)
and the corresponding canonical Detect Steps (`read-repo-root`,
`read-package-manifests`, `read-ci-workflows`, `read-repo-contract`).

Fixtures live under `tests/fixtures/discover-project/`. Each fixture is a
plain directory (no committed `.git/`). Tests that need a git-initialised
state copy the fixture to `tmp_path` and `git init` it there — this keeps
the repo free of nested git directories while preserving the on-disk
shape each Step expects.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from _discovery.inspector import (
    CiWorkflow,
    LocalFilesystemInspector,
    Manifest,
    NoRemoteError,
    NonGitDirectoryError,
    RepoContract,
    RepoInspector,
    RepoRoot,
)


_HERE = Path(__file__).resolve().parent
_FIXTURES = _HERE.parent / "fixtures" / "discover-project"


def _materialise_fixture(name: str, tmp_path: Path) -> Path:
    """Copy a static fixture tree into ``tmp_path`` and return the copy."""
    src = _FIXTURES / name
    dst = tmp_path / name
    shutil.copytree(src, dst)
    return dst


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=path,
        check=True,
        timeout=10,
    )
    # Configure a local identity so commits don't depend on global config.
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        timeout=10,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test Runner"],
        cwd=path,
        check=True,
        timeout=10,
    )
    subprocess.run(
        ["git", "add", "-A"], cwd=path, check=True, timeout=10
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=path,
        check=True,
        timeout=10,
    )


def _add_remote(path: Path, url: str = "git@github.com:acme/payments-app.git") -> None:
    subprocess.run(
        ["git", "remote", "add", "origin", url],
        cwd=path,
        check=True,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# RepoInspector contract tests
# ---------------------------------------------------------------------------


class TestReadRoot:
    def test_contract_read_root_on_git_with_remote(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-git-with-remote", tmp_path)
        _git_init(repo)
        _add_remote(repo)

        inspector = LocalFilesystemInspector()
        result = inspector.read_root(repo)

        assert isinstance(result, RepoRoot)
        assert result.is_git is True
        assert result.has_remote is True
        assert result.remote_url == "git@github.com:acme/payments-app.git"
        assert result.primary_branch == "main"
        assert result.repo_root is not None
        assert result.repo_root.resolve() == repo.resolve()

    def test_contract_read_root_raises_NonGitDirectoryError(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-not-git", tmp_path)

        inspector = LocalFilesystemInspector()
        with pytest.raises(NonGitDirectoryError):
            inspector.read_root(repo)

    def test_contract_read_root_raises_NoRemoteError(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-git-no-remote", tmp_path)
        _git_init(repo)
        # deliberately no remote configured

        inspector = LocalFilesystemInspector()
        with pytest.raises(NoRemoteError):
            inspector.read_root(repo)


class TestReadPackageManifests:
    def test_contract_read_package_manifests_finds_package_json(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-git-with-remote", tmp_path)

        inspector = LocalFilesystemInspector()
        manifests = inspector.read_package_manifests(repo)

        pkg = [m for m in manifests if m.kind == "package.json"]
        assert len(pkg) == 1
        m = pkg[0]
        assert isinstance(m, Manifest)
        assert m.name == "tiny-app"
        assert m.version == "1.2.3"
        assert m.private is False
        assert sorted(m.scripts_keys) == ["build", "test"]
        assert m.path == repo / "package.json"

    def test_contract_read_package_manifests_finds_pyproject_toml(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-git-with-remote", tmp_path)

        inspector = LocalFilesystemInspector()
        manifests = inspector.read_package_manifests(repo)

        py = [m for m in manifests if m.kind == "pyproject.toml"]
        assert len(py) == 1
        m = py[0]
        assert m.name == "tiny-py"
        assert m.version == "0.1.0"
        assert m.scripts_keys == []  # pyproject.toml has no `scripts` mapping
        assert m.path == repo / "pyproject.toml"

    def test_read_package_manifests_returns_empty_list_when_none(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-not-git", tmp_path)

        inspector = LocalFilesystemInspector()
        manifests = inspector.read_package_manifests(repo)

        assert manifests == []


class TestReadCiWorkflows:
    def test_contract_read_ci_workflows_enumerates_github_actions(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-git-with-remote", tmp_path)

        inspector = LocalFilesystemInspector()
        workflows = inspector.read_ci_workflows(repo)

        gh = [w for w in workflows if w.path.name == "release.yml"]
        assert len(gh) == 1
        w = gh[0]
        assert isinstance(w, CiWorkflow)
        assert w.name == "Release"
        assert sorted(w.triggers) == ["pull_request", "push"]

    def test_contract_read_ci_workflows_enumerates_gitlab_ci(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-git-no-remote", tmp_path)

        inspector = LocalFilesystemInspector()
        workflows = inspector.read_ci_workflows(repo)

        gl = [w for w in workflows if w.path.name == ".gitlab-ci.yml"]
        assert len(gl) == 1
        # GitLab CI's stages are the trigger surrogate for v1; `name` is None
        # because .gitlab-ci.yml has no top-level `name:` field.
        assert gl[0].name is None
        # The "triggers" list captures the stage names for GitLab; presence is
        # enough for v1.
        assert gl[0].triggers  # non-empty

    def test_read_ci_workflows_returns_empty_list_when_none(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-not-git", tmp_path)

        inspector = LocalFilesystemInspector()
        workflows = inspector.read_ci_workflows(repo)

        assert workflows == []


class TestReadRepoContract:
    def test_contract_read_repo_contract_returns_None_when_absent(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-not-git", tmp_path)

        inspector = LocalFilesystemInspector()
        result = inspector.read_repo_contract(repo)

        assert result is None

    def test_contract_read_repo_contract_parses_yaml_when_present(self, tmp_path: Path) -> None:
        repo = _materialise_fixture("tiny-git-with-remote", tmp_path)

        inspector = LocalFilesystemInspector()
        result = inspector.read_repo_contract(repo)

        assert isinstance(result, RepoContract)
        assert result.path == repo / ".sulis" / "repo-contract.yml"
        assert result.parsed["version"] == 1
        assert result.parsed["deploy"]["target"] == "vercel"
        assert result.parsed["deploy"]["env"] == "production"


# ---------------------------------------------------------------------------
# LocalFilesystemInspector adapter-specific tests
# ---------------------------------------------------------------------------


class TestLocalFilesystemInspectorAdapter:
    def test_implements_port_protocol(self) -> None:
        """`isinstance(LocalFilesystemInspector(), RepoInspector)` via
        ``@runtime_checkable``.
        """
        adapter = LocalFilesystemInspector()
        assert isinstance(adapter, RepoInspector)

    def test_git_subprocess_timeout_at_5s(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The adapter enforces a 5-second per-subprocess timeout per
        TDD §Armor §External dependencies. A chaos shim that holds the call
        open longer than the timeout MUST raise ``subprocess.TimeoutExpired``
        and not hang the test suite.
        """
        repo = _materialise_fixture("tiny-git-with-remote", tmp_path)
        _git_init(repo)
        _add_remote(repo)

        # Shorten the timeout for the test so we don't actually wait 5 seconds.
        # The contract is "subprocess calls honour a configurable timeout";
        # the timeout boundary itself is set by GIT_TIMEOUT_S — patch it for
        # this test.
        monkeypatch.setattr(LocalFilesystemInspector, "GIT_TIMEOUT_S", 0.5)

        real_run = subprocess.run

        def slow_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            # If the call has a positive timeout, honour it by sleeping past
            # the boundary. The real subprocess.run raises TimeoutExpired in
            # this case; we simulate the same shape directly to keep the
            # test independent of any shell.
            timeout = kwargs.get("timeout")
            if timeout is not None and timeout < 5:
                raise subprocess.TimeoutExpired(cmd=args[0], timeout=timeout)
            return real_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", slow_run)

        inspector = LocalFilesystemInspector()
        with pytest.raises(subprocess.TimeoutExpired):
            inspector.read_root(repo)
