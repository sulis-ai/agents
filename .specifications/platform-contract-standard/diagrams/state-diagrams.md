# State Diagram — Lifecycle of a Platform Contract Claim

%% A single claim moves through these states. Any transition not shown is not allowed.

```mermaid
stateDiagram-v2
    [*] --> Proposed: Architect enumerates a claim the contract needs

    Proposed --> Grounded: Bound to an official source whose meaning supports it
    Proposed --> Assumed: No official source (manifest-insufficient → flagged inference)

    Grounded --> MeaningDrift: self-critique finds the source doesn't mean this
    MeaningDrift --> Grounded: Reworded to match source meaning
    MeaningDrift --> Assumed: Source genuinely doesn't support it

    Assumed --> Probed: Real sandbox exercise run
    Grounded --> Probed: Load-bearing → probe run

    Probed --> Confirmed: probe-result confirmed (doc says X AND platform does X)
    Probed --> Refuted: probe-result refuted → escalate (doc wrong or reading wrong)
    Refuted --> Proposed: Re-investigate the claim

    Confirmed --> Stale: retrieval-date exceeds freshness threshold
    Grounded --> Stale: retrieval-date exceeds freshness threshold
    Stale --> Grounded: Re-grounded against current docs
    Stale --> Probed: Re-probed against current platform

    Confirmed --> [*]: Ships in the contract (load-bearing, fully grounded)
    Grounded --> [*]: Ships (non-load-bearing, cited)
```

## Narrative

- **Proposed → Assumed** is the refusal path — the gate against fabrication. An
  assumed claim is never asserted as documented fact; it carries `inferred: true`.
- **Grounded → MeaningDrift → Assumed** is MUC-002 being caught: a real citation
  whose meaning doesn't support the claim is demoted, not trusted.
- **Probed → Refuted** is the most valuable transition — the empirical check
  contradicting the documentation, the exact signal the reusable-workflow incident
  needed and never got.
- **Stale** is the freshness boundary (FR-013). A claim re-enters grounding/probing
  rather than being silently reused. The automated re-probe that *detects* staleness
  is deferred (Out of Scope); the manual flag from the retrieval date ships now.
