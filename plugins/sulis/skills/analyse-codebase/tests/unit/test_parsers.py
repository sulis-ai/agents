"""Unit tests for the per-runner output parsers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from probe.runners.scc_runner import _parse_scc_output
from probe.runners.astgrep_capability import _parse_astgrep_stream, _extract_name
from probe.runners.lizard_runner import _parse_lizard_warnings
from probe.runners.coupling_runner import _find_cycles


# ─── scc parser ───────────────────────────────────────────────────────────


def test_scc_parser_handles_typical_output(tmp_path: Path):
    stdout = json.dumps([
        {"Name": "Python", "Count": 5, "Code": 100, "Blank": 10, "Comment": 5, "Complexity": 20},
        {"Name": "TypeScript", "Count": 3, "Code": 50, "Blank": 5, "Comment": 0, "Complexity": 7},
    ])
    payload = _parse_scc_output(stdout, workspace_path=tmp_path)
    assert payload["primary_language"] == "Python"
    assert payload["total_files"] == 8
    assert payload["total_loc"] == 150
    assert payload["languages"]["Python"]["code"] == 100


def test_scc_parser_handles_empty_output(tmp_path: Path):
    payload = _parse_scc_output("", workspace_path=tmp_path)
    assert payload["total_files"] == 0
    assert payload["primary_language"] is None


# ─── ast-grep parser ──────────────────────────────────────────────────────


def test_extract_name_from_metavariable():
    obj = {
        "text": "class Foo",
        "metaVariables": {"single": {"NAME": {"text": "Foo"}}},
    }
    assert _extract_name(obj, kind="class") == "Foo"


def test_extract_name_from_python_lines():
    """Python bare-keyword pattern has only 'class' in text; name is in lines."""
    obj = {
        "text": "class",
        "lines": "class MyService:",
        "metaVariables": {"single": {}},
    }
    assert _extract_name(obj, kind="class") == "MyService"


def test_extract_name_handles_def():
    obj = {
        "text": "def",
        "lines": "    def process(self, item: Item) -> Result:",
        "metaVariables": {"single": {}},
    }
    assert _extract_name(obj, kind="function") == "process"


def test_astgrep_stream_parser(tmp_path: Path):
    sample = tmp_path / "x.ts"
    sample.write_text("export class Foo {}\n", encoding="utf-8")
    stream = json.dumps({
        "file": str(sample),
        "range": {"start": {"line": 0}, "end": {"line": 0}},
        "text": "class Foo",
        "metaVariables": {"single": {"NAME": {"text": "Foo"}}},
    })
    items = _parse_astgrep_stream(
        stream, workspace_path=tmp_path, language="ts", kind="class"
    )
    assert len(items) == 1
    assert items[0].name == "Foo"
    assert items[0].file == "x.ts"
    assert items[0].kind == "class"


# ─── lizard parser ────────────────────────────────────────────────────────


def test_lizard_parser_extracts_warnings(tmp_path: Path):
    stdout = (
        f"{tmp_path}/runners/x.py:42: warning: foo has 50 NLOC, 20 CCN, 200 token, 3 PARAM, 60 length, 0 ND\n"
        f"{tmp_path}/runners/x.py:120: warning: bar has 30 NLOC, 25 CCN, 150 token, 2 PARAM, 40 length, 0 ND\n"
    )
    payload = _parse_lizard_warnings(stdout, workspace_path=tmp_path)
    # Functions are dicts (already serialised)
    assert len(payload.functions) == 2
    ccns = [f["ccn"] for f in payload.functions]
    assert max(ccns) == 25
    assert payload.functions[0]["function"] == "bar"  # sorted desc by CCN


def test_lizard_parser_handles_empty(tmp_path: Path):
    payload = _parse_lizard_warnings("", workspace_path=tmp_path)
    assert payload.functions == []
    assert payload.fragile_files == []


# ─── Tarjan SCC ───────────────────────────────────────────────────────────


def test_tarjan_no_cycles():
    edges = {"a": {"b"}, "b": {"c"}, "c": set()}
    assert _find_cycles(edges) == []


def test_tarjan_simple_cycle():
    edges = {"a": {"b"}, "b": {"a"}}
    cycles = _find_cycles(edges)
    assert len(cycles) == 1
    assert sorted(cycles[0]) == ["a", "b"]


def test_tarjan_self_loop():
    edges = {"a": {"a"}}
    cycles = _find_cycles(edges)
    assert cycles == [["a"]]


def test_tarjan_disjoint_graphs():
    edges = {
        "a": {"b"}, "b": {"a"},
        "c": {"d"}, "d": {"c"},
        "e": {"f"}, "f": set(),
    }
    cycles = _find_cycles(edges)
    cycle_sets = sorted(tuple(sorted(c)) for c in cycles)
    assert cycle_sets == [("a", "b"), ("c", "d")]
