#!/usr/bin/env python3
"""Detect name collisions + tin-test failures between source plugin and sulis.

Reads inventory JSON (from inventory.py), checks each item against
plugins/sulis/, applies the tin-test rubric (bare verbs / acronyms), and emits
a Markdown report to stdout.

Usage:
  python3 plugins/sulis/skills/consolidate-into-sulis/scripts/inventory.py \\
    --source-plugin sulis-context > /tmp/inv.json

  python3 plugins/sulis/skills/consolidate-into-sulis/scripts/detect_collisions.py \\
    --marketplace-root . \\
    --target-plugin sulis \\
    --inventory-json /tmp/inv.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Bare verbs that fail the tin test (no noun → founder can't tell what they operate on).
# Drawn from observed skill names across sea / srd / sulis-context.
BARE_VERB_PATTERN = re.compile(
    r"^(decompose|harden|probe|verify|blueprint|refresh|show|discover|"
    r"synthesise|synthesize|audit|review|map|sync|build|test|run|fix|"
    r"check|deploy|release|publish|generate|create|update|delete|remove)$",
    re.IGNORECASE,
)

# Internal-jargon acronyms that fail the tin test for founder-visible skills.
# Universal acronyms (pr, ci, url, api) are allowed.
ACRONYM_PATTERN = re.compile(
    r"\b(srd|sea|aaf|fe|cp|tdd|adr|nfr|fr|uc|muc|wp)\b",
    re.IGNORECASE,
)


def is_bare_verb(name: str) -> bool:
    """Tin test: is this name a bare verb without a noun?"""
    return bool(BARE_VERB_PATTERN.match(name))


def has_internal_acronym(name: str) -> bool:
    """Tin test: does this name contain an internal-jargon acronym?"""
    return bool(ACRONYM_PATTERN.search(name))


def check_collisions(inventory: dict, target_dir: Path) -> dict:
    """For each item, check if same name exists in target plugin."""
    results: dict = {
        "skills": [],
        "agents": [],
        "references": [],
        "ci_workflows": [],
        "scripts": [],
    }

    # Skills
    for skill in inventory.get("skills", []):
        collision = (target_dir / "skills" / skill).is_dir()
        results["skills"].append({
            "name": skill,
            "collision": collision,
            "tin_test_bare_verb": is_bare_verb(skill),
            "tin_test_acronym": has_internal_acronym(skill),
        })

    # Agents
    for agent in inventory.get("agents", []):
        collision = (target_dir / "agents" / agent).is_file()
        results["agents"].append({"name": agent, "collision": collision})

    # References
    for ref in inventory.get("references", []):
        ref_name = Path(ref).name
        collision = (target_dir / "references" / ref_name).is_file()
        results["references"].append({
            "path": ref,
            "name": ref_name,
            "collision": collision,
        })

    # CI workflows — surface for review (renaming always needed)
    for wf in inventory.get("ci_workflows", []):
        results["ci_workflows"].append({
            "path": wf,
            "name": Path(wf).name,
        })

    # Scripts
    target_scripts_dir = target_dir / "scripts"
    if target_scripts_dir.is_dir():
        target_script_names = {
            f.name for f in target_scripts_dir.rglob("*") if f.is_file()
        }
    else:
        target_script_names = set()

    for script in inventory.get("scripts", []):
        script_name = Path(script).name
        results["scripts"].append({
            "path": script,
            "name": script_name,
            "collision": script_name in target_script_names,
        })

    return results


def emit_markdown(inventory: dict, results: dict, target_plugin: str) -> str:
    source = inventory.get("source_plugin", "?")
    out: list[str] = []
    out.append(f"# Collisions detected for `{source}` → `{target_plugin}`")
    out.append("")

    # Direct collisions
    out.append("## Direct name collisions")
    out.append("")
    any_collision = False
    for cat in ("skills", "agents", "references", "scripts"):
        hits = [r for r in results.get(cat, []) if r.get("collision")]
        if hits:
            any_collision = True
            out.append(f"### {cat.title()}")
            out.append("")
            for h in hits:
                name = h.get("name") or h.get("path", "")
                out.append(
                    f"- `{name}` — same name exists in `{target_plugin}/{cat}/`; "
                    "suggested rename: see `conflict-resolution.md` qualifier rule"
                )
            out.append("")
    if not any_collision:
        out.append("None.")
        out.append("")

    # Tin-test failures
    out.append("## Tin-test failures")
    out.append("")
    out.append(
        "Skill names the founder can't decode from the name alone. "
        "Apply the rename rubric in `references/conflict-resolution.md`."
    )
    out.append("")

    tin_fails = [
        r for r in results.get("skills", [])
        if r.get("tin_test_bare_verb") or r.get("tin_test_acronym")
    ]
    if not tin_fails:
        out.append("None.")
        out.append("")
    else:
        for r in tin_fails:
            reasons = []
            if r.get("tin_test_bare_verb"):
                reasons.append("bare verb")
            if r.get("tin_test_acronym"):
                reasons.append("contains internal-jargon acronym")
            out.append(f"- `{r['name']}` — {' + '.join(reasons)}")
        out.append("")

    # CI workflows — always rename
    out.append("## CI workflows to rename")
    out.append("")
    workflows = results.get("ci_workflows", [])
    if not workflows:
        out.append("No CI workflows attached to source plugin.")
    else:
        # The qualifier is whatever follows 'sulis-' in the source name, or the
        # plain source name if no 'sulis-' prefix.
        qualifier = source.replace("sulis-", "") if source.startswith("sulis-") else source
        for wf in workflows:
            existing = wf["name"]
            suggested = f"sulis-{qualifier}-{existing.split('-', 1)[-1]}" if existing.startswith(source) else f"sulis-{qualifier}-{existing}"
            out.append(f"- `{wf['path']}` — suggested rename to `.github/workflows/{suggested}`")
    out.append("")

    # Summary table
    out.append("## Summary")
    out.append("")
    direct_count = sum(
        1 for cat in ("skills", "agents", "references", "scripts")
        for r in results.get(cat, []) if r.get("collision")
    )
    tin_count = len(tin_fails)
    out.append(f"- Direct collisions: **{direct_count}**")
    out.append(f"- Tin-test failures: **{tin_count}**")
    out.append(f"- CI workflows to rename: **{len(workflows)}**")
    out.append("")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marketplace-root", default=".", type=Path)
    parser.add_argument("--target-plugin", default="sulis")
    parser.add_argument(
        "--inventory-json",
        default="-",
        help="Path to inventory JSON, or '-' for stdin (default)",
    )
    args = parser.parse_args()

    if args.inventory_json == "-":
        inventory = json.load(sys.stdin)
    else:
        with open(args.inventory_json) as f:
            inventory = json.load(f)

    marketplace_root = args.marketplace_root.resolve()
    target_dir = marketplace_root / "plugins" / args.target_plugin

    results = check_collisions(inventory, target_dir)
    sys.stdout.write(emit_markdown(inventory, results, args.target_plugin))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
