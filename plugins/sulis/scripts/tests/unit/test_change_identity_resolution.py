"""Unit tests for change identity resolution by --change-id (WP-001, ADR-001).

The disease: a change's identity is its 26-char ULID `change_id`; the 6-char
`CH-XXXXXX` handle is a *display label* derived from it, and the live store has
26 handles each shared by 2-4 changes. `recreate` only accepted `--handle`, so
the cockpit (which already holds the unique id) had no way to drive recreate by
the unambiguous key — it round-tripped through the non-unique handle and could
re-materialise the WRONG change's workspace.

The fix (ADR-001): `recreate` gains a `--change-id <ULID>` entry point that
resolves the EXACT change by its full id, mirroring how `nuke` / `mark-shipped`
already accept `--change-id`. `--handle` / `--slug` keep working unchanged.

These tests drive `cmd_recreate` against a temp `SULIS_STATE_DIR` store seeded
with two *colliding-handle* changes (real in-memory store + real git worktree,
not a mock — MEA-09), asserting the id resolves to its own change and never the
sibling that merely shares the handle.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
_SC_PATH = _SCRIPTS / "sulis-change"


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SC_PATH))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


sc = _load_sulis_change()

# Two distinct, valid 26-char ULIDs (Crockford-base32, excludes I/L/O/U) that
# share the SAME 6-char tail handle (positions 10-15 identical) — the live
# collision condition. ulid_handle() reads ulid[10:16], so both yield CH-DXP999.
_ULID_A = "01HYQC7100DXP9990000000002"
_ULID_B = "01HYQC7100DXP9990000000003"


@pytest.fixture(autouse=True)
def _state_isolation(tmp_path_factory, monkeypatch):
    """Isolate the change store under a temp SULIS_STATE_DIR so list_all_changes
    / read_change_record see only the records this test seeds."""
    state = tmp_path_factory.mktemp("state")
    monkeypatch.setenv("SULIS_STATE_DIR", str(state / ".sulis"))
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)


# ─── emit capture harness (mirrors the nuke suite) ────────────────────────


class _ExitOK(Exception):
    def __init__(self, data):
        self.data = data


class _ExitErr(Exception):
    def __init__(self, message, context=None):
        self.message = message
        self.context = context


def _capture_emit():
    captured: dict = {}

    def _ok(data=None, warnings=None, exit_code=0):
        captured["ok"] = True
        captured["data"] = data
        raise _ExitOK(data)

    def _err(message, context=None):
        captured["ok"] = False
        captured["error"] = message
        captured["context"] = context
        raise _ExitErr(message, context)

    patches = [
        mock.patch.object(sc, "emit_ok", side_effect=_ok),
        mock.patch.object(sc, "emit_error", side_effect=_err),
    ]
    return captured, patches


def _run_recreate(args, captured, patches):
    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with pytest.raises((_ExitOK, _ExitErr)):
            sc.cmd_recreate(args)
    return captured


# ─── fixture: two colliding-handle changes, one with a live worktree ──────


def _seed_change_record(change_id: str, *, slug: str, branch: str,
                        primitive: str = "feat",
                        worktree_path: str | None = None) -> None:
    """Write a change.json under SULIS_STATE_DIR/changes/{change_id}/."""
    from _change_state import write_change_record
    write_change_record(change_id, {
        "change_id": change_id,
        "handle": sc.ulid_handle(change_id),
        "slug": slug,
        "primitive": primitive,
        "branch": branch,
        "worktree_path": worktree_path or "",
        "stage": "shipped",
        "shipped_sha": "",
    })


def _recreate_args(repo, *, change_id=None, handle=None, slug=None,
                   primitive="feat") -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=str(repo),
        change_id=change_id,
        handle=handle,
        slug=slug,
        primitive=primitive,
    )


# ─── RED 1: --change-id resolves the EXACT change, never the sibling ──────


def test_recreate_accepts_change_id_and_resolves_exact_change(
    local_git_repo, tmp_path, monkeypatch,
):
    """Two changes share handle CH-DUP999 but have distinct change_ids and
    distinct branches. `recreate --change-id <a.id>` must resolve A's branch,
    never B's — the unambiguous id is the resolution key (ADR-001).

    Today this fails with argparse `unrecognized arguments: --change-id`
    (the flag doesn't exist on p_recreate); cmd_recreate has no id path.
    """
    # A gets a real, already-materialised worktree on its branch, so recreate
    # hits the "worktree already exists" path and echoes A's branch back.
    branch_a = "change/feat-collide-alpha"
    worktree_a = local_git_repo.parent / f"{local_git_repo.name}-wt-alpha"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch_a, str(worktree_a), "dev"],
        cwd=local_git_repo, check=True, capture_output=True,
    )
    branch_b = "change/feat-collide-beta"

    _seed_change_record(_ULID_A, slug="collide-alpha", branch=branch_a,
                        worktree_path=str(worktree_a))
    _seed_change_record(_ULID_B, slug="collide-beta", branch=branch_b)

    # Sanity: the two changes really do collide on the handle.
    assert sc.ulid_handle(_ULID_A) == sc.ulid_handle(_ULID_B)

    captured, patches = _capture_emit()
    _run_recreate(_recreate_args(local_git_repo, change_id=_ULID_A),
                  captured, patches)

    assert captured["ok"] is True, captured
    assert captured["data"]["branch"] == branch_a
    # Never the colliding sibling.
    assert captured["data"]["branch"] != branch_b


# ─── RED 2: unknown id → clean emit_error, no side effect (Q12) ───────────


def test_recreate_by_change_id_unknown_id_clean_error(
    local_git_repo, tmp_path, monkeypatch,
):
    """An id matching no change returns a clean "not found" (emit_error,
    non-zero) and creates no worktree — the Q12 failure mode."""
    unknown = "01HYQC7100ZZZZZZ0000000099"
    # Seed an unrelated change so the store isn't empty.
    _seed_change_record(_ULID_A, slug="some-other", branch="change/feat-other")

    captured, patches = _capture_emit()
    _run_recreate(_recreate_args(local_git_repo, change_id=unknown),
                  captured, patches)

    assert captured["ok"] is False, captured
    # The error must name the unknown id (the id resolution path fired) — not
    # the generic "--handle or --slug is required" that the old handle-only
    # code emits when it ignores --change-id entirely. This is what makes the
    # test RED today: cmd_recreate has no id path, so it can't report an
    # id-specific "not found".
    err = captured["error"].lower()
    assert ("not found" in err) or ("no change" in err) or (unknown.lower() in err)
    assert "required" not in err
    # No worktree was materialised for the bogus id.
    bogus_wt = local_git_repo.parent / f"{local_git_repo.name}-wt-bogus"
    assert not bogus_wt.exists()


def test_recreate_by_change_id_malformed_id_clean_error(
    local_git_repo, tmp_path, monkeypatch,
):
    """A malformed id (not 26-char Crockford) is rejected up front with a
    clean emit_error — never a stack trace, never a silent fall-through to the
    handle path (Contract: validate the id via validate_change_ulid)."""
    malformed = "not-a-valid-ulid"
    captured, patches = _capture_emit()
    _run_recreate(_recreate_args(local_git_repo, change_id=malformed),
                  captured, patches)

    assert captured["ok"] is False, captured
    err = captured["error"].lower()
    assert "invalid" in err and "change-id" in err


# ─── _resolve_record_by_id helper (shared by recreate + mark-shipped) ──────


def test_resolve_record_by_id_direct_store_read(tmp_path, monkeypatch):
    """The direct per-change store read (change.json) is the primary path."""
    _seed_change_record(_ULID_A, slug="alpha", branch="change/feat-alpha")
    record = sc._resolve_record_by_id(_ULID_A)
    assert record is not None
    assert record["change_id"] == _ULID_A
    assert record["slug"] == "alpha"


def test_resolve_record_by_id_falls_back_to_scan(tmp_path, monkeypatch):
    """When the direct store read misses (a record whose store-dir name
    diverges from its id), the helper falls back to scanning list_all_changes
    for an exact id match — robustness for migrated/relocated records."""
    _seed_change_record(_ULID_A, slug="alpha", branch="change/feat-alpha")

    # Force the direct read to miss so the scan branch is exercised; the scan
    # still finds the record via list_all_changes (which enumerates the store).
    monkeypatch.setattr(sc, "read_change_record", lambda _cid: None)
    record = sc._resolve_record_by_id(_ULID_A)
    assert record is not None
    assert record["change_id"] == _ULID_A


def test_resolve_record_by_id_unknown_returns_none(tmp_path, monkeypatch):
    """An id matching no change yields None (callers turn this into a clean
    not-found error)."""
    _seed_change_record(_ULID_A, slug="alpha", branch="change/feat-alpha")
    assert sc._resolve_record_by_id("01HYQC7100ZZZZZZ0000000099") is None
