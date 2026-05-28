"""Unit tests for `_changeset.py` — the changeset data model + deterministic core.

WP-001 (the TDD keystone). `_changeset.py` is a pure stdlib leaf module: the
data model + every pure function behind the changeset YAML contract
(`.changesets/README.md`). No network, no `gh`, no subprocess — file I/O uses
`tmp_path`, exactly like `test_change_store.py`.

Covers (one test per Definition-of-Done assertion):
  - tier_for_primitive: the full primitive→tier mapping (ADR-002), the
    breaking override, and the admin/docs-only/unknown → None case.
  - cumulative_tier: SemVer max precedence; [] → None.
  - next_version: series-agnostic patch/minor/major over BOTH the 0.x.y plugin
    series and the 1.x.y marketplace series (ADR-003); tier=None → unchanged.
  - changeset_filename: triple-key collision-proofing + slug sanitisation.
  - write_changeset / read_changesets: round-trip field fidelity; non-.yaml
    files ignored; missing dir → [].
  - the .changesets/README.md worked example parses through read_changesets so
    the contract doc and the code cannot drift (ADR-005).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import _changeset as cs


# The parent change's ULID, per the contract example in .changesets/README.md.
_CHANGE_ID = "01KSQNPBPN7W74QVAZ25F79RNH"


# ─── tier_for_primitive (ADR-002) ─────────────────────────────────────────


def test_tier_for_primitive_full_mapping():
    """Table-driven: patch primitives → patch; minor primitives → minor."""
    for primitive in ("fix", "chore", "refactor", "docs"):
        assert cs.tier_for_primitive(primitive) == "patch", primitive
    for primitive in (
        "feat", "create", "extend", "compose", "reuse",
        "strangle", "wrap", "harden", "instrument",
    ):
        assert cs.tier_for_primitive(primitive) == "minor", primitive


def test_tier_for_primitive_breaking_overrides_to_major():
    """Any primitive + breaking=True → "major" regardless of the base tier."""
    assert cs.tier_for_primitive("fix", breaking=True) == "major"
    assert cs.tier_for_primitive("create", breaking=True) == "major"
    assert cs.tier_for_primitive("docs", breaking=True) == "major"


def test_tier_for_primitive_admin_docs_only_is_none():
    """admin / docs-only (changes outside plugins/sulis/**) and any unknown
    primitive → None: the caller writes NO changeset (ADR-002)."""
    assert cs.tier_for_primitive("admin") is None
    assert cs.tier_for_primitive("docs-only") is None
    assert cs.tier_for_primitive("something-not-in-the-vocabulary") is None


# ─── cumulative_tier (SemVer max over a batch) ─────────────────────────────


def test_cumulative_tier_max_precedence():
    """The cumulative tier is the SemVer max: major > minor > patch."""
    assert cs.cumulative_tier([{"tier": "patch"}, {"tier": "minor"}]) == "minor"
    assert cs.cumulative_tier(
        [{"tier": "patch"}, {"tier": "patch"}, {"tier": "major"}]
    ) == "major"
    assert cs.cumulative_tier([{"tier": "patch"}, {"tier": "patch"}]) == "patch"


def test_cumulative_tier_empty_is_none():
    """No changesets → nothing to release → None."""
    assert cs.cumulative_tier([]) is None


# ─── next_version (series-agnostic, ADR-003) ───────────────────────────────


def test_next_version_plugin_series():
    """The 0.x.y plugin series: patch/minor/major."""
    assert cs.next_version("0.77.0", "patch") == "0.77.1"
    assert cs.next_version("0.77.0", "minor") == "0.78.0"
    assert cs.next_version("0.77.0", "major") == "1.0.0"


def test_next_version_marketplace_series():
    """The 1.x.y marketplace umbrella series — the SAME function (series
    agnostic): patch/minor/major."""
    assert cs.next_version("1.122.0", "minor") == "1.123.0"
    assert cs.next_version("1.122.0", "patch") == "1.122.1"
    assert cs.next_version("1.122.0", "major") == "2.0.0"


def test_next_version_none_tier_unchanged():
    """tier=None → the version is unchanged (admin/docs-only release)."""
    assert cs.next_version("1.122.0", None) == "1.122.0"
    assert cs.next_version("0.77.0", None) == "0.77.0"


# ─── changeset_filename (triple-key, collision-proof) ──────────────────────


def test_changeset_filename_triple_key_collision_proof():
    """Same (primitive, slug) at two distinct created_at → two distinct
    filenames — the #64-vs-#52 conflict class is structurally gone."""
    t1 = datetime(2026, 5, 28, 17, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 5, 28, 17, 31, 0, tzinfo=timezone.utc)
    name1 = cs.changeset_filename("create", "release-train", t1)
    name2 = cs.changeset_filename("create", "release-train", t2)
    assert name1 != name2
    assert name1.endswith(".yaml")
    assert name2.endswith(".yaml")
    # The datetime component is the compact UTC ISO-8601 form.
    assert "20260528T173000Z" in name1
    assert "20260528T173100Z" in name2


def test_changeset_filename_sanitises_slug():
    """A slug with spaces / caps / punctuation → a clean kebab component."""
    t = datetime(2026, 5, 28, 17, 30, 0, tzinfo=timezone.utc)
    name = cs.changeset_filename("feat", "Add Payments!! (v2)", t)
    # The slug portion is lowercased, non-alnum collapsed to single '-',
    # with no leading/trailing dashes around the component.
    assert name == "feat-add-payments-v2-20260528T173000Z.yaml"


# ─── write_changeset / read_changesets (round-trip) ────────────────────────


def test_write_read_changeset_round_trip(tmp_path):
    """Write 2 changesets; read 2 dicts back with the written fields intact."""
    d = tmp_path / ".changesets"
    t1 = datetime(2026, 5, 28, 17, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 5, 28, 17, 31, 0, tzinfo=timezone.utc)
    p1 = cs.write_changeset(
        d, change_id=_CHANGE_ID, primitive="create", tier="minor",
        touches_plugin=True, summary="Add the changeset helper.", created_at=t1,
    )
    p2 = cs.write_changeset(
        d, change_id=_CHANGE_ID, primitive="fix", tier="patch",
        touches_plugin=True, summary="Fix the journal step guard.", created_at=t2,
    )
    assert p1.exists() and p2.exists()
    assert p1 != p2

    records = cs.read_changesets(d)
    assert len(records) == 2
    by_primitive = {r["primitive"]: r for r in records}
    assert set(by_primitive) == {"create", "fix"}

    create = by_primitive["create"]
    assert create["change_id"] == _CHANGE_ID
    assert create["tier"] == "minor"
    assert create["touches_plugin"] is True
    assert create["summary"].strip() == "Add the changeset helper."
    assert create["created_at"] == "2026-05-28T17:30:00Z"

    fix = by_primitive["fix"]
    assert fix["tier"] == "patch"
    assert fix["summary"].strip() == "Fix the journal step guard."


def test_write_changeset_honours_human_slug(tmp_path):
    """WP-002 passes the change's human slug → it appears in the filename
    (the ADR-005 worked-example shape, not the raw change_id)."""
    d = tmp_path / ".changesets"
    path = cs.write_changeset(
        d, change_id=_CHANGE_ID, primitive="create", tier="minor",
        touches_plugin=True, summary="keystone", slug="release-train",
        created_at=datetime(2026, 5, 28, 17, 30, 0, tzinfo=timezone.utc),
    )
    assert path.name == "create-release-train-20260528T173000Z.yaml"


def test_read_changesets_ignores_non_yaml(tmp_path):
    """Non-.yaml files in the dir are ignored; a missing dir → []."""
    d = tmp_path / ".changesets"
    t = datetime(2026, 5, 28, 17, 30, 0, tzinfo=timezone.utc)
    cs.write_changeset(
        d, change_id=_CHANGE_ID, primitive="create", tier="minor",
        touches_plugin=True, summary="Only this one counts.", created_at=t,
    )
    # Drop noise the reader must ignore.
    (d / "README.md").write_text("# the contract doc\n", encoding="utf-8")
    (d / "notes.txt").write_text("scratch\n", encoding="utf-8")

    records = cs.read_changesets(d)
    assert len(records) == 1
    assert records[0]["primitive"] == "create"

    # Missing dir → [] (never raises).
    assert cs.read_changesets(tmp_path / "does-not-exist") == []


# ─── the contract's own examples are executable (ADR-005) ──────────────────


def test_readme_examples_parse():
    """Extract the worked-example YAML from .changesets/README.md and parse it
    through the same reader, so the documented contract and the code cannot
    drift. The doc is the contract; this test is its conformance check."""
    readme = _locate_changesets_readme()
    assert readme.exists(), f"contract doc missing: {readme}"

    records = cs.read_changeset_examples(readme)
    assert records, "no worked-example changeset YAML found in README"

    example = records[0]
    # The contract fields are all present (ADR-005's field list).
    for field in ("change_id", "primitive", "tier", "touches_plugin",
                  "summary", "created_at"):
        assert field in example, f"contract field {field!r} missing from example"
    # And they carry sane values, not empty strings.
    assert example["primitive"]
    assert example["tier"] in ("patch", "minor", "major")
    assert isinstance(example["touches_plugin"], bool)


# ─── hardening: the no-pyyaml round-trip's edge behaviours ─────────────────
#
# These pin the parser/writer branches the WP-003 bash reader and hand-editors
# rely on: naive-datetime normalisation, a false bool, multi-line summaries,
# comment/blank lines, and a quoted '#' inside a value.


def test_write_changeset_defaults_created_at_to_now_utc(tmp_path):
    """No created_at → now (UTC, tz-aware); the file lands and reads back."""
    d = tmp_path / ".changesets"
    path = cs.write_changeset(
        d, change_id=_CHANGE_ID, primitive="fix", tier="patch",
        touches_plugin=True, summary="defaulted timestamp",
    )
    assert path.exists()
    record = cs.read_changesets(d)[0]
    # created_at is a full ISO-8601 Z stamp produced from now().
    assert record["created_at"].endswith("Z")
    assert "T" in record["created_at"]


def test_write_changeset_accepts_naive_datetime_as_utc(tmp_path):
    """A naive datetime is treated as already-UTC (no tz shift)."""
    d = tmp_path / ".changesets"
    naive = datetime(2026, 5, 28, 17, 30, 0)  # no tzinfo
    cs.write_changeset(
        d, change_id=_CHANGE_ID, primitive="create", tier="minor",
        touches_plugin=True, summary="naive ts", created_at=naive,
    )
    record = cs.read_changesets(d)[0]
    assert record["created_at"] == "2026-05-28T17:30:00Z"


def test_touches_plugin_false_round_trips_as_bool(tmp_path):
    """touches_plugin=False writes `false` and reads back as a Python bool."""
    d = tmp_path / ".changesets"
    cs.write_changeset(
        d, change_id=_CHANGE_ID, primitive="create", tier="minor",
        touches_plugin=False, summary="outside the plugin",
        created_at=datetime(2026, 5, 28, 17, 30, 0, tzinfo=timezone.utc),
    )
    record = cs.read_changesets(d)[0]
    assert record["touches_plugin"] is False


def test_multiline_summary_round_trips(tmp_path):
    """A multi-line summary survives the block-scalar round-trip intact."""
    d = tmp_path / ".changesets"
    summary = "First line of the summary.\nSecond line with more detail."
    cs.write_changeset(
        d, change_id=_CHANGE_ID, primitive="feat", tier="minor",
        touches_plugin=True, summary=summary,
        created_at=datetime(2026, 5, 28, 17, 30, 0, tzinfo=timezone.utc),
    )
    record = cs.read_changesets(d)[0]
    assert record["summary"] == summary


def test_parse_tolerates_comments_and_blank_lines(tmp_path):
    """A hand-edited changeset with `# comments` and blank lines parses; the
    inline comment after a value is stripped, a quoted '#' is preserved."""
    d = tmp_path / ".changesets"
    d.mkdir(parents=True)
    (d / "feat-x-20260528T173000Z.yaml").write_text(
        "# a hand-written changeset\n"
        "change_id: 01ABC\n"
        "\n"
        "primitive: feat   # the declared primitive\n"
        'summary: "tag #release please"\n'
        "tier: minor\n"
        "touches_plugin: true\n"
        "created_at: 2026-05-28T17:30:00Z\n",
        encoding="utf-8",
    )
    record = cs.read_changesets(d)[0]
    assert record["primitive"] == "feat"           # inline comment stripped
    assert record["summary"] == "tag #release please"  # quoted '#' preserved
    assert record["tier"] == "minor"
    assert record["touches_plugin"] is True


def _locate_changesets_readme() -> Path:
    """Find .changesets/README.md by walking up from this test file to the
    repo root (the dir that contains both `.changesets/` and `plugins/`)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".changesets" / "README.md"
        if candidate.exists():
            return candidate
    # Fall back to the conventional location relative to the repo root so the
    # assertion in the test reports a useful path even when absent.
    return here.parents[5] / ".changesets" / "README.md"
