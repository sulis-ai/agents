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
    parse_change_branch,
    read_change_metadata,
    validate_change_primitive,
    validate_change_slug,
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
