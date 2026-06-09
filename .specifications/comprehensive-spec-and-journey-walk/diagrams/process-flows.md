# Process Flow Diagrams — Comprehensive Spec & Two-Surface Journey Walk

## Flow 1 — Decoupled depth → intake (Phase 1)

The corrected flow: depth sizes the interview; the comprehensive document is
always produced.

```mermaid
%% Depth sizes intake only; the comprehensive document is always produced
flowchart TD
    A([Founder runs /sulis:specify]) --> B[Classify intake depth]
    B --> C{Depth?}
    C -->|lite| D[Short interview]
    C -->|standard| E[Medium interview]
    C -->|deep| F[Full interview]
    D --> G[Produce comprehensive design document<br/>ALL mandatory sections]
    E --> G
    F --> G
    G --> H{Section populated<br/>from intake?}
    H -->|yes| I[Populate detail]
    H -->|no| J["Mark n/a — justification<br/>(never silent omission)"]
    I --> K([Complete document])
    J --> K
```

Contrast with the OLD (backwards) flow, which this change removes: `Depth → lite`
branched to "emit short SPEC, skip use cases / NFR / threat model / diagrams". No
emission branches on depth after this change (FR-03).

## Flow 2 — Two-surface journey walk (Phase 2)

```mermaid
%% The design stage walks BOTH surfaces before completing
flowchart TD
    A([Design stage step 8.5]) --> B{Change has<br/>a surface?}
    B -->|pure docs/infra| Z["Log exempt — recorded reason"]
    B -->|has surface| C[Walk UI surface hops]
    C --> D[Walk tool surface operations]
    D --> E{Every hop<br/>EXISTS or planned-WP?}
    E -->|bare GAP| F[BLOCK design completion]
    E -->|all classified| G[Write both Journey Walk tables]
    F --> H{Turn GAP into<br/>planned-WP or<br/>recorded out-of-scope}
    H --> E
    G --> Y([Design may proceed])
    Z --> Y
```

For a tool operation: EXISTS requires the handler AND its ServiceSpec binding; a
serving interface without a binding is a GAP (FR-09).

## Flow 3 — UC-flow-coverage gate (Phase 2)

```mermaid
%% Ship gate: every UC flow must have a covering scenario
flowchart TD
    A([Founder ships change]) --> B[Enumerate ALL flows<br/>main + alternate + exception]
    B --> C{Each flow has a<br/>covering scenario?}
    C -->|flow uncovered| D{Recorded<br/>out-of-scope?}
    D -->|no| E[Verdict: gaps — BLOCK]
    D -->|yes| F[Covered by decision]
    C -->|all covered| F
    F --> G[Run scenario-required gate #103]
    G --> H[Run journey-coverage gate #86]
    H --> I{All three pass?}
    I -->|no| E
    I -->|yes| J([Verdict: covered — may ship])
    E --> K[Report uncovered flow in plain English]
    K --> B
```
