"""Integration tests for v0.9.0 — polyglot monorepo enumeration + repo-wide phases.

These tests exercise the new 4-stage workspace pipeline plus Phase 1.16
(Deployment Topology) and Phase 1.17 (Credential Scanning) on a single
fixture. They are integration tests because Phase 1.17 invokes the
detect-secrets binary; they skip cleanly when detect-secrets is missing.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from probe.models import RepoInput
from probe.runners.credential_runner import CredentialRunner
from probe.runners.deployment_runner import DeploymentRunner
from probe.workspace import detect_and_enumerate


pytestmark = pytest.mark.integration


def _repo_input(root: Path) -> RepoInput:
    return RepoInput(
        repo_root=str(root),
        project="polyglot-monorepo",
        extra_excludes=(),
        output_dir=str(root),
        workspaces=(),
    )


# ─── Stage A: polyglot workspace enumeration ─────────────────────────────


def test_polyglot_enumeration_finds_pnpm_plus_aux_plus_iac(make_workspace):
    """The fixture has pnpm `apps/web`, Python `apps/api`, Terraform `infrastructure`.

    Stage 1 detects pnpm `apps/web`. Stage 2 picks up `apps/api/pyproject.toml`
    at depth 2 (since pnpm only declares `apps/web`). Stage 3 adds
    `infrastructure/` for the .tf file. Stage 2 also picks up `product/`
    if it has a manifest (it doesn't in our fixture — only MANIFEST.yaml).
    Stage 4 may add it as deployment-dir.
    """
    workspace = make_workspace("polyglot_monorepo", as_git_repo=False)
    workspaces = detect_and_enumerate(workspace)
    by_name = {w.name: w.style for w in workspaces}

    assert "apps/web" in by_name and by_name["apps/web"] == "pnpm"
    assert "apps/api" in by_name and by_name["apps/api"] == "auxiliary-package"
    assert "infrastructure" in by_name and by_name["infrastructure"] == "code-bearing-dir"


# ─── Stage B: deployment topology runner ──────────────────────────────────


def test_polyglot_deployment_captures_all_artifact_kinds(make_workspace):
    """Deployment runner detects Dockerfile + sulis Workload + BusinessManifest
    + GH Action + Terraform.
    """
    workspace = make_workspace("polyglot_monorepo", as_git_repo=False)
    result = DeploymentRunner().run_repo(_repo_input(workspace))
    by_kind = result.payload["by_kind"]

    assert by_kind.get("dockerfile", 0) >= 1
    assert by_kind.get("terraform", 0) >= 1
    assert by_kind.get("github-actions", 0) >= 1
    assert by_kind.get("sulis-manifest", 0) >= 2  # Workload + BusinessManifest

    sulis = result.payload["sulis_kinds_present"]
    assert "Workload" in sulis
    assert "BusinessManifest" in sulis


def test_polyglot_deployment_extracts_secret_names_not_values(make_workspace):
    """The GH Action references ${{ secrets.STAGING_API_TOKEN }}.

    The runner must capture only the NAME, never any value. (There is no
    value to leak here, but the test also asserts the literal token isn't
    in the artifact's `secret_references` field.)
    """
    workspace = make_workspace("polyglot_monorepo", as_git_repo=False)
    result = DeploymentRunner().run_repo(_repo_input(workspace))
    gh_artifact = next(
        a for a in result.payload["artifacts"]
        if a["kind"] == "github-actions"
    )
    assert "STAGING_API_TOKEN" in gh_artifact["secret_references"]
    # No value-shaped strings should appear
    serialised = json.dumps(result.payload)
    assert "secrets.STAGING_API_TOKEN" not in serialised


def test_polyglot_deployment_extracts_sulis_workload_extras(make_workspace):
    workspace = make_workspace("polyglot_monorepo", as_git_repo=False)
    result = DeploymentRunner().run_repo(_repo_input(workspace))
    workload = next(
        a for a in result.payload["artifacts"]
        if a["kind"] == "sulis-manifest" and a["sub_kind"] == "Workload"
    )
    ex = workload["extras"]
    assert "image" in ex
    # Regex fallback emits strings, PyYAML emits ints — accept either.
    assert str(ex.get("port")) == "3000"


# ─── Stage C: credential scanning ─────────────────────────────────────────


@pytest.mark.skipif(
    shutil.which("detect-secrets") is None,
    reason="detect-secrets not installed; install via pipx for this test",
)
def test_polyglot_credentials_flags_planted_aws_key(make_workspace):
    """The fixture has a planted AKIA-prefixed AWS key.

    Verify it's flagged with secret_type containing 'AWS', is_known=False
    (no baseline), AND the plaintext value never appears in any output field.
    """
    workspace = make_workspace("polyglot_monorepo")  # as_git_repo=True
    result = CredentialRunner().run_repo(_repo_input(workspace))
    assert result.payload["skipped"] is False, (
        f"expected scan to run; got skip_reason={result.payload['skip_reason']}"
    )

    findings = result.payload["findings"]
    assert findings, "expected at least one finding from planted AWS key"

    aws_findings = [
        f for f in findings if "AWS" in f["secret_type"]
    ]
    assert aws_findings, (
        f"expected an AWS Access Key finding; got types: "
        f"{[f['secret_type'] for f in findings]}"
    )
    # is_known must be False since no .secrets.baseline exists in the fixture
    assert all(f["is_known"] is False for f in findings)

    # Privacy contract: no plaintext from the fixture appears anywhere.
    serialised = json.dumps(result.payload)
    assert "AKIA1234567890ABCDEF" not in serialised, "PLAINTEXT LEAKED"
    assert "wJalrXUtnFEMI" not in serialised, "PLAINTEXT LEAKED"
