#!/usr/bin/env python3
"""Build REVIEW.html — the investor-facing adversarial-review summary page.

Usage:
    python3 build_review_html.py <ADVERSARIAL_REVIEW.md> <tokens.css> <PITCH.yaml> <output.html>

This page presents the founder's adversarial pass in a form suitable to share
externally — partners, advisors, syndicate leads. It is distinct from the
working `05-adversarial/ADVERSARIAL_REVIEW.md`, which is the source of truth.

Rendering rules:
    - The Markdown source is converted to HTML with minimal styling.
    - Brand tokens are inlined from tokens.css.
    - The same long-form chrome as PITCH.html / FINANCIALS.html (hero + scrolling
      sections, optional topnav for H2 anchors).
    - No JavaScript dependencies — pure HTML/CSS.

This is deliberately lightweight. The substance is in the founder's writing;
the script handles presentation only.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def slug(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "section"


# ----- minimal markdown to HTML -----

INLINE_PATTERNS = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), r"<em>\1</em>"),
    (re.compile(r"`([^`\n]+)`"), r"<code>\1</code>"),
    (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), r'<a href="\2">\1</a>'),
]


def inline(text: str) -> str:
    """Apply minimal inline-markdown to escaped text."""
    out = html.escape(text)
    for pattern, replacement in INLINE_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def render_markdown(md_text: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Render markdown to HTML and return (html, [(level, anchor, title)])."""
    lines = md_text.split("\n")
    html_parts: list[str] = []
    toc: list[tuple[int, str, str]] = []

    state = {"in_list": False, "in_blockquote": False, "in_para": False, "in_table": False, "in_code": False}
    para_buf: list[str] = []

    def close_para():
        if para_buf:
            html_parts.append(f"<p>{inline(' '.join(b.strip() for b in para_buf))}</p>")
            para_buf.clear()
        state["in_para"] = False

    def close_list():
        if state["in_list"]:
            html_parts.append("</ul>")
            state["in_list"] = False

    def close_blockquote():
        if state["in_blockquote"]:
            html_parts.append("</blockquote>")
            state["in_blockquote"] = False

    def close_table():
        if state["in_table"]:
            html_parts.append("</tbody></table>")
            state["in_table"] = False

    def close_all():
        close_para()
        close_list()
        close_blockquote()
        close_table()

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # Fenced code blocks
        if line.startswith("```"):
            close_all()
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_html = html.escape("\n".join(code_lines))
            html_parts.append(f'<pre><code class="lang-{html.escape(lang)}">{code_html}</code></pre>')
            i += 1
            continue

        if not line:
            close_all()
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_all()
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = slug(title)
            toc.append((level, anchor, title))
            html_parts.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$", line):
            close_all()
            html_parts.append("<hr>")
            i += 1
            continue

        # Tables (very simple: pipe-separated, second line dashes)
        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?\s*[-:|\s]+\|?\s*$", lines[i + 1]):
            close_para()
            close_list()
            close_blockquote()
            headers = [c.strip() for c in line.strip().strip("|").split("|")]
            html_parts.append('<table class="data"><thead><tr>')
            for h in headers:
                html_parts.append(f"<th>{inline(h)}</th>")
            html_parts.append("</tr></thead><tbody>")
            state["in_table"] = True
            i += 2  # skip the dash row
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                html_parts.append("<tr>")
                for c in cells:
                    html_parts.append(f"<td>{inline(c)}</td>")
                html_parts.append("</tr>")
                i += 1
            close_table()
            continue

        # Bullet lists
        if line.startswith("- ") or line.startswith("* "):
            close_para()
            close_blockquote()
            if not state["in_list"]:
                html_parts.append("<ul>")
                state["in_list"] = True
            html_parts.append(f"<li>{inline(line[2:].strip())}</li>")
            i += 1
            continue
        else:
            close_list()

        # Blockquotes
        if line.startswith("> "):
            close_para()
            if not state["in_blockquote"]:
                html_parts.append("<blockquote>")
                state["in_blockquote"] = True
            html_parts.append(f"<p>{inline(line[2:].strip())}</p>")
            i += 1
            continue
        else:
            close_blockquote()

        # Paragraph (accumulate)
        para_buf.append(line)
        state["in_para"] = True
        i += 1

    close_all()
    return "\n".join(html_parts), toc


# ----- page assembly -----


def build_html(md_text: str, tokens_css: str, pitch_meta: dict) -> str:
    company = pitch_meta.get("name") or "Company"
    stage = pitch_meta.get("stage", "").replace("-", " ").title()
    title_full = f"{company} — Investor Deck Review"

    body_html, toc = render_markdown(md_text)

    # Build topnav from H2 headings only
    h2_entries = [(anchor, title) for level, anchor, title in toc if level == 2]
    nav_links = "".join(
        f'<a href="#{html.escape(a)}" data-target="{html.escape(a)}">{inline(t)}</a>'
        for a, t in h2_entries
    )
    nav_html = f"""<nav class="topnav">
  <a href="#top" class="brand-link">Top</a>
  <div class="section-links">
    {nav_links}
  </div>
</nav>""" if h2_entries else ""

    base_css = """
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font-sans, system-ui, sans-serif);
  color: var(--colour-ink, #1a1a1a);
  background: var(--colour-surface, #ffffff);
  line-height: 1.6;
  font-variant-numeric: tabular-nums;
}
.wrap { max-width: 880px; margin: 0 auto; padding: 0 2rem; }

nav.topnav {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: saturate(180%) blur(8px);
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
  padding: 0.6rem 2rem;
  display: flex;
  gap: 1rem;
  align-items: center;
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
  padding: 5rem 0 3rem;
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
}
section.hero .wordmark {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--colour-primary, #0066cc);
  margin-bottom: 2rem;
}
section.hero h1 {
  font-size: clamp(1.8rem, 3.6vw, 2.6rem);
  font-weight: 700;
  line-height: 1.15;
  margin: 0 0 0.8rem;
  max-width: 24ch;
}
section.hero .sub {
  font-size: 1.05rem;
  color: var(--colour-ink-muted, #666);
  margin: 0;
  max-width: 60ch;
}

article.review {
  padding: 4rem 0;
  scroll-margin-top: 60px;
}
article.review h2 {
  font-size: clamp(1.4rem, 2.6vw, 1.9rem);
  font-weight: 700;
  margin: 3.5rem 0 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--colour-surface-alt, #eee);
  scroll-margin-top: 80px;
}
article.review h2:first-of-type {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}
article.review h3 {
  font-size: 1.15rem;
  font-weight: 600;
  margin: 2.5rem 0 0.8rem;
}
article.review h4 {
  font-size: 1rem;
  font-weight: 600;
  margin: 2rem 0 0.6rem;
  color: var(--colour-ink-muted, #666);
}
article.review p { max-width: 68ch; margin: 0 0 1.2rem; }
article.review ul {
  padding-left: 1.5rem;
  margin: 0 0 1.5rem;
}
article.review li { margin-bottom: 0.4rem; }
article.review blockquote {
  border-left: 3px solid var(--colour-primary, #0066cc);
  padding: 0.6rem 0 0.6rem 1rem;
  color: var(--colour-ink-muted, #666);
  font-style: italic;
  margin: 1.5rem 0;
  background: var(--colour-surface-alt, #f8f8f8);
}
article.review blockquote p { margin: 0.3rem 0; }
article.review code {
  background: var(--colour-surface-alt, #f5f5f5);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 0.92em;
}
article.review pre {
  background: var(--colour-surface-alt, #f5f5f5);
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 0.9em;
}
article.review pre code { background: transparent; padding: 0; }
article.review hr {
  border: 0;
  border-top: 1px solid var(--colour-surface-alt, #eee);
  margin: 2.5rem 0;
}
article.review a {
  color: var(--colour-primary, #0066cc);
  text-decoration: underline;
  text-underline-offset: 2px;
}

article.review table.data {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5rem 0 2rem;
  font-size: 0.95rem;
}
article.review table.data th,
article.review table.data td {
  padding: 0.7rem 0.9rem;
  text-align: left;
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
  vertical-align: top;
}
article.review table.data th {
  font-weight: 600;
  color: var(--colour-ink-muted, #666);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

footer.colophon {
  padding: 3rem 0;
  text-align: center;
  font-size: 0.8rem;
  color: var(--colour-ink-muted, #666);
}
"""

    nav_script = """
(function () {
  const links = document.querySelectorAll('nav.topnav .section-links a');
  const headings = Array.from(document.querySelectorAll('article.review h2[id]'));
  if (!('IntersectionObserver' in window) || !links.length || !headings.length) return;
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
    { rootMargin: '-30% 0px -65% 0px' }
  );
  headings.forEach((h) => observer.observe(h));
})();
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title_full)}</title>
<style>
/* --- Brand tokens (inlined from brand-assets/tokens.css) --- */
{tokens_css}

/* --- Investor-facing review base styles --- */
{base_css}
</style>
</head>
<body>
{nav_html}
<section class="hero" id="top">
  <div class="wrap">
    <div class="wordmark">{html.escape(str(company))}</div>
    <h1>Investor deck review</h1>
    <p class="sub">An adversarial pass over the pitch, conducted before the partner runs one in the meeting. Every objection and weak claim, in plain sight.</p>
  </div>
</section>
<article class="review">
  <div class="wrap">
    {body_html}
  </div>
</article>
<footer class="colophon">
  <div class="wrap">{html.escape(str(company))} · {html.escape(stage)} · adversarial review</div>
</footer>
<script>
{nav_script}
</script>
</body>
</html>
"""


def build(review_md_path: Path, tokens_css_path: Path, pitch_path: Path, output_path: Path) -> int:
    if not review_md_path.is_file():
        print(f"ERROR: review markdown not found: {review_md_path}", file=sys.stderr)
        return 1
    if not pitch_path.is_file():
        print(f"ERROR: PITCH.yaml not found: {pitch_path}", file=sys.stderr)
        return 1

    md_text = review_md_path.read_text()
    tokens_css = tokens_css_path.read_text() if tokens_css_path.is_file() else ""
    pitch_meta = yaml.safe_load(pitch_path.read_text()) or {}

    output = build_html(md_text, tokens_css, pitch_meta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
    print(f"Wrote {output_path} (investor-facing review summary)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 1
    return build(Path(argv[1]), Path(argv[2]), Path(argv[3]), Path(argv[4]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
