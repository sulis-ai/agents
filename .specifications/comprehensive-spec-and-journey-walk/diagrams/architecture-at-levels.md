# Architecture-at-Levels (C4) — Comprehensive Spec & Two-Surface Journey Walk

This file demonstrates FR-16: the comprehensive design document must carry
architecture at three C4 levels — **context**, **container**, **component** —
beyond the 5 flat Mermaid types Sulis has today. The subject modelled is the
specify/design methodology pipeline itself.

## Level 1 — Context (the methodology in its environment)

```mermaid
%% C4 Level 1: the methodology pipeline and its external actors/systems
graph TB
    Founder([Founder<br/>non-technical])
    Architect([Engineering Architect<br/>downstream])

    subgraph Sulis["Sulis specify/design methodology"]
        Pipeline[Comprehensive-spec + two-surface-walk pipeline]
    end

    Canonical[(Canonical DESIGN.md target<br/>platform repo)]
    Brain[(Brain instance store)]
    Substrate[Verification substrate #98]

    Founder -->|"specifies a change (plain English)"| Pipeline
    Pipeline -->|"comprehensive document + gate verdict"| Founder
    Pipeline -->|"hands off the document"| Architect
    Pipeline -.->|"references target structure"| Canonical
    Pipeline -->|"emits scenarios / reads coverage"| Brain
    Pipeline -->|"drives tool scenarios"| Substrate
```

## Level 2 — Container (deployable / runnable units)

```mermaid
%% C4 Level 2: the runnable units inside the pipeline
graph TB
    subgraph Pipeline["Specify/Design Pipeline"]
        Specify[/sulis:specify skill/]
        Classifier[Depth classifier<br/>_specify_classifier.py]
        Analyst[requirements-analyst agent]
        Design[/sulis:draft-architecture skill/]
        ScenTool[sulis-author-scenario]
        CovGate[_verify_scenario_coverage.py]
        Templates[requirements-templates]
    end

    Substrate[sulis-verify-acceptance #98]
    Brain[(Brain)]

    Specify --> Classifier
    Specify --> Analyst
    Analyst --> Templates
    Analyst --> ScenTool
    Design --> Analyst
    Design --> CovGate
    ScenTool --> Brain
    CovGate --> Brain
    Design --> Substrate
    Substrate --> Brain
```

## Level 3 — Component (internals of the design skill / coverage gate)

```mermaid
%% C4 Level 3: components inside the design stage that implement this change
graph TB
    subgraph Design["draft-architecture (design stage)"]
        DocGen[Comprehensive doc generator<br/>always all sections]
        UIWalk[UI surface walker #85]
        ToolWalk[Tool surface walker NEW]
        StrideGen[STRIDE threat-model section NEW always-on]
        C4Gen[Architecture-at-levels generator NEW]
        ADRBDR[ADR + BDR recorder NEW BDR]
        WalkTable[Journey Walk writer<br/>UI table + tool table]
    end

    subgraph Gate["UC-flow-coverage gate"]
        FlowEnum[Flow enumerator<br/>main+alternate+exception]
        CovCheck[Coverage check<br/>flow → covering scenario]
        Verdict[covered / gaps verdict]
    end

    Binding[ServiceSpec binding citer]

    DocGen --> StrideGen
    DocGen --> C4Gen
    DocGen --> ADRBDR
    UIWalk --> WalkTable
    ToolWalk --> Binding
    ToolWalk --> WalkTable
    FlowEnum --> CovCheck
    CovCheck --> Verdict
```

## Notes

- The **NEW** components (tool surface walker, always-on STRIDE generator,
  architecture-at-levels generator, BDR recorder, flow enumerator) are what this
  change introduces; the rest are extended existing units.
- This three-level set is itself the proof that architecture-at-levels is
  producible — the produced comprehensive document carries the same shape for
  the system *it* designs.
