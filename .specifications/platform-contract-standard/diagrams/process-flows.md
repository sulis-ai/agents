# Process Flow — The Design-Stage Gate + Harness Run

%% Shows the gate decision and the harness loop that produces a Platform Contract.

```mermaid
flowchart TD
    A([Change reaches design phase]) --> B{Touches a third-party platform?}
    B -->|No| Z([Proceed — no contract needed])
    B -->|Yes| C{Write/deploy touch, or read-only?}
    C -->|Read-only| Y[Recommend lightweight contract · SHOULD]
    Y --> Z
    C -->|Write/deploy| D{Contract exists for this platform?}
    D -->|Yes| E{Any claim past staleness threshold?}
    E -->|No| Z2([Reuse contract — proceed])
    E -->|Yes| F[Flag stale claims for re-grounding]
    F --> G
    D -->|No| G[Run faithful-generation-harness]

    subgraph Harness["faithful-generation-harness"]
        G --> H[observe-manifest: official docs as closed manifest]
        H --> I[orient: select relevant doc variables]
        I --> J[decide: commit claim→source binding table]
        J --> K{Load-bearing claim ungrounded?}
        K -->|Yes| L[manifest-insufficient: REFUSE → record flagged assumption needing a probe]
        K -->|No| M[act: generate contract, expand only bound claims, flag inferences]
        L --> M
        M --> N[self-critique: re-read each claim against source MEANING]
        N --> O{Grounded + no false citation?}
        O -->|No| J
        O -->|Yes| P[Probe load-bearing claims · record probe-result]
    end

    P --> Q[Write contract → platform-contracts/<platform>.md]
    Q --> R[Feed constraints into Verification Plan]
    R --> Z3([Proceed — design grounded in contract])
```

## Narrative

The diamond at `K` is the gate that prevents the triggering incident: an ungrounded
load-bearing claim does not silently become content — it forces a refusal and a
flagged assumption. The loop `O → J` is the meaning-check rejecting drifted or
falsely-cited spans before the contract passes.
