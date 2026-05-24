#!/usr/bin/env python3
"""Generate a monogram SVG for the brand-discovery proposal flow.

Usage:
    python3 generate_monogram.py <company_name> <tokens.json> <output.svg>
    python3 generate_monogram.py <company_name> <tokens.json> <output.svg> --variant dark

Reads `colour-primary`, `colour-surface`, and `font-sans` from tokens.json
and generates a square SVG monogram:
    - Light variant (default): primary on surface
    - Dark variant: surface on primary (inverse)

Initial-extraction rules:
    - One word → first letter
    - Two words → both first letters
    - Three+ words → first letters of first three words

The output is a self-contained SVG file. No raster image is produced — SVG
scales cleanly for both PPTX and HTML rendering. (Pillow is not required.)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def derive_initials(name: str) -> str:
    """Extract 1–3 letters from the company name for the monogram."""
    words = [w for w in re.split(r"[\s\-_]+", name.strip()) if w]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][0].upper()
    if len(words) == 2:
        return (words[0][0] + words[1][0]).upper()
    return (words[0][0] + words[1][0] + words[2][0]).upper()


def load_tokens(tokens_path: Path) -> dict:
    data = json.loads(tokens_path.read_text())
    flat: dict[str, str] = {}

    def walk(d: dict, prefix: str = ""):
        for k, v in d.items():
            full = f"{prefix}-{k}" if prefix else k
            if isinstance(v, dict):
                walk(v, full)
            else:
                flat[full] = v

    walk(data)
    return flat


def build_svg(initials: str, primary: str, surface: str, font_sans: str, variant: str = "light") -> str:
    if variant == "dark":
        fg, bg = surface, primary
    else:
        fg, bg = primary, surface

    # Inner font size scales with character count
    char_count = len(initials)
    font_size = {1: 220, 2: 170, 3: 130}.get(char_count, 130)

    # Use a generic font-family string so the SVG remains portable.
    # If font_sans starts with a stack, take the first family.
    font_family = font_sans.split(",")[0].strip().strip('"').strip("'") or "system-ui"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400" role="img" aria-label="Monogram: {initials}">
  <rect width="400" height="400" rx="48" ry="48" fill="{bg}"/>
  <text x="50%" y="50%"
        text-anchor="middle"
        dominant-baseline="central"
        font-family="{font_family}, system-ui, sans-serif"
        font-size="{font_size}"
        font-weight="700"
        fill="{fg}">{initials}</text>
</svg>
"""


def build_monogram(company_name: str, tokens_path: Path, output_path: Path, variant: str = "light") -> int:
    if not tokens_path.is_file():
        print(f"ERROR: tokens.json not found: {tokens_path}", file=sys.stderr)
        return 1

    tokens = load_tokens(tokens_path)
    primary = tokens.get("colour-primary", "#0066cc")
    surface = tokens.get("colour-surface", "#ffffff")
    font_sans = tokens.get("font-sans", "system-ui")

    initials = derive_initials(company_name)
    svg = build_svg(initials, primary, surface, font_sans, variant=variant)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg)
    print(f"Wrote {output_path} (initials={initials}, variant={variant})")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    variant = "light"
    if "--variant" in args:
        idx = args.index("--variant")
        if idx + 1 >= len(args):
            print(__doc__, file=sys.stderr)
            return 1
        variant = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if len(args) != 3:
        print(__doc__, file=sys.stderr)
        return 1

    return build_monogram(args[0], Path(args[1]), Path(args[2]), variant=variant)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
