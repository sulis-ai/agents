# Use Case Diagram — Platform Contract Standard

%% Shows who interacts with the Platform Contract discipline and the six use cases.

```mermaid
graph LR
    Founder([Founder])
    Architect([Engineering-Architect agent])
    Harness([faithful-generation-harness])
    Rubric([decompose-validation-rubric · P-PLAT])

    subgraph System["Platform Contract Standard"]
        UC1[UC-001 Gate: require contract before integration design proceeds]
        UC2[UC-002 Reuse durable contract on a later change]
        UC3[UC-003 Refuse ungrounded claim → record flagged assumption]
        UC4[UC-004 Probe a load-bearing claim → record result]
        UC5[UC-005 Produce the GitHub Actions contract n=1 dogfood]
        UC6[UC-006 Feed contract constraints into the Verification Plan]
    end

    Founder --> UC1
    Founder --> UC2
    Architect --> UC1
    Architect --> UC2
    Architect --> UC3
    Architect --> UC4
    Architect --> UC5
    Architect --> UC6
    Harness --> UC3
    Harness --> UC5
    Rubric --> UC1
```

## Narrative

- **UC-001 (the gate)** — the load-bearing use case. An integration design cannot
  proceed without a contract. Enforced by both the architect (prose) and the rubric
  (mechanical). The direct fix for the triggering incident.
- **UC-002 (reuse)** — contracts are durable assets that accrue across changes, not
  per-change throwaways.
- **UC-003 (refusal)** — the harness refuses to fabricate; the gate that would have
  caught "reusable workflow in a plugin subdir".
- **UC-004 (probe)** — load-bearing claims get empirical confirmation, not just a
  citation.
- **UC-005 (n=1 dogfood)** — produces the GitHub Actions contract this change ships.
- **UC-006 (verification feed)** — each constraint becomes a test assertion or a
  named post-ship observable (#138).
