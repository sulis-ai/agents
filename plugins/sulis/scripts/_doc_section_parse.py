"""Shared markdown-section parser for the document-section assertion scripts.

This is the single source of header detection (WP-003 Blue): every
``_assert_*.py`` document inspector parses sections through this module rather
than carrying its own header regex. Keeping detection in one place means the
five scripts agree on what "a section" is — a divergence here would let one
asserter pass a document another would fail.

A *section* is an ATX markdown heading (``## Name`` … ``###### Name``) and the
lines beneath it up to the next heading of the same-or-shallower depth. We treat
``# Title`` (depth 1, the document title) as a heading too, so a doc with only a
top-level title and no sub-sections parses cleanly.

Header names are normalised for comparison: stripped, lower-cased, and inner
whitespace collapsed — so ``## NFR`` and ``##  nfr `` match. The original
(display) name is preserved alongside the normalised key.

Pure — no I/O. Callers read the file and pass the text in. Stdlib only,
Python 3.11-safe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# An ATX heading line: 1–6 leading '#', a space, then the heading text.
# Trailing '#' run (closed ATX, e.g. "## Name ##") is stripped from the text.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def normalise_header(name: str) -> str:
    """Normalise a header name for comparison: strip, lower-case, collapse
    inner whitespace. ``"  Threat  Model "`` → ``"threat model"``."""
    return re.sub(r"\s+", " ", name.strip()).lower()


@dataclass(frozen=True)
class Section:
    """One parsed markdown section."""

    name: str        # display name, as written (e.g. "Threat Model")
    key: str         # normalised name for comparison (e.g. "threat model")
    level: int       # heading depth (1–6)
    body: str        # the lines beneath this heading, up to the next sibling-
                     # or-shallower heading; leading/trailing blank lines trimmed


def parse_sections(text: str) -> list[Section]:
    """Parse all ATX-heading sections from ``text``, in document order.

    Each section's ``body`` runs from the line after its heading to the line
    before the next heading whose level is the same or shallower (a deeper
    sub-heading is part of the parent's body, mirroring how a reader nests
    them). Fenced code blocks are not specially handled — a ``#`` inside a
    fence is rare in our design docs and would only ever cause a *stricter*
    parse, never a missed real heading.
    """
    lines = text.splitlines()
    headings: list[tuple[int, int, str]] = []  # (line_index, level, name)
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            name = m.group(2).strip()
            headings.append((i, level, name))

    sections: list[Section] = []
    for idx, (line_i, level, name) in enumerate(headings):
        # Body ends at the next heading of same-or-shallower level.
        body_end = len(lines)
        for next_line_i, next_level, _ in headings[idx + 1 :]:
            if next_level <= level:
                body_end = next_line_i
                break
        body = "\n".join(lines[line_i + 1 : body_end]).strip()
        sections.append(
            Section(name=name, key=normalise_header(name), level=level, body=body)
        )
    return sections


def section_keys(text: str) -> set[str]:
    """The set of normalised header keys present in ``text``."""
    return {s.key for s in parse_sections(text)}


def find_section(text: str, name: str) -> Section | None:
    """Return the first section whose normalised name matches ``name``
    (also normalised), or None if absent."""
    target = normalise_header(name)
    for section in parse_sections(text):
        if section.key == target:
            return section
    return None
