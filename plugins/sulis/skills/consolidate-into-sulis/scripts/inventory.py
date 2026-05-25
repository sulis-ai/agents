#!/usr/bin/env python3
"""Inventory a source plugin's structure for consolidation.

Emits JSON to stdout describing every file in plugins/{source}/ grouped by
category (scripts, skills, agents, references, docs, CI workflows, manifest
files, metadata files). Consumed by detect_collisions.py and
find_external_refs.py.

Usage:
  python3 plugins/sulis/skills/consolidate-into-sulis/scripts/inventory.py \\
    --marketplace-root . \\
    --source-plugin sulis-context
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def collect(plugin_dir: Path) -> dict:
    """Walk plugin_dir and return categorised inventory."""
    inv: dict = {
        "source_plugin": plugin_dir.name,
        "scripts": [],
        "script_tests": [],
        "skills": [],
        "agents": [],
        "references": [],
        "docs": [],
        "ci_workflows": [],
        "manifest_files": [],
        "metadata_files": [],
    }

    if not plugin_dir.is_dir():
        return inv

    # scripts/ — flat or nested files; tests/ subtree separated for clarity
    scripts = plugin_dir / "scripts"
    if scripts.is_dir():
        for f in scripts.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(plugin_dir)
            if "tests" in rel.parts:
                inv["script_tests"].append(str(rel))
            else:
                inv["scripts"].append(str(rel))

    # skills/ — each subdirectory is one skill
    skills = plugin_dir / "skills"
    if skills.is_dir():
        for sd in sorted(skills.iterdir()):
            if sd.is_dir():
                inv["skills"].append(sd.name)

    # agents/ — flat .md files
    agents = plugin_dir / "agents"
    if agents.is_dir():
        for f in sorted(agents.glob("*.md")):
            inv["agents"].append(f.name)

    # references/ — .md files possibly nested
    refs = plugin_dir / "references"
    if refs.is_dir():
        for f in sorted(refs.rglob("*.md")):
            rel = f.relative_to(plugin_dir)
            inv["references"].append(str(rel))

    # docs/ — .md files possibly nested
    docs = plugin_dir / "docs"
    if docs.is_dir():
        for f in sorted(docs.rglob("*.md")):
            rel = f.relative_to(plugin_dir)
            inv["docs"].append(str(rel))

    # manifest + metadata files
    metadata_candidates = [
        ".claude-plugin/plugin.json",
        "README.md",
        "CHANGELOG.md",
        "CLAUDE.md",
        "settings.json",
    ]
    for name in metadata_candidates:
        p = plugin_dir / name
        if p.is_file():
            if name == ".claude-plugin/plugin.json":
                inv["manifest_files"].append(name)
            else:
                inv["metadata_files"].append(name)

    return inv


def find_ci_workflows(marketplace_root: Path, source_plugin: str) -> list[str]:
    """Find .github/workflows/*.yml files attached to this source plugin."""
    workflows_dir = marketplace_root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    matches: list[str] = []
    for f in sorted(workflows_dir.glob(f"{source_plugin}*.yml")):
        matches.append(str(f.relative_to(marketplace_root)))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marketplace-root", default=".", type=Path)
    parser.add_argument("--source-plugin", required=True)
    args = parser.parse_args()

    marketplace_root = args.marketplace_root.resolve()
    plugin_dir = marketplace_root / "plugins" / args.source_plugin

    if not plugin_dir.is_dir():
        print(f"Error: plugin not found at {plugin_dir}", file=sys.stderr)
        return 1

    inv = collect(plugin_dir)
    inv["ci_workflows"] = find_ci_workflows(marketplace_root, args.source_plugin)
    inv["marketplace_root"] = str(marketplace_root)
    inv["plugin_dir"] = str(plugin_dir.relative_to(marketplace_root))

    json.dump(inv, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
