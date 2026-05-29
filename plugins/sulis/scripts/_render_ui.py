"""UI-contract renderer — render a change's visual contract to UI.html, or
emit nothing + a note when the change has no visual contract.

WP-002 (cockpit-contract-preview). EXPAND-Create: a net-new wpx render path,
sibling to wpx-render-contract (WP-001), sharing the wpx shape — worktree-only
input, generic per-change resolution (ADR-003), emit_ok/emit_error JSON at the
CLI edge (ADR-001).

Reuse, not reinvention (EP-03). The design-system skill already defines the
VIEWER shape — a self-contained HTML preview that inlines a token map and
renders a token showcase + component gallery, opening from file:// with no
external token fetch. The skill is LLM-driven (no callable CLI), so this module
reuses its VIEWER *mechanism*: it discovers the change's visual contract
(design tokens / DESIGN source) in the worktree by convention, then composes a
UI.html in that same VIEWER shape from the change's own tokens. It does NOT
invent a second, different preview format.

When a change carries no visual contract (a non-user-facing change), the
renderer writes nothing for UI.html and records ``ui_contract: "none"`` plus a
plain human note in the shared manifest, so the cockpit shows "no UI contract
for this change" rather than a broken link or an exception (TDD §2.4 / §4.2).

Stdlib-only. Pure functions here; the CLI wrapper lives in ``wpx-render-ui``.
"""

from __future__ import annotations

import re
from pathlib import Path

# ─── Discovery (ADR-003: generic, never a fixed filename for one change) ──
#
# A visual contract is recognised by CONVENTION, in precedence order. These
# globs match what the design-system skill produces (TOKEN_MAP.css /
# TOKEN_MAP.json / DESIGN.md / VIEWER.html) anywhere in the worktree, plus the
# common token-file conventions a hand-authored visual contract uses. The
# search is recursive and parent-dir-agnostic, so it works for ANY change's
# layout — it does not depend on a change-specific path.

# Token sources carry the actual design values we inline into the VIEWER.
_TOKEN_GLOBS: tuple[str, ...] = (
    "**/TOKEN_MAP.css",
    "**/tokens.css",
    "**/variables.css",
    "**/theme.css",
    "**/design-tokens.json",
    "**/*.tokens.json",
    "**/tokens.json",
)

# Companion design-contract files: their presence signals a visual contract
# even when a token file is absent (e.g. a VIEWER.html already produced, or a
# DESIGN.md frontmatter carrying tokens).
_DESIGN_GLOBS: tuple[str, ...] = (
    "**/VIEWER.html",
    "**/DESIGN.md",
)

# Directories never searched (vendored / build output — not the change's own
# visual contract).
_SKIP_DIRS: frozenset[str] = frozenset(
    {"node_modules", ".git", "dist", "build", ".venv", "__pycache__"}
)

# Pull `--name: value;` CSS custom properties out of a token file.
_CSS_VAR_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;}\n]+)")


def _is_skipped(path: Path, worktree: Path) -> bool:
    """True if any path component between the worktree and the file is a
    skipped (vendored / build) directory."""
    rel = path.relative_to(worktree)
    return any(part in _SKIP_DIRS for part in rel.parts)


def _first_match(worktree: Path, globs: tuple[str, ...]) -> Path | None:
    """First file (sorted, deterministic) matching any glob, skipping vendored
    dirs. Returns None if none match."""
    for pattern in globs:
        candidates = sorted(
            p for p in worktree.glob(pattern)
            if p.is_file() and not _is_skipped(p, worktree)
        )
        if candidates:
            return candidates[0]
    return None


def locate_visual_contract(worktree: Path) -> Path | None:
    """Discover the change's visual contract inside ``worktree`` by convention.

    Returns the path to a token source (preferred — it carries the actual
    design values) or, failing that, a companion design-contract file
    (VIEWER.html / DESIGN.md). Returns None when the change carries no visual
    contract at all (a non-user-facing change).

    Generic per ADR-003: recognised by convention-based recursive globs, never
    a fixed filename keyed to one change.
    """
    worktree = Path(worktree)
    return _first_match(worktree, _TOKEN_GLOBS) or _first_match(
        worktree, _DESIGN_GLOBS
    )


# ─── Token extraction ─────────────────────────────────────────────────────


def _extract_tokens(contract_path: Path) -> dict[str, str]:
    """Extract `--name: value` design tokens from a CSS-ish token source.

    Defensive: a non-CSS source (a DESIGN.md or VIEWER.html with no `--var`
    declarations) simply yields no tokens, and the VIEWER renders with its
    built-in fallbacks. Never raises on malformed content.
    """
    try:
        text = contract_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    tokens: dict[str, str] = {}
    for name, value in _CSS_VAR_RE.findall(text):
        tokens.setdefault(name.strip(), value.strip())
    return tokens


# ─── VIEWER composition (reuses the design-system VIEWER shape) ───────────


def _css_value_safe(value: str) -> str:
    """Defang a token value before inlining it into a ``<style>`` block.

    The token regex already stops a value at ``;``, ``}`` or newline, so a
    value cannot inject a new declaration or close the ``:root`` block. This
    closes the remaining theoretical gap — a literal ``</style>`` substring in
    a value escaping the style element — by neutralising any ``<`` it carries.
    Token values are trusted design tokens, so this never alters a legitimate
    value (CSS values do not contain ``<``); it is defence-in-depth for a
    malformed or hostile contract file (Armor / path-and-content safety).
    """
    return value.replace("<", r"\3c ")


def build_viewer_html(contract_path: Path) -> str:
    """Compose a self-contained UI.html in the design-system VIEWER shape.

    The VIEWER mechanism (per the design-system skill's Phase 5) is: inline the
    token map into a `<style>` block (no external token fetch), then render a
    token showcase + component gallery that bind to those tokens, so the page
    opens from file:// and shows the change's own visual system. We reuse that
    shape here, populated from the change's own contract — we do not invent a
    different preview.
    """
    tokens = _extract_tokens(contract_path)
    inline_tokens = "\n".join(
        f"    {name}: {_css_value_safe(value)};"
        for name, value in sorted(tokens.items())
    )
    root_block = f":root {{\n{inline_tokens}\n  }}" if inline_tokens else ":root {}"

    # Swatch tiles for any --color-* token, so the change's palette is visible.
    swatches = "\n".join(
        f'      <div class="swatch">'
        f'<div class="swatch-color" style="background:var({name})"></div>'
        f'<div class="swatch-label">{name}</div></div>'
        for name in sorted(tokens)
        if name.startswith("--color")
    )
    swatch_block = swatches or "      <p>No colour tokens found in this contract.</p>"

    title = "UI Contract Preview"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    /* ── Inlined design tokens (no external fetch — opens from file://) ── */
    {root_block}

    /* ── Viewer chrome (design-system VIEWER shape) ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-family-base, system-ui, -apple-system, sans-serif);
      background: var(--color-surface-default, #f9fafb);
      color: var(--color-foreground, #111827);
      line-height: 1.5;
    }}
    .viewer-nav {{
      position: sticky; top: 0; z-index: 100;
      background: var(--color-surface-default, #fff);
      border-bottom: 1px solid var(--color-border, #e5e7eb);
      padding: 0.75rem 1.5rem;
      display: flex; gap: 1.5rem; align-items: center; flex-wrap: wrap;
    }}
    .viewer-section {{ padding: 2rem 1.5rem; max-width: 1100px; margin: 0 auto; }}
    .section-title {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 1.25rem; }}
    .swatch-grid {{ display: flex; flex-wrap: wrap; gap: 1rem; }}
    .swatch {{ display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }}
    .swatch-color {{
      width: 64px; height: 64px;
      border-radius: var(--radius-sm, 4px);
      border: 1px solid var(--color-border, #e5e7eb);
    }}
    .swatch-label {{
      font-size: 0.625rem; text-align: center;
      color: var(--color-foreground-muted, #6b7280); max-width: 80px;
      word-break: break-all;
    }}
  </style>
</head>
<body>
  <nav class="viewer-nav">
    <strong style="font-size:0.875rem">{title}</strong>
    <a href="#tokens" style="font-size:0.875rem">Tokens</a>
    <a href="#components" style="font-size:0.875rem">Components</a>
  </nav>

  <section class="viewer-section" id="tokens">
    <h2 class="section-title">Token Showcase</h2>
    <div class="swatch-grid">
{swatch_block}
    </div>
  </section>

  <section class="viewer-section" id="components">
    <h2 class="section-title">Component Gallery</h2>
    <button style="background:var(--color-primary,#2563eb);color:var(--color-primary-foreground,#fff);
      border-radius:var(--radius-interactive,8px);padding:0.5rem 1.25rem;border:none;cursor:pointer;
      font-weight:600">Primary</button>
    <div style="background:var(--color-surface-default,#fff);border-radius:var(--radius-lg,12px);
      box-shadow:var(--shadow-md,0 4px 6px rgba(0,0,0,0.07));padding:var(--spacing-lg,24px);
      border:1px solid var(--color-border,#e5e7eb);margin-top:1rem;max-width:360px">
      <p style="font-weight:600;margin-bottom:0.5rem">Card Title</p>
      <p style="color:var(--color-foreground-muted,#6b7280);font-size:0.875rem">
        Card body text rendered from this change's own design tokens.</p>
    </div>
  </section>
</body>
</html>
"""


# ─── Orchestration + manifest ──────────────────────────────────────────────

# Filenames are conventional, written inside the resolved worktree root.
UI_HTML_NAME = "UI.html"
MANIFEST_NAME = "manifest.json"

_NO_VISUAL_NOTE = (
    "No UI contract for this change — it carries no visual contract / design "
    "tokens (a non-user-facing change). Nothing to preview."
)


def render_ui(worktree: Path | str) -> dict:
    """Render the change's visual contract to UI.html, or emit nothing + note.

    Present → write ``UI.html`` (self-contained VIEWER) into the worktree and
    return ``{"ui_contract": "present", "path": <abs UI.html path>}``.

    Absent → write nothing and return ``{"ui_contract": "none", "note": ...}``
    so the cockpit shows a note rather than a broken link. Never raises for the
    absent case (TDD §2.4 / §4.2).

    Raises ``FileNotFoundError`` only when the worktree itself does not exist —
    that is a caller error, distinct from the in-scope "no visual contract"
    case.
    """
    worktree = Path(worktree)
    if not worktree.is_dir():
        raise FileNotFoundError(f"worktree not found: {worktree}")

    contract = locate_visual_contract(worktree)
    if contract is None:
        return {"ui_contract": "none", "note": _NO_VISUAL_NOTE}

    html = build_viewer_html(contract)
    ui_html = worktree / UI_HTML_NAME
    ui_html.write_text(html, encoding="utf-8")
    return {"ui_contract": "present", "path": str(ui_html)}


def write_manifest(worktree: Path | str, ui_state: dict) -> Path:
    """Merge the ui state into the change's shared manifest and return its path.

    The manifest is shared with WP-001's data-contract renderer, so this MERGES
    the ui keys (``ui_contract`` + ``path``/``note``) into any existing
    manifest rather than clobbering a sibling renderer's ``data_contract``
    entry. The write stays inside the resolved worktree root.
    """
    import json

    worktree = Path(worktree)
    manifest_path = worktree / MANIFEST_NAME

    manifest: dict = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}

    manifest.update(ui_state)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest_path
