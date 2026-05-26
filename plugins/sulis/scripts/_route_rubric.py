"""Parser for the authored routing layer (`references/routing-rubric.md`).

WP-003 / TDD §3.3, §8 / ADR-003, ADR-004.

The rubric is a human-edited Markdown file with two parseable sections:

    ## Exclusions          | Skill | Reason |
    ## Trigger keywords     | Route | Trigger keywords |

`parse(text)` is pure (text in, `RubricData` out); `load(repo_root)` is the
only filesystem adapter. Table parsing reuses the existing `_wpxlib` helpers
(`find_section`, `parse_md_table`) — no new table parser (CP-01: reuse before
create). The folded-scalar limitation in `_wpxlib`'s *frontmatter* parser does
not affect its *table* helpers, which are sound and reused as-is.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from _wpxlib import find_section, parse_md_table

RUBRIC_RELPATH = Path("plugins/sulis/references/routing-rubric.md")

_EXCLUSIONS_HEADING = "## Exclusions"
_TRIGGERS_HEADING = "## Trigger keywords"


@dataclass(frozen=True)
class RubricData:
    """The authored layer: exclusions + trigger refinements (TDD §3.3)."""

    exclusions: frozenset[str]
    trigger_keywords: dict[str, tuple[str, ...]]


def _cell(row: list[str], index: int) -> str:
    """Safely read a stripped cell from a table row; '' if absent.

    Shared by both section parsers (exclusions + triggers) so neither
    repeats bounds-checked indexing (Non-Negotiable #2: extract at the
    2-consumer threshold)."""
    return row[index].strip() if len(row) > index else ""


def _section_table_text(text: str, heading: str) -> str | None:
    """Return the Markdown-table block within a section, or None if the
    section is absent. An absent section is not an error — it means that
    refinement layer simply wasn't authored (TDD §8)."""
    try:
        start, end = find_section(text, heading)
    except ValueError:
        return None
    section = text[start:end]
    # Keep only the contiguous table block (lines starting with "|"); the
    # section may carry prose before the table. parse_md_table tolerates
    # surrounding blank lines, so we hand it the table lines verbatim.
    table_lines = [ln for ln in section.splitlines() if ln.lstrip().startswith("|")]
    if not table_lines:
        return None
    return "\n".join(table_lines)


def _parse_exclusions(text: str) -> frozenset[str]:
    table_text = _section_table_text(text, _EXCLUSIONS_HEADING)
    if table_text is None:
        return frozenset()
    table = parse_md_table(table_text)
    names: set[str] = set()
    for row in table.rows:
        skill = _cell(row, 0)
        reason = _cell(row, 1)
        # ADR-004: an exclusion is a positive, authored act with a reason.
        # A blank skill or blank reason is a defect, not a valid exclusion.
        if skill and reason:
            names.add(skill)
    return frozenset(names)


def _parse_triggers(text: str) -> dict[str, tuple[str, ...]]:
    table_text = _section_table_text(text, _TRIGGERS_HEADING)
    if table_text is None:
        return {}
    table = parse_md_table(table_text)
    keywords: dict[str, tuple[str, ...]] = {}
    for row in table.rows:
        route = _cell(row, 0)
        cell = _cell(row, 1)
        if not route:
            continue
        phrases = tuple(p.strip() for p in cell.split(",") if p.strip())
        if phrases:
            keywords[route] = phrases
    return keywords


def parse(text: str) -> RubricData:
    """Parse the two Markdown sections into `RubricData`. Pure; no file I/O.

    An absent `## Trigger keywords` section yields an empty dict (an absent
    refinement is not a failure). Exclusion rows with a blank skill or blank
    reason are rejected (ADR-004).
    """
    return RubricData(
        exclusions=_parse_exclusions(text),
        trigger_keywords=_parse_triggers(text),
    )


def load(repo_root: Path) -> RubricData:
    """Thin FS adapter: read `references/routing-rubric.md`, call `parse()`."""
    rubric_path = Path(repo_root) / RUBRIC_RELPATH
    return parse(rubric_path.read_text(encoding="utf-8"))
