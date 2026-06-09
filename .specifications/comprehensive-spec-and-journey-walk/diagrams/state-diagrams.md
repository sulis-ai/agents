# State Diagrams — Comprehensive Spec & Two-Surface Journey Walk

## ST-01 — Hop classification lifecycle (a single hop in a journey walk)

```mermaid
%% A hop moves between classifications as the design evolves
stateDiagram-v2
    [*] --> Unclassified: hop identified in journey
    Unclassified --> EXISTS: component cited (file+function); tool hop also needs ServiceSpec binding
    Unclassified --> PlannedWP: no component, but a WP is planned
    Unclassified --> GAP: neither built nor planned
    GAP --> PlannedWP: turn into a planned WP
    GAP --> OutOfScope: recorded out-of-scope decision
    PlannedWP --> EXISTS: WP built and cited
    EXISTS --> [*]: design completes
    PlannedWP --> [*]: design completes (planned)
    OutOfScope --> [*]: design completes (recorded)

    note right of GAP
        A bare GAP BLOCKS design completion.
        It must become PlannedWP or OutOfScope.
    end note
```

## ST-02 — Use-case flow coverage lifecycle (a single flow)

```mermaid
%% Each flow must reach a covered state before ship
stateDiagram-v2
    [*] --> Specified: flow written (main/alternate/exception)
    Specified --> ScenarioAuthored: scenario derived for the flow
    Specified --> RecordedOutOfScope: conscious out-of-scope (recorded)
    ScenarioAuthored --> Covered: scenario observed-green OR planned
    ScenarioAuthored --> Uncovered: no covering scenario yet
    Uncovered --> ScenarioAuthored: author the scenario
    RecordedOutOfScope --> Covered: covered-by-decision
    Covered --> [*]: gate passes
    Uncovered --> Blocked: ship gate runs
    Blocked --> ScenarioAuthored: address the gap

    note right of Blocked
        Verdict = gaps.
        UC-flow-coverage gate blocks the ship.
    end note
```

## ST-03 — Tool scenario drive status

```mermaid
%% A tool scenario is green only after a real round-trip
stateDiagram-v2
    [*] --> Authored: scenario emitted to brain
    Authored --> NotYetRun: no TestResult on record
    NotYetRun --> Green: real driven round-trip, passing TestResult deposited
    NotYetRun --> Blocked: driven but failed / undrivable
    Blocked --> Deferred: no sandbox/creds → recorded infra need
    Green --> [*]
    Deferred --> [*]: recorded, never silently dropped

    note right of Green
        Green requires a deposited TestResult (NFR-S03),
        never inspection alone.
    end note
```
