"""Regression: the LIVE 26-collision state, proving every change resolves to
itself across all four act-on verbs (WP-004, HD-003, SPEC Scenario 7).

The disease (recap): a change's identity is its 26-char ULID `change_id`; the
6-char `CH-XXXXXX` handle is a *display label* derived from the ULID's random
tail (`CH-<ulid[10:16]>`). The live store has 26 handles each shared by 2-4
changes — one handle (the real `CH-01KSNX`) shared by FOUR. Before WP-001/002,
three act-on paths (recreate / nuke / mark-shipped) could resolve a handle to
the WRONG change. WP-001 gave `recreate` a `--change-id` entry point; WP-002
routed `nuke` through the shared safe matcher and added the readable candidate
name. This suite is the regression that proves Scenarios 1-6 stay CLOSED against
the real collision shape: it reproduces the colliding population in a temp store
+ real git worktrees (no `~/.sulis` dependence, MEA-09 / SPEC Verification Plan
§3) and asserts that EVERY one of the 26 changes resolves to ITSELF across all
four verbs — and that the shared-by-four handle, typed bare, REFUSES with a
4-candidate disambiguation list rather than silently picking a sibling.

Self-contained: the fixture builds its own colliding population via the REAL
record + worktree writers (not hand-rolled JSON), so it stays correct as the
record schema evolves. Isolation is the repo-wide autouse `_isolate_sulis_state`
(temp `SULIS_STATE_DIR`, `SULIS_CHANGE_ID` cleared) plus a per-test clear here.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
from contextlib import ExitStack
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

from _change_state import write_change_record  # noqa: E402 (sys.path set by sc import)
from _wpxlib import ulid_handle, validate_change_ulid  # noqa: E402


# ─── the colliding population: 26 changes, one handle shared by FOUR ───────
#
# A change's handle is CH-<ulid[10:16]>, so two ULIDs collide iff positions
# 10-15 are identical. We synthesise groups that share a tail-prefix (the
# colliding handle) but differ in the trailing randomness (positions 16-25),
# so each change keeps a UNIQUE full id. All characters are Crockford-base32
# (excludes I/L/O/U). The shared timestamp head ("01HYQC7100") is irrelevant to
# the handle — only the tail decides collision — and mirrors changes started in
# the same coarse window.
#
# Shape (26 changes total), mirroring the real store:
#   - ONE handle shared by 4 (the CH-01KSNX→4 case): tail "D00000".
#   - groups of 3 and 2 across several other handles.
#   - the remainder as solo (unique-handle) changes, so resolution must work
#     for colliding AND non-colliding changes alike.
_HEAD = "01HYQC7100"  # 10-char timestamp head; shared, handle-irrelevant.

# (tail6, count) groups. Counts sum to 26.
_GROUPS: list[tuple[str, int]] = [
    ("D00000", 4),   # the shared-by-FOUR handle (mirrors CH-01KSNX → 4)
    ("E11111", 3),
    ("F22222", 3),
    ("G33333", 2),
    ("H44444", 2),
    ("J55555", 2),
    ("K66666", 2),
    ("M77777", 2),   # solo-ish small groups + singles below
    ("N88888", 1),
    ("P99999", 1),
    ("Q00001", 1),
    ("R00002", 1),
    ("S00003", 1),
    ("T00004", 1),
]
assert sum(c for _, c in _GROUPS) == 26


def _ulid_for(tail6: str, idx: int) -> str:
    """A valid 26-char Crockford-base32 ULID with the given 6-char handle tail.

    Positions 0-9 = shared head; 10-15 = the colliding tail (the handle);
    16-25 = 10 chars of per-change randomness so the FULL id stays unique
    within the group. ``idx`` (0-9) varies the trailing chars deterministically.
    """
    # 10 trailing Crockford chars: encode idx into the last position, pad the
    # rest with a fixed filler that keeps the id distinct per (tail, idx).
    suffix = "00000000" + "0123456789ABCDEFGHJK"[idx]  # 8 + 1 = 9 chars
    suffix = (suffix + "Z")[:10]  # pad to exactly 10
    ulid = _HEAD + tail6 + suffix
    assert len(ulid) == 26, ulid
    ok, reason = validate_change_ulid(ulid)
    assert ok, f"synthesised ULID invalid: {ulid} ({reason})"
    return ulid


def _build_population() -> list[dict]:
    """Return the 26-change colliding population as plain dicts (id/slug/handle/
    branch/intent/group_tail), WITHOUT touching any store or git — pure data so
    the shape can be asserted independently of materialisation."""
    pop: list[dict] = []
    n = 0
    for tail6, count in _GROUPS:
        for i in range(count):
            n += 1
            change_id = _ulid_for(tail6, i)
            slug = f"collide-{n:02d}-{tail6.lower()}"
            pop.append({
                "change_id": change_id,
                "handle": ulid_handle(change_id),
                "slug": slug,
                "primitive": "feat",
                "branch": f"change/feat-{slug}",
                "intent": f"readable intent for change {n:02d}",
                "group_tail": tail6,
            })
    assert len(pop) == 26
    return pop


def _materialise(repo: Path, change: dict) -> None:
    """Seed ONE change into the live shape: a real git branch + worktree off
    dev, and a global change.json written via the REAL record writer (so the
    record stays schema-correct as fields evolve — Blue/Contract requirement).
    """
    branch = change["branch"]
    worktree = repo.parent / f"{repo.name}-change-feat-{change['slug']}"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree), "dev"],
        cwd=repo, check=True, capture_output=True,
    )
    write_change_record(change["change_id"], {
        "change_id": change["change_id"],
        "handle": change["handle"],
        "slug": change["slug"],
        "primitive": change["primitive"],
        "branch": branch,
        "worktree_path": str(worktree),
        "intent": change["intent"],
        "stage": "shipped",
        "shipped_sha": "",
    })


@pytest.fixture
def collision_fixture(local_git_repo, monkeypatch):
    """The LIVE collision state in a self-contained temp store + real worktrees.

    Builds 26 colliding-handle changes (one handle shared by FOUR), each a
    distinct ULID with a real `change/feat-*` branch + worktree off dev and a
    global change.json record. Returns (repo, population) where ``population``
    is the list of change dicts. State isolation rides on the repo-wide autouse
    `_isolate_sulis_state` fixture (temp SULIS_STATE_DIR); we additionally clear
    SULIS_CHANGE_ID per-test so the focus-binding assertion controls it itself.
    """
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    population = _build_population()
    for change in population:
        _materialise(local_git_repo, change)
    return local_git_repo, population


# ─── emit capture harness (mirrors the WP-001/002 suites) ──────────────────


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


def _run_capturing(call):
    """Run ``call`` under the emit-capture patches; swallow the emit-exit
    sentinel. Returns the captured dict."""
    captured, patches = _capture_emit()
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        try:
            call()
        except (_ExitOK, _ExitErr):
            pass
    return captured


def _recreate_args(repo, *, change_id) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=str(repo), change_id=change_id, handle=None, slug=None,
        primitive="feat",
    )


def _nuke_args(repo, *, change_id=None, handle=None) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=str(repo), slug=None, handle=handle, change_id=change_id,
        force=False,
    )


# ─── verb probes: each resolves a change and returns the branch it landed on ─


def _recreate_branch(repo: Path, change_id: str) -> dict:
    """Drive `recreate --change-id`; return the captured emit payload. A
    correctly-resolved recreate echoes the change's OWN branch (the worktree
    already exists, so it's the cheap no-op path)."""
    return _run_capturing(
        lambda: sc.cmd_recreate(_recreate_args(repo, change_id=change_id))
    )


def _nuke_target(repo: Path, *, change_id=None, handle=None) -> dict:
    """Drive nuke's target RESOLUTION (not the destructive removal) and return
    the resolved descriptor, or None if resolution refused/failed."""
    result = {"target": None}

    def _call():
        result["target"] = sc._resolve_nuke_target(
            Path(repo), _nuke_args(repo, change_id=change_id, handle=handle)
        )

    captured = _run_capturing(_call)
    return result["target"], captured


def _ship_resolves(records: list, *, change_id=None, handle=None,
                   env_change_id=None) -> str:
    """The mark-shipped / ship resolution authority — resolve the change id
    refusing on ambiguity/conflict. Returns the resolved id (or raises emit)."""
    return sc._select_change_id_refusing_conflict(
        explicit_change_id=change_id,
        explicit_handle=handle,
        env_change_id=env_change_id,
        records=records,
    )


# ─── RED/GREEN 1: every change resolves to ITSELF across all four verbs ────


def test_every_colliding_change_resolves_to_itself_across_all_verbs(
    collision_fixture,
):
    """For each of the 26 colliding changes: recreate (--change-id) lands on
    its OWN branch; nuke (--change-id) resolves its OWN id+branch; ship resolves
    its OWN id; and the focus-binding (SULIS_CHANGE_ID) resolves SELF. Never a
    sibling that merely shares the handle. This is Scenario 7 — proof that the
    safe-resolution fix holds against the real collision shape."""
    repo, population = collision_fixture
    records = sc.list_all_changes()
    assert len(records) == 26

    for change in population:
        cid = change["change_id"]
        branch = change["branch"]

        # 1) recreate --change-id → own branch (worktree already materialised).
        rec = _recreate_branch(repo, cid)
        assert rec.get("ok") is True, (cid, rec)
        assert rec["data"]["branch"] == branch, (
            f"recreate resolved {cid} to {rec['data']['branch']!r}, "
            f"expected own branch {branch!r}"
        )

        # 2) nuke --change-id → own id + own branch (resolution only).
        target, ncap = _nuke_target(repo, change_id=cid)
        assert target is not None, (cid, ncap.get("error"))
        assert target["change_id"] == cid
        assert target["branch"] == branch

        # 3) ship/mark-shipped resolution → own id (explicit --change-id path).
        assert _ship_resolves(records, change_id=cid) == cid

        # 4) focus-binding: a session bound to this change (SULIS_CHANGE_ID)
        #    resolves SELF — the env id is honoured with no explicit selector.
        assert _ship_resolves(records, env_change_id=cid) == cid


# ─── RED/GREEN 2: the shared-by-four handle REFUSES with a candidate list ──


def test_ambiguous_handle_lists_candidates_and_refuses(collision_fixture):
    """The handle shared by FOUR changes (the CH-01KSNX→4 case), typed bare,
    must REFUSE across the act-on verbs and surface ALL FOUR candidates with
    handle + readable name + branch — never silently pick a sibling
    (SPEC Scenario 5, reproduced at the worst-case collision width)."""
    repo, population = collision_fixture
    shared = [c for c in population if c["group_tail"] == "D00000"]
    assert len(shared) == 4, "fixture must include a handle shared by exactly 4"
    shared_handle = shared[0]["handle"]
    assert all(c["handle"] == shared_handle for c in shared)
    expected_ids = {c["change_id"] for c in shared}

    # nuke: resolving the bare shared handle refuses + lists 4 candidates.
    target, ncap = _nuke_target(repo, handle=shared_handle)
    assert target is None
    assert ncap["ok"] is False
    assert "refusing to guess" in ncap["error"]
    candidates = ncap["context"]["candidates"]
    assert {c["change_id"] for c in candidates} == expected_ids
    # Each candidate carries the readable name + branch (Scenario 5).
    names = {c.get("name") for c in candidates}
    branches = {c.get("branch") for c in candidates}
    for c in shared:
        assert c["intent"] in names
        assert c["branch"] in branches

    # recreate: the same bare handle refuses identically (the safe matcher is
    # the single resolution authority across verbs).
    rcap = _run_capturing(
        lambda: sc.cmd_recreate(argparse.Namespace(
            repo_root=str(repo), change_id=None, handle=shared_handle,
            slug=None, primitive="feat",
        ))
    )
    assert rcap["ok"] is False
    assert "refusing to guess" in rcap["error"]
    assert {c["change_id"] for c in rcap["context"]["candidates"]} == expected_ids

    # ship/mark-shipped: the resolution authority refuses the shared handle too.
    scap = _run_capturing(
        lambda: sc._select_change_id_refusing_conflict(
            explicit_change_id=None, explicit_handle=shared_handle,
            env_change_id=None, records=sc.list_all_changes(),
        )
    )
    assert scap["ok"] is False
    assert "refusing to guess" in scap["error"]
    assert {c["change_id"] for c in scap["context"]["candidates"]} == expected_ids
