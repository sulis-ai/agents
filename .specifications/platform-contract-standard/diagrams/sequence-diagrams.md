# Sequence Diagram — Harness Producing a Platform Contract

%% Shows the interaction between the architect, the harness steps, the official docs,
%% and the probe target while producing the GitHub Actions contract.

```mermaid
sequenceDiagram
    participant AR as Engineering-Architect
    participant HM as Harness (manifest)
    participant DOCS as Official GitHub Docs
    participant HB as Harness (bindings)
    participant HG as Harness (generate)
    participant HC as Harness (self-critique)
    participant PR as Probe (scratch GitHub repo)
    participant FILE as platform-contracts/github-actions.md

    AR->>HM: dispatch with generation-goal "GitHub Actions contract"
    activate HM
    HM->>DOCS: read official docs (retrieval-date stamped)
    DOCS-->>HM: {claim, source-URL, verbatim-quote} entries
    HM-->>AR: closed manifest (structural shape verified)
    deactivate HM

    AR->>HB: commit claim→source binding table
    activate HB
    alt Load-bearing claim has no doc source
        HB-->>AR: manifest-insufficient — REFUSE; record flagged assumption + probe-needed
    else All required claims bound
        HB-->>AR: binding-table (every binding → real manifest variable)
    end
    deactivate HB

    AR->>HG: generate — expand only committed bindings
    activate HG
    HG-->>AR: content + span-citations + flagged unattributed spans
    deactivate HG

    AR->>HC: self-critique — re-read each span against source MEANING
    activate HC
    alt False citation or meaning-drift detected
        HC-->>AR: route back to bindings (regenerate span)
    else Grounded
        HC-->>AR: final-verdict: grounded
    end
    deactivate HC

    AR->>PR: run probe — reusable workflow in .github/workflows/ vs subdir
    activate PR
    PR-->>AR: probe-result confirmed (resolves in .github/workflows/; fails in subdir)
    deactivate PR

    AR->>FILE: write contract (claims + citations + probe-results)
```

## Narrative

The `alt` at the binding step is the refusal gate — `manifest-insufficient` rather
than a fabricated binding. The `alt` at self-critique is the meaning-check catching
the MUC-002 drift. The probe interaction is the empirical leg: the reusable-workflow
rule is confirmed against a *real* scratch repo, not just a doc quote — which is
exactly the confirmation the triggering incident never had.
