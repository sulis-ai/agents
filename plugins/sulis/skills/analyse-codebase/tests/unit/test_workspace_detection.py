"""Unit tests for monorepo detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from probe.workspace import detect_and_enumerate, detect_style


def _write(p: Path, content: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_single_repo_no_manifests(tmp_path: Path):
    """No manifest → single workspace at root."""
    workspaces = detect_and_enumerate(tmp_path)
    assert len(workspaces) == 1
    assert workspaces[0].name == "."
    assert workspaces[0].style == "single-repo"


def test_pnpm_workspace_detection(tmp_path: Path):
    _write(tmp_path / "pnpm-workspace.yaml", 'packages:\n  - "packages/*"\n')
    _write(tmp_path / "packages/api/package.json", "{}")
    _write(tmp_path / "packages/web/package.json", "{}")

    workspaces = detect_and_enumerate(tmp_path)
    names = sorted(w.name for w in workspaces)
    assert names == ["packages/api", "packages/web"]
    for w in workspaces:
        assert w.style == "pnpm"


def test_lerna_detection(tmp_path: Path):
    _write(
        tmp_path / "lerna.json",
        json.dumps({"packages": ["modules/*"]}),
    )
    _write(tmp_path / "modules/foo/package.json", "{}")
    _write(tmp_path / "modules/bar/package.json", "{}")

    workspaces = detect_and_enumerate(tmp_path)
    names = sorted(w.name for w in workspaces)
    assert "modules/foo" in names and "modules/bar" in names


def test_cargo_workspace_detection(tmp_path: Path):
    _write(
        tmp_path / "Cargo.toml",
        '[workspace]\nmembers = ["crates/a", "crates/b"]\n',
    )
    (tmp_path / "crates/a").mkdir(parents=True)
    (tmp_path / "crates/b").mkdir(parents=True)

    workspaces = detect_and_enumerate(tmp_path)
    names = sorted(w.name for w in workspaces)
    assert names == ["crates/a", "crates/b"]
    assert all(w.style == "cargo" for w in workspaces)


def test_cargo_non_workspace_is_aux_package(tmp_path: Path):
    """A Cargo.toml WITHOUT [workspace] is not a monorepo manifest.

    Under the v0.9.0 polyglot pipeline, a flat-repo manifest at the root is
    picked up by Stage 2 as an auxiliary-package (not the legacy
    'single-repo' fallback, which now only applies when nothing matches at all).
    """
    _write(tmp_path / "Cargo.toml", '[package]\nname = "x"\nversion = "0.1.0"\n')
    workspaces = detect_and_enumerate(tmp_path)
    assert len(workspaces) == 1
    assert workspaces[0].style == "auxiliary-package"
    assert workspaces[0].name == "."


def test_go_workspaces_detection(tmp_path: Path):
    _write(tmp_path / "go.work", "go 1.21\n\nuse (\n  ./a\n  ./b\n)\n")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()

    workspaces = detect_and_enumerate(tmp_path)
    names = sorted(w.name for w in workspaces)
    assert names == ["a", "b"]
    assert all(w.style == "go-workspaces" for w in workspaces)


def test_detect_style_first_match_wins(tmp_path: Path):
    """When multiple manifests exist, pnpm wins (it's first in the order)."""
    _write(tmp_path / "pnpm-workspace.yaml", 'packages:\n  - "p/*"\n')
    _write(tmp_path / "lerna.json", '{"packages":["p/*"]}')
    detected = detect_style(tmp_path)
    assert detected is not None
    style, _ = detected
    assert style == "pnpm"


# ─── v0.9.0 4-stage polyglot pipeline ─────────────────────────────────────


def test_polyglot_root_pyproject_added_as_aux(tmp_path: Path):
    """A flat repo with only pyproject.toml at root → Stage 2 picks it up."""
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    workspaces = detect_and_enumerate(tmp_path)
    assert len(workspaces) == 1
    assert workspaces[0].style == "auxiliary-package"
    assert workspaces[0].name == "."


def test_polyglot_pnpm_plus_python_aux(tmp_path: Path):
    """pnpm monorepo + a depth-2 dir with pyproject.toml not declared by pnpm.

    Stage 2 walks both depth-1 and depth-2 dirs, so `services/api/pyproject.toml`
    is detected even though `services/` itself is just a container.
    """
    _write(tmp_path / "pnpm-workspace.yaml", 'packages:\n  - "apps/web"\n')
    _write(tmp_path / "apps/web/package.json", "{}")
    _write(tmp_path / "services/api/pyproject.toml", '[project]\nname = "api"\n')

    workspaces = detect_and_enumerate(tmp_path)
    styles = {w.name: w.style for w in workspaces}
    assert styles.get("apps/web") == "pnpm"
    assert styles.get("services/api") == "auxiliary-package"


def test_terraform_dir_becomes_code_bearing(tmp_path: Path):
    """A dir with several .tf files → Stage 3 'code-bearing-dir'."""
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')  # root claims itself
    for n in range(3):
        _write(tmp_path / "infrastructure" / f"main_{n}.tf", "resource {}\n")
    workspaces = detect_and_enumerate(tmp_path)
    by_name = {w.name: w for w in workspaces}
    assert "infrastructure" in by_name
    assert by_name["infrastructure"].style == "code-bearing-dir"


def test_code_bearing_threshold_enforced(tmp_path: Path):
    """A dir with only 2 Python files (below 10) is NOT a code-bearing workspace."""
    _write(tmp_path / "pnpm-workspace.yaml", 'packages:\n  - "apps/web"\n')
    _write(tmp_path / "apps/web/package.json", "{}")
    _write(tmp_path / "tiny/a.py", "x=1\n")
    _write(tmp_path / "tiny/b.py", "y=2\n")
    workspaces = detect_and_enumerate(tmp_path)
    names = {w.name for w in workspaces}
    assert "tiny" not in names


def test_infra_dir_becomes_deployment_only(tmp_path: Path):
    """A dir with only a Dockerfile and a k8s manifest → Stage 4 'deployment-dir'."""
    _write(tmp_path / "pnpm-workspace.yaml", 'packages:\n  - "apps/web"\n')
    _write(tmp_path / "apps/web/package.json", "{}")
    _write(tmp_path / "infra/Dockerfile", "FROM alpine\n")
    _write(
        tmp_path / "infra/deploy.yaml",
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: x\n",
    )
    workspaces = detect_and_enumerate(tmp_path)
    by_name = {w.name: w.style for w in workspaces}
    assert by_name.get("infra") == "deployment-dir"


def test_double_count_guard_skips_claimed(tmp_path: Path):
    """A workspace claimed by Stage 1 (pnpm) must not reappear from Stage 2."""
    _write(tmp_path / "pnpm-workspace.yaml", 'packages:\n  - "apps/*"\n')
    # apps/api has BOTH package.json (claimed by pnpm) AND pyproject.toml.
    # Stage 2 must NOT re-add it.
    _write(tmp_path / "apps/api/package.json", "{}")
    _write(tmp_path / "apps/api/pyproject.toml", '[project]\nname = "api"\n')

    workspaces = detect_and_enumerate(tmp_path)
    matches = [w for w in workspaces if w.name == "apps/api"]
    assert len(matches) == 1, f"apps/api should appear once, got {matches}"
    assert matches[0].style == "pnpm"


def test_skip_dirs_never_enumerated(tmp_path: Path):
    """`.github`, `docs`, etc. are skipped even if they contain manifests."""
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')  # claims root
    _write(tmp_path / ".github/workflows/ci.yml", "name: ci\n")
    _write(tmp_path / "docs/pyproject.toml", '[project]\nname = "docs"\n')
    workspaces = detect_and_enumerate(tmp_path)
    names = {w.name for w in workspaces}
    assert ".github" not in names
    assert "docs" not in names


def test_sulis_manifest_dir_triggers_deployment_stage(tmp_path: Path):
    """A dir containing a YAML with `apiVersion: sulis.io/v1` → deployment-dir."""
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    _write(
        tmp_path / "manifests/web.yaml",
        "apiVersion: sulis.io/v1\nkind: Workload\nmetadata:\n  name: web\n",
    )
    workspaces = detect_and_enumerate(tmp_path)
    by_name = {w.name: w.style for w in workspaces}
    assert by_name.get("manifests") == "deployment-dir"
