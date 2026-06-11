"""Reusable Hypothesis strategies for change-identity property tests (WP-006).

This module is the FOUNDATION for the property layer that proves the
WP-001..005 safe-resolution invariants UNIVERSALLY (over generated inputs)
rather than on the single fixed 26-change population WP-004 uses. WP-007
(pure-core properties) and WP-008 (stateful lifecycle model) both consume the
strategies exported here.

It is underscore-prefixed so pytest does NOT collect it as a test module — it
is a plain helper imported by the test modules (the same convention as
``_route_fixtures.py`` / ``_recovery_contract_fixtures.py`` in this directory).

Design oracle
-------------
The handle derivation is owned by ``_wpxlib.ulid_handle`` —
``ulid_handle(u) == "CH-" + u[10:16]`` (the first 6 chars of the 80-bit random
TAIL, per #101). The strategies are built to AGREE with that oracle; they NEVER
re-implement it. A "handle collision" is therefore two distinct 26-char ULIDs
that share ``u[10:16]`` but differ elsewhere.

ULID layout (26 Crockford-base32 chars):
    [0:10]   timestamp  (head)        — arbitrary here
    [10:16]  handle-tail (6 chars)    — DETERMINES the handle
    [16:26]  trailing randomness (10) — DISAMBIGUATES collided ids

``_wpxlib`` is importable via the conftest ``sys.path`` injection
(``tests/conftest.py`` inserts the scripts dir).

Stdlib + hypothesis. Python 3.11-safe.
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from _wpxlib import ulid_handle  # noqa: E402  (sys.path injected by conftest)

# The Crockford-base32 alphabet — excludes I, L, O, U by construction. This is
# the SAME alphabet as ``_wpxlib._CROCKFORD_BASE32``; redeclared here (rather
# than imported as a private) so the generator reads self-contained, and pinned
# by ``test_valid_ulid_always_validates`` against the real validator.
_CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _crockford_block(length: int) -> SearchStrategy[str]:
    """A strategy for a fixed-length string over the Crockford-base32 alphabet."""
    return st.text(alphabet=_CROCKFORD_BASE32, min_size=length, max_size=length)


def valid_ulid() -> SearchStrategy[str]:
    """Strategy for a valid 26-char Crockford-base32 ULID.

    Invariant: every drawn value satisfies ``validate_change_ulid`` and
    contains none of I/L/O/U (those are absent from the Crockford alphabet by
    construction).
    """
    return _crockford_block(26)


def _distinct_blocks(length: int, n: int) -> SearchStrategy[list[str]]:
    """Strategy for ``n`` PAIRWISE-DISTINCT fixed-length Crockford blocks."""
    return st.lists(
        _crockford_block(length),
        min_size=n,
        max_size=n,
        unique=True,
    )


def colliding_ulid_group(n: int) -> SearchStrategy[list[str]]:
    """Strategy for ``n`` distinct ULIDs that all share ONE ``ulid_handle``.

    Invariant (pinned by ``test_colliding_ulid_group_shares_handle``): the
    returned list has exactly ``n`` ULIDs, all valid, pairwise distinct as ids,
    and all mapping to the SAME ``ulid_handle`` — i.e. they share ``[10:16]``
    (the handle-tail) and differ in ``[16:26]`` (trailing randomness). Heads
    (``[0:10]``) are arbitrary and do not affect the handle.

    ``n`` must be >= 1. The shared 6-char handle-tail is drawn once; the ``n``
    distinct 10-char trailing suffixes guarantee distinct ids even if two heads
    happen to coincide.
    """
    if n < 1:
        raise ValueError(f"colliding_ulid_group needs n >= 1, got {n}")

    @st.composite
    def _build(draw) -> list[str]:
        shared_tail = draw(_crockford_block(6))          # [10:16] — the handle
        suffixes = draw(_distinct_blocks(10, n))         # [16:26] — distinct ids
        heads = draw(st.lists(_crockford_block(10), min_size=n, max_size=n))
        return [heads[i] + shared_tail + suffixes[i] for i in range(n)]

    return _build()


def _record_from_id(change_id: str, *, stale_handle: bool = False) -> dict:
    """Build a store-shaped record dict for ``change_id``.

    Shape matches the records ``_changes_matching_handle`` reads:
    ``{change_id, handle, slug, intent, branch, primitive}``. ``handle`` is the
    canonical ``ulid_handle(change_id)`` so stored- and recomputed-handle paths
    agree by default; ``stale_handle=True`` writes a HEAD-derived handle
    (``"CH-" + change_id[:6]``) instead, exercising the migration-robust
    recompute path (#101) where a pre-change record's stored handle disagrees
    with the recomputed tail handle.
    """
    handle = "CH-" + change_id[:6] if stale_handle else ulid_handle(change_id)
    short = change_id[-6:].lower()
    return {
        "change_id": change_id,
        "handle": handle,
        "slug": f"slug-{short}",
        "intent": f"intent for {short}",
        "branch": f"change/{short}",
        "primitive": "fix",
    }


def change_record(change_id: str | None = None) -> SearchStrategy[dict]:
    """Strategy for a single store-shaped change record.

    Invariant: the drawn dict carries the six store keys
    (``change_id, handle, slug, intent, branch, primitive``); its ``handle``
    is the canonical ``ulid_handle(change_id)`` so the stored- and
    recomputed-handle resolution paths agree. When ``change_id`` is supplied the
    record is built around it; otherwise a fresh ``valid_ulid`` is drawn.
    """
    id_strategy = st.just(change_id) if change_id is not None else valid_ulid()
    return id_strategy.map(_record_from_id)


def planned_collision_groups(max_size: int, max_collision_groups: int) -> int:
    """The number of collision groups a ``change_set`` will EXACTLY realise.

    ``change_set`` treats ``max_collision_groups`` as the requested count and
    produces exactly that many groups, clamped down only when ``max_size`` can
    not fit ``2 * groups`` records (each group needs >= 2 members). Callers that
    want to assert the realised collision structure compute the expected count
    from this helper rather than re-deriving the clamp.
    """
    return max(0, min(max_collision_groups, max_size // 2))


def change_set(
    min_size: int = 1,
    max_size: int = 12,
    max_collision_groups: int = 3,
) -> SearchStrategy[list[dict]]:
    """Strategy for a list of change records with a CONTROLLABLE collision shape.

    The returned records contain EXACTLY ``max_collision_groups`` handle-
    collision groups (each a set of >= 2 records sharing one ``ulid_handle``) —
    clamped down only when ``max_size`` can not fit ``2 * groups`` records —
    plus singleton records, with EVERY ``change_id`` globally distinct.

    "Controllable" means deterministic: a caller that requests N groups gets N
    groups (clamped to fit), never a free 0..N draw. Use
    ``planned_collision_groups(max_size, max_collision_groups)`` to compute the
    realised count.

    Invariants (pinned by the self-test):
      * ``test_change_set_ids_globally_distinct`` — no two records share a
        ``change_id``.
      * ``test_change_set_collision_structure_is_controllable`` — the number of
        handles held by >= 2 records equals
        ``planned_collision_groups(max_size, max_collision_groups)``.

    To keep the collision count exact, every group and every singleton is
    allocated its OWN distinct 6-char handle-tail up front, so a singleton can
    never accidentally land on a group's handle and groups never share a handle
    with each other.

    ``min_size``/``max_size`` bound the TOTAL record count; the realised total
    is at least ``2 * groups`` and at least ``min_size`` (with a floor of 1 —
    ``change_set`` is never empty).
    """
    if min_size < 0 or max_size < min_size:
        raise ValueError(
            f"invalid bounds: min_size={min_size}, max_size={max_size}"
        )

    @st.composite
    def _build(draw) -> list[dict]:
        # Exactly this many groups (clamped so 2*groups fits max_size).
        n_groups = planned_collision_groups(max_size, max_collision_groups)

        # Each group is minimally a colliding PAIR (>= 2 members); this keeps
        # the per-group budget tight so the requested group count always fits.
        group_sizes = [2] * n_groups
        used_by_groups = sum(group_sizes)

        # Singletons fill the remainder up to a drawn total within bounds. The
        # total is at least max(min_size, used_by_groups, 1) and never exceeds
        # max_size (which fits used_by_groups by the clamp above).
        low = max(min_size, used_by_groups, 1)
        high = max(low, max_size)
        total = draw(st.integers(min_value=low, max_value=high))
        n_singletons = total - used_by_groups

        # Allocate ONE distinct handle-tail per group AND per singleton so no
        # two groups, and no singleton, ever collide unintentionally.
        n_tails = n_groups + n_singletons
        tails = draw(_distinct_blocks(6, n_tails)) if n_tails else []

        # Globally-distinct disambiguating suffixes ([16:26]) across ALL ids.
        n_ids = used_by_groups + n_singletons
        suffixes = draw(_distinct_blocks(10, n_ids)) if n_ids else []
        heads = draw(
            st.lists(_crockford_block(10), min_size=n_ids, max_size=n_ids)
        ) if n_ids else []

        records: list[dict] = []
        tail_idx = 0
        id_idx = 0
        # Collision groups: all members share their group's handle-tail.
        for size in group_sizes:
            shared_tail = tails[tail_idx]
            tail_idx += 1
            for _ in range(size):
                cid = heads[id_idx] + shared_tail + suffixes[id_idx]
                records.append(_record_from_id(cid))
                id_idx += 1
        # Singletons: each gets its own (group-distinct) handle-tail.
        for _ in range(n_singletons):
            solo_tail = tails[tail_idx]
            tail_idx += 1
            cid = heads[id_idx] + solo_tail + suffixes[id_idx]
            records.append(_record_from_id(cid))
            id_idx += 1

        return records

    return _build()
