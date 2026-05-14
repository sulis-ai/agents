"""Unit tests for probe/models.py — dataclass JSON round-trips."""

from __future__ import annotations

import json

import pytest

from probe.models import (
    Capability,
    CapabilityPayload,
    ComplexFunction,
    ComplexityPayload,
    HistoryPayload,
    LanguageStats,
    StackPayload,
    Workspace,
    to_json,
)


def test_workspace_round_trip():
    w = Workspace(name="api", path="/abs/path", style="pnpm", manifest_path="/abs/m")
    d = json.loads(to_json(w))
    assert d == {"name": "api", "path": "/abs/path", "style": "pnpm", "manifest_path": "/abs/m"}


def test_stack_payload_round_trip():
    p = StackPayload(
        languages={"Python": LanguageStats(files=10, code=100, blanks=5, comments=3, complexity_total=20).__dict__},
        primary_language="Python",
        total_files=10, total_loc=100, total_complexity=20,
        frameworks=[], manifest_files_found=["pyproject.toml"],
    )
    encoded = to_json(p)
    parsed = json.loads(encoded)
    assert parsed["primary_language"] == "Python"
    assert parsed["languages"]["Python"]["code"] == 100
    assert parsed["manifest_files_found"] == ["pyproject.toml"]


def test_capability_round_trip():
    c = Capability(
        kind="class", name="Foo", file="src/foo.ts", line=10,
        language="ts", signature="export class Foo", visibility="exported",
    )
    parsed = json.loads(to_json(c))
    assert parsed["name"] == "Foo"
    assert parsed["line"] == 10


def test_complexity_payload_round_trip():
    p = ComplexityPayload(
        functions=[ComplexFunction(
            file="a.py", function="f", line_start=1, line_end=10,
            ccn=20, nloc=8, tokens=50, params=2,
        ).__dict__],
        fragile_files=[],
        threshold_ccn=15,
        threshold_file_avg=10,
    )
    parsed = json.loads(to_json(p))
    assert parsed["functions"][0]["ccn"] == 20
    assert parsed["threshold_ccn"] == 15


def test_history_payload_handles_empty():
    p = HistoryPayload(
        lookback_days=365,
        file_churn=[], high_churn_files=[], bus_factor_one=[],
        co_change_pairs=[],
        repo_first_commit_iso=None, repo_last_commit_iso=None,
    )
    parsed = json.loads(to_json(p))
    assert parsed["lookback_days"] == 365
    assert parsed["repo_first_commit_iso"] is None
