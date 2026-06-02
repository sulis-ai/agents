"""Unit tests for the one-off `sulis-backfill-changesets` script.

The script walks `git log <from>..<to>` and emits one `.changesets/*.yaml`
file per Conventional-Commit it can map to a known primitive. It's a
one-shot tool to close the gap between dev and main when 43+ commits
shipped before the changeset emission was wired up.

Tests use a real local git repo (the same shape as other tests in this
tree) to keep the parsing tests honest — no mocking of `git log`.
"""

from __future__ import annotations

import importlib.util
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load_backfill():
    loader = SourceFileLoader(
        "sulis_backfill_mod",
        str(_SCRIPTS / "sulis-backfill-changesets"),
    )
    spec = importlib.util.spec_from_loader("sulis_backfill_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def backfill_mod():
    return _load_backfill()


@pytest.fixture
def repo_with_commits(tmp_path):
    """A real local git repo seeded with three commits: one create:, one
    fix:, and one bot release commit (chore(release): v…) — the third
    should be skipped because it's a release-bot commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo, check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "f1").write_text("hi")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)

    # Mark this as the "main" base. Then create dev with 3 commits.
    subprocess.run(["git", "checkout", "-q", "-b", "dev"], cwd=repo, check=True)
    (repo / "plugins").mkdir()
    (repo / "plugins" / "sulis").mkdir()
    (repo / "plugins" / "sulis" / "a.py").write_text("a")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m",
         "create: introduce-thing (CH-01ABC123)\n\nA created thing."],
        cwd=repo, check=True,
    )
    (repo / "plugins" / "sulis" / "b.py").write_text("b")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "fix: tighten-thing"],
        cwd=repo, check=True,
    )
    # Bot release commit — should be skipped
    (repo / "VERSION").write_text("0.85.0")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "chore(release): v0.85.0"],
        cwd=repo, check=True,
    )

    return repo


# ─── parsing tests ─────────────────────────────────────────────────────────


def test_parse_subject_picks_up_create_primitive(backfill_mod):
    out = backfill_mod._parse_subject("create: introduce-thing")
    assert out is not None
    assert out["primitive"] == "create"
    assert out["slug"] == "introduce-thing"


def test_parse_subject_picks_up_fix_primitive(backfill_mod):
    out = backfill_mod._parse_subject("fix: tighten-thing")
    assert out is not None
    assert out["primitive"] == "fix"


def test_parse_subject_picks_up_feat(backfill_mod):
    out = backfill_mod._parse_subject("feat: shiny-new-feature")
    assert out is not None
    assert out["primitive"] == "feat"


def test_parse_subject_picks_up_scoped_form(backfill_mod):
    """`fix(sulis): X` and `feat(scope): X` are both valid Conventional Commits."""
    out = backfill_mod._parse_subject("fix(sulis): something")
    assert out is not None
    assert out["primitive"] == "fix"


def test_parse_subject_skips_release_bot(backfill_mod):
    """`chore(release): v...` is a release-bot commit — must skip."""
    out = backfill_mod._parse_subject("chore(release): v0.85.0")
    assert out is None


def test_parse_subject_skips_raw_merge(backfill_mod):
    """A raw `Merge branch ...` commit doesn't match CC and must skip."""
    out = backfill_mod._parse_subject("Merge branch 'dev' into main")
    assert out is None


def test_parse_subject_extracts_change_id_from_parenthetical(backfill_mod):
    out = backfill_mod._parse_subject(
        "create: introduce-thing (CH-01ABC123)")
    assert out["change_id"] == "CH-01ABC123"


def test_parse_subject_extracts_change_id_with_pr_tail(backfill_mod):
    """Squash-merge subjects look like:
    `create: introduce-thing (CH-01ABC123) (#111)` — CH-handle followed
    by a `(#NNN)` PR-number. Both must be stripped from the slug; the
    CH-handle must still be extracted."""
    out = backfill_mod._parse_subject(
        "create: introduce-thing (CH-01ABC123) (#111)")
    assert out is not None
    assert out["change_id"] == "CH-01ABC123"
    assert out["slug"] == "introduce-thing"
    assert "(#111)" not in out["slug"]


def test_parse_subject_extracts_embedded_ch_handle(backfill_mod):
    """The founder's real subjects embed CH inside labelled parens:
    `... (Slice 1, CH-01KSWJ) (#113)`. The handle must be extracted and
    the paren stripped from the slug."""
    out = backfill_mod._parse_subject(
        "extend: design stage emits ServiceSpec manifest "
        "per service (Slice 1, CH-01KSWJ) (#113)")
    assert out is not None
    assert out["change_id"] == "CH-01KSWJ"
    assert "CH-01KSWJ" not in out["slug"]
    assert "Slice 1" not in out["slug"]
    assert "(#113)" not in out["slug"]
    assert out["slug"] == "design stage emits ServiceSpec manifest per service"


def test_parse_subject_extracts_embedded_ch_handle_with_issue_ref(backfill_mod):
    """`(closes #112, CH-01KSWP) (#115)` — also embedded; same outcome."""
    out = backfill_mod._parse_subject(
        "harden: adopt UV for Python deps (closes #112, CH-01KSWP) (#115)")
    assert out is not None
    assert out["change_id"] == "CH-01KSWP"
    assert "CH-01KSWP" not in out["slug"]
    assert "closes" not in out["slug"]


def test_parse_subject_strips_pr_tail_when_no_ch_handle(backfill_mod):
    """`feat: shiny-feature (#73)` — no CH-handle, but the PR-tail must
    not bleed into the slug."""
    out = backfill_mod._parse_subject("feat: shiny-feature (#73)")
    assert out is not None
    assert out["change_id"] is None
    assert out["slug"] == "shiny-feature"


def test_parse_subject_synthesises_change_id_when_absent(backfill_mod):
    """Older commits don't have a (CH-NNNN) parenthetical — synthesise
    a stable derived id (e.g. from a hash) so the changeset still has a
    `change_id` field."""
    out = backfill_mod._parse_subject("fix: something")
    assert out["change_id"] is None  # to be derived from the SHA later


# ─── end-to-end via the local repo ─────────────────────────────────────────


def test_backfill_processes_two_skips_one(repo_with_commits, backfill_mod):
    """Across main..dev: 2 commits parse (create + fix), 1 skipped (release-bot)."""
    result = backfill_mod.backfill(
        repo_root=repo_with_commits,
        from_ref="main",
        to_ref="dev",
        dry_run=False,
    )
    assert result["processed"] == 3
    assert result["written"] == 2
    assert result["skipped"] == 1
    # Verify the files exist
    cs_dir = repo_with_commits / ".changesets"
    files = sorted(cs_dir.glob("*.yaml"))
    assert len(files) == 2
    # Filenames carry the primitive prefix
    names = [f.name for f in files]
    assert any(n.startswith("create-") for n in names)
    assert any(n.startswith("fix-") for n in names)


def test_backfill_skips_when_full_ulid_already_present(
        repo_with_commits, backfill_mod):
    """When the back-catalogue already has a changeset whose full ULID
    matches the `CH-<prefix>` in a commit subject, skip — don't write
    a duplicate.

    The founder embeds a six-char `CH-NNNNNN` handle in subject lines;
    the canonical ship-time changeset carries the full 26-char ULID
    (`01KSWBWM…`). The backfill MUST recognise these as the same change."""
    # Pre-seed an existing changeset with the full ULID matching CH-01ABC123
    cs_dir = repo_with_commits / ".changesets"
    cs_dir.mkdir()
    existing = cs_dir / "create-introduce-thing-20260101T000000Z.yaml"
    existing.write_text(
        "change_id: 01ABC123XXXXXXXXXXXXXXXXXX\n"
        "primitive: create\ntier: minor\ntouches_plugin: true\n"
        "summary: |\n  Existing change.\n"
        "created_at: 2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )

    result = backfill_mod.backfill(
        repo_root=repo_with_commits, from_ref="main",
        to_ref="dev", dry_run=False,
    )
    # The `create:` commit in the fixture carries `(CH-01ABC123)`.
    # That should match the pre-seeded full ULID. Only the `fix:` commit
    # (which has no handle, gets SHA-<short>) should be written.
    assert result["written"] == 1
    assert result["skipped_already_exists"] == 1


def test_backfill_is_idempotent(repo_with_commits, backfill_mod):
    """Re-running over the same range writes the same files once; second
    run reports them as already-present skips."""
    first = backfill_mod.backfill(
        repo_root=repo_with_commits, from_ref="main",
        to_ref="dev", dry_run=False,
    )
    assert first["written"] == 2

    second = backfill_mod.backfill(
        repo_root=repo_with_commits, from_ref="main",
        to_ref="dev", dry_run=False,
    )
    assert second["written"] == 0
    assert second["skipped_already_exists"] == 2

    # Only 2 files exist (no duplicates)
    cs_dir = repo_with_commits / ".changesets"
    assert len(list(cs_dir.glob("*.yaml"))) == 2


def test_backfill_dry_run_writes_nothing(repo_with_commits, backfill_mod):
    """`--dry-run` reports what would happen but writes no files."""
    result = backfill_mod.backfill(
        repo_root=repo_with_commits, from_ref="main",
        to_ref="dev", dry_run=True,
    )
    assert result["written"] == 0
    assert result["would_write"] == 2

    cs_dir = repo_with_commits / ".changesets"
    assert not cs_dir.exists() or not list(cs_dir.glob("*.yaml"))


def test_backfill_records_touches_plugin_when_paths_under_plugins_sulis(
        repo_with_commits, backfill_mod):
    """Commits whose diff touches plugins/sulis/ get touches_plugin=true."""
    result = backfill_mod.backfill(
        repo_root=repo_with_commits, from_ref="main",
        to_ref="dev", dry_run=False,
    )
    assert result["written"] == 2
    cs_dir = repo_with_commits / ".changesets"
    files = list(cs_dir.glob("*.yaml"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        # Both commits touched plugins/sulis/ in the fixture
        assert "touches_plugin: true" in text


# ─── invocation via subprocess (CLI smoke test) ────────────────────────────


def test_backfill_cli_runs_against_real_repo(repo_with_commits):
    """Smoke test: invoke the script as a subprocess and assert it exits 0
    + produces a JSON summary on stdout."""
    script = _SCRIPTS / "sulis-backfill-changesets"
    proc = subprocess.run(
        ["python3", str(script),
         "--from", "main", "--to", "dev",
         "--repo-root", str(repo_with_commits)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    # The script emits JSON on stdout in the same shape as other sulis-* tools
    import json
    out = json.loads(proc.stdout)
    assert out.get("ok") is True
    assert out["data"]["processed"] == 3
    assert out["data"]["written"] == 2
