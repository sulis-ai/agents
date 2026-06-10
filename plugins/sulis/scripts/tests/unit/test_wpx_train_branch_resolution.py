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

Dual-prefix fixture inventory (WP-006, change wp-branch-collision)
-----------------------------------------------------------------
The branch-namespacing fix retains the legacy ``feat/wp-NNN-*`` path for one
release AND adds the scoped ``wp/{scope}/wp-NNN-*`` path. Both must stay
covered. Test roles across the ~16 files that carry ``feat/wp-`` fixtures:

* SCOPED-PATH coverage (assert ``wp/{scope}/`` resolution; pass change_scope):
    - test_wpx_train_branch_resolution.py — ``test_resolve_scoped_*`` +
      ``test_scoped_glob_does_not_match_foreign_change_branch`` (#105/#106 repro)
    - test_wpx_train_eligibility.py — ``test_eligibility_uses_scoped_resolution``
    - test_compute_wp_status.py — ``test_compute_status_threads_scope``
    - test_wpx_wp.py — ``test_branch_name_subcommand_emits_scoped_then_legacy``
* LEGACY-PATH characterisation (no change_scope; assert ``feat/wp-NNN-*``;
  KEEP byte-for-byte — they are the oracle for the retained fallback):
    every other ``feat/wp-`` fixture (eligibility no-scope cases, failure-paths,
    patch-id, inspect, run, state-machine, paused-state, drift-detection,
    worktree, change). None migrated; none deleted.

Follow-up (legacy-fallback removal, next release): the suppress-when-scoped
behaviour means scoped callers never touch ``feat/``. When the legacy glob is
removed, the no-scope ``feat/`` characterisation tests are what to delete;
they are greppable by their lack of ``change_scope`` + their ``feat/wp-``
assertions. The scoped tests (``_scoped_`` / ``change_scope=``) stay.
"""

from __future__ import annotations

import _wpxlib


# ─── Fixtures ─────────────────────────────────────────────────────────────


def _seed_wp_file(wp_dir, wp_id: str, slug: str) -> None:
    """Create an empty WP-{id}-{slug}.md file so _wp_slug_from_file resolves."""
    wp_dir.mkdir(parents=True, exist_ok=True)
    (wp_dir / f"{wp_id}-{slug}.md").write_text(f"# {wp_id}\n", encoding="utf-8")


def _seed_journal(
    wp_dir, wp_id: str, pushed_branch: str | None, *, step7_outcome: str | None = None,
) -> None:
    """Create the executor journal (.executor-{wp_id}.md) with a Step-7 trace
    row recording the exact pushed branch.

    Mirrors the canonical journal shape written by ``wpx-journal
    complete-step --step 7 --outcome "Pushed to <branch> at SHA <sha>"``.

    - ``pushed_branch`` None + ``step7_outcome`` None → Step-7 row omitted
      (journal exists but has no recorded push yet).
    - ``step7_outcome`` set → use it verbatim as the Step-7 Outcome cell
      (lets a test exercise malformed / alternative phrasings).
    """
    wp_dir.mkdir(parents=True, exist_ok=True)
    step7 = ""
    if step7_outcome is not None:
        outcome = step7_outcome
        step7 = (
            f"| 7 | 2026-06-01T10:00:00Z | 2026-06-01T10:05:00Z | {outcome} |\n"
        )
    elif pushed_branch is not None:
        step7 = (
            f"| 7 | 2026-06-01T10:00:00Z | 2026-06-01T10:05:00Z | "
            f"Pushed to {pushed_branch} at SHA abc1234 (commit: feat: do the thing) |\n"
        )
    text = (
        f"# Executor journal — {wp_id}\n\n"
        "## Step trace\n\n"
        "| Step | Started | Completed | Outcome |\n"
        "|---|---|---|---|\n"
        "| 1 | 2026-06-01T09:00:00Z | 2026-06-01T09:01:00Z | worktree |\n"
        f"{step7}\n"
    )
    (wp_dir / f".executor-{wp_id}.md").write_text(text, encoding="utf-8")


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


# ─── 7. journal-recorded branch wins over the ambiguous glob (#229) ───────


def test_resolve_journal_branch_wins_over_ambiguous_glob(
    tmp_project, monkeypatch
):
    """When the executor journal records an exact pushed branch AND multiple
    ``feat/wp-NNN-*`` globs exist on origin (the recycled-WP-number hazard),
    resolution returns the JOURNAL's branch — proving the journal is
    consulted FIRST and the ambiguous glob never decides.

    Real-world failure (#229): WP numbers are recycled across years of
    changes, so ``feat/wp-002-*`` matched ``feat/wp-002-session-manager-host``
    from an unrelated past change and got picked by committerdate recency,
    shipping the wrong branch for the dark-mode run.
    """
    wp_id = "WP-002"
    _seed_wp_file(tmp_project.wp_dir, wp_id, "dark-token-block")
    journal_branch = "feat/wp-002-dark-token-block"
    _seed_journal(tmp_project.wp_dir, wp_id, journal_branch)
    _stub_gh(
        monkeypatch,
        # The journal branch exists on origin; the literal slug also happens
        # to coincide here, but the point is the journal short-circuits BEFORE
        # any glob is consulted. Include unrelated recycled branches in the
        # glob to prove they are never chosen.
        branches_present={journal_branch},
        matching_branches={
            "feat/wp-002-*": [
                {
                    "name": "feat/wp-002-session-manager-host",
                    "committerdate": "2026-05-30T15:00:00Z",  # newer — would win the glob
                },
                {
                    "name": journal_branch,
                    "committerdate": "2026-05-29T10:00:00Z",  # older
                },
            ],
        },
    )

    branch = _wpxlib.resolve_wp_branch(
        wp_id,
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == journal_branch, (
        "Journal-recorded branch must win over the most-recent glob match; "
        f"got {branch!r}."
    )


def test_resolve_journal_branch_distinct_from_literal_slug(
    tmp_project, monkeypatch
):
    """The journal branch is authoritative even when it differs from BOTH the
    literal slug AND the most-recent glob candidate.

    This is the crux of #229: the journal records what THIS change's executor
    actually pushed, scoping resolution and eliminating cross-change ambiguity.
    """
    wp_id = "WP-002"
    # WP file slug differs from the actual pushed branch (drift).
    _seed_wp_file(tmp_project.wp_dir, wp_id, "dark-token-block-and-toggle")
    journal_branch = "feat/wp-002-dark-token-block"
    _seed_journal(tmp_project.wp_dir, wp_id, journal_branch)
    _stub_gh(
        monkeypatch,
        # Literal slug branch does NOT exist; journal branch DOES.
        branches_present={journal_branch},
        matching_branches={
            "feat/wp-002-*": [
                {
                    "name": "feat/wp-002-session-manager-host",  # recycled, unrelated
                    "committerdate": "2026-06-05T15:00:00Z",  # most recent — glob would pick this
                },
                {
                    "name": journal_branch,
                    "committerdate": "2026-05-29T10:00:00Z",
                },
            ],
        },
    )

    branch = _wpxlib.resolve_wp_branch(
        wp_id,
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == journal_branch


def test_resolve_no_journal_preserves_glob_behaviour(tmp_project, monkeypatch):
    """When there is NO journal (or no recorded push), resolution falls
    through to the existing literal → glob → None order, byte-for-byte.

    Re-asserts the #228-era fuzzy-single-candidate behaviour with no journal
    present, so the journal-first step is proven additive (not a regression).
    """
    wp_id = "WP-008"
    _seed_wp_file(tmp_project.wp_dir, wp_id, "wire-drift-detector-into-branch-ci")
    # No _seed_journal call → no .executor file at all.
    _stub_gh(
        monkeypatch,
        branches_present=set(),  # literal slug missing
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
        wp_id,
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == "feat/wp-008-wire-drift-detector"


def test_resolve_journal_branch_missing_on_origin_falls_through(
    tmp_project, monkeypatch
):
    """If the journal names a branch that no longer exists on origin (deleted
    after merge, force-pushed away), the journal step is skipped and we fall
    through to literal → glob. Robustness: a stale journal must not strand the
    WP at a vanished ref."""
    wp_id = "WP-008"
    _seed_wp_file(tmp_project.wp_dir, wp_id, "wire-drift-detector-into-branch-ci")
    _seed_journal(tmp_project.wp_dir, wp_id, "feat/wp-008-gone-from-origin")
    _stub_gh(
        monkeypatch,
        # Journal branch NOT in branches_present → _gh_branch_exists False.
        # Literal slug also absent; the single glob is the live branch.
        branches_present=set(),
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
        wp_id,
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == "feat/wp-008-wire-drift-detector"


def test_resolve_malformed_journal_falls_through(tmp_project, monkeypatch):
    """A journal that exists but has no parseable Step-7 push line is treated
    as 'no record' — fall through to the existing order without raising."""
    wp_id = "WP-008"
    _seed_wp_file(tmp_project.wp_dir, wp_id, "wire-drift-detector-into-branch-ci")
    # Step-7 outcome present but with no recognisable branch token.
    _seed_journal(
        tmp_project.wp_dir, wp_id, None,
        step7_outcome="blocked: CI red, see BLOCKER-WP-008",
    )
    _stub_gh(
        monkeypatch,
        branches_present=set(),
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
        wp_id,
        repo="acme/x",
        wp_dir=tmp_project.wp_dir,
    )
    assert branch == "feat/wp-008-wire-drift-detector"


# ─── WP-001: _branch_name change-identity threading (ADR-001) ──────────────


def test_branch_name_scoped_and_legacy():
    """_branch_name composes the ADR-001 scoped shape when a change_scope is
    given, and the byte-for-byte legacy shape when it is not.

    Scoped:  wp/{change_scope}/wp-{id-lower}-{slug}
    Legacy:  feat/wp-{id-lower}-{slug}   (change_scope None/empty)
    The WP- prefix strip + lowercase are preserved in both shapes.
    """
    # Scoped — change identity known
    assert _wpxlib._branch_name("WP-001", "foo", "fix-x") == "wp/fix-x/wp-001-foo"
    # Legacy — change identity unresolvable (default arg)
    assert _wpxlib._branch_name("WP-001", "foo") == "feat/wp-001-foo"
    # Legacy — prefix-strip + lowercase preserved for a bare numeric id
    assert _wpxlib._branch_name("wp-7", "bar") == "feat/wp-7-bar"


# ─── WP-002: journal pushed-branch regex widening (wp/ + change/) ───────────


def test_journal_regex_matches_wp_and_change_prefixes(tmp_project):
    """_JOURNAL_PUSHED_BRANCH_RE accepts the new wp/... and change/... pushed
    branch tokens in a Step-7 trace, not just legacy feat/... — otherwise #229
    Step-0 resolution silently falls through for namespaced branches.
    """
    cases = [
        ("WP-001", "Pushed to wp/fix-x/wp-001-foo at SHA abc1234 (commit: x)",
         "wp/fix-x/wp-001-foo"),
        ("WP-002", "pushed change/fix-x at SHA def5678",
         "change/fix-x"),
        ("WP-003", "Pushed to feat/wp-003-bar at SHA 9999abc",
         "feat/wp-003-bar"),
    ]
    for wp_id, outcome, expected in cases:
        _seed_journal(tmp_project.wp_dir, wp_id, None, step7_outcome=outcome)
        assert (
            _wpxlib._journal_pushed_branch(tmp_project.wp_dir, wp_id) == expected
        ), f"{outcome!r} should parse to {expected!r}"


# ─── WP-003: dual-prefix resolution (scoped glob + legacy fallback) ─────────


def test_resolve_scoped_literal_match(tmp_project, monkeypatch):
    """With change_scope set, the scoped literal wp/{scope}/wp-NNN-{slug} is
    returned directly when it exists on origin — no glob consulted."""
    wp_id = "WP-001"
    _seed_wp_file(tmp_project.wp_dir, wp_id, "foo")
    _stub_gh(
        monkeypatch,
        branches_present={"wp/change-a/wp-001-foo"},
        # A foreign legacy branch exists but must never be reached.
        matching_branches={"feat/wp-001-*": [
            {"name": "feat/wp-001-foreign", "committerdate": "2026-06-01T00:00:00Z"},
        ]},
    )
    branch = _wpxlib.resolve_wp_branch(
        wp_id, repo="acme/x", wp_dir=tmp_project.wp_dir, change_scope="change-a",
    )
    assert branch == "wp/change-a/wp-001-foo"


def test_scoped_glob_does_not_match_foreign_change_branch(tmp_project, monkeypatch):
    """The #105/#106 reproduction: a foreign change's feat/wp-001-* branch must
    NEVER be selected for this change's WP-001 when a change_scope is supplied.

    Variant A: scoped branch exists → it is chosen.
    Variant B: scoped branch absent → None, NOT the foreign feat/ branch.
    """
    wp_id = "WP-001"
    _seed_wp_file(tmp_project.wp_dir, wp_id, "mine")

    # Variant A — scoped branch present.
    _stub_gh(
        monkeypatch,
        matching_branches={
            "wp/change-a/wp-001-*": [
                {"name": "wp/change-a/wp-001-mine", "committerdate": "2026-06-02T00:00:00Z"},
            ],
            "feat/wp-001-*": [
                {"name": "feat/wp-001-change-B-branch", "committerdate": "2026-06-09T00:00:00Z"},
            ],
        },
    )
    branch = _wpxlib.resolve_wp_branch(
        wp_id, repo="acme/x", wp_dir=tmp_project.wp_dir, change_scope="change-a",
    )
    assert branch == "wp/change-a/wp-001-mine"
    assert branch != "feat/wp-001-change-B-branch"

    # Variant B — scoped branch absent; foreign legacy branch must not leak.
    _stub_gh(
        monkeypatch,
        matching_branches={
            "wp/change-a/wp-001-*": [],
            "feat/wp-001-*": [
                {"name": "feat/wp-001-change-B-branch", "committerdate": "2026-06-09T00:00:00Z"},
            ],
        },
    )
    branch = _wpxlib.resolve_wp_branch(
        wp_id, repo="acme/x", wp_dir=tmp_project.wp_dir, change_scope="change-a",
    )
    assert branch is None


def test_resolve_scoped_inflight_legacy_branch_resolves_via_journal(
    tmp_project, monkeypatch
):
    """One-release compat window — discharged by Step-0, NOT by the legacy glob.

    When a scope is supplied and this change's in-flight branch was minted the
    OLD way (feat/wp-NNN-...) during the compat window, it still resolves —
    because the executor journal records the exact pushed branch (any prefix,
    after WP-002's regex widening) and Step-0 returns it after confirming it is
    on origin. The repo-wide legacy glob is NOT consulted under a scope; it
    cannot tell this change's own old branch from a foreign collision, so
    relying on it would re-open #105/#106. The journal can — it is per-change
    by construction.
    """
    wp_id = "WP-001"
    _seed_wp_file(tmp_project.wp_dir, wp_id, "drifted-slug")
    inflight = "feat/wp-001-drifted"  # minted the old way, this change's own
    _seed_journal(tmp_project.wp_dir, wp_id, inflight)
    _stub_gh(
        monkeypatch,
        branches_present={inflight},  # journal branch IS on origin
        matching_branches={
            # Scoped glob empty (nothing minted the new way), and a FOREIGN
            # feat/wp-001-* exists. Neither is consulted: Step-0 short-circuits.
            "wp/change-a/wp-001-*": [],
            "feat/wp-001-*": [
                {"name": "feat/wp-001-foreign", "committerdate": "2026-06-09T00:00:00Z"},
            ],
        },
    )
    branch = _wpxlib.resolve_wp_branch(
        wp_id, repo="acme/x", wp_dir=tmp_project.wp_dir, change_scope="change-a",
    )
    assert branch == inflight
    assert branch != "feat/wp-001-foreign"


def test_resolve_scoped_suppresses_legacy_glob_when_no_journal(
    tmp_project, monkeypatch
):
    """With a scope set, the repo-wide legacy feat/wp-NNN-* glob is suppressed.

    No journal record, no scoped branch, but a foreign feat/wp-001-* exists on
    origin. The resolver MUST return None — never the foreign branch. This is
    the direct guard against #105/#106: under a scope, any feat/ glob hit is a
    foreign change's recycled-number branch, so the legacy step is skipped
    entirely. (A built WP would have a journal entry resolving via Step-0; a WP
    with neither journal nor scoped branch is unresolvable under its own scope,
    and None is strictly safer than guessing a foreign ref.)
    """
    wp_id = "WP-001"
    _seed_wp_file(tmp_project.wp_dir, wp_id, "mine")
    _stub_gh(
        monkeypatch,
        branches_present=set(),  # no journal branch (none seeded), nothing literal
        matching_branches={
            "wp/change-a/wp-001-*": [],
            "feat/wp-001-*": [
                {"name": "feat/wp-001-foreign", "committerdate": "2026-06-09T00:00:00Z"},
            ],
        },
    )
    branch = _wpxlib.resolve_wp_branch(
        wp_id, repo="acme/x", wp_dir=tmp_project.wp_dir, change_scope="change-a",
    )
    assert branch is None
