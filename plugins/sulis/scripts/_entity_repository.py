"""EntityRepository port + EntityValidationError exception.

The marketplace-side half of the Brain↔OS contract. Per the contract, the
Brain compiles to STANDARDS — JSON Schema 2020-12, JSON-LD payloads, RDF
triple manifests, SPARQL queries — and consumers conform. This port is the
seam: anything that speaks the standards can be an adapter.

Adapters:
  - `LocalFileEntityAdapter` (now) — writes validated `.jsonld` to a git-
    tracked directory; the dev-loop substrate.
  - `StorageServiceAdapter` (Phase 2, once Track 2 lands) — wraps the Sulis
    Platform Storage Service via `entity/create` + `entity/get`. Same port,
    same call sites — coupling lives at the adapter boundary.

The Brain doesn't move when the store changes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class EntityValidationError(ValueError):
    """Raised when an entity instance fails schema validation at the
    repository boundary.

    The message names the failing field(s) plainly so a caller can act on it.
    Subclasses `ValueError` for callers that already catch validation errors
    generically.
    """


@runtime_checkable
class EntityRepository(Protocol):
    """Persistence surface for Brain entity instances.

    Implementations MUST:
      - validate `instance` against the compiled schema for `entity_type`
        BEFORE persisting (reject-on-invalid; never write a partial entity).
      - resolve schemas from the same Brain compile outputs (no per-adapter
        schema fork).
      - treat `instance_id` as the entity's `@id` from its `field_spec` — a
        ULID-shaped string (`dna:{entity_type}:{ulid}`).

    `find_by_id` returns `None` for an unknown id rather than raising — a
    missing instance is a normal query outcome, not a failure.
    """

    def save(self, entity_type: str, instance: dict) -> None:
        """Validate `instance` and persist. Raise `EntityValidationError`
        without persisting on validation failure."""
        ...

    def find_by_id(self, entity_type: str, instance_id: str) -> dict | None:
        """Return the saved instance for `instance_id`, or `None` if no
        instance with that id exists."""
        ...

    def validate(self, entity_type: str, instance: dict) -> None:
        """Validate without persisting. Raise `EntityValidationError` on
        failure; return `None` on success."""
        ...

    def iter_entities(self, entity_type: "str | None" = None) -> "Iterator[dict]":
        """Yield stored instances — all, or just one `entity_type`. A missing
        store yields nothing. Backs cross-entity reads (e.g. the change-as-
        transaction produced/evolved sets, #67)."""
        ...
