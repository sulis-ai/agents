# Discussion — living product knowledge vs. the change transaction

> **Status:** OPEN — surfaced during the testable-state-done design; the build
> is **paused** pending a decision here, because it changes where verification
> cases live. Captured 2026-06-02.

## The trigger

While designing the testable-state DoD, the spec/TDD put verification cases at
`.architecture/{change}/verification-cases.yaml` — **inside the change dir.**
Founder flagged this as an antipattern: test cases (and requirements, specs,
solutions) **get lost in change dirs**. They feel like they belong in
**long-lived entities that build and evolve over time**, not ephemeral
per-change artifacts. Plus: a manual tester works a **backlog** of journeys
that span beyond any one change (pre/post journeys, regression), and we need to
**test the contracts**, not just behavioural flows.

## The distinction

- **The change is a *transaction*** — a delta with a start/end. Home: the
  change dir (lineage, diff, recon, WP execution). Ephemeral by design.
- **Requirements, specs, designs, contracts, test journeys are *living
  knowledge*** — exist independent of any change, accrete, evolve. Home: a
  long-lived store. Putting them in the change dir = source-of-truth on a
  Post-it thrown away when the ticket closes.

Verification cases sit on the **living** side — as do requirements, specs,
solutions.

## Substrate that already exists

The **brain graph** (`.brain/instances/product-development/`) is already the
long-lived store: `Requirement` (from SRDs), `Design`/`Component`/`Release`,
`Decision` (from ADRs), `TestRun`/`TestResult`, `Deployment`. Three gaps:

1. **No `Journey`/`TestCase` entity.** `TestRun`/`TestResult` are *execution
   records*, not durable *case/journey definitions*. The tester backlog has no
   home.
2. **The flow is deposit, not evolve.** A change *deposits* instances; it does
   not *read the current entity → propose a delta → merge it back* on ship.
   (Decisions even key id on `change_id` — per-change identity, not
   entity-over-time.)
3. **Verification is change-scoped, not product-scoped** (no regression slice).

## The reframe — change = transaction against the living graph (Path A generalised)

> change **reads** relevant living entities → **proposes deltas** → change dir
> holds the working copy + audit → on **ship**, deltas **merge into the graph**;
> the entity carries lineage through the chain of changes that touched it.

This re-opens **#42** (we decided `.architecture/` travels *with* the change
branch). That's right for the **working copy**; the **source of truth** should
be the graph, and ship should **reconcile** the working copy into it.

## The two specific answers

- **Contracts:** contracts (service/data/platform/visual) are themselves living
  entities. **Contract-conformance** (impl matches schema — CF-07, P-PLAT,
  visual sign-off) is one verification dimension; **behavioural journeys** are
  the other. The testable-state gate runs both. (TDD under-weighted the
  conformance half.)
- **Pre/post journeys + backlog:** the `Journey` entity — a persistent,
  evolving product-level suite. A change's verification = *new journeys it
  adds* ∪ *existing journeys in its blast radius that must stay green*
  (regression). A human works the backlog like a manual tester; the runner
  automates what it can, leaves the rest as recorded-status checklist items.

## Forks to decide

1. **The boundary** — living (requirements, specs/solutions, designs,
   contracts, journeys/test-cases) vs transactional (recon, WP execution,
   diff). Lean: *describes the product → graph; describes this unit of work →
   change dir.*
2. **The delta/merge mechanism** — how a change proposes an entity edit + how
   ship merges it, incl. two in-flight changes touching the same requirement.
   *Entity-level version control — the hard part.*
3. **Identity + evolution** — stable entity identity + lineage via the chain of
   changes (free, if we stop keying identity to a single change).
4. **Regression scope** — how a change finds the journeys in its blast radius
   (via the Component/contract entities it touches).

## Lean

Pause the narrow testable-state build; fold it into *"the living product graph
+ change-as-transaction."* Make `Journey`/`TestCase` the first new long-lived
entity type, with the testable-state gate as its first consumer. This also
feeds the ADE cockpit (it renders the living graph + the changes evolving it).

## Open question to the founder

Push first on the **boundary** or the **merge mechanism**? And is "the living
product graph" the right altitude, or over-built vs. just getting `Journey`
entities out of the change dir?
