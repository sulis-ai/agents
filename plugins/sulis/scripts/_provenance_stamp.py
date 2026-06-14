"""Provenance stamping — tag emitted entities with the active change (#67 slice 3b).

When work happens inside a change (``SULIS_CHANGE_ID`` set), the entities it
emits should record WHICH change made them — so "what did change X produce /
revise?" becomes a reverse-query (the transaction set for ship=commit /
nuke=rollback). This is a thin decorator over the EntityRepository port: it
stamps ``produced_by_change`` on first creation and appends ``evolved_by_change``
when a DIFFERENT change later revises the entity, then delegates to the inner
repo. One seam (the port), not 30-odd emitters.

Semantics:
  - new entity (not yet on disk)      → produced_by_change = the active change
  - re-saved by its OWN producer      → no change (still the same change working)
  - re-saved by a DIFFERENT change     → append that change to evolved_by_change,
                                         producer carried forward unchanged
  - entity_type == "change"            → never stamped (a change isn't produced
                                         by another change; its lineage is parent_change)
"""

from __future__ import annotations

import os
import re

from _entity_repository import EntityRepository

_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def _change_ref_from(change_id: "str | None") -> "str | None":
    """Normalise a change id (bare ULID or full ``dna:change:…``) to a full ref,
    or None when absent / malformed (never stamp a bad ref — it would fail schema
    validation and break the emission)."""
    cid = (change_id or os.environ.get("SULIS_CHANGE_ID", "")).strip()
    if cid.startswith("dna:change:"):
        cid = cid.rsplit(":", 1)[-1]
    if not _ULID_RE.match(cid):
        return None
    return f"dna:change:{cid}"


class ProvenanceStampingRepository:
    """Decorates an EntityRepository to stamp change-provenance on save."""

    def __init__(self, inner: EntityRepository, change_ref: str) -> None:
        self._inner = inner
        self._change_ref = change_ref

    def save(self, entity_type: str, instance: dict) -> None:
        if entity_type != "change":
            instance = self._stamped(entity_type, instance)
        self._inner.save(entity_type, instance)

    def _stamped(self, entity_type: str, instance: dict) -> dict:
        inst = dict(instance)  # never mutate the caller's dict
        eid = inst.get("id", "")
        existing = self._inner.find_by_id(entity_type, eid) if eid else None
        if existing is None:
            inst.setdefault("produced_by_change", self._change_ref)
            return inst
        # Evolution of an entity that already exists.
        producer = existing.get("produced_by_change")
        if producer and "produced_by_change" not in inst:
            inst["produced_by_change"] = producer            # carry forward
        evolved = list(inst.get("evolved_by_change")
                       or existing.get("evolved_by_change") or [])
        if producer != self._change_ref and self._change_ref not in evolved:
            evolved.append(self._change_ref)
        if evolved:
            inst["evolved_by_change"] = evolved
        return inst

    # ─── pass-through ────────────────────────────────────────────────────────
    def find_by_id(self, entity_type: str, instance_id: str) -> "dict | None":
        return self._inner.find_by_id(entity_type, instance_id)

    def validate(self, entity_type: str, instance: dict) -> None:
        self._inner.validate(entity_type, instance)

    def iter_entities(self, entity_type: "str | None" = None):
        return self._inner.iter_entities(entity_type)


def stamping_repo(inner: EntityRepository, change_id: "str | None" = None) -> EntityRepository:
    """Wrap ``inner`` to stamp the active change, or return it unchanged when no
    valid change is active. The default seam: pass nothing and it reads
    ``SULIS_CHANGE_ID``. No change / a malformed id → no stamping (plain repo)."""
    ref = _change_ref_from(change_id)
    return ProvenanceStampingRepository(inner, ref) if ref else inner
