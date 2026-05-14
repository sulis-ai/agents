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


def test_cargo_non_workspace_is_single_repo(tmp_path: Path):
    """A Cargo.toml WITHOUT [workspace] is not a monorepo manifest."""
    _write(tmp_path / "Cargo.toml", '[package]\nname = "x"\nversion = "0.1.0"\n')
    workspaces = detect_and_enumerate(tmp_path)
    assert len(workspaces) == 1
    assert workspaces[0].style == "single-repo"


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
