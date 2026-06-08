---
founder_facing: false
---
# Spec — Brain as a living backlog + traversable memory

**Change:** CH-01KT60 · create

## Intent

Make the brain a living backlog the founder can deposit ideas into and ask
questions of, on one principle: **no orphan requirements** — every idea
roots in an opportunity (the *why*) before it becomes a requirement (the
*what*). Three pieces: a lightweight **capture** path that lands a
scoped-out idea durably (rooted in a why, optionally tagged Roadmap), a
**traverse** path that answers "what's open / on the roadmap / the state of
the work" off the brain graph, and an **opportunity-analyst agent** that
pressure-tests and validates the why so the principle has teeth (mirrors the
requirements-analyst). The brief mandated a thin slice; the founder
consciously expanded it to include the full agent.

## Acceptance (summary)

- Capture lands a whole ref chain (tenant → product → opportunity →
  requirement) with no dangling refs; rejects a what with no why.
- The two pieces of this change + the opportunity-analyst idea land as
  Roadmap items (the dogfood).
- `/sulis:backlog` and the Sulis agent both answer "what's open / roadmap"
  off brain entities, distinct from the change-store.
- Two verification journeys (capture, traverse) run green from-graph.

## Full requirements

See `.specifications/brain-backlog-and-traversal/SRD.md` (FR-01..FR-10,
NFR-01..04, non-goals, Verification Plan). Authored by Sulis this session;
drafting ownership transferred by the founder for this change (normally the
requirements-analyst's artifact).

## What to avoid / out of scope

- Rewiring all sessions to be opportunity-rooted (principle embodied in
  capture + the agent here; enforcing everywhere is follow-on).
- Cross-repo / Platform-tier central store; idea history / time-travel (#67).
- No third-party platform write → no Platform Contract gate.
