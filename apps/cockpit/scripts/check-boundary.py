#!/usr/bin/env python3
"""Extractability-boundary gate for apps/cockpit/ (TDD §9, ADR-008).

The cockpit must be liftable into its own repo without rework, so no file
under apps/cockpit/ may import a path that resolves OUTSIDE apps/cockpit/.
Intra-cockpit imports — including client/server reaching the shared/ module
(e.g. `client/src/components/X.tsx` importing `../../../shared/api-types`,
which resolves to `apps/cockpit/shared/api-types`) — are legitimate.

This replaces the original naive grep gate, which flagged any `(../){3,}`
import as an escape. That assumption was wrong: the cockpit's own tree is
three levels deep (client/src/components), so a three-up import lands back
inside apps/cockpit/. A text grep cannot tell the two apart; this resolves
each relative import against its file location and checks the real target.

It deliberately duplicates the ESLint `import/no-restricted-paths` rule:
ESLint only covers TS/JS, this covers every text file type (css, html,
json, md) that might reference a path outside the workspace.

Exit 0 = clean. Exit 1 = at least one true escape (printed). Bash/CI-friendly.

Usage:
    python3 apps/cockpit/scripts/check-boundary.py [--root apps/cockpit]
    python3 apps/cockpit/scripts/check-boundary.py --self-test
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Matches the path string in:
#   import ... from '<path>'        / "<path>"
#   export ... from '<path>'
#   import('<path>')                (dynamic)
#   require('<path>')
# We only care about *relative* specifiers (starting with . or ..); bare
# specifiers (react, @monaco-editor/react) are package imports, not boundary
# concerns.
_IMPORT_RE = re.compile(
    r"""(?:from|import|require)\s*\(?\s*['"](?P<path>\.{1,2}/[^'"]*)['"]"""
)

_SCAN_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".json", ".html", ".css", ".md"}
_SKIP_DIRS = {"node_modules", "dist", "build", ".git", "coverage", "playwright-report"}


def _iter_source_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix in _SCAN_SUFFIXES:
                yield p


def find_escapes(root: Path) -> list[str]:
    """Return a list of 'file:line: import' strings that escape `root`."""
    root = root.resolve()
    violations: list[str] = []
    for f in _iter_source_files(root):
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in _IMPORT_RE.finditer(line):
                spec = m.group("path")
                # Resolve the import target against the importing file's dir.
                target = (f.parent / spec).resolve()
                # An escape is any target not under root. (Suffix-less module
                # specifiers resolve to a path that doesn't exist on disk, but
                # os.path normalisation via resolve() still tells us whether
                # the *location* is inside root — which is all we need.)
                try:
                    target.relative_to(root)
                except ValueError:
                    rel = f.relative_to(root.parent)
                    violations.append(f"{rel}:{lineno}: {line.strip()}")
    return violations


def _self_test() -> int:
    """Prove the gate fires on an escape and passes on a legitimate import."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "cockpit"
        (root / "client" / "src" / "components").mkdir(parents=True)
        (root / "shared").mkdir(parents=True)
        # Legitimate: client component → shared (3 up, lands in cockpit/shared)
        (root / "client" / "src" / "components" / "Ok.tsx").write_text(
            'import type { X } from "../../../shared/api-types";\n'
        )
        # Escape: client component → repo root (4 up, leaves cockpit)
        (root / "client" / "src" / "components" / "Bad.tsx").write_text(
            'import pkg from "../../../../package.json";\n'
        )
        escapes = find_escapes(root)
        ok = (
            len(escapes) == 1
            and "Bad.tsx" in escapes[0]
            and not any("Ok.tsx" in e for e in escapes)
        )
        if ok:
            print("self-test PASS: legitimate shared import allowed, escape caught")
            return 0
        print("self-test FAIL:", escapes)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="apps/cockpit", help="cockpit root to scan")
    ap.add_argument("--self-test", action="store_true", help="run the built-in self-test")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    root = Path(args.root)
    if not root.is_dir():
        print(f"::error::cockpit root not found: {root}", file=sys.stderr)
        return 2

    escapes = find_escapes(root)
    if escapes:
        print("::error::cross-boundary imports detected (escape apps/cockpit/)")
        for v in escapes:
            print(v)
        return 1

    print(f"OK — no cross-boundary imports under {root}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
