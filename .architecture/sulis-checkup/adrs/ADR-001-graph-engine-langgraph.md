---
id: ADR-001
title: Use LangGraph as the checkup graph engine
status: accepted
date: 2026-05-23
deciders: [iain, sea-architect-agent]
---

## Context

The checkup needs a graph engine. Three viable options:

1. **Adopt LangGraph directly.** Used by the platform's workflows service
   underneath the `GenericGraphCompiler` abstraction.
2. **Port the platform's workflows-service patterns** to the marketplace
   (the `GraphDefinition` / `NodeDef` / `EdgeDef` DSL on top of LangGraph,
   plus the lint rules, plus the hexagonal port discipline).
3. **Build a minimal custom graph engine.** Just enough to walk tiers
   sequentially with hard-stop short-circuit.

Constraints:

- Marketplace lives at `/Users/iain/Documents/repos/agents/`. Must not
  take a platform dependency.
- Single founder, single process, local run. Not multi-tenant.
- Checkup graph is small: 15-25 nodes, 30-40 edges.
- Needs resumability (process crash mid-run; founder Ctrl-C; long-running
  adversarial-review interrupts).
- Needs interrupt/resume for human-in-the-loop adversarial review.
- Needs dynamic parallel dispatch for per-finding healing
  (4 findings → 4 parallel healing nodes).
- Needs typed shared state with reducers for list-accumulating fields
  (findings, healing actions).

## Decision

**Adopt LangGraph directly.** Define the checkup graph in Python, using
`StateGraph` for the outer tier sequencing, sub-`StateGraph` per tier for
the OODA cycle, `add_conditional_edges` for tier gating, `Send()` for
per-finding parallel healing dispatch, `SqliteSaver` checkpointer with
`thread_id = invocation_id` for resumability, and `interrupt()` for the
adversarial-review human-in-the-loop nodes.

## Options Considered

### Option 1 — Adopt LangGraph directly (chosen)

**Pros:**
- Battle-tested in the platform; the platform's `GenericGraphCompiler` is
  literally an abstraction on top of LangGraph. We sit one layer closer
  to the metal but the metal is the same.
- All primitives needed map natively: conditional_edges (gating), Send()
  (parallel healing), checkpointer (resumability), interrupt() (HIL),
  reducers (list accumulation).
- One Python dependency (`pip install langgraph`).
- Documentation is current as of 2026-05; community examples abundant.
- Skill-author learning curve is small — Python with `StateGraph(state_class)`
  and `add_node` / `add_edge` is roughly as complex as the platform DSL,
  and contributors who know the platform also know LangGraph because of
  the lower-layer composition.

**Cons:**
- Marketplace gains a dependency on a third-party graph library.
- LangGraph's typing story is decent but not perfect (state TypedDict is
  the conventional shape; Annotated[list, operator.add] for reducers is
  idiomatic but not statically validated).

### Option 2 — Port platform workflows patterns

**Pros:**
- Shared mental model with the platform team; contributors who know one
  know the other.
- Hexagonal architecture with port/adapter discipline already validated
  at scale.
- The `GraphDefinition` DSL would let checkup graphs be defined in YAML
  (consistent with manifest engine, Kind YAML, etc.).

**Cons:**
- Massive overhead for a 15-25 node graph. `GenericGraphCompiler` has
  size limits (MAX_NODES=200) because it's designed for graphs an order
  of magnitude larger than checkup.
- L01-L10 lint rules enforce architectural separation across hundreds of
  files; the checkup is a few hundred lines total.
- The DSL is justified at the platform because graphs compose from typed
  Kind YAML; checkup composes one stable graph from Python code.
- Porting drags in the composition root, AdapterIdentity freeze, observability
  port, signing primitives, etc. — all valuable at the platform, all
  overhead at the marketplace.
- "Implementing the abstraction over LangGraph" duplicates the platform's
  work without the platform's volume.

**Rejected because:** the abstraction earns its keep at platform scale.
At marketplace scale, it imports cost without commensurate benefit.

### Option 3 — Build a minimal custom engine

**Pros:**
- Zero dependencies.
- Maximum control.
- Easiest to fully understand for a new contributor.

**Cons:**
- The moment you need checkpointing for resumability, you're re-implementing
  LangGraph's SqliteSaver.
- The moment you need interrupt/resume for adversarial review, you're
  re-implementing LangGraph's interrupt() primitive.
- The moment you need parallel Send-style dispatch, you're re-implementing
  LangGraph's runtime scheduler.
- Sequential composition is one afternoon. Adding the four features above
  is a person-week each, plus ongoing maintenance.
- Building a worse LangGraph is not a competitive advantage.

**Rejected because:** the deciding factor is not "can we build sequential
node walking" (yes, trivially); it's whether we'll need the other features
(yes, for the adversarial-review healing prototype and the per-finding
parallel dispatch). Once you need those, LangGraph beats hand-rolled by
an order of magnitude on time-to-correct.

## Consequences

**Positive:**
- Founders' adversarial-review interrupts work out of the box (LangGraph's
  `interrupt()` is the canonical HIL pattern).
- Resumability comes free with SqliteSaver — `.checkup/{project}/state.db`
  persists checkpoint state across process restarts.
- Per-finding parallel healing dispatch is `Send()` — declarative, tested,
  documented.
- New contributors get one well-documented framework instead of a bespoke
  engine.

**Negative:**
- One more dependency for the marketplace. LangGraph itself depends on
  langchain-core (minor) and langgraph-checkpoint-sqlite (small). Total
  install ~10MB, negligible.
- LangGraph version drift becomes a maintenance concern. Pinning to a
  minor version (`langgraph >= 0.X, < 0.Y`) is standard practice; checkup
  should follow.
- Skill-author docs need a "if you're new to LangGraph, read this first"
  pointer in the new skill READMEs.

**Neutral:**
- The platform team and the marketplace team end up using the same engine
  at different abstraction levels. If the platform ever needs to push its
  DSL into marketplace tooling, it can — but the marketplace doesn't pay
  that cost up front.

## Implementation hint (not part of the decision, retained for the SRD author)

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Send, interrupt
from typing import Annotated, TypedDict
import operator

class CheckupState(TypedDict):
    # see TDD §7 for full schema
    findings: Annotated[list, operator.add]
    ...

def build_checkup_graph() -> Any:
    g = StateGraph(CheckupState)
    g.add_node("tier_1", tier_1_node)
    g.add_node("tier_2", tier_2_node)
    # ... etc
    g.add_conditional_edges("tier_1", route_after_tier, {
        "continue": "tier_2",
        "hard_stop": "render",
    })
    # ... etc
    g.add_edge("render", END)
    g.set_entry_point("tier_1")
    return g.compile(checkpointer=SqliteSaver.from_conn_string(...))
```
