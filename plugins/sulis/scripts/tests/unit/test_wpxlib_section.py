"""Unit tests for _wpxlib.find_section and replace_section."""

from __future__ import annotations

import pytest

from _wpxlib import find_section, replace_section


SAMPLE = """# Top

## First

content of first

## Second

content of second

### Nested

deeper content

## Third

content of third
"""


def test_find_section_returns_byte_range():
    start, end = find_section(SAMPLE, "## Second")
    section = SAMPLE[start:end]
    assert section.startswith("## Second")
    assert "content of second" in section
    assert "Nested" in section  # nested h3 is part of the section
    assert "## Third" not in section


def test_find_section_stops_at_next_same_level():
    start, end = find_section(SAMPLE, "## First")
    section = SAMPLE[start:end]
    assert section.startswith("## First")
    assert "content of first" in section
    assert "## Second" not in section


def test_find_section_raises_on_missing():
    with pytest.raises(ValueError, match="Section not found"):
        find_section(SAMPLE, "## Nonexistent")


def test_replace_section_preserves_heading():
    out = replace_section(SAMPLE, "## Second", "\nNEW CONTENT\n\n")
    assert "## Second" in out
    assert "NEW CONTENT" in out
    assert "content of second" not in out
    # Surrounding sections unchanged
    assert "content of first" in out
    assert "content of third" in out


def test_find_section_at_end_of_file():
    start, end = find_section(SAMPLE, "## Third")
    section = SAMPLE[start:end]
    assert section.startswith("## Third")
    assert end == len(SAMPLE)
