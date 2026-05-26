"""Narrowly-scoped frontmatter reader for the routing discovery layer.

This is an EXPAND-Create module (ADR-006 / TDD §2.3): an independent reader
for the discovery contract this domain owns. It does **not** wrap, delegate
to, or modify ``_wpxlib.parse_frontmatter`` — converging the two parsers is an
explicitly-deferred future REORGANISE WP (ADR-006 / TDD §10.3).

Why a new reader exists: ``_wpxlib.parse_frontmatter`` cannot produce two
things discovery needs (verified against the live marketplace):

  * ``description: >`` (a YAML folded scalar, used by every skill) parses to
    the literal string ``">"`` there. The full joined text is the primary
    matching signal (ADR-001), so losing it is fatal.
  * ``routes_to:`` (a list of mappings on the orchestrator agent) parses to
    raw strings like ``"slug: context-cartographer"`` there, not dicts.

Scope — the closed set of value shapes this reader handles, and nothing more:

  * plain scalar              ``name: specify``            -> str
  * inline list               ``keys: [a, b]``             -> list[str]
  * block list of scalars     ``- a`` / ``- b``            -> list[str]
  * folded scalar             ``description: >``           -> str (lines joined
        with spaces; a blank line becomes a single newline, per YAML folding)
  * literal block             ``body: |``                  -> str (lines joined
        with newlines; the block's common indent is stripped)
  * nested list-of-mappings   ``routes_to:`` -> ``- slug: x`` / ``  triggers:
        [..]``                                              -> list[dict]

This is deliberately NOT a general YAML parser. Anything outside the shapes
above falls back to the plain-scalar/string behaviour ``_wpxlib`` would give
(the raw text after the colon, stripped) rather than raising — the caller can
still proceed, just without structured enrichment for that one key.

Pure functions: no file I/O at the parse boundary (callers pass text), no
``print``, stdlib only.
"""

from __future__ import annotations


class FrontmatterError(ValueError):
    """Raised on a malformed or absent frontmatter block.

    Callers surface this as a structured ``parse_failure`` rather than
    silently skipping the file (TDD R5 — surface, don't swallow).
    """


_FENCE = "---"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse a YAML-ish frontmatter block delimited by leading ``---`` lines.

    Returns ``(mapping, body)``. See the module docstring for the closed set
    of value shapes handled. Raises :class:`FrontmatterError` when the block
    is absent (no leading fence) or unterminated (no closing fence).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FENCE:
        raise FrontmatterError("frontmatter must begin with a leading '---' line")

    # Find the closing fence.
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FENCE:
            close_idx = i
            break
    if close_idx is None:
        raise FrontmatterError("frontmatter block is not terminated by a closing '---'")

    block = lines[1:close_idx]
    body = "\n".join(lines[close_idx + 1:])
    mapping = _parse_block(block)
    return mapping, body


def _indent_of(line: str) -> int:
    """Number of leading space characters on a line."""
    return len(line) - len(line.lstrip(" "))


def _join_scalar_lines(raw_lines: list[str], *, folded: bool) -> str:
    """Join the lines of a ``>`` (folded) or ``|`` (literal) block scalar.

    The block's common (minimum) indentation is stripped first. For a folded
    scalar, content lines join with single spaces and a blank line becomes a
    single newline (paragraph break). For a literal scalar, lines join with
    newlines verbatim (after the common indent is removed). This helper is the
    single line-join primitive shared by both block-scalar branches (Blue).
    """
    # Drop trailing blank lines (they carry no content for either style).
    while raw_lines and raw_lines[-1].strip() == "":
        raw_lines.pop()
    if not raw_lines:
        return ""

    indents = [_indent_of(ln) for ln in raw_lines if ln.strip() != ""]
    common = min(indents) if indents else 0
    stripped = [ln[common:] if len(ln) >= common else ln.lstrip(" ") for ln in raw_lines]

    if not folded:
        return "\n".join(stripped)

    # Folded: collapse runs of content lines into space-joined paragraphs;
    # a blank line separates paragraphs with a single newline.
    paragraphs: list[str] = []
    current: list[str] = []
    for ln in stripped:
        if ln.strip() == "":
            if current:
                paragraphs.append(" ".join(s.strip() for s in current))
                current = []
        else:
            current.append(ln)
    if current:
        paragraphs.append(" ".join(s.strip() for s in current))
    return "\n".join(paragraphs)


def _parse_inline_list(value: str) -> list[str]:
    """Parse an inline ``[a, b, c]`` sequence into a list of scalar strings."""
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    return [_unquote(item.strip()) for item in inner.split(",")]


def _unquote(value: str) -> str:
    """Strip a single matching pair of surrounding quotes, if present."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_block(block: list[str]) -> dict:
    """Parse the frontmatter block lines into a mapping.

    An explicit line-by-line state machine (boring code; no regex cleverness).
    Top-level keys live at indentation 0; everything more-indented belongs to
    the key that opened it.
    """
    mapping: dict = {}
    i = 0
    n = len(block)

    while i < n:
        line = block[i]
        if line.strip() == "":
            i += 1
            continue

        # Only top-level (unindented) keys start a new mapping entry; deeper
        # lines are consumed by the handler for the key that opened them.
        if _indent_of(line) != 0 or ":" not in line:
            i += 1
            continue

        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest in (">", ">-", ">+"):
            i, value = _consume_block_scalar(block, i + 1, folded=True)
            mapping[key] = value
        elif rest in ("|", "|-", "|+"):
            i, value = _consume_block_scalar(block, i + 1, folded=False)
            mapping[key] = value
        elif rest.startswith("[") and rest.endswith("]"):
            mapping[key] = _parse_inline_list(rest)
            i += 1
        elif rest == "":
            # A key with no inline value: either a block list, a list of
            # mappings, or simply an empty value. Peek at what follows.
            i, value = _consume_nested(block, i + 1)
            mapping[key] = value
        else:
            mapping[key] = _unquote(rest)
            i += 1

    return mapping


def _consume_block_scalar(block: list[str], start: int, *, folded: bool) -> tuple[int, str]:
    """Consume the indented lines of a ``>``/``|`` block scalar from ``start``.

    Returns ``(next_index, joined_value)``. A line belongs to the block while
    it is blank or indented deeper than column 0 (the key's column).
    """
    raw: list[str] = []
    i = start
    n = len(block)
    while i < n:
        line = block[i]
        if line.strip() != "" and _indent_of(line) == 0:
            break
        raw.append(line)
        i += 1
    return i, _join_scalar_lines(raw, folded=folded)


def _consume_nested(block: list[str], start: int) -> tuple[int, object]:
    """Consume the indented region following a bare ``key:`` line.

    Resolves to one of:
      * ``list[dict]``  when the region is a sequence of mappings
        (``- slug: x`` followed by ``  key: y`` continuation lines)
      * ``list[str]``   when the region is a sequence of scalars
        (``- a`` / ``- b``)
      * ``""``          when the region is empty (bare key, nothing under it)
    """
    i = start
    n = len(block)

    # Skip blank lines, then look at the first child line.
    while i < n and block[i].strip() == "":
        i += 1
    if i >= n or _indent_of(block[i]) == 0:
        return i, ""

    child_indent = _indent_of(block[i])
    # Collect every line belonging to this nested region (>= child_indent, or
    # blank). Blanks inside are dropped; they don't occur in our shapes.
    region: list[str] = []
    while i < n:
        line = block[i]
        if line.strip() == "":
            i += 1
            continue
        if _indent_of(line) < child_indent:
            break
        region.append(line)
        i += 1

    if not region:
        return i, ""

    if not region[0].lstrip(" ").startswith("- "):
        # Not a sequence — out of this reader's closed shape set. Fall back to
        # an empty string (the caller still gets a defined value).
        return i, ""

    return i, _parse_sequence(region)


def _parse_sequence(region: list[str]) -> list:
    """Parse a block sequence region into ``list[str]`` or ``list[dict]``.

    A ``- key: value`` item starts a mapping entry (``list[dict]``); a bare
    ``- value`` item is a scalar (``list[str]``); a non-dashed line continues
    the most recent mapping item. The two element kinds don't mix within one
    sequence in our closed shape set, so the resulting list is homogeneous.
    """
    items: list = []
    current: dict | None = None

    for line in region:
        stripped = line.lstrip(" ")
        if stripped.startswith("- "):
            entry = stripped[2:].strip()
            if ":" in entry and not (entry.startswith("[") or entry.startswith(("'", '"'))):
                # "- slug: x" — a mapping item.
                current = {}
                items.append(current)
                _set_mapping_field(current, entry)
            else:
                # "- a" — a scalar item.
                items.append(_unquote(entry))
        elif current is not None:
            # Continuation line of the current mapping item ("  key: y").
            _set_mapping_field(current, stripped)

    return items


def _set_mapping_field(target: dict, field: str) -> None:
    """Set one ``key: value`` field on a mapping-sequence item."""
    key, _, value = field.partition(":")
    key = key.strip()
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        target[key] = _parse_inline_list(value)
    else:
        target[key] = _unquote(value)
