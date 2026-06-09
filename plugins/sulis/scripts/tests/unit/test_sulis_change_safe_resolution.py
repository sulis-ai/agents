"""Unit tests for safe change resolution (#101 + #274).

The disease: change tooling resolved a change from a selector and, when the
selector was ambiguous (a colliding handle, #101) or overridden (an explicit
selector vs the session's SULIS_CHANGE_ID, #274), it *silently picked one* —
so `nuke` / `ship` / `mark-shipped` could act on the WRONG change, caught only
by luck. The fix: refuse + make the operator resolve.

These cover the shared resolver helpers in `sulis-change`:
  _changes_matching_handle        — returns ALL matches (so callers can refuse)
  _emit_ambiguous_match           — refuse + list candidates
  _select_change_id_refusing_conflict — the ship/mark-shipped resolver (#274)
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

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

# Two distinct, valid 26-char ULIDs (Crockford-base32, excludes I/L/O/U).
_ULID_A = "01HYQC71000000000000000001"
_ULID_B = "01HYQC71000000000000000002"


# ─── _changes_matching_handle ─────────────────────────────────────────────


def test_matcher_finds_by_stored_handle():
    records = [{"change_id": _ULID_A, "handle": "CH-ABC123", "slug": "a"}]
    assert sc._changes_matching_handle("ch-abc123", records) == records


def test_matcher_finds_by_recomputed_handle_when_stored_absent():
    # No stored handle → match by recomputing ulid_handle(change_id) (migration
    # robustness across the head→tail derivation change).
    from _wpxlib import ulid_handle
    records = [{"change_id": _ULID_A, "slug": "a"}]
    h = ulid_handle(_ULID_A)
    assert sc._changes_matching_handle(h, records) == records


def test_matcher_returns_ALL_colliding_matches():
    # The #101 core: a handle shared by two changes returns BOTH, so the caller
    # can refuse instead of silently taking the first.
    records = [
        {"change_id": _ULID_A, "handle": "CH-DUP999", "slug": "first"},
        {"change_id": _ULID_B, "handle": "CH-DUP999", "slug": "second"},
    ]
    matches = sc._changes_matching_handle("CH-DUP999", records)
    assert len(matches) == 2


def test_matcher_empty_handle_matches_nothing():
    records = [{"change_id": _ULID_A, "handle": "CH-ABC123"}]
    assert sc._changes_matching_handle("", records) == []


# ─── _emit_ambiguous_match (refuse, never guess) ──────────────────────────


def test_ambiguous_match_refuses_and_lists_candidates(capsys):
    matches = [
        {"change_id": _ULID_A, "branch": "change/fix-a", "slug": "a", "stage": "x"},
        {"change_id": _ULID_B, "branch": "change/fix-b", "slug": "b", "stage": "y"},
    ]
    with pytest.raises(SystemExit):
        sc._emit_ambiguous_match("Handle CH-DUP999", matches)
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "refusing to guess" in payload["error"]
    # Both candidates surfaced so the operator can disambiguate.
    ids = {c["change_id"] for c in payload["context"]["candidates"]}
    assert ids == {_ULID_A, _ULID_B}


# ─── _select_change_id_refusing_conflict (#274 + #101 for ship) ───────────


def test_explicit_handle_vs_session_conflict_refuses(capsys):
    # #274: --handle resolves to A, session is bound to B → REFUSE (do not
    # silently act on the session's change).
    records = [{"change_id": _ULID_A, "handle": "CH-AAAAAA", "slug": "a"}]
    with pytest.raises(SystemExit):
        sc._select_change_id_refusing_conflict(
            explicit_change_id=None,
            explicit_handle="CH-AAAAAA",
            env_change_id=_ULID_B,
            records=records,
        )
    payload = json.loads(capsys.readouterr().out)
    assert "conflicts with the session" in payload["error"]


def test_explicit_handle_matching_session_resolves(capsys):
    # No conflict when the explicit handle resolves to the session's own change.
    records = [{"change_id": _ULID_A, "handle": "CH-AAAAAA", "slug": "a"}]
    out = sc._select_change_id_refusing_conflict(
        explicit_change_id=None,
        explicit_handle="CH-AAAAAA",
        env_change_id=_ULID_A,
        records=records,
    )
    assert out == _ULID_A


def test_session_only_resolves_to_session_change():
    out = sc._select_change_id_refusing_conflict(
        explicit_change_id=None,
        explicit_handle=None,
        env_change_id=_ULID_B,
        records=[],
    )
    assert out == _ULID_B


def test_ambiguous_explicit_handle_refuses(capsys):
    # #101 for the ship path: an explicit handle that matches >1 change refuses.
    records = [
        {"change_id": _ULID_A, "handle": "CH-DUP999", "slug": "first"},
        {"change_id": _ULID_B, "handle": "CH-DUP999", "slug": "second"},
    ]
    with pytest.raises(SystemExit):
        sc._select_change_id_refusing_conflict(
            explicit_change_id=None,
            explicit_handle="CH-DUP999",
            env_change_id=None,
            records=records,
        )
    payload = json.loads(capsys.readouterr().out)
    assert "refusing to guess" in payload["error"]


def test_nothing_given_refuses(capsys):
    with pytest.raises(SystemExit):
        sc._select_change_id_refusing_conflict(
            explicit_change_id=None,
            explicit_handle=None,
            env_change_id=None,
            records=[],
        )
    payload = json.loads(capsys.readouterr().out)
    assert "required" in payload["error"]
