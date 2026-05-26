"""Unit tests for _route_rubric — the authored routing layer parser (WP-003).

Covers TDD §3.3 (RubricData), §8 (rubric file format), §10.1 R13.
The parser reuses _wpxlib table helpers (parse_md_table, find_section);
these tests pin its contract: pure parse() + thin load() FS adapter.
"""

from __future__ import annotations

from pathlib import Path

from _route_rubric import RubricData, load, parse

# A fixture rubric string carrying both parseable sections (TDD §8 shape).
FIXTURE_RUBRIC = """# Routing Rubric — the authored routing layer

> Inventory is derived; this file holds only exclusions + trigger refinements.

## Exclusions

Every exclusion needs a reason.

| Skill | Reason |
|---|---|
| requirements-templates | template; consumed by requirements-analyst, not a route |
| index-specifications | meta; rebuilds an index, not founder-facing intent |

## Trigger keywords

Additive only — never removes the description signal.

| Route | Trigger keywords |
|---|---|
| check-security | secrets, vulnerability, leak |
| dashboard | what am I working on, in flight, overview |
"""


def test_parse_exclusions_and_triggers():
    """R13 — both sections parse into a RubricData with the expected
    exclusions frozenset and trigger_keywords dict."""
    data = parse(FIXTURE_RUBRIC)
    assert isinstance(data, RubricData)
    assert data.exclusions == frozenset(
        {"requirements-templates", "index-specifications"}
    )
    assert data.trigger_keywords["check-security"] == (
        "secrets",
        "vulnerability",
        "leak",
    )
    assert data.trigger_keywords["dashboard"] == (
        "what am I working on",
        "in flight",
        "overview",
    )


def test_trigger_keywords_split_into_tuple():
    """A comma-separated trigger cell becomes a trimmed tuple."""
    data = parse(FIXTURE_RUBRIC)
    assert data.trigger_keywords["check-security"] == (
        "secrets",
        "vulnerability",
        "leak",
    )
    # No stray empties or whitespace
    for phrases in data.trigger_keywords.values():
        for p in phrases:
            assert p == p.strip()
            assert p != ""


def test_missing_section_is_empty_not_error():
    """A rubric with only an Exclusions section yields empty
    trigger_keywords — an absent refinement is not a failure."""
    only_exclusions = """# Routing Rubric

## Exclusions

| Skill | Reason |
|---|---|
| jargon | maintenance/lint; not founder intent |
"""
    data = parse(only_exclusions)
    assert data.exclusions == frozenset({"jargon"})
    assert data.trigger_keywords == {}


def test_load_reads_real_rubric_file():
    """load(repo_root) against the authored references/routing-rubric.md
    returns a RubricData whose exclusions contain the seeded names —
    proves the authored file and the parser agree."""
    # test file: plugins/sulis/scripts/tests/unit/test_route_rubric.py
    # parents: [0]unit [1]tests [2]scripts [3]sulis [4]plugins [5]repo_root
    repo_root = Path(__file__).resolve().parents[5]
    rubric_path = repo_root / "plugins" / "sulis" / "references" / "routing-rubric.md"
    assert rubric_path.is_file(), f"authored rubric missing at {rubric_path}"
    data = load(repo_root)
    assert isinstance(data, RubricData)
    # Seeded §7.4 exclusion names (reconciled against the live tree).
    for name in (
        "requirements-templates",
        "index-specifications",
        "requirements-validation",
        "consolidate-into-sulis",
        "backfill-gates",
        "backfill-code-review",
        "jargon",
        "orchestrator",
    ):
        assert name in data.exclusions, f"{name} missing from authored exclusions"
    # Every exclusion is a non-empty name (closed-world: no blank rows).
    for name in data.exclusions:
        assert name and name == name.strip()


def test_exclusions_reject_blank_reason():
    """ADR-004: a blank-reason exclusion row is a defect, not a valid
    exclusion — it MUST NOT silently become an exclusion."""
    blank_reason = """# Routing Rubric

## Exclusions

| Skill | Reason |
|---|---|
| good-skill | a real reason |
| bad-skill |  |
"""
    data = parse(blank_reason)
    assert "good-skill" in data.exclusions
    assert "bad-skill" not in data.exclusions
