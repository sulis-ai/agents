#!/usr/bin/env python3
"""Apply a bulk path + slash-command rewrite across the marketplace.

For consolidations with 50+ external refs, this is the right tool — it
applies a deterministic replacement table across every tracked file in
the repo (excluding the source plugin's DEPRECATED shell, historical
files, and the recipe's own pedagogical examples).

The replacement table is provided via a JSON file. Example:

  [
    ["/sea:blueprint", "/sulis:draft-architecture"],
    ["plugins/sea/skills/blueprint", "plugins/sulis/skills/draft-architecture"],
    ...
  ]

Usage:
  python3 plugins/sulis/skills/consolidate-into-sulis/scripts/bulk_rewrite.py \\
    --source-plugin sea \\
    --replacements-json /tmp/sea-replacements.json

The script:
- Runs `git ls-files` to find every tracked file
- Skips files inside the source plugin (DEPRECATED shell preserved)
- Skips CHANGELOG.md and VERIFICATION_REPORT.md files (historical narration)
- Skips the consolidate-into-sulis skill's own SKILL.md + references/ + runs/
  (pedagogical examples in those files would otherwise be rewritten)
- Applies replacements in order (later entries can match the output of earlier
  ones; put skill-with-rename patterns FIRST so they don't get partially
  matched by later more-general patterns)
- Reports substitutions per file + total

v0.1.2 — packaged from the ad-hoc /tmp/{srd,sea}_sweep.py scripts used in
the srd + sea consolidations.

**Ordering note (v0.1.2 — the move-then-sweep fix):** Run this script AFTER
all source-plugin content has been moved (skills + agent + references + docs).
If you run it before moving content out of the source plugin, the
`source_plugin` exclusion will protect that content from the sweep — leaving
old self-references inside the moved files that have to be cleaned up with
fix-forward commits. This bit twice during the sea consolidation; the
2-commit fix-forward pattern is preserved for audit but should not recur.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


EXCLUDED_FILENAMES = ("CHANGELOG.md", "VERIFICATION_REPORT.md")

# Files inside this list, even when found by git ls-files, are skipped.
# - sulis.VERIFICATION_REPORT.md: historical record of a prior agent verification
RECIPE_PEDAGOGICAL_PATHS = (
    "plugins/sulis/skills/consolidate-into-sulis/SKILL.md",
    "plugins/sulis/skills/consolidate-into-sulis/references/",
    "plugins/sulis/skills/consolidate-into-sulis/runs/",
)


def should_skip(path: Path, source_plugin: str) -> bool:
    """Return True iff this file is exempt from the sweep."""
    s = str(path)
    if s.startswith(f"plugins/{source_plugin}/"):
        return True
    if any(p in s for p in RECIPE_PEDAGOGICAL_PATHS):
        return True
    if path.name in EXCLUDED_FILENAMES:
        return True
    if "sulis.VERIFICATION_REPORT.md" in s:
        return True
    if ".git/" in s:
        return True
    return False


def apply_to_file(file_path: Path, replacements: list[tuple[str, str]]) -> int:
    """Apply all replacements to one file. Returns number of substitutions made."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
        return 0
    original = content
    total = 0
    for old, new in replacements:
        count = content.count(old)
        if count:
            content = content.replace(old, new)
            total += count
    if content != original:
        file_path.write_text(content, encoding="utf-8")
    return total


def load_replacements(path: Path) -> list[tuple[str, str]]:
    """Load replacements from JSON. Format: list of [old, new] pairs."""
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list at {path}, got {type(data)}")
    out: list[tuple[str, str]] = []
    for i, entry in enumerate(data):
        if not isinstance(entry, list) or len(entry) != 2:
            raise ValueError(f"Entry {i} is not a [old, new] pair: {entry}")
        old, new = entry
        if not isinstance(old, str) or not isinstance(new, str):
            raise ValueError(f"Entry {i} has non-string components: {entry}")
        out.append((old, new))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-plugin", required=True,
                        help="Source plugin name (e.g. 'sea', 'srd') — excluded from the sweep")
    parser.add_argument("--replacements-json", required=True, type=Path,
                        help="Path to JSON file with replacements (list of [old, new] pairs)")
    parser.add_argument("--marketplace-root", default=".", type=Path,
                        help="Path to marketplace root (default: current directory)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print proposed substitutions but don't write files")
    args = parser.parse_args()

    marketplace_root = args.marketplace_root.resolve()
    replacements = load_replacements(args.replacements_json)
    print(f"Loaded {len(replacements)} replacement rules from {args.replacements_json}", file=sys.stderr)

    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=marketplace_root,
        capture_output=True,
        text=True,
        check=True,
    )
    files = [Path(f) for f in proc.stdout.splitlines()]
    files = [f for f in files if not should_skip(f, args.source_plugin)]
    print(f"Scanning {len(files)} tracked files (excluded source plugin + historical + pedagogical)", file=sys.stderr)

    if args.dry_run:
        print("[DRY RUN — no files will be modified]", file=sys.stderr)

    total = 0
    files_changed = 0
    for fp in files:
        abs_fp = marketplace_root / fp
        if args.dry_run:
            # In dry-run mode, count what would change without writing.
            try:
                content = abs_fp.read_text(encoding="utf-8")
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
            n = sum(content.count(old) for old, _ in replacements)
        else:
            n = apply_to_file(abs_fp, replacements)
        if n:
            total += n
            files_changed += 1
            print(f"  {n:>4} subs  {fp}")

    print()
    print(f"Total: {total} substitutions across {files_changed} files")
    if args.dry_run:
        print("(dry-run — no files modified)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
