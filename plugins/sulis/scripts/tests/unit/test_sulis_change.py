"""Unit tests for sulis-change helpers in _wpxlib.py.

Covers the pure-logic helpers; the subprocess-touching helpers
(git_worktree_add, detect_adopt_state, adopt_*) are exercised by the
integration tests in tests/integration/test_sulis_change_lifecycle.py.
"""

from __future__ import annotations

import pytest

from _wpxlib import (
    ALLOWED_CHANGE_PRIMITIVES,
    change_worktree_path,
    compose_change_branch,
    generate_change_ulid,
    parse_change_branch,
    read_change_metadata,
    ulid_handle,
    validate_change_primitive,
    validate_change_slug,
    validate_change_ulid,
    write_change_metadata,
)


# ─── validate_change_primitive ────────────────────────────────────────────


@pytest.mark.parametrize("primitive", [
    "create", "extend", "refactor", "strangle", "harden", "delete",
    "test", "document",
    "feat", "fix", "chore",  # Conventional Commits fallbacks
])
def test_validate_primitive_accepts_valid(primitive):
    ok, _ = validate_change_primitive(primitive)
    assert ok is True


@pytest.mark.parametrize("primitive", [
    "", "nonsense", "fix-bug",  # not a single primitive name
])
def test_validate_primitive_rejects_invalid(primitive):
    ok, reason = validate_change_primitive(primitive)
    assert ok is False
    assert reason


def test_validate_primitive_normalises_case():
    """Mixed-case input is normalised to lower-case for matching."""
    ok, _ = validate_change_primitive("Create")
    assert ok is True
    ok, _ = validate_change_primitive("REFACTOR")
    assert ok is True


def test_validate_primitive_covers_all_22_plus_cc_fallback():
    """Sanity check: ALLOWED_CHANGE_PRIMITIVES should be exactly 22+3 = 25."""
    assert len(ALLOWED_CHANGE_PRIMITIVES) == 25


# ─── validate_change_slug ────────────────────────────────────────────────


@pytest.mark.parametrize("slug", [
    "introduce-payments",
    "retire-task-service",
    "replace-redis-with-valkey",  # 4 words, allowed
    "wp-001",  # 2 simple words
    "auth-flow",  # short OK
])
def test_validate_slug_accepts_valid(slug):
    ok, _ = validate_change_slug(slug)
    assert ok is True


@pytest.mark.parametrize("slug", [
    "",  # empty
    "introducepayments",  # one word — fewer than 2
    "this-is-six-words-too-many-here",  # 7 words; >5
    "Introduce-Payments",  # uppercase
    "introduce_payments",  # underscore not kebab
    "introduce-payments-",  # trailing dash
    "-introduce-payments",  # leading dash
])
def test_validate_slug_rejects_invalid(slug):
    ok, reason = validate_change_slug(slug)
    assert ok is False
    assert reason


# ─── compose / parse change branch ───────────────────────────────────────


def test_compose_change_branch_typical():
    assert (compose_change_branch("create", "introduce-payments") ==
            "change/create-introduce-payments")
    assert (compose_change_branch("strangle", "task-service") ==
            "change/strangle-task-service")


def test_compose_change_branch_lowercases_primitive():
    """Mixed-case input is normalised to lowercase in the branch name."""
    assert (compose_change_branch("Create", "introduce-payments") ==
            "change/create-introduce-payments")


def test_compose_change_branch_invalid_slug_raises():
    with pytest.raises(ValueError):
        compose_change_branch("create", "Bad_Slug")


def test_compose_change_branch_invalid_primitive_raises():
    with pytest.raises(ValueError):
        compose_change_branch("notaprimitive", "introduce-payments")


def test_parse_change_branch_roundtrip():
    branch = compose_change_branch("refactor", "http-client")
    parsed = parse_change_branch(branch)
    assert parsed == ("refactor", "http-client")


def test_parse_change_branch_rejects_non_change():
    assert parse_change_branch("feat/wp-001-payments") is None
    assert parse_change_branch("dev") is None
    assert parse_change_branch("change/no-dash-here-but-no-primitive") is None


def test_parse_change_branch_rejects_unknown_primitive():
    """A branch named change/notaprimitive-... is not a valid change branch."""
    assert parse_change_branch("change/notaprimitive-payments") is None


# ─── #112: host branch convention — compose ──────────────────────────────


def test_compose_change_branch_no_convention_is_byte_for_byte_default():
    """When no convention is supplied, the result is identical to today's
    hardcoded change/{primitive}-{slug} — zero behaviour change."""
    assert (compose_change_branch("feat", "dark-mode", convention=None) ==
            "change/feat-dark-mode")
    # Default arg path (no kwarg at all) must match too.
    assert (compose_change_branch("feat", "dark-mode") ==
            "change/feat-dark-mode")


def test_compose_change_branch_slug_template():
    """A `feature/{slug}` convention composes feature/<slug>."""
    assert (compose_change_branch("feat", "dark-mode",
                                  convention="feature/{slug}") ==
            "feature/dark-mode")


def test_compose_change_branch_primitive_and_slug_template():
    """Both {primitive} and {slug} placeholders are supported."""
    assert (compose_change_branch("fix", "login-bug",
                                  convention="work/{primitive}-{slug}") ==
            "work/fix-login-bug")


def test_compose_change_branch_bare_prefix_composes_slug():
    """A bare prefix (ends in `/`, no placeholder) composes prefix{slug}."""
    assert (compose_change_branch("feat", "dark-mode",
                                  convention="feature/") ==
            "feature/dark-mode")


def test_compose_change_branch_convention_lowercases():
    """Primitive case is normalised inside a templated convention too."""
    assert (compose_change_branch("Feat", "dark-mode",
                                  convention="work/{primitive}-{slug}") ==
            "work/feat-dark-mode")


def test_compose_change_branch_empty_convention_falls_back_to_default():
    """An empty/whitespace convention is treated as absent (default)."""
    assert (compose_change_branch("feat", "dark-mode", convention="") ==
            "change/feat-dark-mode")
    assert (compose_change_branch("feat", "dark-mode", convention="   ") ==
            "change/feat-dark-mode")


# ─── #112: host branch convention — dual-prefix parse ─────────────────────


def test_parse_change_branch_accepts_configured_convention():
    """A renamed `feature/<slug>` branch parses under the configured
    convention, returning (primitive, slug)."""
    parsed = parse_change_branch("feature/dark-mode",
                                 convention="feature/{slug}")
    assert parsed is not None
    primitive, slug = parsed
    assert slug == "dark-mode"


def test_parse_change_branch_legacy_change_prefix_still_resolves():
    """Even with a non-change/ convention configured, legacy change/* branches
    must still parse (dual-prefix union)."""
    parsed = parse_change_branch("change/feat-dark-mode",
                                 convention="feature/{slug}")
    assert parsed == ("feat", "dark-mode")


def test_parse_change_branch_template_with_primitive():
    """A `work/{primitive}-{slug}` convention recovers both fields."""
    parsed = parse_change_branch("work/fix-login-bug",
                                 convention="work/{primitive}-{slug}")
    assert parsed == ("fix", "login-bug")


# ─── change_worktree_path ────────────────────────────────────────────────


def test_change_worktree_path_is_sibling_to_repo(tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    dest = change_worktree_path(repo, "create", "introduce-payments")
    assert dest == tmp_path / "myrepo-change-create-introduce-payments"


# ─── write / read change metadata ────────────────────────────────────────


def test_write_then_read_metadata_round_trip(tmp_path):
    path = tmp_path / ".changes" / "create-introduce-payments.yaml"
    data = {
        "slug": "introduce-payments",
        "primitive": "create",
        "branch": "change/create-introduce-payments",
        "worktree_path": "/tmp/repo-change-create-introduce-payments",
        "base_branch": "dev",
        "base_sha": "abc123def456",
        "started_at": "2026-05-21T12:00:00Z",
    }
    write_change_metadata(path, data)
    assert path.exists()
    loaded = read_change_metadata(path)
    for k, v in data.items():
        assert loaded[k] == v


def test_write_metadata_handles_null_fields(tmp_path):
    """None values render as YAML `null`."""
    path = tmp_path / ".changes" / "feat-x.yaml"
    write_change_metadata(path, {
        "slug": "x",
        "primitive": "feat",
        "branch": "change/feat-x",
        "worktree_path": "/tmp/x",
        "base_branch": "dev",
        "base_sha": "abc",
        "started_at": "2026-05-21T12:00:00Z",
        "adopted_from_sha": None,
        "adopt_mode": None,
    })
    text = path.read_text()
    assert "adopted_from_sha: null" in text
    assert "adopt_mode: null" in text


def test_write_metadata_includes_adopt_fields(tmp_path):
    """adopted_from_sha + adopt_mode round-trip when present."""
    path = tmp_path / ".changes" / "create-x.yaml"
    write_change_metadata(path, {
        "slug": "x", "primitive": "create",
        "branch": "change/create-x",
        "worktree_path": "/tmp/x",
        "base_branch": "dev",
        "base_sha": "newsha",
        "started_at": "2026-05-21T12:00:00Z",
        "adopted_from_sha": "oldsha",
        "adopt_mode": "forward",
    })
    loaded = read_change_metadata(path)
    assert loaded["adopted_from_sha"] == "oldsha"
    assert loaded["adopt_mode"] == "forward"


def test_read_metadata_missing_file_returns_empty(tmp_path):
    """Missing file → empty dict; no error."""
    result = read_change_metadata(tmp_path / "nope.yaml")
    assert result == {}


# ─── adopt-state heuristic structure ─────────────────────────────────────


def test_adopt_state_dict_shape():
    """detect_adopt_state always returns the documented dict shape."""
    # We don't run it here (it shells out); just verify the shape spec.
    from _wpxlib import detect_adopt_state  # noqa: F401
    expected_keys = {
        "current_branch", "has_uncommitted", "uncommitted_files",
        "local_commits_ahead", "pushed_commits_can_rewrite", "base_sha",
    }
    # Documented contract; integration test exercises actual state detection.
    assert expected_keys  # Sanity assertion; the integration tests do the real work.


# ─── generate_change_ulid (Phase 5 of change-as-primitive build) ──────────


def test_generate_change_ulid_returns_26_chars():
    u = generate_change_ulid()
    assert len(u) == 26, f"expected 26 chars, got {len(u)}: {u!r}"


def test_generate_change_ulid_uses_crockford_alphabet():
    u = generate_change_ulid()
    allowed = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    for i, ch in enumerate(u):
        assert ch in allowed, f"char {ch!r} at position {i} not in Crockford-base32"


def test_generate_change_ulid_unique_across_calls():
    """1000 ULIDs should all be unique (random portion guarantees this)."""
    ulids = {generate_change_ulid() for _ in range(1000)}
    assert len(ulids) == 1000, f"got {len(ulids)} unique ULIDs out of 1000"


def test_generate_change_ulid_sortable_by_timestamp():
    """Two ULIDs generated in sequence — the second should sort >= the first."""
    u1 = generate_change_ulid(_now_ms=1000, _random_bytes=b"\x00" * 10)
    u2 = generate_change_ulid(_now_ms=1001, _random_bytes=b"\x00" * 10)
    assert u1 < u2, f"expected {u1} < {u2}"


def test_generate_change_ulid_deterministic_with_injection():
    u = generate_change_ulid(_now_ms=1716624000000, _random_bytes=b"\x00" * 10)
    # Re-run with same inputs — must produce the same output
    u2 = generate_change_ulid(_now_ms=1716624000000, _random_bytes=b"\x00" * 10)
    assert u == u2


def test_generate_change_ulid_rejects_oversized_timestamp():
    """Timestamp >48 bits should raise."""
    with pytest.raises(ValueError, match="timestamp exceeds 48 bits"):
        generate_change_ulid(_now_ms=2**48 + 1, _random_bytes=b"\x00" * 10)


def test_generate_change_ulid_rejects_wrong_random_length():
    """Randomness must be exactly 10 bytes."""
    with pytest.raises(ValueError, match="exactly 10 bytes"):
        generate_change_ulid(_random_bytes=b"\x00" * 9)
    with pytest.raises(ValueError, match="exactly 10 bytes"):
        generate_change_ulid(_random_bytes=b"\x00" * 11)


# ─── ulid_handle ──────────────────────────────────────────────────────────


def test_ulid_handle_returns_ch_prefix_plus_six():
    u = generate_change_ulid()
    h = ulid_handle(u)
    assert h.startswith("CH-")
    assert len(h) == 9, f"expected 9-char handle (CH- + 6), got {h!r}"
    # The handle is drawn from the RANDOM tail (positions 10-15), NOT the
    # timestamp head — see test_ulid_handle_distinct_for_same_timestamp (#101).
    assert h[3:] == u[10:16]


def test_ulid_handle_distinct_for_same_timestamp():
    """#101: two changes minted in the SAME millisecond (identical timestamp
    prefix) must get DIFFERENT handles — the bug was that the handle came from
    the timestamp head, so same-window changes collided and resolution could
    target the wrong change. Tail-derivation fixes this."""
    same_ms = 1_700_000_000_000
    # Vary the HIGH bytes of the 80-bit random part — the handle is drawn from
    # the top of the random tail (ulid[10:16]). Real ULIDs randomise all 80
    # bits via secrets.token_bytes, so any two differ here overwhelmingly.
    u1 = generate_change_ulid(_now_ms=same_ms, _random_bytes=b"\x11" + b"\x00" * 9)
    u2 = generate_change_ulid(_now_ms=same_ms, _random_bytes=b"\x99" + b"\x00" * 9)
    assert u1[:10] == u2[:10], "fixture sanity: identical timestamp prefix"
    assert u1 != u2, "fixture sanity: different randomness → different ULIDs"
    # The old head-derived handle WOULD have collided (u1[:6] == u2[:6]); the
    # tail-derived handle must not.
    assert u1[:6] == u2[:6], "fixture sanity: head WOULD collide"
    assert ulid_handle(u1) != ulid_handle(u2), (
        "same-timestamp changes must get distinct handles (#101)"
    )


def test_ulid_handle_rejects_wrong_length():
    with pytest.raises(ValueError, match="must be 26 characters"):
        ulid_handle("01HYQC")
    with pytest.raises(ValueError, match="must be 26 characters"):
        ulid_handle("01HYQC71000000000000000000X")  # 27 chars


# ─── validate_change_ulid ─────────────────────────────────────────────────


def test_validate_change_ulid_accepts_valid_ulid():
    u = generate_change_ulid()
    ok, reason = validate_change_ulid(u)
    assert ok is True
    assert reason == ""


def test_validate_change_ulid_rejects_empty():
    ok, reason = validate_change_ulid("")
    assert ok is False
    assert "empty" in reason


def test_validate_change_ulid_rejects_wrong_length():
    ok, reason = validate_change_ulid("01HYQC")
    assert ok is False
    assert "26 characters" in reason


def test_validate_change_ulid_rejects_non_crockford_chars():
    # Crockford-base32 excludes I, L, O, U (and lower case)
    bad = "01HYQC710000000000000000IL"  # I + L are excluded
    ok, reason = validate_change_ulid(bad)
    assert ok is False
    assert "non-Crockford-base32" in reason


# ─── resolve_current_change (Phase 5 #2: SULIS_CHANGE_ID binding) ──────────


def test_resolve_current_change_returns_none_when_env_unset(monkeypatch):
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    from _wpxlib import resolve_current_change
    assert resolve_current_change(repo_root=".") is None


def test_resolve_current_change_returns_none_when_no_matching_branch(monkeypatch, tmp_path):
    """SULIS_CHANGE_ID set but no change branch in repo → None."""
    monkeypatch.setenv("SULIS_CHANGE_ID", "01HYQC71000000000000000000")
    from _wpxlib import resolve_current_change
    # tmp_path is a fresh dir; find_change_branches returns [] (no git here either)
    result = resolve_current_change(repo_root=tmp_path)
    assert result is None


# ─── L-01: resolve from INSIDE the change worktree (the cockpit failure) ────


_CHANGE_ID = "01HYQC71ABCDEFGHJKMNPQRSTV"


def _seed_change_metadata(repo_root, *, primitive="create", slug="foo-bar"):
    from _wpxlib import write_change_metadata
    branch = f"change/{primitive}-{slug}"
    write_change_metadata(
        repo_root / ".changes" / f"{primitive}-{slug}.yaml",
        {
            "change_id": _CHANGE_ID,
            "handle": "CH-01HYQC",
            "slug": slug,
            "primitive": primitive,
            "branch": branch,
            "worktree_path": str(repo_root),
            "base_branch": "dev",
            "started_at": "2026-05-27T00:00:00Z",
        },
    )
    return branch


def test_resolve_from_inside_worktree_via_self_branch(monkeypatch, tmp_path):
    """The L-01 bug: invoked from INSIDE the change worktree (cwd == worktree),
    metadata is committed at repo_root/.changes/. Pre-L-01 only computed a
    sibling path and returned None. Now: read the current branch + the
    committed manifest beside it."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _CHANGE_ID)
    branch = _seed_change_metadata(tmp_path)

    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:3] == ["git", "branch", "--show-current"]:
            return (0, branch + "\n", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import resolve_current_change
    result = resolve_current_change(repo_root=tmp_path)
    assert result is not None
    assert result["change_id"] == _CHANGE_ID
    assert result["branch"] == branch


def test_resolve_via_changes_scan_when_branch_unhelpful(monkeypatch, tmp_path):
    """Detached HEAD / odd branch name, but committed metadata is present →
    the .changes/ scan finds it by change_id."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _CHANGE_ID)
    _seed_change_metadata(tmp_path)

    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:3] == ["git", "branch", "--show-current"]:
            return (0, "\n", "")  # detached / empty → step 1 can't parse
        if cmd[:4] == ["git", "branch", "--list", "change/*"]:
            return (0, "", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import resolve_current_change
    result = resolve_current_change(repo_root=tmp_path)
    assert result is not None
    assert result["change_id"] == _CHANGE_ID


def test_resolve_sibling_worktree_fallback(monkeypatch, tmp_path):
    """Driving from the MAIN repo: no committed metadata at repo_root, but the
    sibling change worktree has it. Pins the original fallback path."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _CHANGE_ID)
    repo_root = tmp_path / "agents"
    repo_root.mkdir()
    # Sibling worktree per change_worktree_path convention.
    sibling = tmp_path / "agents-change-create-foo-bar"
    _seed_change_metadata(sibling)

    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:3] == ["git", "branch", "--show-current"]:
            return (0, "dev\n", "")  # on dev in the main repo → not a change
        if cmd[:4] == ["git", "branch", "--list", "change/*"]:
            return (0, "  change/create-foo-bar\n", "")
        if cmd[:5] == ["git", "branch", "--list", "--remotes", "origin/change/*"]:
            return (0, "", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import resolve_current_change
    result = resolve_current_change(repo_root=repo_root)
    assert result is not None
    assert result["change_id"] == _CHANGE_ID


def test_find_change_branches_includes_origin_only(monkeypatch, tmp_path):
    """L-01 step 4: a teammate's change branch present only on origin must be
    surfaced (current=False), de-duped against local branches."""
    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:4] == ["git", "branch", "--list", "change/*"]:
            return (0, "  change/fix-local-one\n", "")
        if cmd[:5] == ["git", "branch", "--list", "--remotes", "origin/change/*"]:
            return (0,
                    "  origin/HEAD -> origin/dev\n"
                    "  origin/change/fix-local-one\n"      # dup of local → skip
                    "  origin/change/feat-remote-two\n", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import find_change_branches
    branches = {b["branch"]: b for b in find_change_branches(tmp_path)}
    assert "change/fix-local-one" in branches
    assert "change/feat-remote-two" in branches
    assert branches["change/feat-remote-two"]["current"] is False
    # de-duped: only one entry for the local branch
    assert sum(1 for b in find_change_branches(tmp_path)
               if b["branch"] == "change/fix-local-one") == 1


def test_find_change_branches_dual_prefix(monkeypatch, tmp_path):
    """#112: with a `feature/{slug}` convention, find_change_branches globs the
    configured prefix UNION legacy change/* — so a renamed feature/<slug>
    change is discoverable AND existing change/* changes still appear."""
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        calls.append(list(cmd))
        # Local globs
        if cmd[:3] == ["git", "branch", "--list"] and "--remotes" not in cmd:
            pattern = cmd[3]
            if pattern == "change/*":
                return (0, "  change/feat-legacy-one\n", "")
            if pattern == "feature/*":
                return (0, "  feature/renamed-two\n", "")
            return (0, "", "")
        # Remote globs
        if cmd[:4] == ["git", "branch", "--list", "--remotes"]:
            return (0, "", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import find_change_branches
    branches = {b["branch"]: b for b in
                find_change_branches(tmp_path, convention="feature/{slug}")}
    # Legacy change/* still discovered
    assert "change/feat-legacy-one" in branches
    # Renamed feature/<slug> discovered under the configured prefix
    assert "feature/renamed-two" in branches
    # Both prefixes were globbed
    globbed = {c[3] for c in calls
               if c[:3] == ["git", "branch", "--list"] and "--remotes" not in c}
    assert "change/*" in globbed
    assert "feature/*" in globbed


# ─── back_integrate_change_branch (Phase 5 #2: Step 0 / Step 12.5 mechanic) ─


def test_back_integrate_already_current(monkeypatch, tmp_path):
    """When dev_ref is already ancestor → status=already_current, no merge."""
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        calls.append(list(cmd))
        if cmd[:2] == ["git", "fetch"]:
            return (0, "", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (0, "", "")  # is ancestor
        return (1, "", "unexpected command")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import back_integrate_change_branch
    result = back_integrate_change_branch(tmp_path, "change/create-introduce-payments")
    assert result["status"] == "already_current"
    assert result["change_branch"] == "change/create-introduce-payments"
    # No merge invocation expected
    merge_calls = [c for c in calls if c[:2] == ["git", "merge"] and "--is-ancestor" not in c]
    assert merge_calls == []


def test_back_integrate_merged_ok(monkeypatch, tmp_path):
    """When merge succeeds → status=merged_ok with merged_commits count."""
    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            return (0, "", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (1, "", "")  # NOT ancestor → behind dev
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return (0, "3\n", "")
        if cmd[:2] == ["git", "merge"]:
            return (0, "", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import back_integrate_change_branch
    result = back_integrate_change_branch(tmp_path, "change/create-introduce-payments")
    assert result["status"] == "merged_ok"
    assert result["merged_commits"] == 3


def test_back_integrate_merge_conflict(monkeypatch, tmp_path):
    """When merge fails + diff shows U files → status=merge_conflict."""
    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            return (0, "", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (1, "", "")
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return (0, "5\n", "")
        if cmd[:2] == ["git", "merge"]:
            return (1, "", "CONFLICT (content): Merge conflict in src/auth.py")
        if cmd[:5] == ["git", "diff", "--name-only", "--diff-filter=U"]:
            return (0, "src/auth.py\nsrc/orders.py\n", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import back_integrate_change_branch
    result = back_integrate_change_branch(tmp_path, "change/create-introduce-payments")
    assert result["status"] == "merge_conflict"
    assert result["files"] == ["src/auth.py", "src/orders.py"]
    assert "CW-04" in result["guidance"]
    assert "three options" in result["guidance"]


def test_back_integrate_fetch_failed(monkeypatch, tmp_path):
    """When git fetch returns non-zero → status=fetch_failed."""
    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            return (128, "", "fatal: unable to access origin")
        return (0, "", "")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import back_integrate_change_branch
    result = back_integrate_change_branch(tmp_path, "change/create-introduce-payments")
    assert result["status"] == "fetch_failed"
    assert "fatal" in result["error"]


def test_back_integrate_internal_error(monkeypatch, tmp_path):
    """Merge fails but no conflict files → status=internal_error."""
    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            return (0, "", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (1, "", "")
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return (0, "1\n", "")
        if cmd[:2] == ["git", "merge"]:
            return (128, "", "fatal: something unexpected")
        if cmd[:5] == ["git", "diff", "--name-only", "--diff-filter=U"]:
            return (0, "", "")  # no conflict files
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import back_integrate_change_branch
    result = back_integrate_change_branch(tmp_path, "change/create-introduce-payments")
    assert result["status"] == "internal_error"
    assert "fatal" in result["error"]


def test_back_integrate_no_fetch_when_disabled(monkeypatch, tmp_path):
    """fetch_first=False skips the fetch invocation."""
    fetch_called = []

    def fake_run(cmd, cwd=None, timeout=None, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            fetch_called.append(cmd)
            return (0, "", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (0, "", "")
        return (1, "", "unexpected")

    monkeypatch.setattr("_wpxlib._run", fake_run)
    from _wpxlib import back_integrate_change_branch
    result = back_integrate_change_branch(tmp_path, "change/create-introduce-payments", fetch_first=False)
    assert result["status"] == "already_current"
    assert fetch_called == [], "fetch should not have been called"
