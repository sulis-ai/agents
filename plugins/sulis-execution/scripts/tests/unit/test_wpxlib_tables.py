"""Unit tests for _wpxlib.MdTable and parse_md_table."""

from __future__ import annotations

from _wpxlib import MdTable, parse_md_table


def test_parse_basic_table():
    text = """| A | B | C |
|---|---|---|
| 1 | 2 | 3 |
| 4 | 5 | 6 |
"""
    table = parse_md_table(text)
    assert table.headers == ["A", "B", "C"]
    assert table.rows == [["1", "2", "3"], ["4", "5", "6"]]


def test_parse_table_with_alignments():
    text = """| A | B |
|---:|---|
| 1 | 2 |
"""
    table = parse_md_table(text)
    assert table.alignments == ["---:", "---"]


def test_parse_empty_table():
    text = """| A | B |
|---|---|
"""
    table = parse_md_table(text)
    assert table.headers == ["A", "B"]
    assert table.rows == []


def test_render_round_trip():
    table = MdTable(
        headers=["A", "B"],
        alignments=["---", "---"],
        rows=[["x", "y"], ["z", "w"]],
    )
    out = table.render()
    parsed = parse_md_table(out)
    assert parsed.headers == ["A", "B"]
    assert parsed.rows == [["x", "y"], ["z", "w"]]


def test_render_pads_ragged_rows():
    table = MdTable(
        headers=["A", "B", "C"],
        alignments=["---", "---", "---"],
        rows=[["x"]],  # missing B and C cells
    )
    out = table.render()
    # Should pad to 3 cells
    parsed = parse_md_table(out)
    assert len(parsed.rows[0]) == 3
    assert parsed.rows[0][0] == "x"
    assert parsed.rows[0][1] == ""
    assert parsed.rows[0][2] == ""


def test_parse_table_handles_blank_lines():
    text = """
| A | B |
|---|---|
| 1 | 2 |

"""
    table = parse_md_table(text)
    assert table.headers == ["A", "B"]
    assert table.rows == [["1", "2"]]
