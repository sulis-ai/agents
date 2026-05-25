"""Unit tests for Phase 1.16 — Deployment Topology runner."""

from __future__ import annotations

import json
from pathlib import Path

from probe.models import RepoInput
from probe.runners.deployment_runner import (
    DeploymentRunner,
    _classify,
    _classify_from_api_version,
    _infer_env_from_path,
    _parse_yaml_docs,
    _scan_secret_refs,
)


def _w(p: Path, content: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _input(root: Path) -> RepoInput:
    return RepoInput(
        repo_root=str(root),
        project="test",
        extra_excludes=(),
        output_dir=str(root),
        workspaces=(),
    )


# ─── Classification helpers ────────────────────────────────────────────────


def test_classify_dockerfile_basename(tmp_path: Path):
    f = tmp_path / "Dockerfile"
    _w(f, "FROM alpine\n")
    result = _classify(f, tmp_path)
    assert result is not None
    assert result[0] == "dockerfile"


def test_classify_dockerfile_with_suffix(tmp_path: Path):
    f = tmp_path / "Dockerfile.prod"
    _w(f, "FROM alpine\n")
    result = _classify(f, tmp_path)
    assert result is not None
    assert result[0] == "dockerfile"


def test_classify_docker_compose(tmp_path: Path):
    f = tmp_path / "docker-compose.yml"
    _w(f, "services:\n  api: {}\n")
    result = _classify(f, tmp_path)
    assert result is not None
    assert result[0] == "docker-compose"


def test_classify_terraform_by_extension(tmp_path: Path):
    f = tmp_path / "main.tf"
    _w(f, 'resource "aws_s3_bucket" "b" {}\n')
    result = _classify(f, tmp_path)
    assert result is not None
    assert result[0] == "terraform"


def test_classify_github_actions_only_under_workflows_dir(tmp_path: Path):
    """A .yml file at root must NOT be classified as github-actions."""
    f = tmp_path / "stray.yml"
    _w(f, "name: anything\n")
    result = _classify(f, tmp_path)
    # Could be None or a YAML-api kind, but never github-actions at root.
    if result is not None:
        assert result[0] != "github-actions"


def test_classify_github_actions_in_workflows(tmp_path: Path):
    f = tmp_path / ".github/workflows/deploy.yml"
    _w(f, "name: deploy\n")
    result = _classify(f, tmp_path)
    assert result is not None
    assert result[0] == "github-actions"


def test_classify_sulis_manifest(tmp_path: Path):
    f = tmp_path / "manifest.yaml"
    _w(f, "apiVersion: sulis.io/v1\nkind: Workload\nmetadata:\n  name: web\n")
    result = _classify(f, tmp_path)
    assert result is not None
    assert result[0] == "sulis-manifest"


def test_classify_k8s_manifest(tmp_path: Path):
    f = tmp_path / "deploy.yaml"
    _w(f, "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: x\n")
    result = _classify(f, tmp_path)
    assert result is not None
    assert result[0] == "k8s-manifest"


def test_classify_argocd_application(tmp_path: Path):
    f = tmp_path / "app.yaml"
    _w(f, "apiVersion: argoproj.io/v1alpha1\nkind: Application\n")
    result = _classify(f, tmp_path)
    assert result is not None
    assert result[0] == "argocd"


def test_classify_from_api_version():
    assert _classify_from_api_version("sulis.io/v1") == "sulis-manifest"
    assert _classify_from_api_version("apps/v1") == "k8s-manifest"
    assert _classify_from_api_version("argoproj.io/v1alpha1") == "argocd"
    assert _classify_from_api_version("source.toolkit.fluxcd.io/v1") == "flux"
    assert _classify_from_api_version("") is None
    assert _classify_from_api_version("nonsense") is None


# ─── Multi-doc YAML parsing ────────────────────────────────────────────────


def test_parse_multi_doc_yaml_handles_sulis_and_k8s(tmp_path: Path):
    f = tmp_path / "mixed.yaml"
    _w(f, """apiVersion: sulis.io/v1
kind: Workload
metadata:
  name: web
spec:
  image: app:1.0
  port: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
""")
    docs = _parse_yaml_docs(f)
    assert len(docs) == 2
    assert docs[0].get("apiVersion") == "sulis.io/v1"
    assert docs[0].get("kind") == "Workload"
    assert docs[1].get("kind") == "Service"


# ─── Environment inference ─────────────────────────────────────────────────


def test_env_inference_environments_dir():
    assert _infer_env_from_path("infra/environments/prod/main.tf") == "prod"
    assert _infer_env_from_path("infra/environments/staging/main.tf") == "staging"


def test_env_inference_deploy_workflow_name():
    assert _infer_env_from_path(".github/workflows/deploy-staging.yml") == "staging"
    assert _infer_env_from_path(".github/workflows/deploy-prod.yaml") == "prod"


def test_env_inference_returns_none_when_no_signal():
    assert _infer_env_from_path("apps/web/Dockerfile") is None


# ─── Secret reference scanning ─────────────────────────────────────────────


def test_scan_gh_actions_secrets():
    content = """
jobs:
  deploy:
    steps:
      - env:
          KEY: ${{ secrets.GCP_SA_KEY }}
          TOKEN: ${{ secrets.NPM_TOKEN }}
"""
    refs = _scan_secret_refs(content)
    assert "GCP_SA_KEY" in refs and "NPM_TOKEN" in refs


def test_scan_k8s_secret_ref():
    content = """env:
  - name: PASS
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: password
"""
    refs = _scan_secret_refs(content)
    assert "db-credentials" in refs


def test_scan_secret_refs_captures_names_only_not_values():
    """The scanner must capture NAMES from `secrets.NAME`, never any value."""
    content = "value: ${{ secrets.MY_TOKEN }}"
    refs = _scan_secret_refs(content)
    assert refs == ["MY_TOKEN"]
    # No accidental capture of the surrounding text
    assert "$" not in refs[0]


# ─── End-to-end runner ─────────────────────────────────────────────────────


def test_runner_aggregates_by_kind(tmp_path: Path):
    _w(tmp_path / "apps/web/Dockerfile", "FROM node:20\nEXPOSE 3000\n")
    _w(tmp_path / "infra/main.tf", 'resource "aws_s3" "b" {}\n')
    _w(tmp_path / ".github/workflows/deploy.yml",
       "name: deploy\njobs:\n  d:\n    steps:\n      - run: echo hi\n")
    _w(tmp_path / "manifests/web.yaml",
       "apiVersion: sulis.io/v1\nkind: Workload\nmetadata:\n  name: web\nspec:\n"
       "  image: app:1.0\n  port: 3000\n")

    result = DeploymentRunner().run_repo(_input(tmp_path))
    by_kind = result.payload["by_kind"]
    assert by_kind.get("dockerfile") == 1
    assert by_kind.get("terraform") == 1
    assert by_kind.get("github-actions") == 1
    assert by_kind.get("sulis-manifest") == 1


def test_runner_extracts_sulis_workload_extras(tmp_path: Path):
    _w(tmp_path / "manifests/web.yaml", """apiVersion: sulis.io/v1
kind: Workload
metadata:
  name: web
spec:
  image: app:1.0
  port: 8080
  replicas: 3
""")
    result = DeploymentRunner().run_repo(_input(tmp_path))
    artifacts = result.payload["artifacts"]
    workload = next(
        a for a in artifacts
        if a["kind"] == "sulis-manifest" and a["sub_kind"] == "Workload"
    )
    assert workload["extras"].get("image") == "app:1.0"
    # Regex fallback parses scalars as strings; PyYAML returns ints. Accept either.
    assert str(workload["extras"].get("port")) == "8080"
    assert str(workload["extras"].get("replicas")) == "3"


def test_runner_serialised_payload_never_contains_secret_values(tmp_path: Path):
    """Secret references in YAML manifests are captured as NAMES, not values.

    Even if the YAML has `password: hunter2` as a literal, the secret-reference
    extractor should only surface ${{ secrets.NAME }} style references, never
    raw scalar values from the YAML.
    """
    _w(tmp_path / ".github/workflows/deploy.yml", """name: deploy
jobs:
  deploy:
    steps:
      - name: deploy
        env:
          API_KEY: ${{ secrets.PROD_API_KEY }}
          # NOT a secret reference, just a misleading literal:
          DECOY: "verysecretvalue"
""")
    result = DeploymentRunner().run_repo(_input(tmp_path))
    serialised = json.dumps(result.payload)
    # The NAME is allowed
    assert "PROD_API_KEY" in serialised
    # The literal scalar must NOT be captured into any secret-reference field
    artifact = next(
        a for a in result.payload["artifacts"]
        if a["kind"] == "github-actions"
    )
    assert "verysecretvalue" not in artifact["secret_references"]


def test_runner_skips_test_fixtures(tmp_path: Path):
    """Files inside `tests/` and `fixtures/` are not scanned for deployment."""
    _w(tmp_path / "tests/fixtures/Dockerfile", "FROM alpine\n")
    _w(tmp_path / "apps/web/Dockerfile", "FROM alpine\n")

    result = DeploymentRunner().run_repo(_input(tmp_path))
    paths = [a["path"] for a in result.payload["artifacts"]]
    assert any("apps/web/Dockerfile" in p for p in paths)
    assert not any("tests/" in p for p in paths)
