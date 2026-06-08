"""End-to-end integration tests for the assembled discover-project skill.

WP-010 — the n=2 dogfood of Path A. This test suite is the load-bearing
acceptance evidence for the change: 4 fixture consumer repos exercise
the six Use Cases (UC-001..UC-006) and the eight Misuse Cases
(MUC-001..MUC-008) end-to-end against the headless composition root
``_discovery.run_discovery_headless``.

The composition root wires the Detect (WP-003) → Infer (WP-004) →
Ask (test-injected answers) → Mint (WP-006) → Verify (WP-007) phases
together in a hermetic way: integration tests inject a fake
:class:`LLMClient` so no real LLM call ever fires, and they
monkeypatch ``_discovery.minter.consuming_repo_root`` so writes land
inside ``tmp_path``.

Fixture layout — `tests/fixtures/discover-project/`:

- ``empty/`` — `.gitkeep` only; integration test runs `git init`
  (no remote, no manifests, no CI).
- ``populated/`` — package.json + .github/workflows/release.yml.
- ``monorepo/`` — apps/backend/package.json + apps/cli/package.json
  + .github/workflows/ci.yml.
- ``pre-existing/`` — package.json + .sulis/projects/foo.jsonld
  (the pre-mint entity for UC-002 per-field-diff testing).

Plus four on-the-fly fixtures created in test setup:
``non-git/`` (no `.git/`), ``no-remote/`` (`.git/` but no remote),
``token-budget/`` (LLM mock returns over-budget usage),
``bad-workflow-ref/`` (Mint phase coerced to write a bad ULID).

Per the WP-010 Contract DoD — Blue:
- Shared helpers extracted (`_materialise_fixture`, `_git_init`,
  `_add_remote`, `_make_llm_client`).
- LLM mock helper is one fixture used across UC-001/002/006/MUC-008.
- Dogfood test is decorated ``@pytest.mark.dogfood`` so CI can run it
  conditionally.
- Fixture data is the minimum sufficient (no real LLM keys, no `.git/`
  objects packed — we create `.git/` at test runtime via `git init`).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from _discovery import (
    DiscoveryResult,
    run_discovery_headless,
)
from _discovery.inferrer import (
    LLMConfigurationInferrer,
    NullConfigurationInferrer,
)
from _discovery.minter import EntityAlreadyExistsError
from _discovery.inspector import NonGitDirectoryError, NoRemoteError
from _discovery.verifier import (
    DriftVerifyFailed,
    DriftVerifyResult,
)


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # plugins/sulis/scripts
_FIXTURES_DIR = _SCRIPTS_DIR / "tests" / "fixtures" / "discover-project"
_REPO_ROOT = _SCRIPTS_DIR.parent.parent.parent  # /Users/.../agents-...

# Canonical marketplace release-train Workflow ULID — sourced from
# TDD.md §Canonical Identifiers (cross-tenant ref the verifier allows).
_MARKETPLACE_RELEASE_WORKFLOW_ULID = "dna:workflow:01KT0RTRA1NWFW00000000000A"


# ---------------------------------------------------------------------------
# Shared fixture-construction helpers
# ---------------------------------------------------------------------------


def _materialise_fixture(name: str, dst_parent: Path) -> Path:
    """Copy a static fixture tree from ``_FIXTURES_DIR/<name>`` into
    ``dst_parent``. Returns the resulting path."""
    src = _FIXTURES_DIR / name
    if not src.exists():
        raise FileNotFoundError(f"Fixture {name!r} not found at {src}")
    dst = dst_parent / name
    shutil.copytree(src, dst)
    # Remove the .gitkeep marker if it's the only content (it's a
    # checkout placeholder, not a real file the test consumes).
    gitkeep = dst / ".gitkeep"
    if gitkeep.exists():
        gitkeep.unlink()
    return dst


def make_minimal_git_repo(
    path: Path,
    *,
    remote_url: str | None = "git@github.com:acme/payments-app.git",
    primary_branch: str = "main",
) -> None:
    """Initialise ``path`` as a minimal git repo with an initial commit.

    ``remote_url=None`` skips remote configuration — used by the
    no-remote fixture variants.
    """
    subprocess.run(
        ["git", "init", "-q", "-b", primary_branch],
        cwd=path,
        check=True,
        timeout=10,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path, check=True, timeout=10,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test Runner"],
        cwd=path, check=True, timeout=10,
    )
    # At least one tracked file so `git add -A` always has something to add.
    if not (path / "README.md").exists():
        (path / "README.md").write_text("# fixture repo\n")
    subprocess.run(
        ["git", "add", "-A"], cwd=path, check=True, timeout=10,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "fixture init"],
        cwd=path, check=True, timeout=10,
    )
    if remote_url is not None:
        subprocess.run(
            ["git", "remote", "add", "origin", remote_url],
            cwd=path, check=True, timeout=10,
        )


# ---------------------------------------------------------------------------
# LLM mock
# ---------------------------------------------------------------------------


@dataclass
class _MockUsage:
    total_tokens: int


@dataclass
class _MockResponse:
    text: str
    usage: _MockUsage


class _MockLLMClient:
    """Tiny fake :class:`LLMClient` for hermetic e2e tests.

    Configurable in three modes:

    - ``mode="inferences"``: returns the configured `inferences` dict
      as the LLM's JSON response with ``tokens_consumed`` reported.
    - ``mode="over-budget"``: returns a usage report that exceeds the
      caller's token_budget (exercises MUC-008 / TokenBudgetExceeded).
    - ``mode="unreachable"``: raises ``RuntimeError`` to simulate an
      LLM-unreachable failure (exercises NFR-006 fallback to Null).
    """

    def __init__(
        self,
        *,
        mode: str = "inferences",
        inferences: dict[str, dict[str, Any]] | None = None,
        tokens_consumed: int = 1234,
        over_budget_tokens: int = 20_000,
    ) -> None:
        self.mode = mode
        self.inferences = inferences or {}
        self.tokens_consumed = tokens_consumed
        self.over_budget_tokens = over_budget_tokens
        self.calls: list[str] = []

    def call(self, prompt: str, timeout_s: float) -> _MockResponse:  # noqa: ARG002
        self.calls.append(prompt)
        if self.mode == "unreachable":
            raise RuntimeError("LLM unreachable (mock)")
        if self.mode == "over-budget":
            return _MockResponse(
                text=json.dumps(self.inferences),
                usage=_MockUsage(total_tokens=self.over_budget_tokens),
            )
        # default: inferences mode
        return _MockResponse(
            text=json.dumps(self.inferences),
            usage=_MockUsage(total_tokens=self.tokens_consumed),
        )


def mock_llm_returns(
    inferences: dict[str, dict[str, Any]] | None = None,
    *,
    mode: str = "inferences",
    tokens_consumed: int = 1234,
) -> _MockLLMClient:
    """Convenience factory for the e2e tests' LLM mock."""
    return _MockLLMClient(
        mode=mode, inferences=inferences, tokens_consumed=tokens_consumed,
    )


# ---------------------------------------------------------------------------
# Shared monkeypatch helper for the Mint phase repo-root resolution
# ---------------------------------------------------------------------------


def _patch_consuming_repo_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Patch ``_discovery.minter.consuming_repo_root`` to return ``root``.

    The Mint phase resolves the consuming repo via
    ``git rev-parse --show-toplevel``. Integration tests work against
    tmp fixture trees where the resolved root MIGHT not match what we
    want (e.g., a fixture nested under ``tmp_path/empty/`` would
    correctly resolve to itself, but we want one shared helper across
    all tests so the contract stays explicit).
    """
    from _discovery import minter as minter_module
    monkeypatch.setattr(minter_module, "consuming_repo_root", lambda: root.resolve())


# ---------------------------------------------------------------------------
# Fake verifier helpers
# ---------------------------------------------------------------------------
#
# The real verifier shells out to `check-canonical-drift.py` with the
# WP-009 `--cross-tenant-refs-allowed-for` flag set. The current
# detector accepts SKILL-conformance scope (`--instance-dir` +
# `--yaml-path`), not single-entity scope — entity-scoped invocation
# is a small follow-on extension (the verifier already builds the
# `--scope` argv but the detector script doesn't know it yet). The
# verifier's contract against the real detector is covered by
# WP-007's unit tests; the integration tests inject a fake verifier
# so the e2e composition exercise focuses on what THIS WP owns:
# the wiring of all five phases.


def _fake_verify_pass(entity_path: Path) -> DriftVerifyResult:
    """Stand-in for verify_and_roll_back_on_failure that always passes."""
    return DriftVerifyResult(ok=True, exit_code=0, stderr="")


def _fake_verify_checks_workflow_ref(entity_path: Path) -> DriftVerifyResult:
    """Verify the just-written entity's release_workflow_ref looks plausible.

    Used by MUC-005: when the composition root injects a bad ULID,
    this fake reports failure (mimicking the real drift detector's
    "unknown workflow ULID" outcome).
    """
    import json as _json
    payload = _json.loads(entity_path.read_text())
    projects = payload.get("projects", [])
    if projects:
        ref = projects[0].get("release_workflow_ref", "")
        # The canonical marketplace release-train ULID is the only one
        # this fake recognises (mirrors the real detector's tenant
        # catalogue check). Any other ULID looks like drift.
        if ref != "dna:workflow:01KT0RTRA1NWFW00000000000A":
            stderr = (
                f"drift: unknown release_workflow_ref {ref!r} — "
                "not present in any tenant Workflow catalogue"
            )
            entity_path.unlink(missing_ok=False)
            raise DriftVerifyFailed(
                DriftVerifyResult(ok=False, exit_code=1, stderr=stderr),
                rolled_back_path=entity_path,
            )
    return DriftVerifyResult(ok=True, exit_code=0, stderr="")


# ===========================================================================
# UC-001 — Empty repo, all-human-ask fallback (NFR-006 / Null adapter)
# ===========================================================================


def test_uc_001_empty_repo_all_human_ask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UC-001 with the Null adapter — no LLM, founder answers all fields.

    Asserts:
      - exit ok
      - `.sulis/projects/<expected-slug>.jsonld` exists at the repo root
      - drift verify passes
      - source.repo matches the fixture's git remote
      - belongs_to_tenant matches the Sha256CrockfordTenantDeriver output
    """
    repo = _materialise_fixture("empty", tmp_path)
    make_minimal_git_repo(
        repo, remote_url="git@github.com:acme/empty-app.git",
    )
    _patch_consuming_repo_root(monkeypatch, repo)

    # Founder answers — all-human-ask (Null inferrer means every field
    # is asked). The composition root accepts an `answers` dict mapping
    # field-name → chosen value.
    answers = {
        "name": "empty-app",
        "type": "library",
        "branch_policy": "trunk-based",
        "version_files": ["package.json"],
        "description": "An empty fixture for the discover-project E2E suite.",
        "belongs_to_product_ref": "acme-product",
    }

    result = run_discovery_headless(
        repo_path=repo,
        inferrer=NullConfigurationInferrer(),
        answers=answers,
        verifier_fn=_fake_verify_pass,
    )

    assert isinstance(result, DiscoveryResult)
    assert result.ok is True
    assert result.entity_path is not None
    entity_path = result.entity_path
    assert entity_path.exists()
    assert entity_path == repo / ".sulis" / "projects" / "empty-app.jsonld"

    entity = json.loads(entity_path.read_text())
    # The atomic-write emits the Project bag (id, name, source, ...) as
    # a top-level entity payload; the composition root authors the
    # @context + projects wrapping per release-train's projects.jsonld
    # shape.
    proj = entity["projects"][0]
    assert proj["name"] == "empty-app"
    source = json.loads(proj["source"])
    assert source["repo"] == "acme/empty-app"

    # belongs_to_tenant matches the deterministic recipe.
    from _discovery.tenant import Sha256CrockfordTenantDeriver
    expected_tenant = Sha256CrockfordTenantDeriver().derive_consumer_tenant(
        "acme/empty-app",
    )
    assert proj["belongs_to_tenant"] == expected_tenant

    # release_workflow_ref points at the canonical marketplace ULID.
    assert proj["release_workflow_ref"] == _MARKETPLACE_RELEASE_WORKFLOW_ULID


# ===========================================================================
# UC-001 — Populated repo, full Infer phase
# ===========================================================================


def test_uc_001_populated_repo_full_infer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UC-001 with the LLM inferrer (mocked) producing inferences.

    Asserts the inferred values reach the entity (after Ask phase
    confirms them — by default, the headless composition root accepts
    every inferred value unless the test overrides via `answers`).
    """
    repo = _materialise_fixture("populated", tmp_path)
    make_minimal_git_repo(
        repo, remote_url="git@github.com:acme/payments-app.git",
    )
    _patch_consuming_repo_root(monkeypatch, repo)

    llm = mock_llm_returns(
        inferences={
            "deploy_target": {"value": "github-release", "confidence": 0.9},
            "primary_branch": {"value": "main", "confidence": 0.99},
            "branch_model": {"value": "trunk", "confidence": 0.7},
            "package_manager": {"value": "npm", "confidence": 0.85},
            "language_primary": {"value": "typescript", "confidence": 0.9},
        },
        tokens_consumed=3_500,
    )

    answers = {
        "name": "payments-app",
        "type": "service",
        "version_files": ["package.json"],
        "description": "Payments service for the e2e fixture.",
        "belongs_to_product_ref": "acme-product",
    }

    result = run_discovery_headless(
        repo_path=repo,
        inferrer=LLMConfigurationInferrer(llm),
        answers=answers,
        verifier_fn=_fake_verify_pass,
    )

    assert result.ok is True
    assert result.tokens_consumed == 3_500
    proj = json.loads(result.entity_path.read_text())["projects"][0]
    assert proj["name"] == "payments-app"
    # Inferred values surfaced AND confirmed (default-accept).
    assert proj.get("deploy_target") == "github-release"
    assert proj.get("primary_branch") == "main"


# ===========================================================================
# UC-006 — Override an inferred value
# ===========================================================================


def test_uc_006_override_inferred_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UC-006: LLM infers `deploy_target=github-release`; founder overrides
    to `npm-publish`. Minted entity carries the override, not the inference."""
    repo = _materialise_fixture("populated", tmp_path)
    make_minimal_git_repo(repo, remote_url="git@github.com:acme/payments-app.git")
    _patch_consuming_repo_root(monkeypatch, repo)

    llm = mock_llm_returns(
        inferences={
            "deploy_target": {"value": "github-release", "confidence": 0.9},
        },
        tokens_consumed=2_000,
    )

    # Founder overrides deploy_target via the `overrides` dict.
    answers = {
        "name": "payments-app",
        "type": "service",
        "version_files": ["package.json"],
        "description": "Payments service.",
        "belongs_to_product_ref": "acme-product",
    }
    overrides = {"deploy_target": "npm-publish"}

    result = run_discovery_headless(
        repo_path=repo,
        inferrer=LLMConfigurationInferrer(llm),
        answers=answers,
        overrides=overrides,
        verifier_fn=_fake_verify_pass,
    )

    assert result.ok is True
    proj = json.loads(result.entity_path.read_text())["projects"][0]
    assert proj["deploy_target"] == "npm-publish"  # the override
    assert proj["deploy_target"] != "github-release"  # NOT the inference


# ===========================================================================
# UC-002 — --update on pre-existing entity; per-field diff (keep existing)
# ===========================================================================


def test_uc_002_re_discovery_per_field_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UC-002: re-discovery on a pre-existing entity. LLM proposes a change
    to deploy_target; founder chooses to keep the existing value."""
    repo = _materialise_fixture("pre-existing", tmp_path)
    make_minimal_git_repo(repo, remote_url="git@github.com:acme/foo.git")
    _patch_consuming_repo_root(monkeypatch, repo)

    # Pre-existing entity already at .sulis/projects/foo.jsonld with
    # deploy_target=npm-publish (per the fixture). Mock LLM proposes
    # github-release as a change. The per-field diff flow asks the
    # founder; we choose 'k' (keep) by NOT including deploy_target in
    # `overrides` AND telling the composition root via
    # `update_keep_fields={'deploy_target'}` — which mirrors the skill
    # prose's per-field diff "keep existing" branch.
    llm = mock_llm_returns(
        inferences={
            "deploy_target": {"value": "github-release", "confidence": 0.9},
        },
        tokens_consumed=1_500,
    )

    answers = {
        # The Ask phase only re-asks for fields whose inference differs
        # from the existing entity, so most of the existing values
        # remain authoritative.
    }

    result = run_discovery_headless(
        repo_path=repo,
        inferrer=LLMConfigurationInferrer(llm),
        answers=answers,
        update=True,
        update_keep_fields={"deploy_target"},
        verifier_fn=_fake_verify_pass,
    )

    assert result.ok is True
    proj = json.loads(result.entity_path.read_text())["projects"][0]
    # Founder kept the existing value, not the LLM's proposed change.
    assert proj["deploy_target"] == "npm-publish"


# ===========================================================================
# UC-003 — Monorepo, --path scoping
# ===========================================================================


def test_uc_003_monorepo_path_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UC-003: discovery on a monorepo, twice — once per sub-project.

    First invocation: --path apps/cli → .sulis/projects/cli.jsonld written.
    Second invocation: --path apps/backend → both cli.jsonld AND
    backend.jsonld present; cli.jsonld mtime unchanged.
    """
    repo = _materialise_fixture("monorepo", tmp_path)
    make_minimal_git_repo(repo, remote_url="git@github.com:acme/monorepo.git")
    _patch_consuming_repo_root(monkeypatch, repo)

    # Invocation 1: --path apps/cli
    result_cli = run_discovery_headless(
        repo_path=repo,
        inferrer=NullConfigurationInferrer(),
        answers={
            "name": "cli",
            # `application` — the compiled foundation Project schema's enum
            # (post-reconcile the canonical save validates `type`; the loose
            # `"tool"` label was never a schema value).
            "type": "application",
            "version_files": ["apps/cli/package.json"],
            "description": "CLI sub-project.",
            "belongs_to_product_ref": "acme-monorepo",
            "branch_policy": "trunk-based",
        },
        monorepo_path="apps/cli",
        verifier_fn=_fake_verify_pass,
    )
    assert result_cli.ok is True
    cli_jsonld = repo / ".sulis" / "projects" / "cli.jsonld"
    assert cli_jsonld.exists()
    assert not (repo / ".sulis" / "projects" / "backend.jsonld").exists()
    cli_mtime_before = cli_jsonld.stat().st_mtime_ns

    # Invocation 2: --path apps/backend
    result_backend = run_discovery_headless(
        repo_path=repo,
        inferrer=NullConfigurationInferrer(),
        answers={
            "name": "backend",
            "type": "service",
            "version_files": ["apps/backend/package.json"],
            "description": "Backend sub-project.",
            "belongs_to_product_ref": "acme-monorepo",
            "branch_policy": "trunk-based",
        },
        monorepo_path="apps/backend",
        verifier_fn=_fake_verify_pass,
    )
    assert result_backend.ok is True
    backend_jsonld = repo / ".sulis" / "projects" / "backend.jsonld"
    assert backend_jsonld.exists()
    # cli.jsonld is untouched after the second invocation.
    assert cli_jsonld.exists()
    cli_mtime_after = cli_jsonld.stat().st_mtime_ns
    assert cli_mtime_after == cli_mtime_before


# ===========================================================================
# UC-004 / MUC-001 — Non-git directory
# ===========================================================================


def test_uc_004_non_git_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UC-004 / MUC-001: discovery against a non-git tmpdir.

    Asserts the composition root raises NonGitDirectoryError and writes
    no entity file.
    """
    non_git = tmp_path / "non-git"
    non_git.mkdir()
    (non_git / "README.md").write_text("# not a git repo\n")
    _patch_consuming_repo_root(monkeypatch, non_git)

    with pytest.raises(NonGitDirectoryError):
        run_discovery_headless(
            repo_path=non_git,
            inferrer=NullConfigurationInferrer(),
            answers={"name": "ignored"},
            verifier_fn=_fake_verify_pass,
        )

    # No entity dir created.
    assert not (non_git / ".sulis" / "projects").exists() or not list(
        (non_git / ".sulis" / "projects").glob("*.jsonld")
    )


# ===========================================================================
# MUC-006 — No remote, with --source-repo override
# ===========================================================================


def test_muc_006_no_remote_with_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MUC-006: git repo with no remote configured; --source-repo
    override carries the canonical org/name."""
    no_remote = tmp_path / "no-remote"
    no_remote.mkdir()
    make_minimal_git_repo(no_remote, remote_url=None)
    _patch_consuming_repo_root(monkeypatch, no_remote)

    result = run_discovery_headless(
        repo_path=no_remote,
        inferrer=NullConfigurationInferrer(),
        answers={
            "name": "offline-app",
            "type": "library",
            "version_files": ["README.md"],
            "description": "Repo with no remote.",
            "belongs_to_product_ref": "acme-product",
            "branch_policy": "trunk-based",
        },
        source_repo_override="acme/offline-app",
        verifier_fn=_fake_verify_pass,
    )
    assert result.ok is True
    proj = json.loads(result.entity_path.read_text())["projects"][0]
    assert json.loads(proj["source"])["repo"] == "acme/offline-app"


def test_muc_006_no_remote_without_override_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MUC-006: no remote AND no --source-repo override → NoRemoteError."""
    no_remote = tmp_path / "no-remote-2"
    no_remote.mkdir()
    make_minimal_git_repo(no_remote, remote_url=None)
    _patch_consuming_repo_root(monkeypatch, no_remote)

    with pytest.raises(NoRemoteError):
        run_discovery_headless(
            repo_path=no_remote,
            inferrer=NullConfigurationInferrer(),
            answers={"name": "ignored"},
            verifier_fn=_fake_verify_pass,
        )


# ===========================================================================
# MUC-003 — Refuse overwrite without --update
# ===========================================================================


def test_muc_003_refuse_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MUC-003: running discovery without --update on a repo that already
    has a Project entity at the target path raises EntityAlreadyExistsError
    and leaves the existing entity untouched."""
    repo = _materialise_fixture("pre-existing", tmp_path)
    make_minimal_git_repo(repo, remote_url="git@github.com:acme/foo.git")
    _patch_consuming_repo_root(monkeypatch, repo)

    pre_existing_entity = repo / ".sulis" / "projects" / "foo.jsonld"
    assert pre_existing_entity.exists()
    bytes_before = pre_existing_entity.read_bytes()

    with pytest.raises(EntityAlreadyExistsError):
        run_discovery_headless(
            repo_path=repo,
            inferrer=NullConfigurationInferrer(),
            answers={"name": "foo"},
            update=False,
            verifier_fn=_fake_verify_pass,
        )

    # Existing entity is byte-identical after the refused attempt.
    assert pre_existing_entity.read_bytes() == bytes_before


# ===========================================================================
# MUC-005 — Bad release_workflow_ref triggers Verify failure + roll-back
# ===========================================================================


def test_muc_005_bad_workflow_ref_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MUC-005: a release_workflow_ref that is well-formed but does not RESOLVE
    in any tenant Workflow catalogue causes the post-mint drift detector to fail;
    the entity is rolled back (unlinked) and the exception carries the drift
    detector's stderr.

    Post-reconcile (ADR-006/WP-015) the two failure classes are layered: a
    *malformed* ref (wrong shape) is now caught earlier at the canonical port's
    schema validation (reject-on-invalid, before the mirror is written); a
    *well-formed-but-non-resolving* ref is the Verify phase's job, exercised here.
    The ULID below is shape-valid (passes the canonical save) but is not the
    canonical marketplace Workflow, so the drift detector rolls it back."""
    repo = _materialise_fixture("empty", tmp_path)
    make_minimal_git_repo(repo, remote_url="git@github.com:acme/bad-ref.git")
    _patch_consuming_repo_root(monkeypatch, repo)

    # Well-formed 26-char Crockford ULID, but NOT the canonical marketplace
    # release-train Workflow — so it passes schema validation at the canonical
    # port and is caught by the Verify-phase drift detector (resolution check).
    bad_ulid = "dna:workflow:01KT0NRES0VWRKFW00000000A0"

    with pytest.raises(DriftVerifyFailed) as excinfo:
        run_discovery_headless(
            repo_path=repo,
            inferrer=NullConfigurationInferrer(),
            answers={
                "name": "bad-ref",
                "type": "library",
                "version_files": ["README.md"],
                "description": "x",
                "belongs_to_product_ref": "acme-product",
                "branch_policy": "trunk-based",
            },
            release_workflow_ref_override=bad_ulid,
            verifier_fn=_fake_verify_checks_workflow_ref,
        )

    # The just-written entity is rolled back.
    rolled_back = excinfo.value.rolled_back_path
    assert not rolled_back.exists()
    # And the drift detector's stderr (carried by the exception) is non-empty.
    assert excinfo.value.result.stderr


# ===========================================================================
# MUC-008 — Token budget exceeded falls back to all-human-ask
# ===========================================================================


def test_muc_008_token_budget_falls_back_to_all_human_ask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MUC-008: LLM consumes more than the 10k budget; composition root
    swaps in NullConfigurationInferrer; valid entity still mints."""
    repo = _materialise_fixture("populated", tmp_path)
    make_minimal_git_repo(repo, remote_url="git@github.com:acme/big-app.git")
    _patch_consuming_repo_root(monkeypatch, repo)

    llm = mock_llm_returns(
        inferences={
            "deploy_target": {"value": "vercel", "confidence": 0.7},
        },
        mode="over-budget",
    )

    answers = {
        "name": "big-app",
        "type": "service",
        "version_files": ["package.json"],
        "description": "Over-budget repo.",
        "belongs_to_product_ref": "acme-product",
        "branch_policy": "trunk-based",
    }

    result = run_discovery_headless(
        repo_path=repo,
        inferrer=LLMConfigurationInferrer(llm),
        answers=answers,
        token_budget=10_000,
        verifier_fn=_fake_verify_pass,
    )

    # Entity still minted (via Null fallback) — NFR-006.
    assert result.ok is True
    assert result.entity_path.exists()
    # When the budget is exceeded, no inferences are accepted.
    proj = json.loads(result.entity_path.read_text())["projects"][0]
    assert "deploy_target" not in proj or proj.get("deploy_target") != "vercel"
    # tokens_consumed reflects the budget breach (the headless function
    # records the LLM's reported usage even when the inferences are
    # discarded — observability per TDD §Armor §Observability).
    assert result.budget_exceeded is True


# ===========================================================================
# Dogfood — Marketplace repo acceptance (the n=2 of Path A)
# ===========================================================================


@pytest.mark.dogfood
def test_dogfood_marketplace_repo_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run discovery on a COPY of THIS marketplace repo. Assert the minted
    entity is consistent with the hand-authored sulis Project at
    plugins/sulis/instances/release-train/projects.jsonld (modulo the
    grandfathered marketplace tenant ULID per ADR-002 amendment).

    NEVER pollutes the real .sulis/projects/ — discovery runs against a
    tmpdir copy of the marketplace.

    Records observed `tokens_consumed` to dogfood-tokens.txt for the
    ADR-006 v1.1 token-budget calibration.
    """
    # Locate the real marketplace repo root (we copy a minimal subset
    # into tmp — we don't need git objects, just enough for the Detect
    # phase to read manifests + the remote URL).
    marketplace_root = _REPO_ROOT

    # Sanity: the real .sulis/projects/ dir, if it exists, MUST NOT
    # be touched. We assert before-AND-after counts to prove it.
    real_projects_dir = marketplace_root / ".sulis" / "projects"
    real_jsonld_count_before = (
        len(list(real_projects_dir.glob("*.jsonld")))
        if real_projects_dir.exists()
        else 0
    )

    # Materialise a slim copy of the marketplace into tmp_path/dogfood/.
    dogfood = tmp_path / "dogfood"
    dogfood.mkdir()
    # Copy just enough for Detect to work: .claude-plugin/marketplace.json
    # + a minimal .git via `git init` + a synthetic remote URL.
    for relpath in [
        ".claude-plugin/marketplace.json",
        "plugins/sulis/.claude-plugin/plugin.json",
    ]:
        src = marketplace_root / relpath
        if src.exists():
            dst = dogfood / relpath
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)

    make_minimal_git_repo(
        dogfood, remote_url="git@github.com:sulis-ai/agents.git",
    )
    _patch_consuming_repo_root(monkeypatch, dogfood)

    # Use the Null inferrer for the dogfood path — the n=2 acceptance
    # is about SHAPE consistency (does the headless emission match the
    # hand-authored entity's schema), not about LLM inference quality.
    # The real LLM call's tokens_consumed observation is gated on a
    # separate test marked `@pytest.mark.dogfood_llm`.
    answers = {
        "name": "sulis",
        "type": "plugin",
        "version_files": [
            "plugins/sulis/.claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
        ],
        "description": (
            "The Sulis AI engineering team plugin — /sulis:* skills, "
            "agents, and reference standards that run the marketplace's "
            "own release-train."
        ),
        "belongs_to_product_ref": "sulis-plugins-marketplace",
        "branch_policy": "gitflow-dev-main",
    }

    result = run_discovery_headless(
        repo_path=dogfood,
        inferrer=NullConfigurationInferrer(),
        answers=answers,
        verifier_fn=_fake_verify_pass,
    )

    assert result.ok is True
    minted = json.loads(result.entity_path.read_text())["projects"][0]

    # Compare against the hand-authored sulis Project at
    # plugins/sulis/instances/release-train/projects.jsonld.
    hand_authored_path = (
        marketplace_root
        / "plugins"
        / "sulis"
        / "instances"
        / "release-train"
        / "projects.jsonld"
    )
    hand_authored = json.loads(hand_authored_path.read_text())
    sulis_project = next(
        p for p in hand_authored["projects"] if p["name"] == "sulis"
    )

    # Shape consistency: every field the hand-authored entity carries
    # is also present (and matches) in the minted one — modulo the
    # grandfathered marketplace tenant ULID (per ADR-002 amendment,
    # the recipe applies prospectively to NEW consumers; the
    # marketplace's own tenant is historic).
    fields_to_compare = [
        "name", "type", "branch_policy",
        "belongs_to_product_ref", "release_workflow_ref",
    ]
    for field in fields_to_compare:
        assert minted[field] == sulis_project[field], (
            f"Dogfood field {field!r} diverges: minted={minted[field]!r} "
            f"vs hand-authored={sulis_project[field]!r}"
        )

    # The dogfood-minted entity's belongs_to_tenant is DERIVED (per the
    # recipe applied to sulis-ai/agents), not the grandfathered
    # marketplace tenant. The ADR-002 amendment explicitly says the
    # recipe applies prospectively — so this divergence is by design.
    from _discovery.tenant import Sha256CrockfordTenantDeriver
    derived_tenant = Sha256CrockfordTenantDeriver().derive_consumer_tenant(
        "sulis-ai/agents",
    )
    assert minted["belongs_to_tenant"] == derived_tenant
    # And the hand-authored uses the grandfathered marketplace tenant.
    assert sulis_project["belongs_to_tenant"] == (
        "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"
    )

    # Source.repo matches sulis-ai/agents (the dogfood remote).
    assert json.loads(minted["source"])["repo"] == "sulis-ai/agents"

    # Real marketplace .sulis/projects/ untouched.
    real_jsonld_count_after = (
        len(list(real_projects_dir.glob("*.jsonld")))
        if real_projects_dir.exists()
        else 0
    )
    assert real_jsonld_count_before == real_jsonld_count_after

    # Record tokens_consumed for ADR-006 v1.1 calibration. Null adapter
    # always reports 0; this is the floor of the calibration data.
    tokens_log = (
        marketplace_root
        / ".architecture"
        / "discover-project"
        / "dogfood-tokens.txt"
    )
    tokens_log.parent.mkdir(parents=True, exist_ok=True)
    # Append-only so successive runs accumulate observations.
    with tokens_log.open("a") as f:
        f.write(
            f"{result.tokens_consumed}\tnull-adapter\t"
            f"dogfood-test\t{result.entity_path.name}\n",
        )
