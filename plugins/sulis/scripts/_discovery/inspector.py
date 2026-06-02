"""`RepoInspector` port + `LocalFilesystemInspector` adapter.

Implements the Detect phase per
``# canonical-source: TDD.md§Form §Ports & Adapters — Port 1 (RepoInspector)``.

The four Detect Steps map to the four port methods:

- ``# canonical:step:read-repo-root`` (Step ULID ``dna:step:01KT1WDSST01RDREP0R00T000A``)
  → :meth:`RepoInspector.read_root`
- ``# canonical:step:read-package-manifests`` (Step ULID
  ``dna:step:01KT1WDSST02RDPKGMAN1FEST0``) → :meth:`RepoInspector.read_package_manifests`
- ``# canonical:step:read-ci-workflows`` (Step ULID
  ``dna:step:01KT1WDSST03RDC1W0RKF10W00``) → :meth:`RepoInspector.read_ci_workflows`
- ``# canonical:step:read-repo-contract`` (Step ULID
  ``dna:step:01KT1WDSST04RDREP0C0NTR00A``) → :meth:`RepoInspector.read_repo_contract`

The adapter resolves repo state by shelling out to ``git`` (subprocess with
a 5-second timeout per TDD §Armor §External dependencies) for the
git-aware operations, and by direct filesystem reads for the manifest /
CI / repo-contract files.

Failure mapping:

- ``git rev-parse --show-toplevel`` non-zero → :class:`NonGitDirectoryError`
  (MUC-001 ``non-git-directory``,
  FailureMode ULID ``dna:failuremode:01KT1WFM01N0NG1TD1R000000A``).
- ``git remote get-url origin`` non-zero on a known-git directory →
  :class:`NoRemoteError` (MUC-006 ``git-no-remote``,
  FailureMode ULID ``dna:failuremode:01KT1WFM06G1TN0REM0TE00000``).

No retries — these are deterministic local commands; failure is a real
signal.
"""

from __future__ import annotations

import json
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

import yaml


# ---------------------------------------------------------------------------
# Typed result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RepoRoot:
    """Result of :meth:`RepoInspector.read_root`."""

    is_git: bool
    has_remote: bool
    remote_url: str | None
    primary_branch: str | None
    repo_root: Path | None


@dataclass(frozen=True)
class Manifest:
    """Result row from :meth:`RepoInspector.read_package_manifests`."""

    kind: str  # "package.json" | "pyproject.toml" | ...
    path: Path
    name: str | None
    version: str | None
    private: bool | None
    scripts_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CiWorkflow:
    """Result row from :meth:`RepoInspector.read_ci_workflows`."""

    path: Path
    name: str | None
    triggers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepoContract:
    """Result of :meth:`RepoInspector.read_repo_contract` when a contract
    file is present at ``.sulis/repo-contract.yml``."""

    path: Path
    parsed: dict


# ---------------------------------------------------------------------------
# Typed errors (MUC mapping)
# ---------------------------------------------------------------------------


class NonGitDirectoryError(Exception):
    """``git rev-parse --show-toplevel`` returned non-zero.

    Maps to MUC-001 (``non-git-directory``,
    FailureMode ULID ``dna:failuremode:01KT1WFM01N0NG1TD1R000000A``).
    """


class NoRemoteError(Exception):
    """``git remote get-url origin`` returned non-zero on a known-git dir.

    Maps to MUC-006 (``git-no-remote``,
    FailureMode ULID ``dna:failuremode:01KT1WFM06G1TN0REM0TE00000``).
    """


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------


@runtime_checkable
class RepoInspector(Protocol):
    """The repo-inspection seam the Detect phase consumes.

    Defined in the discovery domain (the marketplace owns what "repo
    inspection" means in this Workflow); satisfied by concrete adapters
    backed by the local filesystem, an in-memory mock, or — in the
    future — a remote repo browser API.
    """

    def read_root(self, path: Path) -> RepoRoot: ...

    def read_package_manifests(self, path: Path) -> list[Manifest]: ...

    def read_ci_workflows(self, path: Path) -> list[CiWorkflow]: ...

    def read_repo_contract(self, path: Path) -> RepoContract | None: ...


# ---------------------------------------------------------------------------
# Adapter — LocalFilesystemInspector
# ---------------------------------------------------------------------------


_REPO_CONTRACT_RELPATH: Final[tuple[str, ...]] = (".sulis", "repo-contract.yml")


class LocalFilesystemInspector:
    """Concrete :class:`RepoInspector` backed by subprocess + filesystem.

    Each ``git`` subprocess call has a configurable timeout (default 5 s
    per TDD §Armor §External dependencies). Non-zero exit codes are mapped
    to typed errors per the module docstring.
    """

    #: Per-subprocess timeout in seconds. Patchable for chaos tests.
    GIT_TIMEOUT_S: float = 5.0

    # ------------------------------------------------------------------
    # canonical:step:read-repo-root
    # ------------------------------------------------------------------
    def read_root(self, path: Path) -> RepoRoot:
        """Read git remote, primary branch, and repo root.

        Raises:
            NonGitDirectoryError: when ``git rev-parse --show-toplevel``
                returns non-zero (MUC-001).
            NoRemoteError: when the directory is a git repo but
                ``git remote get-url origin`` returns non-zero (MUC-006).
        """
        toplevel = self._run_git(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            on_failure=NonGitDirectoryError(
                f"{path} is not inside a git working tree"
            ),
        )
        repo_root = Path(toplevel.strip())

        # Repo DEFAULT branch (not the checked-out branch). A mint run from a
        # feature branch must record the repo default (e.g. "main"), not the
        # transient checkout — recording the feature branch was the bug this
        # WP fixes. Standard resolution per CP (the established mechanism, not a
        # bespoke heuristic):
        #   git symbolic-ref refs/remotes/origin/HEAD  ->  "refs/remotes/origin/main"
        # Strip the "refs/remotes/origin/" prefix to get the bare branch name.
        # Best-effort (``on_failure=None``): origin/HEAD is unset when the
        # remote was never fetched or ``git remote set-head`` never ran — fall
        # back to "main" in that case.
        primary_branch: str | None = self._default_branch(path)

        remote_url = self._run_git(
            ["git", "remote", "get-url", "origin"],
            cwd=path,
            on_failure=NoRemoteError(
                f"git remote 'origin' is not configured in {repo_root}"
            ),
        ).strip()

        return RepoRoot(
            is_git=True,
            has_remote=True,
            remote_url=remote_url,
            primary_branch=primary_branch,
            repo_root=repo_root,
        )

    # ------------------------------------------------------------------
    # canonical:step:read-package-manifests
    # ------------------------------------------------------------------
    def read_package_manifests(self, path: Path) -> list[Manifest]:
        """Enumerate package manifests at the repo root.

        v1 scope: ``package.json`` (Node), ``pyproject.toml`` (Python).
        Other ecosystems (Cargo, go.mod, Gemfile, ...) are deferred.
        """
        manifests: list[Manifest] = []

        pkg_json = path / "package.json"
        if pkg_json.is_file():
            manifests.append(_parse_package_json(pkg_json))

        pyproject = path / "pyproject.toml"
        if pyproject.is_file():
            manifests.append(_parse_pyproject_toml(pyproject))

        return manifests

    # ------------------------------------------------------------------
    # canonical:step:read-ci-workflows
    # ------------------------------------------------------------------
    def read_ci_workflows(self, path: Path) -> list[CiWorkflow]:
        """Enumerate CI workflows under common locations.

        v1 scope: ``.github/workflows/*.yml``/``*.yaml`` and
        ``.gitlab-ci.yml``. Other providers (CircleCI, Buildkite,
        Jenkinsfile) are deferred.
        """
        workflows: list[CiWorkflow] = []

        gh_dir = path / ".github" / "workflows"
        if gh_dir.is_dir():
            for ext in ("*.yml", "*.yaml"):
                for wf_path in sorted(gh_dir.glob(ext)):
                    workflows.append(_parse_github_workflow(wf_path))

        gitlab = path / ".gitlab-ci.yml"
        if gitlab.is_file():
            workflows.append(_parse_gitlab_ci(gitlab))

        return workflows

    # ------------------------------------------------------------------
    # canonical:step:read-repo-contract
    # ------------------------------------------------------------------
    def read_repo_contract(self, path: Path) -> RepoContract | None:
        """Read ``.sulis/repo-contract.yml`` if present; ``None`` otherwise."""
        contract_path = path.joinpath(*_REPO_CONTRACT_RELPATH)
        if not contract_path.is_file():
            return None
        parsed = yaml.safe_load(contract_path.read_text()) or {}
        if not isinstance(parsed, dict):
            # The repo-contract schema is an object; anything else is
            # malformed and we treat it as absent for the Detect phase's
            # purposes (Mint will re-validate when it tries to use it).
            return None
        return RepoContract(path=contract_path, parsed=parsed)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    #: Prefix on ``git symbolic-ref refs/remotes/origin/HEAD`` output.
    _ORIGIN_HEAD_PREFIX: Final[str] = "refs/remotes/origin/"

    #: Fallback branch when the repo default can't be determined.
    _DEFAULT_BRANCH_FALLBACK: Final[str] = "main"

    def _default_branch(self, path: Path) -> str:
        """Resolve the repo's default branch via ``origin/HEAD``.

        Returns the bare branch name (e.g. ``"main"``). Falls back to
        :attr:`_DEFAULT_BRANCH_FALLBACK` when ``origin/HEAD`` is unset or the
        git call fails — both non-fatal (best-effort resolution).
        """
        try:
            ref = self._run_git(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=path,
                on_failure=None,
            ).strip()
        except subprocess.CalledProcessError:
            return self._DEFAULT_BRANCH_FALLBACK
        if ref.startswith(self._ORIGIN_HEAD_PREFIX):
            branch = ref[len(self._ORIGIN_HEAD_PREFIX) :]
            if branch:
                return branch
        return self._DEFAULT_BRANCH_FALLBACK

    def _run_git(
        self,
        argv: list[str],
        *,
        cwd: Path,
        on_failure: Exception | None,
    ) -> str:
        """Run a git subprocess with the standard timeout + error mapping.

        ``on_failure`` is the typed exception to raise when ``git`` exits
        non-zero. When ``None``, the underlying
        :class:`subprocess.CalledProcessError` is re-raised (lets callers
        treat the failure as "best-effort, ignore me").
        """
        try:
            result = subprocess.run(
                argv,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.GIT_TIMEOUT_S,
            )
        except subprocess.CalledProcessError:
            if on_failure is not None:
                raise on_failure from None
            raise
        return result.stdout


# ---------------------------------------------------------------------------
# Parsing helpers (module-level — small and individually testable)
# ---------------------------------------------------------------------------


def _parse_package_json(path: Path) -> Manifest:
    data = json.loads(path.read_text())
    scripts = data.get("scripts") or {}
    return Manifest(
        kind="package.json",
        path=path,
        name=data.get("name"),
        version=data.get("version"),
        private=data.get("private"),
        scripts_keys=sorted(scripts.keys()) if isinstance(scripts, dict) else [],
    )


def _parse_pyproject_toml(path: Path) -> Manifest:
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    project = data.get("project") or {}
    return Manifest(
        kind="pyproject.toml",
        path=path,
        name=project.get("name"),
        version=project.get("version"),
        # pyproject.toml has no canonical `private` field; left as None.
        private=None,
        scripts_keys=[],
    )


def _parse_github_workflow(path: Path) -> CiWorkflow:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        return CiWorkflow(path=path, name=None, triggers=[])
    name = data.get("name")
    on = data.get("on") or data.get(True)  # PyYAML coerces bare `on:` to True
    triggers = _normalise_triggers(on)
    return CiWorkflow(path=path, name=name if isinstance(name, str) else None, triggers=triggers)


def _parse_gitlab_ci(path: Path) -> CiWorkflow:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        return CiWorkflow(path=path, name=None, triggers=[])
    # GitLab CI has no top-level `name`; use stage names as the trigger
    # surrogate for v1 (good enough for the Detect phase's purposes —
    # the Infer phase reads richer fields).
    name = data.get("name") if isinstance(data.get("name"), str) else None
    stages = data.get("stages") or []
    if isinstance(stages, list):
        triggers = [str(s) for s in stages]
    else:
        triggers = []
    return CiWorkflow(path=path, name=name, triggers=triggers)


def _normalise_triggers(on: object) -> list[str]:
    """Normalise the ``on:`` field of a GitHub Actions workflow to a flat
    list of trigger names.
    """
    if isinstance(on, str):
        return [on]
    if isinstance(on, list):
        return [str(item) for item in on if isinstance(item, str)]
    if isinstance(on, dict):
        return sorted(str(k) for k in on.keys())
    return []
