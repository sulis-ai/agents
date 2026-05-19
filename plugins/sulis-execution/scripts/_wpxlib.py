"""Shared helpers for the wpx-* CLI tools.

Stdlib only. Provides:
- Path resolution for project-relative artifacts.
- Markdown frontmatter parsing (tiny, no pyyaml dependency).
- JSON output helpers (consistent shape).
- Markdown table parsing/writing (for journal + INDEX manipulation).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────
# Path resolution
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class WpxPaths:
    """Project-relative paths for executor artifacts."""

    repo_root: Path
    project: str

    @property
    def arch_root(self) -> Path:
        return self.repo_root / ".architecture" / self.project

    @property
    def wp_dir(self) -> Path:
        return self.arch_root / "work-packages"

    @property
    def index_md(self) -> Path:
        return self.wp_dir / "INDEX.md"

    @property
    def security_dir(self) -> Path:
        return self.repo_root / ".security" / self.project

    @property
    def findings_dir(self) -> Path:
        return self.security_dir / "findings"

    @property
    def findings_register(self) -> Path:
        return self.security_dir / "findings-register.md"

    def journal(self, wp: str) -> Path:
        return self.wp_dir / f".executor-{wp}.md"

    def blocker(self, wp: str) -> Path:
        return self.wp_dir / f"BLOCKER-{wp}.md"

    def wp_file(self, wp: str) -> Path:
        # Look for WP-NNN-*.md (the file's name includes a slug)
        matches = list(self.wp_dir.glob(f"{wp}-*.md"))
        # Filter out journal/blocker/auto-draft files
        matches = [
            m for m in matches
            if not m.name.startswith(".")
            and not m.name.startswith("BLOCKER-")
        ]
        if not matches:
            raise FileNotFoundError(
                f"No WP file matching {wp}-*.md in {self.wp_dir}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"Multiple WP files match {wp}-*.md: {matches}"
            )
        return matches[0]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add --project and --repo-root to a parser."""
    parser.add_argument(
        "--project",
        required=True,
        help="Project slug (used to resolve .architecture/<project>/ paths)",
    )
    parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="Repo root directory (defaults to cwd)",
    )


def paths_from_args(args: argparse.Namespace) -> WpxPaths:
    return WpxPaths(repo_root=Path(args.repo_root).resolve(), project=args.project)


# ─────────────────────────────────────────────────────────────────────────
# JSON output
# ─────────────────────────────────────────────────────────────────────────


def emit_ok(
    data: dict | None = None,
    warnings: list[str] | None = None,
    exit_code: int = 0,
) -> None:
    """Print success JSON to stdout and exit with the given code (default 0).

    The `exit_code` parameter exists for tools that emit a
    structured-JSON result alongside a non-zero exit semantic.
    Concrete use case: `wpx-pipeline` emits a fully-formed result
    object with `outcome="blocker"` and `exit_code=1` so the calling
    session's `Bash(run_in_background)` notification can distinguish
    a clean pipeline-blocker (exit 1, structured JSON readable from
    the stdout file) from a successful pipeline (exit 0) or an
    internal-error crash (exit 2 via emit_internal_error).

    For normal success in every other wpx-* tool, the default
    exit_code=0 preserves the prior contract.
    """
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    if warnings:
        payload["warnings"] = warnings
    print(json.dumps(payload, indent=2, sort_keys=True))
    sys.exit(exit_code)


def emit_error(message: str, context: dict | None = None) -> None:
    """Print error JSON to stdout, error to stderr, exit 1 (expected failure)."""
    payload = {"ok": False, "error": message}
    if context is not None:
        payload["context"] = context
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def emit_internal_error(exc: BaseException) -> None:
    """Print traceback to stderr, exit 2 (bug)."""
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    sys.exit(2)


def cli_main(parser: argparse.ArgumentParser, handlers: dict) -> None:
    """Run a CLI tool with subcommand dispatch."""
    args = parser.parse_args()
    handler = handlers.get(args.subcommand)
    if handler is None:
        emit_error(f"Unknown subcommand: {args.subcommand}")
    try:
        handler(args)
    except FileNotFoundError as e:
        emit_error(str(e))
    except ValueError as e:
        emit_error(str(e))
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001
        emit_internal_error(e)


# ─────────────────────────────────────────────────────────────────────────
# Markdown frontmatter (YAML-like, tiny inline parser)
# ─────────────────────────────────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str]:
    """Parse a Markdown file's YAML-like frontmatter.

    Supports:
      key: value          (scalar)
      key:                (start of list)
        - item1
        - item2
      key: [a, b, c]      (inline list)

    Returns (frontmatter_dict, body_after_frontmatter).
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fm_text = match.group(1)
    body = text[match.end():]
    fm: dict[str, str | list[str]] = {}
    current_list_key: str | None = None
    for raw_line in fm_text.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        if current_list_key is not None and line.startswith("  - "):
            # Continue list
            item = line[4:].strip().strip("'\"")
            assert isinstance(fm[current_list_key], list)
            fm[current_list_key].append(item)  # type: ignore[union-attr]
            continue
        # New key
        current_list_key = None
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            # Start of a list
            fm[key] = []
            current_list_key = key
        elif rest.startswith("[") and rest.endswith("]"):
            # Inline list
            inner = rest[1:-1]
            items = [i.strip().strip("'\"") for i in inner.split(",") if i.strip()]
            fm[key] = items
        else:
            # Scalar
            value = rest.strip("'\"")
            fm[key] = value
    return fm, body


def read_frontmatter(path: Path) -> dict[str, str | list[str]]:
    text = path.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(text)
    return fm


# ─────────────────────────────────────────────────────────────────────────
# Markdown table helpers
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class MdTable:
    """Lightweight Markdown table representation."""

    headers: list[str] = field(default_factory=list)
    alignments: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def render(self) -> str:
        lines = []
        lines.append("| " + " | ".join(self.headers) + " |")
        lines.append("|" + "|".join(self.alignments or ["---"] * len(self.headers)) + "|")
        for row in self.rows:
            # Pad / truncate to headers length
            padded = list(row) + [""] * (len(self.headers) - len(row))
            padded = padded[: len(self.headers)]
            lines.append("| " + " | ".join(padded) + " |")
        return "\n".join(lines)


def parse_md_table(table_text: str) -> MdTable:
    """Parse a Markdown table block (starting with | header |)."""
    lines = [ln for ln in table_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return MdTable()
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    alignments = [c.strip() for c in lines[1].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return MdTable(headers=headers, alignments=alignments, rows=rows)


def find_section(text: str, heading: str) -> tuple[int, int]:
    """Find the byte range of a Markdown section by heading.

    Returns (start, end) where start is the first char of the section's
    heading line and end is one past the last char before the next heading
    of equal-or-higher level (or EOF).

    Raises ValueError if the heading is not found.
    """
    # Match "## Heading" or "# Heading" — derive level from input
    level = 0
    for ch in heading:
        if ch == "#":
            level += 1
        else:
            break
    title = heading[level:].strip()
    pattern = re.compile(
        rf"^(#{{{level}}}) {re.escape(title)}\s*$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Section not found: {heading}")
    start = match.start()
    # Find next heading of equal or higher level
    next_pattern = re.compile(
        rf"^#{{1,{level}}} \S",
        re.MULTILINE,
    )
    next_match = next_pattern.search(text, pos=match.end())
    end = next_match.start() if next_match else len(text)
    return start, end


def replace_section(text: str, heading: str, new_content: str) -> str:
    """Replace a section's content (everything after the heading line, up to next heading).

    new_content should NOT include the heading itself.
    """
    start, end = find_section(text, heading)
    # Find end of heading line
    nl = text.index("\n", start) + 1
    return text[:nl] + new_content + (text[end:] if end < len(text) else "")
