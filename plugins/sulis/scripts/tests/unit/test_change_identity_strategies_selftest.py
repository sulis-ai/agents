"""Self-test for the change-identity Hypothesis strategies (WP-006).

These are *meta-properties*: they pin the generators in
``_change_identity_strategies`` before WP-007 (pure-core properties) and
WP-008 (stateful model) rely on them. If a generator silently stops doing
what it claims (e.g. ``colliding_ulid_group`` produces ids that DON'T share a
handle, or ``change_set`` yields duplicate ids), these tests fail loudly here
rather than producing false confidence in the consumer suites.

The oracle is ``_wpxlib.ulid_handle`` — the strategies are built to AGREE with
it, never to re-implement it. ``_wpxlib`` is importable via the conftest
``sys.path`` injection (``tests/conftest.py``).

Stdlib + pytest + hypothesis. Python 3.11-safe.
"""

from __future__ import annotations

from collections import Counter

from hypothesis import given
from hypothesis import strategies as st

from _wpxlib import ulid_handle, validate_change_ulid  # noqa: E402

from unit._change_identity_strategies import (  # noqa: E402
    change_record,
    change_set,
    colliding_ulid_group,
    planned_collision_groups,
    valid_ulid,
)

# Characters the Crockford-base32 alphabet deliberately excludes (I, L, O, U).
_EXCLUDED = set("ILOU")

# The store-record keys ``_changes_matching_handle`` reads.
_RECORD_KEYS = {"change_id", "handle", "slug", "intent", "branch", "primitive"}


@given(valid_ulid())
def test_valid_ulid_always_validates(ulid: str) -> None:
    """Every drawn ULID is a real 26-char Crockford id and excludes I/L/O/U."""
    ok, reason = validate_change_ulid(ulid)
    assert ok, f"drawn ULID failed validation: {reason} ({ulid!r})"
    assert len(ulid) == 26
    assert not (_EXCLUDED & set(ulid)), f"ULID contains excluded char(s): {ulid!r}"


@given(change_record())
def test_change_record_shape_and_handle_agree(record: dict) -> None:
    """A change_record carries the six store keys and a canonical handle.

    Pins the contract WP-007/008 consume: the dict has exactly the store-record
    keys, and its stored ``handle`` equals ``ulid_handle(change_id)`` (so the
    stored- and recomputed-handle resolution paths agree by default).
    """
    assert set(record.keys()) == _RECORD_KEYS, f"unexpected keys: {record.keys()}"
    assert record["handle"] == ulid_handle(record["change_id"]), (
        f"stored handle {record['handle']!r} != "
        f"ulid_handle({record['change_id']!r})"
    )
    ok, reason = validate_change_ulid(record["change_id"])
    assert ok, f"record change_id invalid: {reason}"


@given(st.integers(min_value=2, max_value=8).flatmap(colliding_ulid_group))
def test_colliding_ulid_group_shares_handle(group: list[str]) -> None:
    """All members of a colliding group share ONE handle and are distinct ids."""
    handles = {ulid_handle(u) for u in group}
    assert len(handles) == 1, f"colliding group spread across handles: {handles}"
    assert len(set(group)) == len(group), "colliding group has duplicate ids"
    for u in group:
        ok, reason = validate_change_ulid(u)
        assert ok, f"colliding-group member invalid: {reason} ({u!r})"


@given(change_set())
def test_change_set_ids_globally_distinct(records: list[dict]) -> None:
    """No change_set ever yields two records with the same change_id."""
    ids = [r["change_id"] for r in records]
    assert len(ids) == len(set(ids)), "change_set produced duplicate change_id(s)"


def _controllable_case(g: int):
    """A (expected_groups, records) pair for a requested ``g`` collision groups.

    ``max_size`` is chosen so the clamp never bites (room for 2*g group records
    plus a few singletons), so the expected realised count equals ``g``.
    """
    max_size = max(2 * g, 1) + 4
    expected = planned_collision_groups(max_size, g)
    return change_set(
        min_size=2 * g if g else 1,
        max_size=max_size,
        max_collision_groups=g,
    ).map(lambda recs: (expected, recs))


@given(st.integers(min_value=0, max_value=3).flatmap(_controllable_case))
def test_change_set_collision_structure_is_controllable(case: tuple) -> None:
    """The count of handles held by >=2 records matches the requested groups."""
    expected_groups, records = case
    handle_counts = Counter(ulid_handle(r["change_id"]) for r in records)
    colliding_handles = sum(1 for n in handle_counts.values() if n >= 2)
    assert colliding_handles == expected_groups, (
        f"requested {expected_groups} collision group(s) but observed "
        f"{colliding_handles}: {dict(handle_counts)}"
    )
