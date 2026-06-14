"""ChangeService — the programmatic Change-entity lifecycle (#128, slice 2).

Moves change-entity handling from scattered prose + a best-effort start hook
into ONE handler over the EntityRepository port (#52). The CLI commands call it
(`sulis-change start` → open, `mark-shipped` → ship, `nuke` → nuke), and it is
importable as the SDK surface — so "what happens to the Change entity across
its life" lives in code, in one place, not in skill markdown.

Lifecycle = the transaction axis on the entity:
  open  → state=in-flight   (a change begins)
  ship  → state=shipped      (the commit point)
  nuke  → state=nuked        (the rollback point)

The provenance edges (produced_by_change / evolved_by_change) + the actual
commit/rollback of the produced-entity set ride ON this handler — that's #67.
This slice gives the handler + the state lifecycle; #67 adds the edges.
"""

from __future__ import annotations

from datetime import datetime, timezone

from _change_emission import emit_change
from _entity_repository import EntityRepository

_TYPE = "change"


def _full_id(change_id: str) -> str:
    """Accept a bare ULID or a full ``dna:change:<ulid>`` and return the full id."""
    cid = str(change_id)
    return cid if cid.startswith("dna:change:") else f"dna:change:{cid}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ChangeService:
    """The Change-entity lifecycle over an EntityRepository (the SDK handler)."""

    def __init__(self, repo: EntityRepository) -> None:
        self._repo = repo

    # ─── create ────────────────────────────────────────────────────────────

    def open(self, record: dict, *, for_product: str | None = None) -> dict:
        """Emit the Change in its initial in-flight state (start). Idempotent —
        the entity id reuses the manifest ULID, so a re-open overwrites in place."""
        return emit_change({**record, "state": "in-flight"}, self._repo,
                           for_product=for_product)

    # ─── read ──────────────────────────────────────────────────────────────

    def get(self, change_id: str) -> "dict | None":
        return self._repo.find_by_id(_TYPE, _full_id(change_id))

    # ─── transitions ─────────────────────────────────────────────────────────

    def ship(self, change_id: str, *, shipped_at: "str | None" = None) -> "dict | None":
        """Transition to shipped — the transaction COMMIT point. Sets shipped_at.
        Returns the updated entity, or None when no such Change exists (a change
        that never emitted an entity — e.g. started on an older plugin)."""
        entity = self.get(change_id)
        if entity is None:
            return None
        entity["state"] = "shipped"
        entity["shipped_at"] = shipped_at or _now_iso()
        self._repo.save(_TYPE, entity)
        return entity

    def nuke(self, change_id: str, *, at: "str | None" = None) -> "dict | None":
        """Transition to nuked — the transaction ROLLBACK point. A nuke's end is
        marked by valid_to (the bitemporal window close), NOT shipped_at — a
        nuked change never shipped. Returns the updated entity, or None if absent."""
        entity = self.get(change_id)
        if entity is None:
            return None
        entity["state"] = "nuked"
        entity["valid_to"] = at or _now_iso()
        entity.pop("shipped_at", None)  # never shipped
        self._repo.save(_TYPE, entity)
        return entity

    # ─── transaction set (#67 slice 3c) ─────────────────────────────────────

    def produced(self, change_id: str) -> list:
        """Entities this change CREATED (produced_by_change == this change) —
        the change's transaction set. Live + already-deleted both returned;
        callers filter sys_status if they want only live ones."""
        ref = _full_id(change_id)
        return [e for e in self._repo.iter_entities()
                if e.get("produced_by_change") == ref]

    def evolved(self, change_id: str) -> list:
        """Entities this change REVISED (pre-existed; not created by it)."""
        ref = _full_id(change_id)
        return [e for e in self._repo.iter_entities()
                if ref in (e.get("evolved_by_change") or [])
                and e.get("produced_by_change") != ref]

    def rollback(self, change_id: str) -> list:
        """nuke=rollback: SOFT-delete the entities this change produced —
        sys_status=deleted, the record kept as audit (the way nuke keeps the
        branch). Entities the change merely EVOLVED pre-existed, so they are
        left untouched. Returns the rolled-back entities. Idempotent: an
        already-deleted entity is re-saved deleted (no error)."""
        rolled = []
        for entity in self.produced(change_id):
            # entity_type from the canonical id (dna:{type}:{ulid}) — reliable,
            # unlike @type which may be a vocab IRI.
            etype = str(entity["id"]).split(":")[1]
            entity["sys_status"] = "deleted"
            self._repo.save(etype, entity)
            rolled.append(entity)
        return rolled

    # ─── stage derived from the run-trace (#129 B3) ──────────────────────────

    _STAGE_PREFIX = "change-stage:"

    def stage_history(self, change_id: str) -> list:
        """The change's stage journey, DERIVED from the run-trace — the ordered
        list of `change-stage:<stage>` LifecycleRuns this change produced (B2),
        newest last. Each entry: {stage, at}. The run-sequence IS the progress;
        no hand-written stage string is consulted."""
        runs = [
            e for e in self.produced(change_id)
            if str(e.get("step_name", "")).startswith(self._STAGE_PREFIX)
        ]
        runs.sort(key=lambda e: str(e.get("at") or ""))
        return [
            {"stage": str(e["step_name"])[len(self._STAGE_PREFIX):], "at": e.get("at")}
            for e in runs
        ]

    def current_stage(self, change_id: str) -> "str | None":
        """The stage the change has reached, derived from the trace — the latest
        `change-stage:*` run, or None if it has produced no stage runs yet."""
        history = self.stage_history(change_id)
        return history[-1]["stage"] if history else None
