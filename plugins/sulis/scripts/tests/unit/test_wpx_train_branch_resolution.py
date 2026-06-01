"""Unit tests for resolve_wp_branch — read-side slug tolerance.

Background (the bug the fix addresses):

  ``wpx-train queue-list`` (and ``compute_wp_status``) derive the
  expected feat-branch name from the WP file: ``feat/wp-NNN-<slug>``
  where ``<slug>`` comes from the WP filename ``WP-NNN-<slug>.md``.

  When the executor pushes a feat branch with a SHORTER name than the
  WP-file's slug (an observed real-world drift — e.g. WP-008 file
  ``WP-008-wire-drift-detector-into-branch-ci.md`` but pushed branch
  ``feat/wp-008-wire-drift-detector``), the train reports
  ``"reason": "status step-7-complete but origin branch missing"`` and
  the WP isn't shipped — even though there IS a ``feat/wp-008-*``
  branch on origin with the WP's work.

The fix:

  ``resolve_wp_branch(wp_id, repo, wp_dir, *, gh=None)`` returns the
  feat-branch on origin matching the WP, in this priority order:

    1. Slug-literal match (``feat/wp-NNN-<slug-from-file>``) — preserves
       byte-for-byte the historical happy path.
    2. Fuzzy ``feat/wp-NNN-*`` match on origin. If exactly one such
       branch exists, use it. Surface a warning that the literal slug
       differs from the actual branch.
    3. Multiple ``feat/wp-NNN-*`` candidates → most-recently-pushed
       (committerdate) wins; warn that the choice is ambiguous.
    4. Zero candidates → return None (fallthrough to the existing
       "origin branch missing" path).

The tests below cover all four branches plus the warning surface.
"""

from __future__ import annotations

import _wpxlib


# ─── Fixtures ─────────────────────────────────────────────────────────────


def _seed_wp_file(wp_dir, wp_id: str, slug: str) -> None:
    """Create an empty WP-{id}-{slug}.md file so _wp_slug_from_file resolves."""
    wp_dir.mkdir(parents=True, exist_ok=True)
    (wp_dir / f"{wp_id}-{slug}.md").write_text(f"# {wp_id}\n", encoding="utf-8")


def _stub_gh(
    monkeypatch,
    *,
    branches_present: set[str] | None = None,
    matching_branches: dict[str, list[dict]] | None = None,
) -> None:
    """Stub gh helpers used by resolve_wp_branch.

    Args:
        branches_present: branches the literal-match path will find via
            ``_gh_branch_exists``.
        matching_branches: maps a ``feat/wp-NNN-*`` prefix glob (e.g.
            ``"feat/wp-008-*"``) to a list of ``{"name": ..., "committerdate":
            ISO8601}`` dicts ordered however the test wants (the helper
            sorts internally).
    """
    branches_present = branches_present or set()
    matching_branches = matching_branches or {}

    def fake_branch_exists(repo, branch, *, gh=None):
        return branch in branches_present

    def fake_list_matching_branches(repo, pattern, *, gh=None):
        # Pattern is ``feat/wp-{nnn}-*``; look up by exact pattern key.
        return list(matching_branches.get(pattern, []))

    monkeypatch.setattr(_wpxlib, "_gh_branch_exists", fake_branch_exists)
    monkeypatch.setattr(
        _wpxlib,
        "_gh_list_matching_branches",
        fake_list_matching_branches,
    )


# ─── 1. slug-literal exact match (characterisation — preserves behaviour) ──


def test_resolve_slug_literal_match(tmp_project, monkeypatch):
    """When ``feat/wp-NNN-<slug>`` exists on origin, return it as-is and
    DO NOT consult the fuzzy-match path.

    This is the historical happy path. Behaviour must be byte-for-byte
    unchanged for any project whose executor uses full slugs.
    """
    _seed_wp_file(tmp_project.wp_dir, "WP-001", "long-full-slug-name")
    _stub_gh(
        monkeypatch,
        branches_present={"feat/wp-001-long-full-slug-name"},
        # Pre-populate matching_branches with a different candidate to
        # PROVE the function returned the literal match without falling
        # through to the fuzzy lookup.
        matching_branches={
            "feat/wp-001-*": [
                {
                    "name": "feat/wp-001-some-shorter",
                    "committerdate": "2026-05-01T00:00:00Z",
                },
            ],
        },
    )

    branch = _wpxlib.resolve_wp_branch(
        "WP-001",
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == "feat/wp-001-long-full-slug-name"


# ─── 2. fuzzy match — exactly one candidate (the bug we're fixing) ────────


def test_resolve_fuzzy_single_candidate(tmp_project, monkeypatch, capsys):
    """When the slug-literal misses BUT exactly one ``feat/wp-NNN-*``
    branch exists on origin, return that branch.

    Real-world example:
      WP file: WP-008-wire-drift-detector-into-branch-ci.md
      Pushed:  feat/wp-008-wire-drift-detector
    """
    _seed_wp_file(tmp_project.wp_dir, "WP-008", "wire-drift-detector-into-branch-ci")
    _stub_gh(
        monkeypatch,
        branches_present=set(),  # literal slug doesn't exist
        matching_branches={
            "feat/wp-008-*": [
                {
                    "name": "feat/wp-008-wire-drift-detector",
                    "committerdate": "2026-05-30T12:00:00Z",
                },
            ],
        },
    )

    branch = _wpxlib.resolve_wp_branch(
        "WP-008",
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == "feat/wp-008-wire-drift-detector"


# ─── 3. fuzzy match — multiple candidates, committerdate tiebreak ────────


def test_resolve_fuzzy_multiple_candidates_picks_most_recent(
    tmp_project,
    monkeypatch,
    capsys,
):
    """Two-or-more ``feat/wp-NNN-*`` candidates → most-recent-by-committerdate
    wins. A warning is surfaced so the operator knows the choice was
    ambiguous (cf. the WP-011 case where the executor pushed twice with
    different short slugs)."""
    _seed_wp_file(tmp_project.wp_dir, "WP-011", "cross-ref-configuration-vocabulary")
    _stub_gh(
        monkeypatch,
        branches_present=set(),
        matching_branches={
            "feat/wp-011-*": [
                {
                    "name": "feat/wp-011-readme-cross-ref",
                    "committerdate": "2026-05-30T15:00:00Z",
                },  # newer
                {
                    "name": "feat/wp-011-config-vocab-old",
                    "committerdate": "2026-05-29T10:00:00Z",
                },  # older
            ],
        },
    )

    branch = _wpxlib.resolve_wp_branch(
        "WP-011",
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == "feat/wp-011-readme-cross-ref"
    captured = capsys.readouterr()
    # Warning surfaces in stderr (per _log convention)
    assert "WP-011" in captured.err
    assert "feat/wp-011-readme-cross-ref" in captured.err


# ─── 4. zero candidates — fallthrough to "branch missing" ────────────────


def test_resolve_fuzzy_zero_candidates_returns_none(tmp_project, monkeypatch):
    """When neither the slug-literal nor any ``feat/wp-NNN-*`` branch exists
    on origin, return None — caller falls through to the existing
    "origin branch missing" path."""
    _seed_wp_file(tmp_project.wp_dir, "WP-099", "no-branch-anywhere")
    _stub_gh(
        monkeypatch,
        branches_present=set(),
        matching_branches={},  # no fuzzy match either
    )

    branch = _wpxlib.resolve_wp_branch(
        "WP-099",
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch is None


# ─── 5. warning surfaced when fuzzy-match deviates from slug-literal ─────


def test_resolve_fuzzy_emits_warning_when_slug_differs(
    tmp_project,
    monkeypatch,
    capsys,
):
    """When the fuzzy-match path fires (slug-literal didn't match but a
    single ``feat/wp-NNN-*`` did), surface a warning that names both the
    expected branch and the actual branch — so the operator can see
    the drift and decide whether to leave it tolerant or rename."""
    _seed_wp_file(
        tmp_project.wp_dir, "WP-010", "extend-release-train-skill-for-dry-run"
    )
    _stub_gh(
        monkeypatch,
        branches_present=set(),
        matching_branches={
            "feat/wp-010-*": [
                {
                    "name": "feat/wp-010-extend-release-train-skill",
                    "committerdate": "2026-05-30T12:00:00Z",
                },
            ],
        },
    )

    branch = _wpxlib.resolve_wp_branch(
        "WP-010",
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == "feat/wp-010-extend-release-train-skill"

    captured = capsys.readouterr()
    # Names the WP, the expected literal, and the actual chosen branch
    # so an operator tailing stderr can spot the drift.
    assert "WP-010" in captured.err
    assert "feat/wp-010-extend-release-train-skill-for-dry-run" in captured.err
    assert "feat/wp-010-extend-release-train-skill" in captured.err


# ─── 6. integration: find_eligible_branches uses resolve_wp_branch ───────


def test_find_eligible_uses_fuzzy_match(tmp_project, monkeypatch):
    """End-to-end: a WP at step-7-complete whose origin branch has a
    shorter slug than the WP file is now ELIGIBLE (not "branch missing")."""
    # Seed INDEX.md with the step-7-complete WP
    index_text = """# Index

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-008 | Drift detector | create | step-7-complete | — | — |

"""
    tmp_project.index_md.parent.mkdir(parents=True, exist_ok=True)
    tmp_project.index_md.write_text(index_text, encoding="utf-8")
    _seed_wp_file(
        tmp_project.wp_dir,
        "WP-008",
        "wire-drift-detector-into-branch-ci",
    )
    _stub_gh(
        monkeypatch,
        branches_present=set(),  # literal slug missing on origin
        matching_branches={
            "feat/wp-008-*": [
                {
                    "name": "feat/wp-008-wire-drift-detector",
                    "committerdate": "2026-05-30T12:00:00Z",
                },
            ],
        },
    )
    # CI check is the second helper; stub it green so we isolate the
    # slug-tolerance behaviour from the CI gate.
    monkeypatch.setattr(
        _wpxlib,
        "_gh_branch_ci_green",
        lambda *a, **kw: True,
    )

    rows = _wpxlib.parse_index_md(tmp_project.index_md)
    results = _wpxlib.find_eligible_branches(
        rows,
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert len(results) == 1
    assert results[0].eligible, (
        f"Expected WP-008 eligible via fuzzy match; got reason: {results[0].reason}"
    )
    # The eligibility result names the ACTUAL branch on origin (not the
    # slug-literal that doesn't exist) so the train uses the right ref.
    assert results[0].branch == "feat/wp-008-wire-drift-detector"
