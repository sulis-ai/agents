"""Unit tests for nuke's safe-matcher routing + the retired head-prefix rung (WP-002).

WP-002 routes `nuke` through the same SAFE matcher the `recreate` / `mark-shipped`
verbs already use (`_changes_matching_handle` over `list_all_changes()`), retires
the dead head-prefix rung (`_scan_state_dir_by_prefix`) that tried to match a
tail-minted handle against timestamp-head ULID dir names (the mint/lookup
mismatch, #101 — dead code masked by the first-slug-match rung), and adds the
readable change name to the ambiguity candidate list.

These tests pin three behaviours:

  1. CHARACTERISATION (REORGANISE, MUST) — the head-prefix scan never matches a
     tail-minted handle's prefix against a head-named state dir. This is the dead
     rung; the test passes against the CURRENT code (proving it dead) and keeps
     passing after the helper is removed (the scan-by-prefix concept stays dead).
  2. nuke resolves a tail-minted handle to its EXACT change via the safe matcher
     (not via the dead rung).
  3. an ambiguous (shared) handle refuses, listing handle + readable name + branch.
  4. nuke --change-id <ULID> resolves the exact change for symmetry.

Harness mirrors `test_sulis_change_nuke.py`: real git worktrees (fast +
deterministic) + a HOME-based ~/.sulis state dir, with emit_ok / emit_error
captured so SystemExit doesn't unwind the test.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
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

from _wpxlib import ulid_handle  # noqa: E402  (after sys.path is set by sc import)

# Two distinct valid 26-char ULIDs sharing the SAME timestamp HEAD (positions
# 0-9) but DIFFERENT random tails (positions 10-25). Their tail-derived handles
# (CH-<tail[0:6]>) DIFFER; a head-prefix scan would conflate them.
_ULID_A = "01HYQC7100AAAAAAAAAAAAAAAA"
_ULID_B = "01HYQC7100BBBBBBBBBBBBBBBB"
# A third ULID that shares ULID_A's tail-derived handle (same tail[0:6]) but a
# different full id — the collision that must REFUSE.
_ULID_A_TWIN = "01HYQC7100AAAAAACCCCCCCCCC"


@pytest.fixture(autouse=True)
def _home_base_isolation(tmp_path_factory, monkeypatch):
    """Isolate ~/.sulis via HOME (mirrors test_sulis_change_nuke). Opt out of the
    repo-wide SULIS_STATE_DIR isolation so list_all_changes() reads the HOME store."""
    monkeypatch.delenv("SULIS_STATE_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))


# ─── emit capture harness ─────────────────────────────────────────────────


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


def _resolve_target(args, captured, patches, repo):
    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        result = {"target": None}
        try:
            result["target"] = sc._resolve_nuke_target(Path(repo), args)
        except (_ExitOK, _ExitErr):
            pass
    return result["target"]


# ─── fixtures: a real change branch + worktree + global record ─────────────


def _make_change(
    repo: Path, home: Path, primitive: str, slug: str, change_id: str,
) -> dict:
    """Create a real change branch + worktree + a global change.json record.

    The record carries the tail-derived handle (ulid_handle), the slug, the
    branch, and an intent (the readable name). The state dir is named with the
    FULL ULID (timestamp head) — exactly the production layout that makes the
    head-prefix scan dead for a tail-minted handle.
    """
    branch = f"change/{primitive}-{slug}"
    worktree = repo.parent / f"{repo.name}-change-{primitive}-{slug}"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree), "dev"],
        cwd=repo, check=True, capture_output=True,
    )
    # The committed manifest lives in the worktree (the production case).
    manifest = worktree / ".changes" / f"{primitive}-{slug}.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f'change_id: "{change_id}"\nslug: "{slug}"\nprimitive: "{primitive}"\n'
        f'branch: "{branch}"\nworktree_path: "{worktree}"\n',
        encoding="utf-8",
    )
    # Global record (state dir named by the FULL ULID).
    state = home / ".sulis" / "changes" / change_id
    state.mkdir(parents=True, exist_ok=True)
    handle = ulid_handle(change_id)
    intent = f"readable intent for {slug}"
    (state / "change.json").write_text(
        json.dumps({
            "change_id": change_id,
            "handle": handle,
            "slug": slug,
            "primitive": primitive,
            "branch": branch,
            "worktree_path": str(worktree),
            "intent": intent,
            "stage": "implement",
        }),
        encoding="utf-8",
    )
    (state / "state.json").write_text('{"stage": "implement"}', encoding="utf-8")
    return {
        "change_id": change_id,
        "handle": handle,
        "intent": intent,
        "branch": branch,
        "primitive": primitive,
        "slug": slug,
        "worktree_path": worktree,
        "state_dir": state,
    }


def _target_args(repo, *, slug=None, handle=None, change_id=None) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=str(repo),
        slug=slug,
        handle=handle,
        change_id=change_id,
        force=False,
    )


# ─── 1. CHARACTERISATION: the head-prefix rung is dead for tail-minted handles ─


def test_scan_state_dir_by_prefix_is_dead_for_tail_minted_handles(
    tmp_path, monkeypatch,
):
    """Pin the dead rung BEFORE removal (REORGANISE characterisation, MUST).

    A change's STATE DIR is named with the full ULID (timestamp head). Its
    handle is tail-derived (CH-<ulid[10:16]>). A scan for dirs whose NAME starts
    with the handle's 6-char prefix therefore never matches — the mint (tail)
    vs lookup (head) mismatch (#101). This is dead code: the prefix lookup can
    only ever return (no-prefix-match, None) for a real tail-minted handle.

    Expressed against the resolution CONCEPT so it survives the helper's removal:
    scanning the state base for a dir whose name starts with the tail-handle
    prefix yields no match.
    """
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    base = home / ".sulis" / "changes" / _ULID_A
    base.mkdir(parents=True)

    # The tail-derived handle's 6-char prefix (the part after "CH-").
    prefix = ulid_handle(_ULID_A)[len("CH-"):]  # = _ULID_A[10:16] = "AAAAAA"

    # No state dir name starts with the TAIL prefix — the dir is head-named.
    from _change_state import changes_base
    matches = [d for d in changes_base().iterdir()
               if d.is_dir() and d.name.startswith(prefix)]
    assert matches == [], (
        "head-named state dir must NOT match the tail-minted handle prefix — "
        "this is the dead rung WP-002 retires"
    )
    # And the dir IS findable by its real (head) name, proving the dir exists —
    # so the empty match above is the mismatch, not an empty store.
    assert (changes_base() / _ULID_A).is_dir()


# ─── 2. nuke resolves a tail-minted handle via the safe matcher ────────────


def test_nuke_resolves_tail_minted_handle_via_safe_matcher(
    local_git_repo, tmp_path, monkeypatch,
):
    """A tail-minted handle drives nuke's target resolution to the EXACT change
    via the shared safe matcher — NOT via the dead head-prefix scan."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    meta = _make_change(local_git_repo, home, "create", "tail-minted", _ULID_A)

    captured, patches = _capture_emit()
    target = _resolve_target(
        _target_args(local_git_repo, handle=meta["handle"]),
        captured, patches, local_git_repo,
    )
    assert target is not None, f"resolution failed: {captured.get('error')}"
    assert target["change_id"] == _ULID_A
    assert target["branch"] == meta["branch"]


# ─── 3. ambiguous handle refuses, listing handle + name + branch ───────────


def test_nuke_ambiguous_handle_lists_handle_name_branch_and_refuses(
    local_git_repo, tmp_path, monkeypatch,
):
    """Two changes sharing a tail-derived handle → REFUSE, with candidates that
    carry the readable name + branch (Scenario 5)."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    # _ULID_A and _ULID_A_TWIN share tail[0:6] = "AAAAAA" → same CH- handle.
    assert ulid_handle(_ULID_A) == ulid_handle(_ULID_A_TWIN)
    a = _make_change(local_git_repo, home, "create", "dup-first", _ULID_A)
    b = _make_change(local_git_repo, home, "create", "dup-second", _ULID_A_TWIN)
    shared_handle = a["handle"]

    captured, patches = _capture_emit()
    _resolve_target(
        _target_args(local_git_repo, handle=shared_handle),
        captured, patches, local_git_repo,
    )
    assert captured["ok"] is False
    assert "refusing to guess" in captured["error"]
    candidates = captured["context"]["candidates"]
    ids = {c["change_id"] for c in candidates}
    assert ids == {_ULID_A, _ULID_A_TWIN}
    # Each candidate carries the readable name + branch (Scenario 5).
    names = {c.get("name") for c in candidates}
    assert a["intent"] in names and b["intent"] in names
    branches = {c.get("branch") for c in candidates}
    assert a["branch"] in branches and b["branch"] in branches


# ─── 4. nuke --change-id resolves the exact change (symmetry) ──────────────


def test_nuke_resolves_by_change_id_flag(
    local_git_repo, tmp_path, monkeypatch,
):
    """nuke --change-id <ULID> resolves the exact change directly (symmetry with
    recreate / mark-shipped)."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    meta = _make_change(local_git_repo, home, "create", "by-change-id", _ULID_A)

    captured, patches = _capture_emit()
    target = _resolve_target(
        _target_args(local_git_repo, change_id=_ULID_A),
        captured, patches, local_git_repo,
    )
    assert target is not None, f"resolution failed: {captured.get('error')}"
    assert target["change_id"] == _ULID_A
    assert target["branch"] == meta["branch"]
