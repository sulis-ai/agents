---
id: WP-003
title: Implement Detect phase — RepoInspector port + LocalFilesystemInspector adapter
status: pending
kind: backend
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-003
dependsOn: [WP-001]
blocks: [WP-008]
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: Form §Ports & Adapters — Port 1 (RepoInspector); Armor §External dependencies — git CLI
adrs: []
---

## Context

Implements the Detect phase per TDD §Form §Ports & Adapters. The
`RepoInspector` port abstracts repo reads (git remote, package
manifests, CI workflows, optional repo-contract); the
`LocalFilesystemInspector` adapter satisfies it via `subprocess` + the
local filesystem.

Per the Ports-vs-Wrappers discriminator (`references/change-primitives.md`):
the port is **domain-owned** (the discovery domain defines what "repo
inspection" means); the adapter is **Create**, not Wrap — even though
it calls out to the `git` CLI internally. The git CLI is *called by*
the adapter; the adapter is not "wrapping" git at the architecture
level.

The four Detect Steps in the canonical (`read-repo-root`,
`read-package-manifests`, `read-ci-workflows`, `read-repo-contract`)
each map to one method on the port. WP-008's skill prose calls these
methods through the composition root in `_discovery/__init__.py`.

## Contract

### Files created

```
plugins/sulis/scripts/_discovery/
└── inspector.py                    # RepoInspector port + LocalFilesystemInspector adapter + typed result dataclasses
plugins/sulis/scripts/tests/unit/
└── test_discovery_inspector.py     # contract tests + adapter tests with fixture repos
plugins/sulis/scripts/tests/fixtures/discover-project/
├── tiny-git-with-remote/           # minimal .git/ + remote (for read_root happy path)
├── tiny-git-no-remote/             # .git/ but no remote (MUC-006)
└── tiny-not-git/                   # no .git/ (MUC-001)
```

3 production files + 3 fixture directories (each containing ~3-5 tiny
files mimicking a real repo's .git/config, package.json, etc.).
Touch surface: 6 logical files + fixture data.

### Port + adapter

```python
# plugins/sulis/scripts/_discovery/inspector.py
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class RepoRoot:
    is_git: bool
    has_remote: bool
    remote_url: str | None        # e.g., "git@github.com:acme/payments-app.git"
    primary_branch: str | None    # e.g., "main"
    repo_root: Path | None        # absolute path to git rev-parse --show-toplevel result


@dataclass(frozen=True)
class Manifest:
    kind: str                     # "package.json" | "pyproject.toml" | "Cargo.toml" | ...
    path: Path
    name: str | None
    version: str | None
    private: bool | None
    scripts_keys: list[str]       # for package.json — empty list otherwise


@dataclass(frozen=True)
class CiWorkflow:
    path: Path
    name: str | None              # workflow's `name:` field if set
    triggers: list[str]           # e.g., ["push", "pull_request"]


@dataclass(frozen=True)
class RepoContract:
    path: Path
    parsed: dict                  # raw YAML → dict; minimal validation


class NonGitDirectoryError(Exception): ...   # MUC-001
class NoRemoteError(Exception): ...          # MUC-006


# canonical-source: TDD.md §Form §Ports & Adapters — Port 1 (RepoInspector)
class RepoInspector(Protocol):
    def read_root(self, path: Path) -> RepoRoot: ...
    def read_package_manifests(self, path: Path) -> list[Manifest]: ...
    def read_ci_workflows(self, path: Path) -> list[CiWorkflow]: ...
    def read_repo_contract(self, path: Path) -> RepoContract | None: ...


class LocalFilesystemInspector:
    """Concrete RepoInspector backed by subprocess + filesystem.

    Each subprocess call has a 5-second timeout (TDD §Armor §External deps).
    Non-zero git exit codes are mapped to typed errors:
      - git rev-parse --show-toplevel non-zero  → NonGitDirectoryError (MUC-001)
      - git remote get-url origin    non-zero  → NoRemoteError         (MUC-006)
    """

    GIT_TIMEOUT_S = 5

    def read_root(self, path: Path) -> RepoRoot: ...
    def read_package_manifests(self, path: Path) -> list[Manifest]: ...
    def read_ci_workflows(self, path: Path) -> list[CiWorkflow]: ...
    def read_repo_contract(self, path: Path) -> RepoContract | None: ...
```

Tool dispatch (per WP-001's `tools.jsonld`):

- `git-remote-read` (Tool ULID `01KT1WTL01GITREMOTEREAD`) → `read_root`
- `read-package-json` + `read-pyproject-toml` (Tool ULIDs `01KT1WTL02RDPKGJSON000A` + `01KT1WTL03RDPYPROJTOML`) → `read_package_manifests`
- `read-ci-workflows` (Tool ULID `01KT1WTL04RDCIWF0000A`) → `read_ci_workflows`
- `repo-contract` reuses the harness `Read` primitive (no new Tool ULID).

## Definition of Done

### Red — Failing tests written

**Contract tests (any `RepoInspector` adapter must pass these):**

- [ ] `test_discovery_inspector.py::test_contract_read_root_on_git_with_remote` — given `tiny-git-with-remote/`, returns `RepoRoot(is_git=True, has_remote=True, remote_url=<expected>, primary_branch=<expected>, repo_root=<expected>)`
- [ ] `test_discovery_inspector.py::test_contract_read_root_raises_NonGitDirectoryError` — given `tiny-not-git/`, raises `NonGitDirectoryError` (MUC-001 mapping)
- [ ] `test_discovery_inspector.py::test_contract_read_root_raises_NoRemoteError` — given `tiny-git-no-remote/`, raises `NoRemoteError` (MUC-006 mapping)
- [ ] `test_discovery_inspector.py::test_contract_read_package_manifests_finds_package_json` — given a fixture with `package.json`, returns 1 `Manifest` with `kind="package.json"` and parsed `name`/`version`/`private`/`scripts_keys`
- [ ] `test_discovery_inspector.py::test_contract_read_package_manifests_finds_pyproject_toml`
- [ ] `test_discovery_inspector.py::test_contract_read_ci_workflows_enumerates_github_actions` — given `.github/workflows/release.yml`, returns 1 `CiWorkflow` with `name` + `triggers` parsed
- [ ] `test_discovery_inspector.py::test_contract_read_ci_workflows_enumerates_gitlab_ci`
- [ ] `test_discovery_inspector.py::test_contract_read_repo_contract_returns_None_when_absent`
- [ ] `test_discovery_inspector.py::test_contract_read_repo_contract_parses_yaml_when_present`

**Adapter-specific (LocalFilesystemInspector):**

- [ ] `test_discovery_inspector.py::test_git_subprocess_timeout_at_5s` — using a chaos shim that holds the subprocess open >5s, asserts the call raises a timeout error after 5s (not after the test's overall timeout)
- [ ] `test_discovery_inspector.py::test_implements_port_protocol` — `isinstance(LocalFilesystemInspector(), RepoInspector)` via `runtime_checkable`

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/scripts/_discovery/inspector.py` authored per Contract
- [ ] Three fixture directories populated with minimal `.git/config` + `HEAD` + (for `tiny-git-with-remote`) a synthetic `remote.origin.url`
- [ ] Fixture `populated-with-manifests/` (re-used in WP-010) shares the directory layout; this WP creates the minimal subset needed for unit tests
- [ ] All 11 Red tests pass
- [ ] Coverage on `inspector.py` ≥ 90%

### Blue — Refactor complete

- [ ] subprocess invocation is wrapped in one helper (`_run_git(...)`) with consistent timeout handling — no per-method duplication
- [ ] Typed-error mapping is centralised — one `match` (or dict) translates git exit codes / stderr patterns → typed exceptions
- [ ] No mutable module-level state; the adapter is constructable + reusable across calls
- [ ] Docstrings name the canonical Step the method maps to (`# canonical:step:read-repo-root` etc.) — these annotations are exercised by WP-009's drift parser

## Sequence

- **dependsOn:** WP-001 (Tool ULIDs + JSON schemas the adapter dispatches against are authored there)
- **blocks:** WP-008 (skill prose imports `LocalFilesystemInspector` to drive Detect)
- **Parallelisable with:** WP-002, WP-004, WP-005, WP-006, WP-007, WP-009 (all unblocked once WP-001 lands; no shared file dependency)

## Estimated Token Cost

- **Input:** ~4k (TDD §Form §Ports + §Armor §External deps + WP-001's Tool schemas + MUC-001/006 system response strings for the error mapping)
- **Output:** ~4k (`inspector.py` ≈ 200 LOC + test file ≈ 180 LOC + 3 fixture dirs minimal-content)
- **Total:** ~8k

## Notes

- Each subprocess call gets a 5-second timeout per TDD §Armor §External deps. The chaos shim test (`test_git_subprocess_timeout_at_5s`) proves the timeout fires before any wrapping retry/loop logic does.
- No retries on git subprocess errors — these are deterministic local commands; failure is a real signal, not a transient. The error mapping (exit code → typed exception) is the recovery surface.
- `read_repo_contract` returns `None` when the file is absent, raising no error — the canonical Step's `agent_instructions` says "read if present" (TDD §Form §Ports — Port 1).
- The fixture directories are shared with WP-010 (E2E tests) — WP-010 may add more fixtures but doesn't modify the ones authored here. Per-WP fixture ownership recorded in WP-010 to avoid peer-collision.
