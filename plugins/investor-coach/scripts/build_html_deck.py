#!/usr/bin/env python3
"""Build PITCH_DECK.html (Reveal.js single-file) from slides + brand tokens.

Usage:
    python3 build_html_deck.py <slides_dir> <tokens.css> <PITCH.yaml> <output.html>

The output is a single self-contained HTML file. Reveal.js is loaded from
CDN at view time. Brand tokens are inlined via the supplied tokens.css.
Speaker notes are accessible via Reveal.js notes view (press 's').
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


REVEAL_CDN = "https://cdn.jsdelivr.net/npm/reveal.js@5.1.0"


@dataclass
class Slide:
    front_matter: dict
    body: str
    speaker_notes: str = ""
    scqa: str = ""
    path_name: str = ""


def parse_slide(path: Path) -> Slide:
    text = path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path.name}: missing YAML front matter")
    fm = yaml.safe_load(match.group(1)) or {}
    rest = match.group(2)
    parts = re.split(r"^## (Speaker Notes|SCQA.*?)$", rest, flags=re.MULTILINE)
    body = parts[0].strip()
    notes, scqa = "", ""
    for i in range(1, len(parts), 2):
        heading = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading.startswith("Speaker"):
            notes = content
        elif heading.startswith("SCQA"):
            scqa = content
    return Slide(front_matter=fm, body=body, speaker_notes=notes, scqa=scqa, path_name=path.name)


def body_to_html(body: str) -> str:
    """Convert simple markdown body (bullets + paragraphs) to HTML."""
    lines = body.split("\n")
    html_parts: list[str] = []
    in_list = False
    for raw in lines:
        line = raw.rstrip()
        if not line:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{html.escape(line[2:].strip())}</li>")
        elif line.startswith("> "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<blockquote>{html.escape(line[2:].strip())}</blockquote>")
        elif line.startswith("#"):
            continue  # skip headings inside body
        elif line.startswith("<!--"):
            continue
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        html_parts.append("</ul>")
    return "\n".join(html_parts)


def render_slide_html(slide: Slide, company: str) -> str:
    fm = slide.front_matter
    headline = html.escape(fm.get("headline", "[MISSING HEADLINE]"))
    layout = fm.get("layout", "title-content")
    proof_points = fm.get("proof_points", []) or []

    body_html = body_to_html(slide.body)
    notes_html = html.escape(slide.speaker_notes).replace("\n", "<br>")
    footer_html = ""
    if proof_points:
        footer_html = (
            "<footer class='proof-points'>Sources: "
            + ", ".join(html.escape(p) for p in proof_points)
            + "</footer>"
        )

    css_class = f"layout-{layout}"

    return f"""
<section class="{css_class}" data-slide-id="{html.escape(fm.get('slide_id', ''))}">
  <h1>{headline}</h1>
  <div class="slide-body">
    {body_html}
  </div>
  {footer_html}
  <div class="slide-meta">{html.escape(company)}</div>
  <aside class="notes">{notes_html}</aside>
</section>
""".strip()


def build_html(slides: list[Slide], tokens_css: str, pitch_meta: dict) -> str:
    company = pitch_meta.get("name", "")
    title = f"{company} — Investor Deck" if company else "Investor Deck"

    sections = "\n".join(render_slide_html(s, company) for s in slides)

    base_css = """
:root {
  --colour-ink: #1a1a1a;
  --colour-ink-muted: #666;
  --colour-surface: #ffffff;
  --colour-surface-alt: #f5f5f5;
  --colour-primary: #0066cc;
  --font-sans: system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --font-serif: Georgia, "Times New Roman", serif;
}
.reveal { font-family: var(--font-sans); color: var(--colour-ink); }
.reveal .slides section { text-align: left; padding: 4% 6%; }
.reveal h1 { font-size: 2.6em; color: var(--colour-ink); font-weight: 700; margin: 0 0 0.6em; line-height: 1.15; }
.reveal .slide-body { font-size: 1.1em; }
.reveal .slide-body ul { list-style: none; padding-left: 0; }
.reveal .slide-body li { padding: 0.3em 0; padding-left: 1.2em; position: relative; }
.reveal .slide-body li::before { content: ""; position: absolute; left: 0; top: 0.85em; width: 0.5em; height: 2px; background: var(--colour-primary); }
.reveal blockquote { border-left: 3px solid var(--colour-primary); padding-left: 1em; color: var(--colour-ink-muted); font-style: italic; }
.reveal .proof-points { position: absolute; bottom: 3%; right: 6%; font-size: 0.6em; color: var(--colour-ink-muted); }
.reveal .slide-meta { position: absolute; bottom: 3%; left: 6%; font-size: 0.6em; color: var(--colour-ink-muted); }
.reveal section.layout-title { text-align: center; }
.reveal section.layout-title h1 { font-size: 3.2em; }
.reveal section.layout-quote blockquote { font-size: 1.3em; }
.reveal section.layout-two-column .slide-body { display: grid; grid-template-columns: 1fr 1fr; gap: 2em; }
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{REVEAL_CDN}/dist/reset.css">
<link rel="stylesheet" href="{REVEAL_CDN}/dist/reveal.css">
<link rel="stylesheet" href="{REVEAL_CDN}/dist/theme/white.css" id="theme">
<style>
/* --- Brand tokens (from brand-assets/tokens.css) --- */
{tokens_css}

/* --- Deck base styles --- */
{base_css}
</style>
</head>
<body>
<div class="reveal">
<div class="slides">
{sections}
</div>
</div>
<script src="{REVEAL_CDN}/dist/reveal.js"></script>
<script src="{REVEAL_CDN}/plugin/notes/notes.js"></script>
<script>
  Reveal.initialize({{
    hash: true,
    slideNumber: true,
    transition: 'fade',
    plugins: [ RevealNotes ]
  }});
</script>
</body>
</html>
"""


def build(slides_dir: Path, tokens_css_path: Path, pitch_path: Path, output_path: Path) -> int:
    if not slides_dir.is_dir():
        print(f"ERROR: slides_dir not found: {slides_dir}", file=sys.stderr)
        return 1
    if not pitch_path.is_file():
        print(f"ERROR: PITCH.yaml not found: {pitch_path}", file=sys.stderr)
        return 1

    tokens_css = tokens_css_path.read_text() if tokens_css_path.is_file() else ""
    pitch_meta = yaml.safe_load(pitch_path.read_text()) or {}

    slide_files = sorted(slides_dir.glob("*.md"))
    if not slide_files:
        print(f"ERROR: no slide files found in {slides_dir}", file=sys.stderr)
        return 1

    slides: list[Slide] = []
    for path in slide_files:
        try:
            slides.append(parse_slide(path))
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    output = build_html(slides, tokens_css, pitch_meta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
    print(f"Wrote {output_path} ({len(slides)} slides)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 1
    return build(Path(argv[1]), Path(argv[2]), Path(argv[3]), Path(argv[4]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
