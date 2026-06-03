# ADR-004 — Capture invokes the opportunity-analyst as a recommended agent, then reads the emitted Opportunity by id

> Change: CH-01KT60 · Status: accepted · Pillar: Form
> Relates: FR-11 (opportunity-analyst agent), FR-02 (full why-rooting), FR-10 (dogfood)

## Decision

The `full` why-rooting path (ADR-003) and the opportunity-analyst agent
compose through the **brain store as the hand-off medium**, not through a
direct function call or an in-process agent spawn:

1. Capture, on `full` intensity, recommends the founder run the
   opportunity-analyst (the same agent-recommendation pattern the Sulis
   agent uses for `requirements-analyst` — "recommend `claude --agent
   opportunity-analyst`").
2. The analyst matures the why and **emits/updates the Opportunity entity**
   to the store (its own responsibility, FR-11), returning the
   `dna:opportunity:<ulid>` it wrote.
3. Capture resumes with that id: it reads the Opportunity back by id
   (`find_by_id`), confirms it resolves and that its `for_product` chain is
   whole, then emits the draft Requirement with `source = <that id>`.

The agent and capture share **no code path** — they share the entity.

## Why

This mirrors the established marketplace convention exactly. The Sulis agent
already routes facilitation work to `requirements-analyst` by recommending a
slash/agent invocation, not by calling it inline (the analyst runs a long
one-question-at-a-time conversation that can't be a synchronous function
return). The opportunity-analyst is the same shape — a full facilitation
agent (FR-11 says "mirroring the requirements-analyst"). Forcing it into an
in-process call would fight its nature.

The store-as-medium hand-off is also the **only** coupling that survives the
Track-2 substrate swap: when `StorageServiceAdapter` replaces
`LocalFileEntityAdapter`, both capture and the analyst keep talking through
the `EntityRepository` port (`_entity_repository.py`) — the hand-off doesn't
move. A direct call would hard-wire the two agents together at a layer the
architecture is explicitly designed to keep decoupled.

It also makes the analyst **stand alone** (FR-11's second requirement)
trivially true: maturing an existing Opportunity later is the same operation
with no capture involvement — the analyst reads an id, matures it, writes it
back.

## Alternatives considered

- **Capture spawns the analyst as a sub-agent and awaits a return value
  (rejected).** Facilitation is interactive and unbounded; there's no
  synchronous "matured opportunity" to await. It also couples capture to the
  analyst's internals. Rejected: wrong interaction model, tight coupling.

- **The analyst is a library the orchestrator imports (rejected).** A
  facilitation agent is a system prompt + conversation, not a pure function.
  There's nothing to import. Rejected: category error.

- **Capture emits a thin Opportunity, analyst edits it in place later
  (rejected for the full path; this IS the quick path).** This collapses
  full into quick — the founder gets a shallow hypothesis and the analyst
  pressure-test never gates the requirement. The whole point of `full` is
  that the matured opportunity exists *before* the what is captured.
  Rejected for `full`; it's exactly what `quick` does.

## Consequences

- The opportunity-analyst agent (`plugins/sulis/agents/opportunity-analyst.md`)
  owns Opportunity emission/update via the existing
  `sulis-emit-opportunity` write seam — but extended for **single-opportunity
  intake** (not `--from-srd`), the same generalisation capture needs
  (ADR-005). The two share the single-idea emission path.
- Capture's `full` branch is, mechanically: (a) ensure backing chain
  (ADR-002), (b) recommend/await the analyst out-of-band, (c) accept the
  returned opportunity id, (d) `find_by_id` to confirm it's real and
  chain-whole, (e) emit the Requirement. If (d) fails (analyst wrote nothing,
  or wrote a dangling opportunity), capture degrades with a plain-English
  error (NFR-01) and emits no orphan requirement.
- The Sulis agent body (FR-08 wiring, see TDD) gains a routing row: a founder
  saying "I want to think through the why properly" → recommend the
  opportunity-analyst, same shape as the existing requirements-analyst row.
- **Dogfood (FR-10):** the change's own opportunity (the why behind "brain as
  a living backlog") is matured by running the analyst against it, then the
  two pieces (capture path, backlog command) are captured as Requirements
  sourced from it and Roadmap-labelled. The analyst is exercised, not just
  shipped.
