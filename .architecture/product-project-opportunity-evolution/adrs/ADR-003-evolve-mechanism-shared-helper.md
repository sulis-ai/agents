---
id: ADR-003
title: The evolve mechanism lives in a shared `_entity_evolve` helper behind the EntityRepository port
status: accepted
date: 2026-06-03
deciders: [iain]
---

## Context

Scope item 3: when a living entity changes, the system must
read-current-version → close the prior valid-window (`valid_to`) → open a new
window (`valid_from` + `confidence` + `sys_status`) → record PROV
`wasGeneratedBy` the generating Activity (+ `used` inputs).

Today the emitters (`_product_emission`, `_opportunity_emission`, …) write a
**current snapshot only** via `repo.save(...)`. `save` overwrites the file at
`{base}/{domain}/{entity_type}/{ulid}.jsonld` — there is one file per entity id,
no history. The bitemporal fields exist on the schemas but no emitter sets
`valid_to` on an old version or chains windows. Evolution is OFF for everyone.

Two facts shape where the mechanism goes:

- **The hexagonal seam already exists.** `EntityRepository` is the port
  (`save` / `find_by_id` / `validate`); `LocalFileEntityAdapter` is today's
  adapter; `StorageServiceAdapter` is anticipated (ADR-005). The evolve logic
  must sit *above* the port so it works unchanged against either adapter.
- **`find_by_id` returns one instance per id.** The current on-disk layout
  (one file per `{ulid}`) cannot hold two windows of the same entity at two
  paths if both share the id's ULID. The history model needs a layout decision.

The question with a real consequence: *where does evolve live, what is its API,
and how does it not break the current-snapshot callers?*

## Decision

**A single shared helper module `_entity_evolve.py`, sitting above the
`EntityRepository` port, owns the close-window / open-window / PROV-write
cycle. Emitters opt in by calling `evolve_entity(...)` instead of `repo.save(...)`.**

### API

```python
def evolve_entity(
    *,
    repo: EntityRepository,
    entity_type: str,
    next_version: dict,          # the new state the caller computed
    generated_by: str | None,    # dna:lifecyclerun:<ulid> — the Activity (ADR-001)
    used: list[str] | None = None,
    confidence: float | None = None,
    valid_from: str | None = None,   # defaults to now (UTC)
    now: str | None = None,          # injectable clock for tests
) -> dict:
    """Close the current open window for next_version['id'] (set valid_to),
    open a new window on next_version (valid_from + confidence + sys_status
    + was_generated_by), persist both. Returns the new open version.

    First-emission case (no prior window): opens the first window only.
    No-op case (next_version byte-identical to current open window): returns
    the current version unchanged, opens no new window — idempotent re-runs
    do not churn history.
    """
```

`used` (the Activity's consumed inputs) is written onto the **LifecycleRun**,
not the entity (PROV-O direction, ADR-002) — so the helper's `used` argument is
passed through to the Activity-emission seam, not onto `next_version`. The
helper's job for the entity is `was_generated_by` + the window fields.

### History layout (the load-bearing sub-decision)

**One file per entity, holding the version history as an ordered list of
windows, keyed by the stable entity id.** The current open window is the last
element (the only one with `valid_to == null`).

Rationale: keeps `find_by_id(type, id)` returning the entity (now: its history
envelope, with a `current()` accessor for the open window), preserves the
"one file per id" git-friendly layout, and the evolve helper appends a window
rather than overwriting. The alternative — one file per (id × window) — would
fork the adapter's `_instance_path` (which derives the path from the id's ULID
alone) and is a larger, riskier change to a seam that other entity types depend
on. The envelope approach is additive to the adapter and the as-of-time query
reads the window list.

> **Open Architecture Question (OAQ-1) deferred to plan-work / store design:**
> whether the file adapter materialises windows as a list-in-one-file or the
> SQLite store materialises them as rows is an *adapter* concern. The port
> contract is "save a new version, close the prior window"; each adapter
> satisfies it in its own storage idiom. The TDD pins the *contract*; the two
> adapters' WPs pin their own materialisation. Recorded here so the
> decomposition does not treat the two as one WP.

### Not breaking current-snapshot callers

Callers that still call `repo.save(...)` directly keep writing current
snapshots — `evolve_entity` is **opt-in**, layered on top, never replacing
`save`. The migration of Product/Opportunity/Project emitters to call
`evolve_entity` is scope item 4 and is done emitter-by-emitter. Event-entity
emitters (Decision, LifecycleRun, Release, Deployment) keep calling `save` —
they are append-only events and MUST NOT evolve (SPEC non-goal; enforced by a
`_LIVING_ENTITY_TYPES` allowlist in the helper that refuses to evolve a type
not on the list).

## Options Considered

- **Put evolve methods on the EntityRepository port (rejected).** Couples every
  adapter to history semantics and bloats the port. `_brain_query.py` set this
  precedent — set-shaped reads got a separate module rather than extra port
  methods *"so the write-validation discipline isn't coupled to read patterns."*
  Evolve follows the same reasoning: a separate module above the port.
- **Each emitter implements its own close/open logic (rejected).** Violates
  check-before-building (EP-03): three emitters would grow the same window-chain
  code. Extract the shared primitive first. The helper is that primitive.
- **Overwrite-with-supersedes (rejected for living entities).** That is the
  *event* model (Decision/LifecycleRun) and is explicitly NOT the living model.
  Living entities need as-of-time queryable windows, not a supersedes pointer.

## Consequences

- New module `_entity_evolve.py` + its unit/characterisation tests.
- The as-of-time read (scope item 4 acceptance: "queryable as-of-time") is a new
  function on the read seam (`_brain_query.py`): given (type, id, as_of) return
  the window whose `[valid_from, valid_to)` contains `as_of`.
- A `_LIVING_ENTITY_TYPES` allowlist is the guard that keeps evolve off event
  entities — a single source of truth for the events-vs-living split.
- The history-envelope layout is additive to `LocalFileEntityAdapter`; the
  SQLite adapter (ADR-005) materialises the same windows as rows.
