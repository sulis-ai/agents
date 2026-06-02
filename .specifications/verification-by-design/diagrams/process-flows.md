# Process Flow Diagrams — verification-by-design

**Change:** CH-01KT2B
**Date:** 2026-06-01

---

## PF-001 — Design phase asks the verification questions

Shows where in the existing design pipeline the new verification questions are
asked and where the Verification Plan section gets populated.

```mermaid
%% Verification questions enter at three points in the existing pipeline:
%% Phase 3 of /sulis:specify (foundational + per-integration), then
%% /sulis:draft-architecture (real-vs-mock concretions), then
%% /sulis:plan-work (per-WP adapter binding).
flowchart TD
    A([Founder runs /sulis:specify]) --> B[Phase 1 orientation +<br/>Phase 2 exploration<br/>unchanged]
    B --> C[Phase 3 convergent spec]
    C --> D{Verification questions<br/>asked from canonical<br/>VERIFICATION_QUESTIONS.md?}
    D -->|Yes| E[Record answers in<br/>SRD Verification Plan section]
    D -->|No| F[Rubric P-VER fails<br/>cannot exit Phase 3]
    F --> C
    E --> G[Rubric P-VER validates<br/>section populated<br/>not placeholders]
    G --> H{Pass?}
    H -->|Yes| I[Phase 4 artifact gen<br/>continues]
    H -->|No| F
    I --> J([SRD.md complete with<br/>Verification Plan])
    J --> K([Founder runs<br/>/sulis:draft-architecture])
    K --> L[SEA reads SRD<br/>Verification Plan]
    L --> M[Asks real-vs-mock<br/>concretion questions]
    M --> N[Populates TDD<br/>Verification Plan with<br/>implementation-side answers]
    N --> O[Rubric P-VER<br/>validates TDD plan]
    O --> P([TDD.md complete])
    P --> Q([Founder runs<br/>/sulis:plan-work])
    Q --> R[For each WP:<br/>verification: field<br/>required]
    R --> S{Adapter<br/>matches kind?}
    S -->|Yes| T[WP frontmatter populated]
    S -->|No| U[Rubric P-VER fails<br/>cannot emit WP]
    T --> V([WPs ready])
```

---

## PF-002 — Infrastructure-need flag and follow-on auto-draft

Shows the flow from "Verification Plan flags a deferred infrastructure need" to
"follow-on change auto-drafted at slice-end review."

```mermaid
%% When a Verification Plan section's "Infrastructure needs surfaced (deferred)"
%% subsection records a need, the slice-end review pattern scans across the
%% slice and auto-drafts a follow-on when the same need appears 2+ times.
flowchart TD
    A([Design phase produces<br/>Verification Plan]) --> B[Per-integration<br/>strategy filled]
    B --> C{Infrastructure<br/>available?}
    C -->|Yes| D[Strategy: real/mock/sandbox<br/>against existing infra]
    C -->|No| E[Record under<br/>Infrastructure needs<br/>surfaced deferred]
    E --> F[Canonical need identifier<br/>recorded for scan]
    D --> G([Plan complete])
    F --> G
    G --> H[Slice ships]
    H --> I[Slice-end review<br/>runs]
    I --> J[Scan all Verification Plans<br/>in slice for deferred needs]
    J --> K{Same need flagged<br/>by 2+ changes?}
    K -->|Yes| L[Auto-draft follow-on change<br/>targeting that infra need]
    K -->|No, singleton| M[Surface to founder:<br/>defer further<br/>or draft now?]
    L --> N([Follow-on change<br/>enters pipeline])
    M --> O{Founder<br/>decision}
    O -->|Defer| P[Need stays open<br/>for next slice-end]
    O -->|Draft| L
    P --> I
```

---

## PF-003 — Rubric P-VER decision tree

The decision tree the verification rubric check evaluates against each design
artifact.

```mermaid
%% The rubric P-VER fires on every SRD, TDD, and WP-set produced after this
%% change merges. Grandfathered changes are recognised by shipped-on date.
flowchart TD
    A([Rubric P-VER runs<br/>on a design artifact]) --> B{Change shipped<br/>before this<br/>refinement merged?}
    B -->|Yes| C([PASS — grandfathered])
    B -->|No| D{Verification Plan<br/>section present?}
    D -->|No| E([FAIL — section missing])
    D -->|Yes| F{Section body<br/>contains placeholder<br/>TBD or ? or empty?}
    F -->|Yes| G([FAIL — placeholder content])
    F -->|No| H{n/a claimed?}
    H -->|Yes| I{Justification line<br/>present?}
    I -->|No| J([FAIL — n/a without<br/>justification])
    I -->|Yes| K{Trivial-change<br/>carveout valid?}
    K -->|Yes| L([PASS — trivial carveout])
    K -->|No| M([FAIL — invalid carveout])
    H -->|No| N{Named infra<br/>classified as existing?}
    N -->|Yes| O{Path resolves<br/>in repo?}
    O -->|No| P([FAIL — hallucinated<br/>infrastructure])
    O -->|Yes| Q{kind: value has<br/>adapter mapping?}
    N -->|No| Q
    Q -->|No| R([FAIL — unmapped kind])
    Q -->|Yes| S{Citation to<br/>VERIFICATION_QUESTIONS.md<br/>present?}
    S -->|No| T([FAIL — no canonical<br/>citation])
    S -->|Yes| U([PASS])
```
