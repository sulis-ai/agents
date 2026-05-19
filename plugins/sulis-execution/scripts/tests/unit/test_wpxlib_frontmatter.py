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
