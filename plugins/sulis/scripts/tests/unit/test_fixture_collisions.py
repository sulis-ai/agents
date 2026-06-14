"""Unit tests for the shared-fixture collision check (task #106 lesson;
decompose-validation rubric Phase 6 check 6.07).

The fixture-shape-collision class: two non-dependent same-batch WPs each
author the SAME logical test fixture under divergent conventions — one as
a directory form (`x/`), the other as a flat-file form (`x.json`). No
contract seam exists (test fixtures, same-kind WPs), so the existing 6.06
contract-seam check does not catch it; it only blows up at bundled-tip CI
when the loader silently resolves one form and breaks the other WP's test.

`validate_fixture_collisions` is the WP-GRAPH-level analog of
`validate_cross_kind_contract_wiring`: it reads each WP's declared
`fixtures_created:` paths, NORMALISES dir-vs-file forms to a logical name
(strip a trailing slash and a single file extension), and FAILs when two
WPs that do not depend on each other resolve a fixture to the same logical
name. The dir/file normalisation is the crux — `sample-tool-surface/` and
`sample-tool-surface.json` MUST compare equal.

Remedy (per the rubric): serialize (add a dep) or hoist a single
fixture-authoring upstream WP the consumers `dependsOn`.
"""

from __future__ import annotations

from _wpxlib import validate_fixture_collisions


def _wp(wp_id, fixtures_created=None, dependsOn=None):
    d = {"id": wp_id, "dependsOn": dependsOn or []}
    if fixtures_created is not None:
        d["fixtures_created"] = fixtures_created
    return d


# ─── no collision ───────────────────────────────────────────────────────────


def test_empty_set_passes():
    assert validate_fixture_collisions([]) == []


def test_no_fixtures_passes():
    wps = [_wp("WP-001"), _wp("WP-002")]
    assert validate_fixture_collisions(wps) == []


def test_distinct_logical_names_pass():
    # x.json and y.json are different logical fixtures — no collision.
    wps = [
        _wp("WP-001", ["tests/fixtures/methodology/x.json"]),
        _wp("WP-002", ["tests/fixtures/methodology/y.json"]),
    ]
    assert validate_fixture_collisions(wps) == []


# ─── the crux: dir-vs-file forms of the SAME logical name collide ────────────


def test_dir_form_and_file_form_collide():
    # WP-001 authors `sample-tool-surface/` (dir + manifest); WP-002 authors
    # `sample-tool-surface.json` (flat file). Same logical fixture, divergent
    # conventions, neither depends on the other → COLLISION.
    wps = [
        _wp("WP-001", ["tests/fixtures/methodology/sample-tool-surface/"]),
        _wp("WP-002", ["tests/fixtures/methodology/sample-tool-surface.json"]),
    ]
    errs = validate_fixture_collisions(wps)
    assert any(
        "WP-001" in e and "WP-002" in e and "sample-tool-surface" in e
        for e in errs
    )


def test_identical_paths_collide():
    wps = [
        _wp("WP-001", ["tests/fixtures/methodology/x.json"]),
        _wp("WP-002", ["tests/fixtures/methodology/x.json"]),
    ]
    errs = validate_fixture_collisions(wps)
    assert any("WP-001" in e and "WP-002" in e for e in errs)


def test_dir_with_trailing_manifest_path_vs_flat_file_collide():
    # A WP may declare the dir-form fixture by its manifest path; the logical
    # name is still the parent fixture directory.
    wps = [
        _wp("WP-001", ["tests/fixtures/methodology/sample-tool-surface/"]),
        _wp("WP-002", ["tests/fixtures/methodology/sample-tool-surface.yaml"]),
    ]
    errs = validate_fixture_collisions(wps)
    assert any("sample-tool-surface" in e for e in errs)


# ─── dependency serialisation resolves the collision ────────────────────────


def test_dependency_resolves_collision():
    # If WP-002 dependsOn WP-001, the fixture is serialised (one authors, the
    # other consumes) — not a parallel-batch collision.
    wps = [
        _wp("WP-001", ["tests/fixtures/methodology/sample-tool-surface/"]),
        _wp(
            "WP-002",
            ["tests/fixtures/methodology/sample-tool-surface.json"],
            dependsOn=["WP-001"],
        ),
    ]
    assert validate_fixture_collisions(wps) == []


def test_transitive_dependency_resolves_collision():
    wps = [
        _wp("WP-001", ["tests/fixtures/methodology/x/"]),
        _wp("WP-002", dependsOn=["WP-001"]),
        _wp(
            "WP-003",
            ["tests/fixtures/methodology/x.json"],
            dependsOn=["WP-002"],
        ),
    ]
    assert validate_fixture_collisions(wps) == []


# ─── normalisation edge cases ───────────────────────────────────────────────


def test_same_basename_different_dir_does_not_collide():
    # Different directories → different logical fixtures even if basenames match.
    wps = [
        _wp("WP-001", ["tests/fixtures/a/sample.json"]),
        _wp("WP-002", ["tests/fixtures/b/sample.json"]),
    ]
    assert validate_fixture_collisions(wps) == []


def test_comma_string_fixtures_are_handled():
    wps = [
        _wp("WP-001", "tests/fixtures/methodology/sample-tool-surface/"),
        _wp("WP-002", "tests/fixtures/methodology/sample-tool-surface.json"),
    ]
    errs = validate_fixture_collisions(wps)
    assert any("sample-tool-surface" in e for e in errs)


def test_one_wp_many_fixtures_no_self_collision():
    # A single WP authoring both forms is not a peer collision (one author).
    wps = [
        _wp(
            "WP-001",
            [
                "tests/fixtures/methodology/sample-tool-surface/",
                "tests/fixtures/methodology/other.json",
            ],
        ),
    ]
    assert validate_fixture_collisions(wps) == []
