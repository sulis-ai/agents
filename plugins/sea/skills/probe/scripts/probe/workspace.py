"""
Workspace detection and monorepo enumeration.

Three stages:
  1. Manifest scan — top-down from the root, find the first monorepo
     manifest filename. Stop on first hit; nested monorepos are an edge
     case handled via `--workspace`.
  2. Per-style enumeration — each style has a dedicated enumerator.
  3. Fallback — no manifest → single synthetic workspace at root.

Supported monorepo styles (from config.MONOREPO_MANIFESTS):
  pnpm, lerna, nx, turborepo, cargo, maven, gradle, bazel, rush,
  go-workspaces.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

# tomllib for Cargo.toml parsing (Python 3.11+; we depend on 3.11 anyway)
if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:
    tomllib = None  # type: ignore[assignment]

import xml.etree.ElementTree as ET

from .config import EXTRA_EXCLUDE_DIRS, MONOREPO_MANIFESTS, WORKSPACE_PROJECT_MANIFESTS
from .models import Workspace


# ─── Stage 1: manifest scan ───────────────────────────────────────────────


def detect_style(root: Path) -> tuple[str, Path] | None:
    """
    Walk `root` top-down (limited depth) looking for monorepo manifests.

    Returns (style, manifest_path) on first hit, or None if no manifest
    found within the workspace-root area. We only check the immediate
    root and the first few levels — manifests should be near the root.
    """
    root = root.resolve()
    manifest_lookup: dict[str, str] = {
        name: style for name, style in MONOREPO_MANIFESTS
    }

    # Check the root directly first (most common)
    for name, style in MONOREPO_MANIFESTS:
        candidate = root / name
        if candidate.exists() and candidate.is_file():
            # Cargo.toml is special — only a monorepo if it has [workspace]
            if style == "cargo" and not _cargo_is_workspace(candidate):
                continue
            return style, candidate

    return None


def _cargo_is_workspace(toml_path: Path) -> bool:
    """A Cargo.toml is a monorepo root only if it has `[workspace]`."""
    if tomllib is None:
        # Fallback: text scan
        try:
            return "[workspace]" in toml_path.read_text(encoding="utf-8")
        except OSError:
            return False
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
        return "workspace" in data
    except (OSError, Exception):
        return False


# ─── Stage 2: per-style enumeration ───────────────────────────────────────


def enumerate_workspaces(style: str, manifest_path: Path) -> list[Workspace]:
    """
    Dispatch to the appropriate enumerator for `style`.

    Returns list of Workspace dataclasses. If enumeration fails or yields
    nothing, returns a single workspace at the manifest's parent directory.
    """
    root = manifest_path.parent.resolve()

    enumerators = {
        "pnpm": _enumerate_pnpm,
        "lerna": _enumerate_lerna,
        "nx": _enumerate_nx,
        "turborepo": _enumerate_turborepo,
        "rush": _enumerate_rush,
        "cargo": _enumerate_cargo,
        "maven": _enumerate_maven,
        "gradle": _enumerate_gradle,
        "bazel": _enumerate_bazel,
        "go-workspaces": _enumerate_go_workspaces,
    }

    fn = enumerators.get(style)
    if fn is None:
        return _single_workspace(root)

    try:
        workspaces = fn(manifest_path, root)
        if not workspaces:
            return _single_workspace(root)
        return workspaces
    except Exception:
        # Any parser failure → fall back to single workspace
        return _single_workspace(root)


def _single_workspace(root: Path, style: str = "single-repo") -> list[Workspace]:
    return [
        Workspace(
            name=".",
            path=str(root),
            style=style,
            manifest_path=None,
        )
    ]


def _glob_packages(root: Path, patterns: list[str]) -> list[Path]:
    """Expand glob patterns relative to root, return existing dir paths."""
    found: list[Path] = []
    for pat in patterns:
        for hit in root.glob(pat):
            if hit.is_dir() and not any(
                part in EXTRA_EXCLUDE_DIRS for part in hit.relative_to(root).parts
            ):
                found.append(hit.resolve())
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _enumerate_pnpm(manifest: Path, root: Path) -> list[Workspace]:
    """
    pnpm-workspace.yaml — parse the `packages:` list. We use a minimal
    YAML-ish line parser (avoiding a YAML dependency).

    Expected format:
        packages:
          - "packages/*"
          - "apps/*"
    """
    text = manifest.read_text(encoding="utf-8")
    patterns: list[str] = []
    in_packages = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("packages:"):
            in_packages = True
            continue
        if in_packages:
            if line.startswith(" ") or line.startswith("\t"):
                # Item line
                m = re.match(r"\s*-\s*['\"]?([^'\"]+)['\"]?", line)
                if m:
                    patterns.append(m.group(1))
            else:
                # End of packages block
                break
    return _from_patterns(root, patterns, "pnpm", manifest)


def _enumerate_lerna(manifest: Path, root: Path) -> list[Workspace]:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    packages = data.get("packages") or ["packages/*"]
    return _from_patterns(root, packages, "lerna", manifest)


def _enumerate_nx(manifest: Path, root: Path) -> list[Workspace]:
    """Find project.json files which mark Nx projects."""
    candidates = []
    for project_json in root.rglob("project.json"):
        if any(part in EXTRA_EXCLUDE_DIRS for part in project_json.relative_to(root).parts):
            continue
        candidates.append(project_json.parent)
    return _from_paths(root, candidates, "nx", manifest)


def _enumerate_turborepo(manifest: Path, root: Path) -> list[Workspace]:
    """Turborepo uses workspaces from package.json or apps/ packages/ dirs."""
    pkg_json = root / "package.json"
    patterns: list[str] = []
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            ws = data.get("workspaces")
            if isinstance(ws, list):
                patterns = ws
            elif isinstance(ws, dict) and isinstance(ws.get("packages"), list):
                patterns = ws["packages"]
        except (OSError, json.JSONDecodeError):
            pass
    if not patterns:
        patterns = ["apps/*", "packages/*"]
    return _from_patterns(root, patterns, "turborepo", manifest)


def _enumerate_rush(manifest: Path, root: Path) -> list[Workspace]:
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    projects = data.get("projects") or []
    paths = []
    for proj in projects:
        folder = proj.get("projectFolder")
        if folder:
            p = root / folder
            if p.is_dir():
                paths.append(p.resolve())
    return _from_paths(root, paths, "rush", manifest)


def _enumerate_cargo(manifest: Path, root: Path) -> list[Workspace]:
    """Cargo workspace — [workspace] members = ["crate1", "crate2/*"]"""
    if tomllib is None:
        return _single_workspace(root, "cargo")
    with manifest.open("rb") as fh:
        data = tomllib.load(fh)
    ws = data.get("workspace") or {}
    members = ws.get("members") or []
    return _from_patterns(root, members, "cargo", manifest)


def _enumerate_maven(manifest: Path, root: Path) -> list[Workspace]:
    """Parse pom.xml <modules> section."""
    try:
        tree = ET.parse(manifest)
    except ET.ParseError:
        return []
    # Strip XML namespace for easier matching
    root_elem = tree.getroot()
    ns_match = re.match(r"\{(.*)\}", root_elem.tag)
    ns = "{" + ns_match.group(1) + "}" if ns_match else ""

    modules_elem = root_elem.find(f"{ns}modules")
    if modules_elem is None:
        return []
    paths = []
    for module in modules_elem.findall(f"{ns}module"):
        if module.text:
            p = root / module.text.strip()
            if p.is_dir():
                paths.append(p.resolve())
    return _from_paths(root, paths, "maven", manifest)


def _enumerate_gradle(manifest: Path, root: Path) -> list[Workspace]:
    """Parse settings.gradle(.kts) for include(...) calls."""
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError:
        return []
    # Match: include 'a', 'b' or include("a", "b") or include(":foo:bar")
    paths = []
    for match in re.finditer(r"""include\s*\(?\s*['"]([^'"]+)['"]""", text):
        spec = match.group(1)
        # Gradle module syntax: ":a:b:c" → "a/b/c"
        rel = spec.lstrip(":").replace(":", "/")
        p = root / rel
        if p.is_dir():
            paths.append(p.resolve())
    return _from_paths(root, paths, "gradle", manifest)


def _enumerate_bazel(manifest: Path, root: Path) -> list[Workspace]:
    """Bazel — find BUILD files; each BUILD dir is a package."""
    candidates = []
    for build_file in root.rglob("BUILD"):
        if any(part in EXTRA_EXCLUDE_DIRS for part in build_file.relative_to(root).parts):
            continue
        candidates.append(build_file.parent)
    for build_file in root.rglob("BUILD.bazel"):
        if any(part in EXTRA_EXCLUDE_DIRS for part in build_file.relative_to(root).parts):
            continue
        candidates.append(build_file.parent)
    return _from_paths(root, candidates, "bazel", manifest)


def _enumerate_go_workspaces(manifest: Path, root: Path) -> list[Workspace]:
    """go.work file with use(...) directives."""
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError:
        return []
    paths: list[Path] = []
    # Capture single-line and multi-line `use` blocks
    use_block = re.search(r"use\s*\((.*?)\)", text, re.DOTALL)
    if use_block:
        for line in use_block.group(1).splitlines():
            line = line.strip()
            if line and not line.startswith("//"):
                rel = line.split()[0].strip("\"'")
                p = root / rel
                if p.is_dir():
                    paths.append(p.resolve())
    else:
        # Single-line: use ./module
        for match in re.finditer(r"use\s+(\S+)", text):
            rel = match.group(1).strip("\"'")
            p = root / rel
            if p.is_dir():
                paths.append(p.resolve())
    return _from_paths(root, paths, "go-workspaces", manifest)


def _from_patterns(
    root: Path,
    patterns: list[str],
    style: str,
    manifest: Path,
) -> list[Workspace]:
    expanded = _glob_packages(root, patterns)
    return _from_paths(root, expanded, style, manifest)


def _from_paths(
    root: Path,
    paths: list[Path],
    style: str,
    manifest: Path,
) -> list[Workspace]:
    workspaces: list[Workspace] = []
    seen: set[Path] = set()
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        try:
            rel = p.relative_to(root)
            name = str(rel) if str(rel) != "." else "."
        except ValueError:
            name = p.name
        workspaces.append(
            Workspace(
                name=name,
                path=str(p),
                style=style,
                manifest_path=str(manifest),
            )
        )
    return workspaces


# ─── Stage 3: fallback ────────────────────────────────────────────────────


def detect_and_enumerate(root: Path) -> list[Workspace]:
    """
    Public entry: detect monorepo style and return the workspace list.
    Falls back to a single-repo workspace if no manifest detected.
    """
    root = root.resolve()
    detection = detect_style(root)
    if detection is None:
        return _single_workspace(root)
    style, manifest_path = detection
    return enumerate_workspaces(style, manifest_path)
