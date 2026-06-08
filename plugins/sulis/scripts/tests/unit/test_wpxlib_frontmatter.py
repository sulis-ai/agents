"""Unit tests for _wpxlib.parse_frontmatter and read_frontmatter."""

from __future__ import annotations

from _wpxlib import parse_frontmatter, read_frontmatter


def test_parses_scalar_fields():
    text = """---
id: WP-001
title: First WP
status: pending
---

# Body
"""
    fm, body = parse_frontmatter(text)
    assert fm["id"] == "WP-001"
    assert fm["title"] == "First WP"
    assert fm["status"] == "pending"
    assert body.strip().startswith("# Body")


def test_parses_inline_list():
    text = """---
id: WP-001
dependsOn: [WP-A, WP-B, WP-C]
blocks: []
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm["dependsOn"] == ["WP-A", "WP-B", "WP-C"]
    assert fm["blocks"] == []


def test_parses_multiline_list():
    text = """---
id: WP-001
dependsOn:
  - WP-A
  - WP-B
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm["dependsOn"] == ["WP-A", "WP-B"]


def test_handles_missing_frontmatter():
    text = "# No frontmatter here\n"
    fm, body = parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_strips_quotes_from_scalar_values():
    text = """---
title: "Quoted title"
other: 'single quotes'
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm["title"] == "Quoted title"
    assert fm["other"] == "single quotes"


def test_ignores_blank_and_comment_lines():
    text = """---
# leading comment
id: WP-001

title: First
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm["id"] == "WP-001"
    assert fm["title"] == "First"


def test_read_frontmatter_from_file(tmp_path):
    p = tmp_path / "wp.md"
    p.write_text("""---
id: WP-005
title: From file
---

body
""")
    fm = read_frontmatter(p)
    assert fm["id"] == "WP-005"
    assert fm["title"] == "From file"


# #104 — snake_case alias + inline `#` comments


def test_depends_on_snake_case_aliases_to_dependsOn():
    """#104 — SEA historically authored `depends_on` (snake) while every
    wpx/execution reader expects `dependsOn` (camel). The parser must alias
    snake-case spelling to the canonical camel-case so an authoring drift
    doesn't silently zero the dep set (and let list-ready dispatch a WP
    whose deps weren't met)."""
    text = """---
id: WP-003
title: Drift example
depends_on: [WP-001, WP-002]
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm.get("dependsOn") == ["WP-001", "WP-002"], (
        f"snake-case `depends_on` must surface as camel `dependsOn`; got "
        f"keys={list(fm)}"
    )


def test_depends_on_snake_case_multiline_list_aliases():
    text = """---
id: WP-003
depends_on:
  - WP-001
  - WP-002
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm.get("dependsOn") == ["WP-001", "WP-002"]


def test_strips_inline_comment_from_scalar():
    """#104 — `primitive: create  # noop` corrupted the parsed value to
    `create  # noop`, then validate_wp_primitive rejected it. Strip inline
    `# comment` from scalars (and only when preceded by whitespace, so a
    `#` glued to a value like `#deadbeef` stays intact)."""
    text = """---
primitive: create  # this is a placeholder
status: pending   # filed by SEA, not yet started
title: Honest #1
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm["primitive"] == "create"
    assert fm["status"] == "pending"
    # Glued `#` (no leading space) is part of the value, not a comment.
    assert fm["title"] == "Honest #1"


def test_strips_inline_comment_from_list_items():
    """Inline comments must also strip from `  - item  # comment` list items
    so a single commented dep doesn't corrupt the whole dependsOn list."""
    text = """---
dependsOn:
  - WP-A   # the contract WP
  - WP-B
  - WP-C   # behind a feature flag
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm["dependsOn"] == ["WP-A", "WP-B", "WP-C"]


def test_strips_inline_comment_from_inline_list_items():
    """Same for the inline `[a, b, c]` shape — each item's trailing comment
    must strip."""
    text = """---
dependsOn: [WP-A, WP-B, WP-C]  # whole-list comment is naturally swallowed
---
"""
    fm, _ = parse_frontmatter(text)
    assert fm["dependsOn"] == ["WP-A", "WP-B", "WP-C"]
