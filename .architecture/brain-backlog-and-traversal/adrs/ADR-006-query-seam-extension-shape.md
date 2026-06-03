# ADR-006 — Query seam grows by-type, by-state, and roadmap-view modes on the existing predicate primitives

> Change: CH-01KT60 · Status: accepted · Pillar: Form + Proof
> Relates: FR-07 (backlog command), FR-08 (conversational traverse), FR-09 (query-seam extension + wiring)

## Decision

Extend `_brain_query.py` and `sulis-brain-query` with the three views the
traverse path needs, built **on the existing predicate combinators** rather
than new bespoke walkers:

- `_brain_query.find_opportunities(base_dir, *, domain="product-development",
  state=None)` — sibling to the existing `find_requirements`; optional
  `state` filter via the existing `where_field_equals("state", ...)`.
- `find_requirements(...)` gains an optional `state=` kwarg, same mechanism.
- A `roadmap_members(base_dir)` reader for the ADR-001 sidecar, and a
  `find_roadmap(base_dir, ...)` that resolves member ids to entities via the
  existing `where_id_in(...)` predicate.
- New CLI modes on `sulis-brain-query`, mutually exclusive with the existing
  ones: `--open` (open = draft requirements + hypothesis opportunities),
  `--roadmap`, `--done` (implemented/verified requirements), plus
  `--by-type <opportunity|requirement>` and `--by-state <state>` for the
  composable case. Same `{"ok":…,"data":{"count":N,"entities":[…]}}`
  envelope.

## Why

The query module's own docstring states the design intent: *"the typed
predicates below cover the common cases ... they compose cheaply with
`find_entities(..., predicate=...)`."* The new views are precisely common
cases. `find_opportunities` is the missing sibling to `find_requirements`
(the module has the requirement enumerator but not the opportunity one,
despite the SRD naming "surface `find_opportunities`"). State filtering is
`where_field_equals` — already written. Roadmap resolution is `where_id_in` —
already written. **Nothing new needs inventing**; this is composition of
existing primitives, the boring path.

The CLI gains plain founder-facing verbs (`--open` / `--roadmap` / `--done`)
because that's the vocabulary FR-07 mandates (open / roadmap / done), and the
composable `--by-type` / `--by-state` because FR-09 names "by entity type,
by state" as the seam-level capability. The verbs are convenience compositions
over the primitives; an agent or skill can drop to `--by-state` when it needs
something the three named views don't cover.

## Alternatives considered

- **A new "backlog" module separate from `_brain_query` (rejected).** The
  query module is explicitly the single read seam ("anything that needs to
  ask which entities match this predicate goes through here ... without it,
  every consumer reaches into the on-disk layout directly"). A second read
  module re-introduces exactly the layout-coupling the seam exists to
  prevent. Rejected: fragments the read surface.

- **Compute open/roadmap/done in the skill prose (rejected).** Pushing the
  state→view mapping into markdown means the skill and the agent (FR-08) each
  re-implement it and drift. The mapping (`open = {draft, hypothesis}`,
  `done = {implemented, verified}`) is a query concern; it belongs in the
  seam so both consumers call one definition. Rejected: duplication across
  the two FR-07/FR-08 consumers.

- **Add a SPARQL/RDF query layer (rejected — premature).** The module
  docstring is explicit that the flat-file walk is the boring choice at
  current N (<200 instances) and the impl swaps behind the function
  signatures when N hurts. Roadmap views over a few dozen entities do not
  justify a query engine. Rejected: over-engineering; defer to the Track-2
  substrate.

## Consequences

- `find_opportunities` + the `state` kwargs are pure additions — existing
  callers (the DoD verification flow using `find_requirements`,
  `find_testresults_verifying`) are unaffected (kwarg defaults preserve
  behaviour). No characterisation test needed for a pure addition, but the
  REINFORCE-Test WP adds unit coverage for the new modes (Proof pillar).
- **FR-09 wiring** is satisfied by two consumers calling the seam:
  `/sulis:backlog` (FR-07) and the Sulis agent body (FR-08). This is what
  turns the orphaned read seam live — the SRD's grounding finding that
  "nothing in any skill or the agent calls it."
- **Empty-store + best-effort (NFR-01, Q3):** every new view returns
  `{"ok":true,"data":{"count":0,"entities":[]}}` against an empty/missing
  store (the existing `iter_entities` already returns early on a missing
  base dir). A malformed roadmap sidecar yields an empty roadmap, never an
  error.
- The `open`/`done` state sets are defined **once** as module constants
  (`_OPEN_REQUIREMENT_STATES`, `_OPEN_OPPORTUNITY_STATES`,
  `_DONE_REQUIREMENT_STATES`) so the skill and agent share the definition.
