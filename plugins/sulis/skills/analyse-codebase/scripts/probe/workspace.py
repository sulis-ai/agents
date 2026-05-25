"""
Workspace detection and monorepo enumeration.

v0.9.0 — 4-stage additive pipeline. The default assumption is a polyglot
monorepo: each stage *adds* workspaces, with later stages skipping any
path already claimed by an earlier one.

  Stage 1 — monorepo manifest. Find the first manifest in MONOREPO_MANIFESTS
            at the root and dispatch to its style-specific enumerator
            (pnpm/lerna/nx/turborepo/cargo/maven/gradle/bazel/rush/go-workspaces).
  Stage 2 — auxiliary packages. Top-level dirs containing one of
            WORKSPACE_PROJECT_MANIFESTS (pyproject.toml, Cargo.toml, etc.)
            that weren't already claimed by Stage 1.
  Stage 3 — code-bearing dirs. Top-level dirs with ≥ CODE_BEARING_MIN_SOURCE_FILES
            files in CODE_BEARING_EXTENSIONS, or any *.tf/*.tfvars.
  Stage 4 — deployment-only dirs. Top-level dirs containing Dockerfile,
            docker-compose YAML, or a k8s/sulis YAML manifest.

Public API preserved:
  - detect_style(root): Stage 1 only — returns (style, manifest_path) or None.
  - enumerate_workspaces(style, manifest_path): per-style Stage 1 enumerator.
  - detect_and_enumerate(root): full 4-stage pipeline.
"""

from __future__ import annotations

import fnmatch
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

from .config import (
    CODE_BEARING_EXTENSIONS,
    CODE_BEARING_MIN_SOURCE_FILES,
    DEPLOYMENT_KIND_PATTERNS,
    EXTRA_EXCLUDE_DIRS,
    MONOREPO_MANIFESTS,
    SULIS_API_VERSION,
    WORKSPACE_COUNT_WARN_THRESHOLD,
    WORKSPACE_PROJECT_MANIFESTS,
    WORKSPACE_SCAN_SKIP_DIRS,
    WS_STYLE_AUX_PACKAGE,
    WS_STYLE_CODE_BEARING,
    WS_STYLE_DEPLOYMENT,
)
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


# ─── 4-stage polyglot pipeline ────────────────────────────────────────────


def _is_claimed(path: Path, claimed: set[Path]) -> bool:
    """True if `path` is, contains, or is contained by any claimed workspace.

    Three cases all mean "skip":
      - `path` equals a claimed path.
      - `path` is a descendant of a claimed path (parent is a workspace).
      - `path` is an ancestor of a claimed path (its children are workspaces;
        adding the parent would double-count the same code).
    """
    p = path.resolve()
    for c in claimed:
        if p == c:
            return True
        try:
            if p.is_relative_to(c):
                return True
            if c.is_relative_to(p):
                return True
        except AttributeError:  # pragma: no cover — Python < 3.9
            try:
                p.relative_to(c)
                return True
            except ValueError:
                try:
                    c.relative_to(p)
                    return True
                except ValueError:
                    continue
    return False


def _iter_top_level_dirs(root: Path) -> list[Path]:
    """Top-level directories under root, skipping WORKSPACE_SCAN_SKIP_DIRS."""
    out: list[Path] = []
    skip = set(WORKSPACE_SCAN_SKIP_DIRS)
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return out
    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name in skip:
            continue
        out.append(entry.resolve())
    return out


def _stage1_monorepo(root: Path) -> tuple[list[Workspace], set[Path], bool]:
    """Run the existing manifest-based detection.

    Returns (workspaces, claimed, root_self_claimed). `root_self_claimed` is
    True when Stage 1 already accounts for the repo root (a monorepo
    manifest sits there), so Stage 2 must not re-add it as an aux-package.
    `claimed` contains only workspace paths — never the root — so that
    `_is_claimed` doesn't blanket-claim every subdir under the root.
    """
    detection = detect_style(root)
    if detection is None:
        return [], set(), False
    style, manifest_path = detection
    workspaces = enumerate_workspaces(style, manifest_path)
    claimed: set[Path] = {Path(w.path).resolve() for w in workspaces}
    return workspaces, claimed, True


def _stage2_auxiliary_packages(
    root: Path, claimed: set[Path], root_self_claimed: bool
) -> list[Workspace]:
    """Top-level dirs (and root itself) with a WORKSPACE_PROJECT_MANIFESTS file.

    The root itself is checked only when Stage 1 didn't already account for
    it (`root_self_claimed=False`) — handles the flat polyglot repo case
    (pyproject.toml at root, no monorepo manifest).
    """
    out: list[Workspace] = []

    if not root_self_claimed:
        for manifest_name in WORKSPACE_PROJECT_MANIFESTS:
            mp = root / manifest_name
            if mp.is_file():
                out.append(
                    Workspace(
                        name=".",
                        path=str(root.resolve()),
                        style=WS_STYLE_AUX_PACKAGE,
                        manifest_path=str(mp),
                    )
                )
                # Deliberately DO NOT add root to `claimed` — if we did,
                # `_is_claimed` would consider every subdir to be claimed
                # (via Path.is_relative_to(root)), which would suppress
                # all subsequent Stage 3/4 detections. The "don't re-add
                # the root" guard is purely the loop boundary below.
                break

    # Check depth-1 and depth-2 dirs. Depth-2 handles the common pattern of
    # `services/api/pyproject.toml` where `services/` is just a container.
    skip = set(WORKSPACE_SCAN_SKIP_DIRS)
    for d in _iter_top_level_dirs(root):
        candidates: list[Path] = [d]
        try:
            for sub in sorted(d.iterdir()):
                if sub.is_dir() and sub.name not in skip:
                    candidates.append(sub.resolve())
        except OSError:
            pass
        for cand in candidates:
            if _is_claimed(cand, claimed):
                continue
            for manifest_name in WORKSPACE_PROJECT_MANIFESTS:
                mp = cand / manifest_name
                if mp.is_file():
                    out.append(
                        Workspace(
                            name=str(cand.relative_to(root)),
                            path=str(cand),
                            style=WS_STYLE_AUX_PACKAGE,
                            manifest_path=str(mp),
                        )
                    )
                    claimed.add(cand)
                    break
    return out


def _count_source_files(
    directory: Path, extensions: tuple[str, ...], cap: int
) -> int:
    """Count files with any of `extensions` under directory; short-circuit at cap."""
    skip = set(WORKSPACE_SCAN_SKIP_DIRS)
    ext_set = {e.lower() for e in extensions}
    count = 0
    for dirpath, dirnames, filenames in _walk(directory):
        # Prune skip-dirs in-place
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            ext = Path(fn).suffix.lower()
            if ext in ext_set:
                count += 1
                if count >= cap:
                    return count
    return count


_TF_TRIGGER_EXTS: frozenset[str] = frozenset({".tf", ".tfvars"})


def _has_any_terraform(directory: Path) -> bool:
    """True if `directory` contains any .tf/.tfvars file (recursively).

    Terraform is treated as a low-volume but architecturally significant
    workspace marker — even 1-2 .tf files indicate IaC worth probing.
    """
    skip = set(WORKSPACE_SCAN_SKIP_DIRS)
    for dirpath, dirnames, filenames in _walk(directory):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if Path(fn).suffix.lower() in _TF_TRIGGER_EXTS:
                return True
    return False


def _stage3_code_bearing(
    root: Path, claimed: set[Path]
) -> list[Workspace]:
    """Top-level dirs with ≥ N source files in CODE_BEARING_EXTENSIONS, or any .tf."""
    out: list[Workspace] = []
    for d in _iter_top_level_dirs(root):
        if _is_claimed(d, claimed):
            continue
        is_code_bearing = (
            _count_source_files(
                d, CODE_BEARING_EXTENSIONS, cap=CODE_BEARING_MIN_SOURCE_FILES
            ) >= CODE_BEARING_MIN_SOURCE_FILES
            or _has_any_terraform(d)
        )
        if is_code_bearing:
            out.append(
                Workspace(
                    name=str(d.relative_to(root)),
                    path=str(d),
                    style=WS_STYLE_CODE_BEARING,
                    manifest_path=None,
                )
            )
            claimed.add(d)
    return out


_DEPLOYMENT_SENTINEL_FILENAMES: tuple[str, ...] = (
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "compose.yml", "compose.yaml",
)
_DEPLOYMENT_SENTINEL_GLOBS: tuple[str, ...] = (
    "Dockerfile.*", "*.Dockerfile",
)


def _has_deployment_sentinel(directory: Path) -> bool:
    """True if `directory` contains a Dockerfile, compose file, or k8s/sulis YAML."""
    skip = set(WORKSPACE_SCAN_SKIP_DIRS)
    yaml_apiversion_re = re.compile(
        rb"^\s*apiVersion\s*:\s*(\S+)", re.MULTILINE,
    )
    k8s_or_sulis_re = re.compile(
        r"(?:^v1$|^apps/v[12]$|^batch/v[12]$|sulis\.io/v1|"
        r"networking\.k8s\.io|rbac\.authorization\.k8s\.io)",
    )
    for dirpath, dirnames, filenames in _walk(directory):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if fn in _DEPLOYMENT_SENTINEL_FILENAMES:
                return True
            if any(fnmatch.fnmatch(fn, g) for g in _DEPLOYMENT_SENTINEL_GLOBS):
                return True
            if fn.endswith((".yaml", ".yml")):
                try:
                    with (Path(dirpath) / fn).open("rb") as fh:
                        head = fh.read(8192)
                    for m in yaml_apiversion_re.finditer(head):
                        api = m.group(1).decode("utf-8", errors="ignore")
                        if k8s_or_sulis_re.search(api):
                            return True
                except OSError:
                    continue
    return False


def _stage4_deployment_only(
    root: Path, claimed: set[Path]
) -> list[Workspace]:
    """Top-level dirs that contain deployment artifacts but no code workspace."""
    out: list[Workspace] = []
    for d in _iter_top_level_dirs(root):
        if _is_claimed(d, claimed):
            continue
        if _has_deployment_sentinel(d):
            out.append(
                Workspace(
                    name=str(d.relative_to(root)),
                    path=str(d),
                    style=WS_STYLE_DEPLOYMENT,
                    manifest_path=None,
                )
            )
            claimed.add(d)
    return out


def _walk(root: Path):
    """os.walk wrapper that yields Path-friendly tuples."""
    import os
    yield from os.walk(root)


def detect_and_enumerate(root: Path) -> list[Workspace]:
    """
    Public entry: run the 4-stage polyglot pipeline.

    Stage 1 may return nothing (no monorepo manifest); stages 2-4 then
    populate the result. If all four stages return nothing, fall back to a
    single synthetic workspace at root.
    """
    root = root.resolve()
    all_workspaces: list[Workspace] = []

    stage1_ws, claimed, root_self_claimed = _stage1_monorepo(root)
    all_workspaces.extend(stage1_ws)

    all_workspaces.extend(_stage2_auxiliary_packages(root, claimed, root_self_claimed))
    all_workspaces.extend(_stage3_code_bearing(root, claimed))
    all_workspaces.extend(_stage4_deployment_only(root, claimed))

    if not all_workspaces:
        return _single_workspace(root)

    if len(all_workspaces) > WORKSPACE_COUNT_WARN_THRESHOLD:
        print(
            f"[probe] warning: {len(all_workspaces)} workspaces detected "
            f"(threshold {WORKSPACE_COUNT_WARN_THRESHOLD}). Use --workspace "
            f"or --exclude-dir to narrow.",
            file=sys.stderr,
        )

    return all_workspaces
