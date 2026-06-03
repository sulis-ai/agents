"""Integration test for the store-walk migration runner (WP-006, ADR-004).

`migrate_store(base_dir, domain)` walks every
`{base_dir}/{domain}/lifecyclerun/*.jsonld`, migrates each v1 instance to v2
(reject-on-invalid, idempotent), and rewrites it in place.

CRITICAL — this test authors a SELF-CONTAINED v1 fixture corpus in a tmp dir.
It NEVER copies or mutates the marketplace's live `.brain/instances`. A prior
attempt at this WP copied the real store as the fixture source and ran the
real migration in-place, which made the suite order-dependent and
non-idempotent on CI (the live store was already-v2 by the time the copied
corpus was read). The fixture corpus here is built from scratch every run.

The corpus is deliberately mixed-state:
  - a minimal v1 instance (the small `step_name`-only shape);
  - a rich v1 instance (JSON-LD envelope + legacy `_`-prefixed fields) plus a
    `.journal.md` companion that must be left untouched;
  - one already-v2 instance, to prove idempotency over a mixed store.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from migrate_lifecyclerun_v1_to_v2 import main, migrate_store


_DOMAIN = "product-development"

_STEP_CHANGE_STARTED = "dna:step:01KT61X5ST01CHANGESTART00A"

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_VENDORED = (
    _SCRIPTS_DIR.parent
    / "brain"
    / "compiled"
    / "product-development"
    / "lifecyclerun.schema.json"
)


def _schema() -> dict:
    return json.loads(_VENDORED.read_text())


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True))


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """Author a self-contained mixed-state v1 corpus under a tmp base_dir."""
    base = tmp_path / ".brain" / "instances"
    runs = base / _DOMAIN / "lifecyclerun"

    # minimal v1
    _write(
        runs / "Q0GXFX856ZY9M7W43YCX3KSE4K.jsonld",
        {
            "at": "2026-06-02T13:55:02Z",
            "id": "dna:lifecyclerun:Q0GXFX856ZY9M7W43YCX3KSE4K",
            "outcome": "completed",
            "step_name": "wpx-pipeline-success:WP-001",
            "sys_status": "active",
        },
    )

    # rich v1 + its journal companion
    _write(
        runs / "01KT419R8MQBQ6BNZPXDSKZBHZ.jsonld",
        {
            "@context": {"@vocab": "https://sulis.co/dna/"},
            "@id": "dna:lifecyclerun:01KT419R8MQBQ6BNZPXDSKZBHZ",
            "@type": "lifecyclerun",
            "id": "dna:lifecyclerun:01KT419R8MQBQ6BNZPXDSKZBHZ",
            "step_name": "faithful-generation-harness",
            "at": "2026-06-02T00:00:00Z",
            "outcome": "completed",
            "sys_status": "active",
            "confidence": 0.88,
            "_workflow": "dna:workflow:01KT3GM8ZF8PC7RJSGSE5JE7QQ",
            "_final_verdict": "partial-unattributed",
        },
    )
    journal = runs / "01KT419R8MQBQ6BNZPXDSKZBHZ.journal.md"
    journal.write_text("# harness journal\n\nleave me alone\n")

    # already-v2 (must be left untouched — mixed-state idempotency)
    _write(
        runs / "01KT61V2A1READYM1GRATED00A.jsonld",
        {
            "id": "dna:lifecyclerun:01KT61V2A1READYM1GRATED00A",
            "step": _STEP_CHANGE_STARTED,
            "at": "2026-06-03T00:00:00Z",
            "outcome": "completed",
            "sys_status": "active",
        },
    )
    return base


def _all_runs(base: Path) -> list[Path]:
    return sorted((base / _DOMAIN / "lifecyclerun").glob("*.jsonld"))


def test_no_v1_remains_after_run(corpus: Path) -> None:
    """After running on the fixture corpus, zero `step_name`-bearing files
    remain and every instance validates against the vendored v2 schema."""
    summary = migrate_store(corpus, _DOMAIN)

    # The two v1 instances were migrated; the already-v2 one was skipped.
    assert summary["migrated"] == 2
    assert summary["skipped"] == 1

    validator = jsonschema.Draft202012Validator(_schema())
    for path in _all_runs(corpus):
        doc = json.loads(path.read_text())
        assert "step_name" not in doc, f"{path.name} still carries step_name"
        assert "step_label" not in doc
        assert "step" in doc
        assert list(validator.iter_errors(doc)) == [], f"{path.name} invalid"


def test_run_is_idempotent(corpus: Path) -> None:
    """A second run mutates nothing: every instance now carries `step`, so
    all are skipped, and the on-disk bytes are unchanged."""
    migrate_store(corpus, _DOMAIN)
    after_first = {p.name: p.read_text() for p in _all_runs(corpus)}

    summary = migrate_store(corpus, _DOMAIN)
    assert summary["migrated"] == 0
    assert summary["skipped"] == 3

    after_second = {p.name: p.read_text() for p in _all_runs(corpus)}
    assert after_first == after_second


def test_journal_companion_untouched(corpus: Path) -> None:
    """Non-`.jsonld` companions (the harness `.journal.md`) are never walked
    or rewritten."""
    journal = corpus / _DOMAIN / "lifecyclerun" / "01KT419R8MQBQ6BNZPXDSKZBHZ.journal.md"
    before = journal.read_text()
    migrate_store(corpus, _DOMAIN)
    assert journal.read_text() == before


def test_missing_store_is_a_noop(tmp_path: Path) -> None:
    """A base_dir with no lifecyclerun store migrates nothing rather than
    raising — graceful for a fresh / downstream repo."""
    summary = migrate_store(tmp_path / "nonexistent", _DOMAIN)
    assert summary["migrated"] == 0
    assert summary["skipped"] == 0


def test_dry_run_reports_without_writing(corpus: Path) -> None:
    """`--dry-run` reports what would change but writes nothing — the v1
    files keep their `step_name`."""
    minimal = corpus / _DOMAIN / "lifecyclerun" / "Q0GXFX856ZY9M7W43YCX3KSE4K.jsonld"
    before = minimal.read_text()
    summary = migrate_store(corpus, _DOMAIN, dry_run=True)
    assert summary["migrated"] == 2
    assert minimal.read_text() == before  # untouched
    assert "step_name" in json.loads(minimal.read_text())


def test_cli_main_migrates_explicit_base_dir(corpus: Path, capsys) -> None:
    """The CLI `main(--base-dir ...)` runs the migration and prints a summary
    line; the live store default is not touched because an explicit base-dir
    is passed (the invocation proven on the fixture corpus, never the real
    `.brain/instances`)."""
    rc = main(["--base-dir", str(corpus), "--domain", _DOMAIN])
    assert rc == 0
    out = capsys.readouterr().out
    assert "migrated 2" in out
    assert "skipped 1" in out
    # The on-disk effect is real: no v1 remains.
    for path in _all_runs(corpus):
        assert "step_name" not in json.loads(path.read_text())
