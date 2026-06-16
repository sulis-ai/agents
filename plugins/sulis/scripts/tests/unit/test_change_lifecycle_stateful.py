"""Phase 2 — stateful, model-based test of the change-identity safety invariant.

WP-008. WP-007 proves each resolution call is safe *in isolation* (the per-call
properties). This module proves the SAME safety holds across arbitrary
OPERATION SEQUENCES — the sequence-level analogue. A Hypothesis
``RuleBasedStateMachine`` (``ChangeLifecycleStateMachine``) drives random
sequences of ``start`` / ``ship`` / ``nuke`` / ``recreate`` / ``focus`` over an
in-memory store model seeded (via the WP-006 strategies) with a mix of
colliding and non-colliding handles, and after EVERY step asserts the
invariant:

    No operation ever acts on a change whose id != the requested id, and an
    ambiguous handle ALWAYS refuses (never silently picks one).

This is the sequence-level guard against the two observed SPEC symptoms — a
session landing on the wrong change, and two colliding sessions braided into
one workspace.

Store model (the design decision recorded in the WP)
----------------------------------------------------
The rules call the SAME pure resolution functions the real CLI uses against an
in-process ``dict[change_id -> record]`` model of the store — never the real
git/filesystem store. Identity logic is pure, so this keeps thousands of
generated sequences fast and deterministic and keeps the machine focused on the
IDENTITY invariant rather than git mechanics:

  * id resolution           — exact lookup in the model dict (the same key
                              ``_resolve_record_by_id`` resolves on in the CLI).
  * handle resolution        — ``_select_change_id_refusing_conflict``'s
                              explicit-handle arm over the model's record list
                              (the same safe matcher + refuse-on-ambiguity the
                              CLI's ship/mark-shipped path uses).
  * worktree path            — ``change_worktree_path(..., change_id=...)`` —
                              id-keyed, computed not materialised.

The destructive verbs (``ship`` / ``nuke``) are modelled as state transitions
(record marked shipped / removed) GATED on a SAFE resolve, so "the resolve
picked the right id" is exercised without spawning git or touching disk.

Refusal is observed via the same ``emit_error`` patch-to-raise technique
WP-007 and the example-based ``test_collision_regression.py`` real-store
complement use: an ambiguous handle calls ``emit_error``, which the patch turns
into a sentinel exception, so "refused" is observable as "raised".

Companions: ``test_change_identity_properties.py`` (WP-007) is the per-call
analogue; ``test_collision_regression.py`` is the example-based real-store
complement over the fixed 26-change live population.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

from hypothesis import settings
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    invariant,
    rule,
)

from unit._change_identity_strategies import (  # noqa: E402
    change_record,
    colliding_ulid_group,
)

_SCRIPTS = Path(__file__).resolve().parents[2]
_SC_PATH = _SCRIPTS / "sulis-change"


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SC_PATH))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


sc = _load_sulis_change()


# ─── refusal harness: emit_error → raise, so "refused" is observable ───────


class _Refused(Exception):
    """Raised in place of ``emit_error`` so a refusal (ambiguous handle,
    not-found, conflict) is observable as an exception rather than a process
    exit. Carries the message for diagnostics on an unexpected refusal."""

    def __init__(self, message, context=None):
        super().__init__(message)
        self.message = message
        self.context = context


def _raise_refused(message, context=None):
    """Stand-in for ``emit_error`` that raises a catchable sentinel instead of
    exiting the process — so a refusal is observable in-process."""
    raise _Refused(message, context)


def _patch_refusal():
    """Patch ``sc.emit_error`` to ``_raise_refused`` (the CLI's ``emit_error``
    calls ``sys.exit``; in-process we want a catchable sentinel). Returns the
    patch context manager — mirrors the ``_err`` side-effect the example-based
    suites (``test_collision_regression.py``) use."""
    return mock.patch.object(sc, "emit_error", side_effect=_raise_refused)


# ─── the pure resolution probes the model drives (the CLI's own functions) ──

# A nominal repo root — only its .parent/.name shape matters to the legacy
# (non-id-keyed) worktree-path form, which the model never exercises (it always
# passes a change_id). Kept stable so worktree paths are a pure function of id.
_REPO_ROOT = Path("/tmp/sulis-stateful-model-repo")


def _resolve_id_selector(model: dict, change_id: str) -> "str | None":
    """Resolve an EXACT id selector against the model.

    Mirrors the CLI's ``_resolve_record_by_id`` semantics against the in-memory
    model: a live record whose key equals ``change_id`` resolves to itself;
    anything else is a miss. By construction the model is keyed by id, so a hit
    can only ever be the requested change — the property the rule then asserts.
    """
    record = model.get(change_id)
    return None if record is None else str(record.get("change_id") or "")


def _resolve_handle_selector(records: list, handle: str) -> str:
    """Resolve a HANDLE selector through the CLI's safe, refuse-on-ambiguity
    path (``_select_change_id_refusing_conflict``'s explicit-handle arm).

    Returns the resolved id on a unique match; raises ``_Refused`` (via the
    patched ``emit_error``) on no-match or on an ambiguous handle. This is the
    exact function ship/mark-shipped resolve through, so the model exercises the
    shipped safe-resolution code, not a re-implementation."""
    return sc._select_change_id_refusing_conflict(
        explicit_change_id=None,
        explicit_handle=handle,
        env_change_id=None,
        records=records,
    )


def _records_by_handle(records: list) -> dict:
    """Group records by their EFFECTIVE handle — recomputed ``ulid_handle`` for
    a valid id, else the stored handle (upper-cased).

    Mirrors the migration-robust keying ``_changes_matching_handle`` uses, so
    "which records share a handle" is computed the same way the resolver sees
    it. Extracted to the single authority shared by the ``resolve_some_handle``
    rule and the ``ambiguous_handle_always_refuses`` invariant (2-consumer
    threshold)."""
    by_handle: dict[str, list] = {}
    for r in records:
        cid = str(r.get("change_id") or "")
        h = sc.ulid_handle(cid).upper() if len(cid) == 26 \
            else str(r.get("handle") or "").upper()
        by_handle.setdefault(h, []).append(r)
    return by_handle


def _worktree_for(record: dict) -> Path:
    """The id-keyed worktree path for a record (the braided-session guard).

    Always passes the change_id, so distinct ids yield distinct worktrees by
    construction (HD-005) — the invariant the machine then checks holds across
    the whole live population after every step."""
    return sc.change_worktree_path(
        _REPO_ROOT, record.get("primitive") or "fix",
        record.get("slug") or "", change_id=record.get("change_id"),
    )


# ─── the state machine ─────────────────────────────────────────────────────


class ChangeLifecycleStateMachine(RuleBasedStateMachine):
    """Drive random change-lifecycle sequences over an in-memory store model;
    after every step assert the change-identity safety invariant.

    Model state:
      * ``live``    — ``dict[change_id -> record]`` of currently-live changes.
      * ``shipped`` — ids marked shipped (removed from ``live``).
      * ``nuked``   — ids destroyed (removed from ``live``).
      * ``ids`` / ``handles`` Bundles — known selectors to draw rules' targets
        from, so a handle drawn for ``recreate``/``focus``/``ship``/``nuke`` may
        be one that ≥2 live records share (the ambiguous case the strategy mix
        guarantees appears).
    """

    ids = Bundle("ids")

    def __init__(self):
        super().__init__()
        self.live: dict[str, dict] = {}
        self.shipped: set[str] = set()
        self.nuked: set[str] = set()
        # Every handle ever introduced (live or not) — the pool the handle
        # resolve rule samples, so a once-colliding handle stays a candidate
        # selector even after some holders ship/nuke.
        self._handle_pool: list[str] = []

    # ── helpers ────────────────────────────────────────────────────────────

    def _add(self, record: dict) -> None:
        cid = str(record.get("change_id") or "")
        # Globally-distinct ids by construction (strategies guarantee it); guard
        # against a re-draw of an already-known id (no-op rather than clobber).
        if cid and cid not in self.live and cid not in self.shipped \
                and cid not in self.nuked:
            self.live[cid] = record

    def _records(self) -> list:
        return list(self.live.values())

    # ── rules: grow the population ───────────────────────────────────────────

    @rule(target=ids, record=change_record())
    def start_fresh(self, record):
        """Start a change with a FRESH (likely non-colliding) handle and add it
        to the model. Returns its id into the ``ids`` bundle, and its handle
        into the ``handles`` bundle via ``_register_handle``."""
        self._add(record)
        self._register_handle(record)
        return str(record.get("change_id") or "")

    @rule(target=ids, group=colliding_ulid_group(2))
    def start_colliding_pair(self, group):
        """Start TWO changes that SHARE one handle — the collision condition.
        Both enter the model; the shared handle becomes an ambiguous selector
        the resolve rules must refuse on. Returns the first id (the second is
        still reachable via the shared handle)."""
        first_id = ""
        for cid in group:
            record = _record_for(cid)
            self._add(record)
            self._register_handle(record)
            first_id = first_id or cid
        return first_id

    def _register_handle(self, record: dict) -> None:
        # The handle is stashed on a plain list the handle resolve rule samples
        # (Bundles only carry rule RETURN values, and a handle is shared by
        # several records so it isn't a per-record token).
        h = str(record.get("handle") or "")
        if h and h not in self._handle_pool:
            self._handle_pool.append(h)

    # ── rules: resolve + act (the safety-critical paths) ─────────────────────

    @rule(change_id=ids)
    def focus_by_id(self, change_id):
        """Focus (bind the session to) a change by its EXACT id. The resolved
        id must be EXACTLY the requested id — never a sibling — or a clean miss
        if it has since been shipped/nuked."""
        resolved = _resolve_id_selector(self.live, change_id)
        if resolved is not None:
            assert resolved == change_id, (
                f"focus_by_id resolved {change_id} -> {resolved} (wrong id!)"
            )

    @rule(change_id=ids)
    def recreate_by_id(self, change_id):
        """Recreate a change by its EXACT id. Resolves to ITSELF (the worktree
        is recomputed id-keyed) or is a clean miss; never a colliding sibling."""
        resolved = _resolve_id_selector(self.live, change_id)
        if resolved is not None:
            assert resolved == change_id, (
                f"recreate_by_id resolved {change_id} -> {resolved}"
            )
            wt = _worktree_for(self.live[change_id])
            # The recreated worktree is the change's OWN id-keyed dir.
            assert str(change_id) in str(wt), (wt, change_id)

    @rule(change_id=ids)
    def ship_by_id(self, change_id):
        """Ship a change by its EXACT id: resolve-then-act. Transition the model
        (live -> shipped) ONLY on a safe exact resolve to SELF."""
        resolved = _resolve_id_selector(self.live, change_id)
        if resolved is None:
            return  # already shipped/nuked — nothing to act on.
        assert resolved == change_id, (
            f"ship_by_id resolved {change_id} -> {resolved} (would ship the "
            f"wrong change!)"
        )
        del self.live[change_id]
        self.shipped.add(change_id)

    @rule(change_id=ids)
    def nuke_by_id(self, change_id):
        """Nuke a change by its EXACT id: resolve-then-act. Destroy the model
        record ONLY on a safe exact resolve to SELF (never a sibling)."""
        resolved = _resolve_id_selector(self.live, change_id)
        if resolved is None:
            return
        assert resolved == change_id, (
            f"nuke_by_id resolved {change_id} -> {resolved} (would nuke the "
            f"wrong change!)"
        )
        del self.live[change_id]
        self.nuked.add(change_id)

    @rule()
    def resolve_some_handle(self):
        """Resolve a KNOWN handle (which may be shared by ≥2 live records)
        through the CLI's safe path. If ≥2 live records hold it, resolution MUST
        refuse (raise); otherwise it resolves to the unique live holder — never
        a guess."""
        if not self._handle_pool:
            return
        records = self._records()
        grouped = _records_by_handle(records)
        for handle in self._handle_pool:
            holders = grouped.get(handle.upper(), [])
            with _patch_refusal():
                if len(holders) >= 2:
                    # Ambiguous → MUST refuse (never silently pick).
                    try:
                        _resolve_handle_selector(records, handle)
                    except _Refused:
                        continue
                    raise AssertionError(
                        f"handle {handle} held by {len(holders)} live changes "
                        f"resolved without refusing (silent pick!)"
                    )
                elif len(holders) == 1:
                    resolved = _resolve_handle_selector(records, handle)
                    assert resolved == str(holders[0].get("change_id") or ""), (
                        f"handle {handle} resolved to {resolved}, not its sole "
                        f"holder {holders[0].get('change_id')}"
                    )
                # 0 live holders (all shipped/nuked): a miss refuses; that's
                # fine and not asserted here (covered by the per-call WP-007
                # not-found property).

    # ── invariants: checked after EVERY step ─────────────────────────────────

    @invariant()
    def ambiguous_handle_always_refuses(self):
        """Any handle held by ≥2 LIVE records, used as a selector, refuses
        rather than resolving to one of them."""
        records = self._records()
        for handle, holders in _records_by_handle(records).items():
            if len(holders) < 2:
                continue
            with _patch_refusal():
                try:
                    _resolve_handle_selector(records, handle)
                except _Refused:
                    continue
            raise AssertionError(
                f"ambiguous handle {handle} ({len(holders)} live holders) did "
                f"not refuse"
            )

    @invariant()
    def no_operation_acts_on_wrong_id(self):
        """Every live id resolves (by id) to EXACTLY itself — the resolution
        key can never name a sibling."""
        for cid, record in self.live.items():
            resolved = _resolve_id_selector(self.live, cid)
            assert resolved == cid, (
                f"id {cid} resolved to {resolved} (sibling leak!)"
            )
            assert str(record.get("change_id") or "") == cid

    @invariant()
    def distinct_ids_keep_distinct_worktrees(self):
        """No two LIVE changes ever share a worktree — the braided-session
        guard (HD-005). Distinct ids ⇒ distinct id-keyed worktree paths."""
        seen: dict[str, str] = {}
        for cid, record in self.live.items():
            wt = str(_worktree_for(record))
            clash = seen.get(wt)
            assert clash is None, (
                f"changes {clash} and {cid} share worktree {wt}"
            )
            seen[wt] = cid


def _record_for(change_id: str) -> dict:
    """Build a store-shaped record for ``change_id`` agreeing with the WP-006
    oracle (handle == ``ulid_handle(change_id)``). Used when a rule draws raw
    ids (the colliding group) rather than a ready-made record."""
    short = change_id[-6:].lower()
    return {
        "change_id": change_id,
        "handle": sc.ulid_handle(change_id),
        "slug": f"slug-{short}",
        "intent": f"intent for {short}",
        "branch": f"change/{short}",
        "primitive": "fix",
    }


# Bound the per-run step count generously enough to reach collision states
# (the strategy mix introduces colliding pairs), but capped so CI stays fast.
ChangeLifecycleStateMachine.TestCase.settings = settings(
    max_examples=100, stateful_step_count=30, deadline=None,
)

# Expose as a pytest-collectable TestCase under the default step budget.
ChangeLifecycleTest = ChangeLifecycleStateMachine.TestCase


# ─── deterministic collision-coverage anchors ─────────────────────────────
#
# The stateful machine REACHES collision states probabilistically (the strategy
# mix introduces colliding pairs — peak coexistence observed during authoring
# was 4 holders of one handle). These three deterministic tests drive a machine
# instance through a KNOWN colliding pair so each invariant is exercised against
# a guaranteed ambiguous state on EVERY run, independent of the generated draws
# — making the collision coverage self-evident rather than implicit, and
# anchoring "what the machine asserts" as readable example. They use the same
# colliding ULIDs as the example-based real-store suite
# (``test_change_identity_resolution.py``).

# Two distinct valid ULIDs sharing handle CH-DXP999 (positions [10:16] equal).
_PAIR_A = "01HYQC7100DXP9990000000002"
_PAIR_B = "01HYQC7100DXP9990000000003"


def _machine_with_colliding_pair() -> ChangeLifecycleStateMachine:
    """A fresh machine seeded with exactly the colliding pair A/B (one shared
    handle) plus one non-colliding singleton, via the machine's own rules so
    the model + handle pool are populated as in a real sequence."""
    m = ChangeLifecycleStateMachine()
    m.start_colliding_pair([_PAIR_A, _PAIR_B])
    m.start_fresh(_record_for("01HYQC7100SOLO990000000007"))
    return m


def test_ambiguous_pair_state_is_reached_and_refuses():
    """The shared handle, held by both live members, refuses to resolve (never
    silently picks A or B). Exercises ``ambiguous_handle_always_refuses`` and
    ``resolve_some_handle`` against a guaranteed ambiguous state."""
    m = _machine_with_colliding_pair()
    assert sc.ulid_handle(_PAIR_A) == sc.ulid_handle(_PAIR_B)
    assert _PAIR_A in m.live and _PAIR_B in m.live
    # Both invariant and the active-resolve rule must hold on this state.
    m.ambiguous_handle_always_refuses()
    m.resolve_some_handle()
    # And the safe resolver itself refuses the shared handle outright.
    with _patch_refusal():
        try:
            _resolve_handle_selector(m._records(), sc.ulid_handle(_PAIR_A))
        except _Refused:
            pass
        else:
            raise AssertionError("shared handle resolved without refusing")


def test_each_member_resolves_to_self_by_id_under_collision():
    """Under the collision, each member's EXACT id still resolves to itself —
    never the sibling. Exercises ``no_operation_acts_on_wrong_id`` and the
    id-selector rules on a known ambiguous population."""
    m = _machine_with_colliding_pair()
    m.no_operation_acts_on_wrong_id()
    m.focus_by_id(_PAIR_A)
    m.recreate_by_id(_PAIR_B)
    assert _resolve_id_selector(m.live, _PAIR_A) == _PAIR_A
    assert _resolve_id_selector(m.live, _PAIR_B) == _PAIR_B


def test_colliding_members_keep_distinct_worktrees():
    """The two handle-colliding members never share a worktree — the
    braided-session guard. Exercises ``distinct_ids_keep_distinct_worktrees``
    on the exact state that motivated HD-005."""
    m = _machine_with_colliding_pair()
    m.distinct_ids_keep_distinct_worktrees()
    wt_a = _worktree_for(m.live[_PAIR_A])
    wt_b = _worktree_for(m.live[_PAIR_B])
    assert wt_a != wt_b, (wt_a, wt_b)


def test_destructive_verb_acts_only_on_resolved_self():
    """ship/nuke transition the model ONLY on a safe exact resolve to self:
    shipping A removes A and leaves the colliding sibling B untouched."""
    m = _machine_with_colliding_pair()
    m.ship_by_id(_PAIR_A)
    assert _PAIR_A not in m.live and _PAIR_A in m.shipped
    assert _PAIR_B in m.live  # the sibling sharing A's handle is untouched.
    m.nuke_by_id(_PAIR_B)
    assert _PAIR_B not in m.live and _PAIR_B in m.nuked
