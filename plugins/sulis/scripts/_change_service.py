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
