# Use Case Diagram — Comprehensive Spec & Two-Surface Journey Walk

The actors are the **Founder** (human, non-technical) and the **Sulis agent**
(automated). The system is the specify/design methodology pipeline.

```mermaid
%% Founder and Sulis agent interacting with the specify/design methodology
graph LR
    Founder([Founder])
    Agent([Sulis Agent])

    subgraph System["Specify / Design Methodology"]
        UC1[UC-01 Specify a small change → full doc]
        UC2[UC-02 Produce comprehensive doc regardless of depth]
        UC3[UC-03 Walk UI surface journey]
        UC4[UC-04 Walk tool surface journey]
        UC5[UC-05 Derive scenarios from UC flows, both surfaces]
        UC6[UC-06 Ship → UC-flow-coverage gate blocks gaps]
    end

    Founder --> UC1
    Founder --> UC6
    Agent --> UC2
    Agent --> UC3
    Agent --> UC4
    Agent --> UC5
    Agent --> UC6
```

## Narrative

- **UC-01 (Founder)** — A founder specifies a small user-facing change and gets a
  comprehensive design document anyway. Depth sizes the questions, not the doc.
- **UC-02 (Agent)** — The agent always emits the full mandatory section set; no
  emission branch is gated on depth.
- **UC-03 (Agent)** — The agent walks the human consumer's path hop-by-hop
  (existing #85 behaviour, retained).
- **UC-04 (Agent)** — The agent ALSO walks the machine consumer's path — an
  agent/SDK calling the tools end-to-end — with the ServiceSpec-binding bar for
  EXISTS.
- **UC-05 (Agent)** — Every use-case flow (main/alternate/exception) becomes a
  drivable scenario, on the UI surface, the tool surface, or both.
- **UC-06 (Founder + Agent)** — The founder ships; the UC-flow-coverage gate
  blocks if any flow has no covering scenario, alongside the scenario-required and
  journey-coverage gates.
