#!/usr/bin/env python3
"""Build PITCH.html — the long-form, scrollable, investor-facing web pitch.

Usage:
    python3 build_web_pitch.py <slides_dir> <tokens.css> <PITCH.yaml> <output.html>

This is distinct from `build_html_deck.py`:
    - `build_html_deck.py`   → Reveal.js slide-by-slide presenter deck (one slide
                               at a time, keyboard navigation, speaker notes view)
    - `build_web_pitch.py`   → Long-form single-page web pitch with sticky topnav,
                               anchored sections, scroll-based reading flow. For
                               DocSend-style asynchronous sharing.

The slide source is the same — each `slides/NN-*.md` becomes one `<section>`. The
hero is constructed from PITCH.yaml. Brand tokens are inlined from tokens.css.

The generated page is a baseline. Founders typically refine the copy and visual
detail in the generated HTML before sharing externally.
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


@dataclass
class Slide:
    front_matter: dict
    body: str
    speaker_notes: str = ""
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
    notes = ""
    for i in range(1, len(parts), 2):
        heading = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading.startswith("Speaker"):
            notes = content
    return Slide(front_matter=fm, body=body, speaker_notes=notes, path_name=path.name)


def slug(text: str) -> str:
    """Convert a string to an HTML id slug."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "section"


def split_body(body: str) -> tuple[str, list[str], str]:
    """Return (lede, bullets, remainder).

    Lede = first non-bullet, non-heading paragraph.
    Bullets = bullet list lines.
    Remainder = any further prose paragraphs.
    """
    lede = ""
    bullets: list[str] = []
    remainder_paragraphs: list[str] = []
    buf: list[str] = []
    seen_lede = False

    def flush_buf():
        nonlocal lede, seen_lede
        if not buf:
            return
        text = " ".join(b.strip() for b in buf if b.strip())
        if not text:
            buf.clear()
            return
        if not seen_lede:
            lede = text
            seen_lede = True
        else:
            remainder_paragraphs.append(text)
        buf.clear()

    for raw in body.split("\n"):
        line = raw.rstrip()
        if not line:
            flush_buf()
            continue
        if line.startswith("- ") or line.startswith("* "):
            flush_buf()
            bullets.append(line[2:].strip())
        elif line.startswith("#"):
            flush_buf()
            continue  # skip in-body headings
        elif line.startswith("<!--"):
            continue
        elif line.startswith("> "):
            flush_buf()
            remainder_paragraphs.append(f"<blockquote>{html.escape(line[2:].strip())}</blockquote>")
        else:
            buf.append(line)
    flush_buf()

    remainder = "\n".join(
        f"<p>{html.escape(p)}</p>" if not p.startswith("<") else p
        for p in remainder_paragraphs
    )
    return lede, bullets, remainder


def render_hero(pitch_meta: dict) -> str:
    """Render the hero section from PITCH.yaml metadata."""
    company = pitch_meta.get("name") or pitch_meta.get("company") or "Company"
    stage = pitch_meta.get("stage", "")
    round_data = pitch_meta.get("round") or {}

    ask_value = (
        round_data.get("target_size_usd")
        or round_data.get("ask_usd")
        or round_data.get("ask_gbp")
        or round_data.get("ask")
    )
    ask_display = ""
    if isinstance(ask_value, (int, float)):
        ask_display = f"${ask_value / 1_000_000:.1f}M" if ask_value >= 1_000_000 else f"${ask_value / 1_000:.0f}k"
    elif ask_value:
        ask_display = str(ask_value)

    structure = round_data.get("structure", "")
    runway = round_data.get("expected_runway_months") or round_data.get("runway_target_months")
    runway_display = f"{runway} months" if runway else ""

    one_line = (pitch_meta.get("company") or {}).get("one_line") if isinstance(pitch_meta.get("company"), dict) else None
    one_line = one_line or pitch_meta.get("one_line") or round_data.get("next_milestone", "")

    ask_items = []
    if ask_display:
        ask_items.append(("Raising", ask_display))
    if structure:
        ask_items.append(("Structure", structure))
    if runway_display:
        ask_items.append(("Runway", runway_display))
    if stage:
        ask_items.append(("Stage", stage.replace("-", " ").title()))

    ask_html = "\n".join(
        f'<div class="item"><div class="k">{html.escape(k)}</div><div class="v">{html.escape(v)}</div></div>'
        for k, v in ask_items
    )

    return f"""<section class="hero" id="top">
  <div class="wrap">
    <div class="wordmark">{html.escape(str(company))}<span class="dot">.</span></div>
    <h1>{html.escape(str(one_line))}</h1>
    <div class="ask-row">
      {ask_html}
    </div>
    <a href="#section-1" class="scroll-cue"><span>Walk the pitch</span></a>
  </div>
</section>"""


def render_section(slide: Slide, idx: int, total: int, next_anchor: str, prev_anchor: str, prev_title: str, next_title: str) -> str:
    """Render one content section from a slide."""
    fm = slide.front_matter
    headline = fm.get("headline", "[MISSING HEADLINE]")
    role = fm.get("slide_role", "")
    eyebrow_num = f"{idx + 1:02d}"
    eyebrow_label = role.split(" ")[-1] if role else slide.path_name.replace(".md", "").split("-", 1)[-1]

    anchor = slug(headline) or f"section-{idx + 1}"

    lede, bullets, remainder = split_body(slide.body)

    bullets_html = ""
    if bullets:
        bullets_html = "<ul class='bullets'>" + "".join(f"<li>{html.escape(b)}</li>" for b in bullets) + "</ul>"

    lede_html = f"<p class='lede'>{html.escape(lede)}</p>" if lede else ""

    nav_html = f"""<div class="section-nav">
  <a href="#{html.escape(prev_anchor)}" class="nav-cell">
    <span class="arr-l"></span>
    <span><span class="label">Back</span><span class="prev-title">{html.escape(prev_title)}</span></span>
  </a>
  <a href="#{html.escape(next_anchor)}" class="nav-cell right">
    <span><span class="label">Next</span><span class="next-title">{html.escape(next_title)}</span></span>
    <span class="arr-r"></span>
  </a>
</div>"""

    return f"""<section class="s" id="{html.escape(anchor)}" data-section-index="{idx + 1}">
  <div class="wrap">
    <div class="eyebrow">{eyebrow_num} — {html.escape(str(eyebrow_label).replace('-', ' ').title())}</div>
    <h2>{html.escape(headline)}</h2>
    {lede_html}
    {bullets_html}
    {remainder}
    {nav_html}
  </div>
</section>"""


def render_topnav(slides: list[Slide], anchors: list[str]) -> str:
    """Render the sticky topnav with section anchors."""
    items = []
    for idx, (slide, anchor) in enumerate(zip(slides, anchors)):
        label = slide.front_matter.get("slide_role", "") or slide.path_name.replace(".md", "")
        # Strip "SQ-NN " prefix and dashes
        label = re.sub(r"^SQ-\d+\s*", "", label).replace("-", " ").title()
        items.append(f'<a href="#{html.escape(anchor)}" data-target="{html.escape(anchor)}">{html.escape(label)}</a>')
    return f"""<nav class="topnav">
  <a href="#top" class="brand-link">Top</a>
  <div class="section-links">
    {''.join(items)}
  </div>
</nav>"""


def build_html(slides: list[Slide], tokens_css: str, pitch_meta: dict) -> str:
    company = pitch_meta.get("name") or pitch_meta.get("company") or "Company"
    stage = pitch_meta.get("stage", "").replace("-", " ").title()
    title = f"{company} — {stage}" if stage else str(company)

    anchors = []
    titles = []
    for idx, slide in enumerate(slides):
        headline = slide.front_matter.get("headline", "")
        anchor = slug(headline) or f"section-{idx + 1}"
        anchors.append(anchor)
        titles.append(slide.front_matter.get("slide_role", "") or headline[:30])

    sections_html = []
    for idx, slide in enumerate(slides):
        anchor = anchors[idx]
        prev_anchor = anchors[idx - 1] if idx > 0 else "top"
        next_anchor = anchors[idx + 1] if idx < len(slides) - 1 else anchors[idx]
        prev_title = titles[idx - 1] if idx > 0 else str(company)
        next_title = titles[idx + 1] if idx < len(slides) - 1 else "End"
        sections_html.append(render_section(slide, idx, len(slides), next_anchor, prev_anchor, prev_title, next_title))

    base_css = """
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font-sans, system-ui, sans-serif);
  color: var(--colour-ink, #1a1a1a);
  background: var(--colour-surface, #ffffff);
  line-height: 1.55;
  font-variant-numeric: tabular-nums;
}
.wrap { max-width: 980px; margin: 0 auto; padding: 0 2rem; }

nav.topnav {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: saturate(180%) blur(8px);
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
  padding: 0.6rem 0;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-left: 2rem;
  padding-right: 2rem;
  font-size: 0.85rem;
}
nav.topnav .brand-link {
  font-weight: 700;
  text-decoration: none;
  color: var(--colour-ink, #1a1a1a);
  flex-shrink: 0;
}
nav.topnav .section-links {
  overflow-x: auto;
  scrollbar-width: none;
  display: flex;
  gap: 1.2rem;
  flex: 1;
}
nav.topnav .section-links::-webkit-scrollbar { display: none; }
nav.topnav .section-links a {
  color: var(--colour-ink-muted, #666);
  text-decoration: none;
  white-space: nowrap;
  padding: 0.3rem 0;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}
nav.topnav .section-links a:hover { color: var(--colour-ink, #1a1a1a); }
nav.topnav .section-links a.active {
  color: var(--colour-primary, #0066cc);
  border-bottom-color: var(--colour-primary, #0066cc);
}

section.hero {
  padding: 6rem 0 4rem;
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
}
section.hero .wordmark {
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--colour-primary, #0066cc);
  margin-bottom: 2.5rem;
}
section.hero .wordmark .dot { color: var(--colour-secondary, var(--colour-primary, #0066cc)); }
section.hero h1 {
  font-size: clamp(2rem, 4.5vw, 3.4rem);
  line-height: 1.1;
  font-weight: 700;
  margin: 0 0 1.5rem;
  max-width: 22ch;
}
section.hero h1 .accent { color: var(--colour-primary, #0066cc); }
section.hero .sub {
  font-size: 1.15rem;
  color: var(--colour-ink-muted, #666);
  max-width: 60ch;
  margin: 0 0 3rem;
}
section.hero .ask-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem 0;
  border-top: 1px solid var(--colour-surface-alt, #eee);
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
  margin-bottom: 2rem;
}
section.hero .item .k {
  font-size: 0.75rem;
  color: var(--colour-ink-muted, #666);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.25rem;
}
section.hero .item .v { font-size: 1.2rem; font-weight: 600; }
section.hero .scroll-cue {
  display: inline-block;
  color: var(--colour-ink-muted, #666);
  text-decoration: none;
  font-size: 0.9rem;
}
section.hero .scroll-cue:hover { color: var(--colour-ink, #1a1a1a); }

section.s {
  padding: 5rem 0;
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
  scroll-margin-top: 60px;
}
section.s:last-of-type { border-bottom: 0; }
section.s .eyebrow {
  font-size: 0.75rem;
  color: var(--colour-primary, #0066cc);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  margin-bottom: 1.2rem;
}
section.s h2 {
  font-size: clamp(1.7rem, 3.4vw, 2.5rem);
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 1.5rem;
  max-width: 26ch;
}
section.s .lede {
  font-size: 1.15rem;
  color: var(--colour-ink-muted, #666);
  max-width: 64ch;
  margin: 0 0 2rem;
}
section.s ul.bullets {
  list-style: none;
  padding: 0;
  margin: 0 0 2rem;
}
section.s ul.bullets li {
  position: relative;
  padding-left: 1.6rem;
  padding-bottom: 0.6rem;
}
section.s ul.bullets li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.85em;
  width: 0.8rem;
  height: 2px;
  background: var(--colour-primary, #0066cc);
}
section.s p { max-width: 64ch; }
section.s blockquote {
  border-left: 3px solid var(--colour-primary, #0066cc);
  padding-left: 1rem;
  color: var(--colour-ink-muted, #666);
  font-style: italic;
  margin: 1.5rem 0;
}

.section-nav {
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--colour-surface-alt, #eee);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.section-nav .nav-cell {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  color: var(--colour-ink-muted, #666);
  font-size: 0.85rem;
  padding: 0.8rem 0;
}
.section-nav .nav-cell.right { justify-content: flex-end; text-align: right; }
.section-nav .nav-cell:hover { color: var(--colour-ink, #1a1a1a); }
.section-nav .nav-cell .label {
  display: block;
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  margin-bottom: 0.15rem;
}
.section-nav .nav-cell .prev-title,
.section-nav .nav-cell .next-title {
  display: block;
  color: var(--colour-ink, #1a1a1a);
  font-weight: 500;
}
.section-nav .nav-cell .arr-l::before { content: "←"; font-size: 1.2rem; }
.section-nav .nav-cell .arr-r::before { content: "→"; font-size: 1.2rem; }

footer.colophon {
  padding: 3rem 0;
  text-align: center;
  font-size: 0.8rem;
  color: var(--colour-ink-muted, #666);
}
"""

    # Highlight-active-section script (light JS)
    nav_script = """
(function () {
  const links = document.querySelectorAll('nav.topnav .section-links a');
  const sections = Array.from(document.querySelectorAll('section[id]'));
  if (!('IntersectionObserver' in window) || !links.length) return;
  const map = new Map();
  links.forEach((a) => { const t = a.dataset.target; if (t) map.set(t, a); });
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        const link = map.get(e.target.id);
        if (!link) return;
        if (e.isIntersecting) {
          links.forEach((l) => l.classList.remove('active'));
          link.classList.add('active');
        }
      });
    },
    { rootMargin: '-40% 0px -55% 0px' }
  );
  sections.forEach((s) => observer.observe(s));
})();
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
/* --- Brand tokens (inlined from brand-assets/tokens.css) --- */
{tokens_css}

/* --- Long-form web pitch base styles --- */
{base_css}
</style>
</head>
<body>
{render_topnav(slides, anchors)}
{render_hero(pitch_meta)}
{''.join(sections_html)}
<footer class="colophon">
  <div class="wrap">{html.escape(str(company))} · {html.escape(stage)} · prepared {html.escape(str(pitch_meta.get('updated', pitch_meta.get('date_compiled', ''))))}</div>
</footer>
<script>
{nav_script}
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
    print(f"Wrote {output_path} ({len(slides)} sections, long-form web pitch)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 1
    return build(Path(argv[1]), Path(argv[2]), Path(argv[3]), Path(argv[4]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
