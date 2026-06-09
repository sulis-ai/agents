# Sequence Diagrams — Comprehensive Spec & Two-Surface Journey Walk

## SD-01 — Specify at lite depth still yields the comprehensive document

```mermaid
%% Depth proposes interview size; the full document is always produced
sequenceDiagram
    participant F as Founder
    participant A as Sulis Agent
    participant CL as Depth Classifier
    participant DOC as Comprehensive Document

    F->>A: /sulis:specify
    activate A
    A->>CL: classify_depth(primitive, file_count, founder_facing)
    activate CL
    CL-->>A: depth = lite (deterministic)
    deactivate CL
    A->>F: "a few quick questions" (interview size, NOT doc thinness)
    F-->>A: short answers
    A->>DOC: emit ALL mandatory sections (FR-11)
    activate DOC
    DOC-->>A: document with use cases, NFR, threat model, personas, scope
    deactivate DOC
    A-->>F: complete document
    deactivate A

    Note over A,DOC: No emission branch is gated on depth (FR-03)
```

## SD-02 — Two-surface journey walk

```mermaid
%% The agent walks the UI surface AND the tool surface before completing
sequenceDiagram
    participant A as Sulis Agent
    participant B as Brain (scenarios)
    participant CODE as Codebase
    participant SS as ServiceSpec bindings
    participant TDD as Journey Walk section

    A->>B: find_scenarios_for_journey(journey)
    activate B
    B-->>A: complete scenario set
    deactivate B

    loop each UI hop
        A->>CODE: cite component (file + function)?
        alt component exists
            CODE-->>A: EXISTS
        else not built / not planned
            CODE-->>A: GAP
        end
    end

    loop each tool operation
        A->>CODE: handler cited?
        A->>SS: ServiceSpec binding cited?
        alt handler AND binding
            SS-->>A: EXISTS
        else handler only (serving, unwired)
            SS-->>A: GAP (FR-09)
        end
    end

    A->>TDD: write UI table + tool table
    Note over A,TDD: bare GAP blocks design completion
```

## SD-03 — Driving a tool scenario for real (#98 substrate)

```mermaid
%% Tool scenarios are driven end-to-end; green requires a real round-trip
sequenceDiagram
    participant A as Sulis Agent
    participant VS as Verification Substrate (#98)
    participant TOOL as Real Tool Endpoint
    participant B as Brain (TestResult)

    A->>VS: drive scenario (http_call / subprocess / agent-step)
    activate VS
    VS->>TOOL: real round-trip (method, path)
    activate TOOL
    TOOL-->>VS: response
    deactivate TOOL
    alt observed pass condition met
        VS->>B: deposit passing TestResult
        VS-->>A: green (observed)
    else cannot drive (no sandbox/creds)
        VS-->>A: blocked → record deferred infra need
    end
    deactivate VS

    Note over A,B: green requires a deposited TestResult, not inspection (NFR-S03)
```
