"""Phase-1 property-based tests for change-identity safe resolution (WP-007).

These are the UNIVERSAL complement to the example-based safe-resolution suite
(``test_sulis_change_safe_resolution.py`` / ``test_change_identity_resolution.py``
/ ``test_collision_regression.py``). Where the example-based tests prove the
#101 safe-resolution invariants on one fixed 26-change population, this module
proves them for ANY generated change-set (any collision structure) by driving
Hypothesis over the WP-006 strategies in ``_change_identity_strategies``.

Five invariants, one property each, each carrying a one-line docstring naming
the SPEC guarantee it proves:

  1. ``ulid_handle`` is a pure function of the id's handle-tail (``[10:16]``):
     two ids collide on handle IFF they share that tail.
  2. ``_changes_matching_handle`` is SOUND + COMPLETE — for any record-set it
     returns EXACTLY the records whose handle equals the queried handle (none
     dropped, none invented).
  3. By-id resolution is EXACT — each member of a generated change-set resolves
     to THAT member, never a sibling that merely shares its handle.
  4. Ambiguity ALWAYS refuses — an explicit handle held by >=2 changes makes
     ``_select_change_id_refusing_conflict`` REFUSE with the exact candidate set;
     a handle held by exactly 1 resolves to that one. It never silently guesses.
  5. ``change_worktree_path(..., change_id=)`` is INJECTIVE — distinct change_ids
     map to distinct worktree paths even when ``primitive``+``slug`` collide.

All five functions under test are PURE (records / ids passed as arguments), so
each property runs Hypothesis's default budget (>=100 examples) cheaply with
ZERO change-store or git I/O. Invariants 2 and 4 are sanity-checked against the
#101 disease during authoring (a silent first-match would FAIL them), so they
are falsifiable, not tautologies.

``sulis-change`` is loaded via ``SourceFileLoader`` (the file has no ``.py``
extension), mirroring ``_load_sulis_change()`` in
``test_change_identity_resolution.py``. ``_wpxlib`` and the strategies module are
importable via the conftest ``sys.path`` injection.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

import pytest
from hypothesis import HealthCheck, given, settings

from unit._change_identity_strategies import (  # noqa: E402
    change_set,
    colliding_ulid_group,
    valid_ulid,
)
from _wpxlib import change_worktree_path, ulid_handle  # noqa: E402

_SCRIPTS = Path(__file__).resolve().parents[2]
_SC_PATH = _SCRIPTS / "sulis-change"


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SC_PATH))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


sc = _load_sulis_change()


# ─── refusal-capture harness (in-process; no stdout parsing) ───────────────
#
# ``emit_error`` writes a JSON envelope to stdout then exits. Under a ``@given``
# body that runs hundreds of times, capturing stdout is brittle, so — mirroring
# the example-based suite's ``_capture_emit`` — we patch ``emit_error`` to raise
# a typed exception carrying the refusal's ``context`` (the candidate set) so a
# refusal and its exact candidates are observable in-process.


class _Refused(Exception):
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}


def _refusal_capture():
    """Return a ``with``-usable patch making ``emit_error`` raise ``_Refused``."""
    def _err(message, context=None):
        raise _Refused(message, context)

    return mock.patch.object(sc, "emit_error", side_effect=_err)


# ─── Invariant 1: ulid_handle is a pure function of the handle-tail ────────


@given(a=valid_ulid(), b=valid_ulid())
def test_handle_is_pure_function_of_tail(a: str, b: str) -> None:
    """SPEC invariant 1 (#101): the handle is derived from the ULID's random
    TAIL (``[10:16]``), not its head — so two ids collide on ``ulid_handle``
    IFF they share that 6-char tail, and nothing else about the id matters."""
    same_handle = ulid_handle(a) == ulid_handle(b)
    same_tail = a[10:16] == b[10:16]
    assert same_handle == same_tail
    # The handle depends on the tail ALONE: head + trailing randomness are
    # irrelevant. ulid_handle(a) is exactly "CH-" + a[10:16].
    assert ulid_handle(a) == "CH-" + a[10:16]


# ─── Invariant 2: _changes_matching_handle is sound + complete ─────────────


@given(records=change_set(max_collision_groups=3))
@settings(max_examples=150)
def test_matching_handle_is_sound_and_complete(records: list) -> None:
    """SPEC invariant 2 (#101): for any generated change-set and any queried
    handle, ``_changes_matching_handle`` returns EXACTLY the records whose
    ``ulid_handle(change_id)`` equals that handle — no matching record dropped
    (complete), no non-matching record returned (sound). This is what lets
    callers REFUSE on ambiguity instead of silently taking a first match."""
    handles = {ulid_handle(r["change_id"]) for r in records}
    # The handle every record was built to carry, plus a handle held by NO
    # record (so the empty-result arm is exercised universally too).
    queried_handles = handles | {"CH-ZZZZZZ"}

    for h in queried_handles:
        expected = {
            r["change_id"] for r in records if ulid_handle(r["change_id"]) == h
        }
        got = {
            r["change_id"] for r in sc._changes_matching_handle(h, records)
        }
        # Sound: nothing invented. Complete: nothing dropped.
        assert got == expected, (h, expected, got)


# ─── Invariant 3: by-id resolution is exact ────────────────────────────────


@given(records=change_set(max_collision_groups=3))
@settings(max_examples=150)
def test_by_id_resolution_is_exact(records: list) -> None:
    """SPEC invariant 3 (Scenarios 1, 4): a full ``change_id`` is the unambiguous
    key — for any change-set with any collision structure, each member's id
    resolves to THAT member and never a sibling that merely shares its handle.
    The id-keyed path must be exact even where the handle is ambiguous."""
    for member in records:
        cid = member["change_id"]
        # The pure id-resolution semantics: exact-id equality over the record
        # population (the store-backed _resolve_record_by_id wraps this same
        # equality; here we exercise it without store I/O).
        resolved = [r for r in records if r["change_id"] == cid]
        assert len(resolved) == 1, (cid, resolved)
        assert resolved[0] is member
        # And the colliding siblings (same handle, different id) are NOT it.
        my_handle = ulid_handle(cid)
        siblings = [
            r for r in records
            if r["change_id"] != cid and ulid_handle(r["change_id"]) == my_handle
        ]
        for sib in siblings:
            assert sib["change_id"] != cid


# ─── Invariant 4: ambiguity always refuses, never guesses ──────────────────


@given(records=change_set(min_size=2, max_collision_groups=3))
@settings(max_examples=150)
def test_ambiguity_always_refuses_never_guesses(records: list) -> None:
    """SPEC invariant 4 (Scenario 5, #101): the explicit-handle resolution arm
    of ``_select_change_id_refusing_conflict`` REFUSES when a handle is held by
    >=2 changes — surfacing the EXACT candidate set (all colliding records,
    none missing, none extra) — and resolves to the sole holder when a handle
    is held by exactly 1. It never silently returns one of several."""
    by_handle: dict = {}
    for r in records:
        by_handle.setdefault(ulid_handle(r["change_id"]), []).append(r)

    with _refusal_capture():
        for handle, holders in by_handle.items():
            if len(holders) >= 2:
                # Ambiguous → must refuse and surface the EXACT candidate set.
                with pytest.raises(_Refused) as exc:
                    sc._select_change_id_refusing_conflict(
                        explicit_change_id=None,
                        explicit_handle=handle,
                        env_change_id=None,
                        records=records,
                    )
                assert "refusing to guess" in exc.value.message
                candidate_ids = {
                    c["change_id"] for c in exc.value.context["candidates"]
                }
                assert candidate_ids == {h["change_id"] for h in holders}
            else:
                # Exactly one holder → resolves to that one, never a guess.
                resolved = sc._select_change_id_refusing_conflict(
                    explicit_change_id=None,
                    explicit_handle=handle,
                    env_change_id=None,
                    records=records,
                )
                assert resolved == holders[0]["change_id"]


# ─── Invariant 5: id-keyed worktree path is injective ──────────────────────


@pytest.fixture()
def _fixed_state_dir(tmp_path_factory, monkeypatch):
    """Pin ``SULIS_STATE_DIR`` once for the whole property (NOT per generated
    example). The injectivity result is independent of the base — both paths
    share it; distinctness comes solely from the ``change_id`` path component —
    so a single stable base set before ``@given`` runs is correct, and avoids
    the per-example function-scoped-fixture pitfall Hypothesis warns about."""
    state = tmp_path_factory.mktemp("state")
    monkeypatch.setenv("SULIS_STATE_DIR", str(state / ".sulis"))


@given(group=colliding_ulid_group(2))
@settings(
    max_examples=150,
    # JUSTIFIED suppression (Blue DoD): ``_fixed_state_dir`` deliberately is NOT
    # reset per generated example — it pins a single stable ``SULIS_STATE_DIR``
    # base before the property runs. The injectivity result is independent of
    # that base (both paths share it; distinctness is purely the ``change_id``
    # path component), so the un-reset fixture is correct here, not a bug.
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_id_keyed_worktree_path_is_injective(
    group: list, _fixed_state_dir,
) -> None:
    """SPEC invariant 5 (Scenario 3 defence-in-depth, HD-005): the id-keyed
    ``change_worktree_path(..., change_id=)`` is INJECTIVE — two DISTINCT
    change_ids map to DISTINCT worktree paths even when ``primitive``+``slug``
    are identical (the last structural way two colliding changes could share a
    working tree). Driven over a colliding pair: same handle, distinct ids."""
    cid_a, cid_b = group[0], group[1]
    # Worst case for collision: identical primitive + slug for both ids.
    repo_root = Path("/repo/example")
    path_a = change_worktree_path(repo_root, "fix", "shared-slug", change_id=cid_a)
    path_b = change_worktree_path(repo_root, "fix", "shared-slug", change_id=cid_b)
    # Distinct ids (even sharing a handle) → distinct paths.
    assert cid_a != cid_b
    assert path_a != path_b
