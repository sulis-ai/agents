#!/usr/bin/env python3
"""Work Package INDEX.md generator.

Per WORK_PACKAGE_STANDARD.md WP-10: scans the per-WP markdown files under
`.architecture/{project}/work-packages/WP-*.md`, parses their YAML
frontmatter, buckets by status (WP-07 lifecycle), and renders the
founder-facing `INDEX.md` summary.

The per-WP files are authoritative; INDEX.md is derived. Never hand-edit
INDEX.md — modify the per-WP files; this script regenerates.

Usage:

    python3 plugins/sulis/_lib/wp_index.py \\
        --project {project} \\
        [--repo-root .] \\
        [--output path/to/INDEX.md] \\
        [--stdout]

Library use:

    from _lib.wp_index import generate_index
    output = generate_index(repo_root, project)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
    _HAVE_YAML = True
except ImportError:
    _HAVE_YAML = False


# ─── Status buckets (WP-07) ──────────────────────────────────────────


STATUS_BUCKETS = [
    ("ready",       "▶ Ready to start",                       ["todo"]),
    ("in_progress", "🔄 In progress",                         ["in_progress"]),
    ("blocked",     "⏸ Blocked",                              ["blocked"]),
    ("sleeping",    "💤 Sleeping — needs a decision",         ["sleeping"]),
    ("done",        "✅ Done — awaiting loop-close",          ["done"]),
    ("closed",      "🔒 Closed (loop-verified)",              ["closed"]),
    ("regressed",   "🔁 Regressed",                           ["regressed"]),
    ("abandoned",   "✗ Abandoned",                             ["abandoned"]),
]


# ─── Data shape ──────────────────────────────────────────────────────


@dataclass
class WPSummary:
    """One Work Package's frontmatter-extracted summary for the index."""

    wp_id: str
    title: str
    kind: str
    source: str
    status: str
    estimate: str = ""
    depends_on: list = field(default_factory=list)
    parent_phase: str = ""
    blocker_note: str = ""
    sleeping_note: str = ""
    claimed_by: str = ""
    started_at: str = ""
    closed_at: str = ""
    addresses_findings_count: int = 0
    invalidated_by_activity: str = ""
    path: str = ""


# ─── Frontmatter parsing ─────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter between `---` markers; return as dict.

    Prefers pyyaml when available. Falls back to a minimal scalar-only
    parser otherwise (handles the WP frontmatter shape; not full YAML).
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    if _HAVE_YAML:
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return _parse_minimal(block)


def _parse_minimal(block: str) -> dict:
    """Minimal YAML parser for the WP frontmatter shape.

    Handles: scalar values, simple lists (block + inline), nested
    one-level dicts. Not a full YAML parser; the WP frontmatter
    intentionally fits this subset.
    """
    out: dict = {}
    current_key: Optional[str] = None
    current_list: Optional[list] = None
    current_dict: Optional[dict] = None
    indent_level = 0

    for raw in block.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        # Top-level `key: value` or `key:`
        if re.match(r"^[a-zA-Z_]", line):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if not value:
                # Opens either a list or a nested dict; defer
                current_key = key
                current_list = []
                current_dict = None
                out[key] = current_list  # tentative; may be replaced by dict
            elif value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                out[key] = [_strip_quotes(x.strip()) for x in inner.split(",")] if inner else []
                current_key = None
            else:
                out[key] = _strip_quotes(value)
                current_key = None
            continue

        # Indented continuation lines
        stripped = line.lstrip()
        leading = len(line) - len(stripped)

        if stripped.startswith("- "):
            # List item under current_key
            item_value = stripped[2:].strip()
            if current_key is None:
                continue
            if ":" in item_value:
                # Dict-style list item (e.g., `- finding: <signature>`)
                k, _, v = item_value.partition(":")
                item = {k.strip(): _strip_quotes(v.strip())}
                out[current_key].append(item)
                current_dict = item
            else:
                out[current_key].append(_strip_quotes(item_value))
                current_dict = None
        elif current_dict is not None and ":" in stripped and leading >= 4:
            # Continuation of dict-style list item
            k, _, v = stripped.partition(":")
            current_dict[k.strip()] = _strip_quotes(v.strip())
        elif current_key is not None and ":" in stripped and leading >= 2:
            # Nested dict (not under a list)
            if not isinstance(out[current_key], dict):
                out[current_key] = {}
            k, _, v = stripped.partition(":")
            out[current_key][k.strip()] = _strip_quotes(v.strip())

    # Collapse empty tentative lists that were actually meant to be empty
    return out


def _strip_quotes(s: str) -> str:
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


# ─── WP summarisation ────────────────────────────────────────────────


def summarise_wp(path: Path) -> Optional[WPSummary]:
    """Read a WP file; return a summary for the index, or None if unparseable."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    fm = parse_frontmatter(text)
    wp_id = fm.get("id", "")
    if not wp_id:
        return None

    addresses = fm.get("addresses_findings") or []
    if isinstance(addresses, str):
        addresses = [addresses]
    elif not isinstance(addresses, list):
        addresses = []

    invalidated = fm.get("invalidated_by") or {}
    if not isinstance(invalidated, dict):
        invalidated = {}

    depends_on = fm.get("depends_on") or []
    if isinstance(depends_on, str):
        depends_on = [depends_on]
    elif not isinstance(depends_on, list):
        depends_on = []

    return WPSummary(
        wp_id=str(wp_id),
        title=str(fm.get("title", "")),
        kind=str(fm.get("kind", "unknown")),
        source=str(fm.get("source", "manual")),
        status=str(fm.get("status", "todo")),
        estimate=str(fm.get("estimate", "")),
        depends_on=[str(d) for d in depends_on],
        parent_phase=str(fm.get("parent_phase", "")),
        blocker_note=str(fm.get("blocker_note", "")),
        sleeping_note=str(fm.get("sleeping_note", "")),
        claimed_by=str(fm.get("claimed_by", "")),
        started_at=str(fm.get("started_at", "")),
        closed_at=str(fm.get("closed_at", "")),
        addresses_findings_count=len(addresses),
        invalidated_by_activity=str(invalidated.get("activity", "") or ""),
        path=str(path),
    )


def find_wp_files(architecture_root: Path, project: str) -> list[Path]:
    wp_dir = architecture_root / project / "work-packages"
    if not wp_dir.is_dir():
        return []
    return sorted(wp_dir.glob("WP-*.md"))


def bucket_wps(wps: list[WPSummary]) -> dict[str, list[WPSummary]]:
    """Bucket WPs by status per WP-07."""
    buckets: dict[str, list[WPSummary]] = {key: [] for key, _, _ in STATUS_BUCKETS}
    for wp in wps:
        for key, _, statuses in STATUS_BUCKETS:
            if wp.status in statuses:
                buckets[key].append(wp)
                break
        else:
            # Unknown status — treat as ready so it surfaces for review
            buckets["ready"].append(wp)
    return buckets


# ─── Rendering ───────────────────────────────────────────────────────


def render_wp_line(wp: WPSummary) -> str:
    """One line per WP for the index."""
    bits = [wp.kind]
    if wp.estimate:
        bits.append(wp.estimate)
    suffix = f"  ({', '.join(bits)})"
    if wp.addresses_findings_count:
        suffix += f" — addresses {wp.addresses_findings_count} finding{'s' if wp.addresses_findings_count != 1 else ''}"
    return f"- {wp.wp_id} — {wp.title}{suffix}"


def render_wp_subline(wp: WPSummary) -> Optional[str]:
    """Optional context line beneath the main line (claimed-by, blocker, etc.)."""
    if wp.claimed_by:
        msg = f"claimed by {wp.claimed_by}"
        if wp.started_at:
            msg += f", started {wp.started_at}"
        return f"       └─ {msg}"
    if wp.blocker_note:
        return f"       └─ {wp.blocker_note}"
    if wp.sleeping_note:
        return f"       └─ {wp.sleeping_note}"
    if wp.depends_on:
        return f"       └─ waiting on {', '.join(wp.depends_on)}"
    if wp.closed_at:
        return f"       └─ closed {wp.closed_at}"
    return None


def render_index(project: str, buckets: dict[str, list[WPSummary]]) -> str:
    out: list[str] = []
    out.append(f"# Work Packages — {project}")
    out.append("")
    out.append(
        f"_Auto-generated from `.architecture/{project}/work-packages/WP-*.md` "
        "(per WORK_PACKAGE_STANDARD WP-10). Do NOT hand-edit — modify the "
        "per-WP files; this index regenerates._"
    )
    out.append("")

    total = sum(len(b) for b in buckets.values())
    if total == 0:
        out.append("No Work Packages yet.")
        out.append("")
        out.append(
            f"Create them via `/sulis:address-findings` or by hand at "
            f"`.architecture/{project}/work-packages/WP-NNN.md` (see "
            "`WORK_PACKAGE_STANDARD.md` for the file shape)."
        )
        return "\n".join(out)

    for key, label, _statuses in STATUS_BUCKETS:
        wps = buckets[key]
        if not wps:
            continue
        out.append(f"## {label} ({len(wps)})")
        out.append("")
        for wp in sorted(wps, key=lambda w: w.wp_id):
            out.append(render_wp_line(wp))
            sub = render_wp_subline(wp)
            if sub:
                out.append(sub)
        out.append("")

    out.append("---")
    out.append("")
    out.append("**Kind distribution:** " + _kind_distribution(buckets))
    return "\n".join(out)


def _kind_distribution(buckets: dict[str, list[WPSummary]]) -> str:
    counts: dict[str, int] = {}
    for wps in buckets.values():
        for wp in wps:
            counts[wp.kind] = counts.get(wp.kind, 0) + 1
    if not counts:
        return "—"
    return ", ".join(f"{k}={n}" for k, n in sorted(counts.items()))


# ─── Public library entry ────────────────────────────────────────────


def generate_index(repo_root: Path, project: str) -> str:
    """Library entry: scan + bucket + render. Returns the INDEX.md text."""
    architecture_root = Path(repo_root) / ".architecture"
    paths = find_wp_files(architecture_root, project)
    wps = [s for s in (summarise_wp(p) for p in paths) if s is not None]
    buckets = bucket_wps(wps)
    return render_index(project, buckets)


# ─── CLI ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True,
        help="Project slug (defines .architecture/{project}/ scope)")
    parser.add_argument("--repo-root", default=".",
        help="Repository root (defaults to cwd)")
    parser.add_argument("--output", default=None,
        help="Path to write INDEX.md; defaults to .architecture/{project}/work-packages/INDEX.md")
    parser.add_argument("--stdout", action="store_true",
        help="Print to stdout instead of writing to file")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_text = generate_index(repo_root, args.project)

    if args.stdout:
        print(output_text)
        return 0

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = repo_root / ".architecture" / args.project / "work-packages" / "INDEX.md"

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
    except OSError as exc:
        print(f"error: could not write {out_path}: {exc}", file=sys.stderr)
        return 2

    # Quick stats for stderr
    wp_count = output_text.count("\n- WP-")
    print(f"wp_index: project={args.project} wps={wp_count} written={out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
