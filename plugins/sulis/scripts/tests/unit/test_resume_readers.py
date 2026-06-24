"""Unit — the live resume readers (CH-GJ9KQR WP-009 GAP-2): the REAL Working Set
+ brain readers the manager injects into the assembler, and their isolation
(a reader fault degrades to empty, never raises into the spawn).

These are pure functions of the change worktree, so they are driven directly
here (the live-path observation is the integration drive,
``test_live_resume_injection.py``; this pins the reader contract + every
degrade branch the integration drive does not exercise)."""

from __future__ import annotations

from pathlib import Path

from _session_manager.resume_readers import (
    make_brain_reader,
    make_working_set_reader,
)

_CHANGE_ID = "01KVX26BDXGJ9KQRJ11HACHMZV"
_STEM = "create-portable-agent-context"


def _write_change(
    repo_root: Path, *, ws_body: str = "the live reasoning state"
) -> None:
    changes = repo_root / ".changes"
    changes.mkdir(parents=True, exist_ok=True)
    (changes / f"{_STEM}.yaml").write_text(
        f'change_id: "{_CHANGE_ID}"\n'
        'slug: "portable-agent-context"\n'
        'primitive: "create"\n',
        encoding="utf-8",
    )
    (changes / f"{_STEM}.WORKING-SET.md").write_text(ws_body, encoding="utf-8")


# ── working set reader ────────────────────────────────────────────────────


def test_working_set_reader_reads_the_bound_changes_file(tmp_path: Path) -> None:
    _write_change(tmp_path, ws_body="problem: recover rich context")
    read = make_working_set_reader(tmp_path, _CHANGE_ID)
    assert "recover rich context" in read(_CHANGE_ID)


def test_working_set_reader_resolves_stem_from_yaml_not_a_blind_glob(
    tmp_path: Path,
) -> None:
    """A worktree with MANY changes resolves the bound one by yaml ``change_id``,
    not a blind glob of the first ``*.WORKING-SET.md``."""
    changes = tmp_path / ".changes"
    changes.mkdir(parents=True)
    # A decoy change's WORKING-SET that must NOT be picked.
    (changes / "feat-other.yaml").write_text(
        'change_id: "01OTHEROTHEROTHEROTHEROTHE"\nslug: "other"\nprimitive: "feat"\n',
        encoding="utf-8",
    )
    (changes / "feat-other.WORKING-SET.md").write_text("DECOY", encoding="utf-8")
    _write_change(tmp_path, ws_body="THE-BOUND-ONE")
    read = make_working_set_reader(tmp_path, _CHANGE_ID)
    got = read(_CHANGE_ID)
    assert "THE-BOUND-ONE" in got
    assert "DECOY" not in got


def test_working_set_reader_empty_when_no_changes_dir(tmp_path: Path) -> None:
    read = make_working_set_reader(tmp_path, _CHANGE_ID)
    assert read(_CHANGE_ID) == ""


def test_working_set_reader_empty_when_no_matching_change(tmp_path: Path) -> None:
    changes = tmp_path / ".changes"
    changes.mkdir(parents=True)
    (changes / "feat-other.yaml").write_text(
        'change_id: "01OTHEROTHEROTHEROTHEROTHE"\nslug: "x"\nprimitive: "feat"\n',
        encoding="utf-8",
    )
    read = make_working_set_reader(tmp_path, _CHANGE_ID)
    assert read(_CHANGE_ID) == ""


def test_working_set_reader_empty_when_file_missing(tmp_path: Path) -> None:
    """Yaml binding present but the WORKING-SET.md sibling absent → empty."""
    changes = tmp_path / ".changes"
    changes.mkdir(parents=True)
    (changes / f"{_STEM}.yaml").write_text(
        f'change_id: "{_CHANGE_ID}"\nslug: "portable-agent-context"\nprimitive: "create"\n',
        encoding="utf-8",
    )
    read = make_working_set_reader(tmp_path, _CHANGE_ID)
    assert read(_CHANGE_ID) == ""


def test_working_set_reader_skips_commented_and_blank_yaml_lines(
    tmp_path: Path,
) -> None:
    changes = tmp_path / ".changes"
    changes.mkdir(parents=True)
    (changes / f"{_STEM}.yaml").write_text(
        "# a comment line\n\n"
        f'change_id: "{_CHANGE_ID}"\n'
        'slug: "portable-agent-context"\n'
        'primitive: "create"\n',
        encoding="utf-8",
    )
    (changes / f"{_STEM}.WORKING-SET.md").write_text("ws here", encoding="utf-8")
    read = make_working_set_reader(tmp_path, _CHANGE_ID)
    assert "ws here" in read(_CHANGE_ID)


# ── brain reader ──────────────────────────────────────────────────────────


def _write_brain_entity(repo_root: Path, type_dir: str, name: str, ent_id: str) -> None:
    d = repo_root / ".brain" / "instances" / "product-development" / type_dir
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{ent_id}.jsonld").write_text(
        '{"id": "dna:%s:%s", "name": "%s"}\n' % (type_dir, ent_id, name),
        encoding="utf-8",
    )


def test_brain_reader_selects_relevant_types(tmp_path: Path) -> None:
    _write_brain_entity(
        tmp_path, "scenario", "a scenario", "AAA0000000000000000000000A"
    )
    _write_brain_entity(
        tmp_path, "requirement", "a requirement", "BBB0000000000000000000000B"
    )
    read = make_brain_reader(tmp_path)
    names = {e.get("name") for e in read(_CHANGE_ID)}
    assert names == {"a scenario", "a requirement"}


def test_brain_reader_skips_irrelevant_types(tmp_path: Path) -> None:
    """Lower-signal types (steps, testruns) are NOT folded in."""
    _write_brain_entity(tmp_path, "testrun", "a testrun", "CCC0000000000000000000000C")
    _write_brain_entity(
        tmp_path, "scenario", "a scenario", "DDD0000000000000000000000D"
    )
    read = make_brain_reader(tmp_path)
    names = {e.get("name") for e in read(_CHANGE_ID)}
    assert names == {"a scenario"}


def test_brain_reader_empty_when_no_brain_dir(tmp_path: Path) -> None:
    read = make_brain_reader(tmp_path)
    assert list(read(_CHANGE_ID)) == []


def test_brain_reader_skips_malformed_instance_not_fatal(tmp_path: Path) -> None:
    d = tmp_path / ".brain" / "instances" / "product-development" / "scenario"
    d.mkdir(parents=True)
    (d / "GOOD000000000000000000000G.jsonld").write_text(
        '{"id": "dna:scenario:GOOD", "name": "good one"}', encoding="utf-8"
    )
    (d / "BAD0000000000000000000000B.jsonld").write_text(
        "{ this is not json", encoding="utf-8"
    )
    read = make_brain_reader(tmp_path)
    names = [e.get("name") for e in read(_CHANGE_ID)]
    assert names == ["good one"]


def test_brain_reader_recency_bound(tmp_path: Path) -> None:
    """More than the recency cap entities → bounded to the cap (newest first)."""
    from _session_manager import resume_readers

    for i in range(resume_readers._BRAIN_RECENCY_CAP + 5):
        _write_brain_entity(tmp_path, "scenario", f"scenario {i}", f"E{i:025d}")
    read = make_brain_reader(tmp_path)
    got = list(read(_CHANGE_ID))
    assert len(got) == resume_readers._BRAIN_RECENCY_CAP


# ── isolation: an unexpected reader fault degrades to empty, never raises ──


def test_working_set_reader_isolates_unexpected_fault(
    tmp_path: Path, monkeypatch
) -> None:
    """If stem resolution raises unexpectedly the reader returns '' (isolation)
    rather than letting the fault crash the spawn."""
    from _session_manager import resume_readers

    _write_change(tmp_path)

    def _boom(*_a, **_k):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(resume_readers, "_change_stem_for", _boom)
    read = make_working_set_reader(tmp_path, _CHANGE_ID)
    assert read(_CHANGE_ID) == ""


def test_brain_reader_isolates_unexpected_fault(tmp_path: Path, monkeypatch) -> None:
    """If entity selection raises unexpectedly the reader returns [] (isolation)."""
    from _session_manager import resume_readers

    def _boom(*_a, **_k):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(resume_readers, "_select_brain_entities", _boom)
    read = make_brain_reader(tmp_path)
    assert list(read(_CHANGE_ID)) == []


def test_scan_flat_yaml_unreadable_returns_empty(tmp_path: Path) -> None:
    """A yaml path that cannot be read yields no fields (isolation) rather than
    raising — the reader then degrades to empty."""
    from _session_manager.resume_readers import _scan_flat_yaml

    # A directory (not a file) at the path → read_text raises OSError → {}.
    bogus = tmp_path / "notafile.yaml"
    bogus.mkdir()
    assert _scan_flat_yaml(bogus) == {}
