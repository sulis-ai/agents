# Chat-driven discovery: discover → mint → start a change

This shows the chat front door (FR-27..FR-32). It does two jobs. **Cold-start
onboarding** (left branch): when the graph is empty, a behind-the-scenes discovery
agent — driven over the **same stream bridge as the two-way chat** — searches the
folder the founder chooses, asks plain-English questions, and (once the founder
confirms) mints the Tenant / Product / Project through the validated spine emitters.
**Start-a-change-from-intent** (right branch): once a Product/Project exists, the same
chat turns plain-English intent into a started change, cloning the repo first if it
isn't on the machine.

The load-bearing safety steps are: the agent **asks before it creates anything**
(FR-N6), it **searches only the chosen area** (FR-N7), it **doesn't mint duplicates**
(FR-31), and entity writes **go through the schema-validated emitters** (FR-32). The
onboarding branch now also **finds-or-creates the Product's repo** (FR-35) and **persists
a durable Product/Project config** (FR-36), so next time the founder needs no re-setup.

```mermaid
%% Chat-driven discovery + setup: cold-start onboarding (find-or-create repo, mint + persist graph) and start-a-change-from-intent.
flowchart TD
    A([Founder opens the chat front door]) --> B{Is there a Product / Project yet?}

    %% ---- Cold-start onboarding (UC-07) ----
    B -->|No — empty graph| B1[Agent asks which Product the founder is on]
    B1 --> B2{Where is the repo?}
    B2 -->|No repo yet| B3{Founder confirms create? FR-N6 / FR-N10}
    B3 -->|No| G
    B3 -->|Yes| B4[Create a new repo for the founder<br/>FR-35]
    B4 --> B5{Create OK?}
    B5 -->|No| G2[Clear failure; no dangling config<br/>FR-N10 / FR-N11]
    B5 -->|Yes| H
    B2 -->|Repos exist| C[Founder picks an area of their machine]
    C --> D[Agent searches ONLY that chosen area<br/>FR-N7 / NFR-DISC-01]
    D --> E[Orchestrate discover-project,<br/>discover-context, codebase-mapping<br/>FR-28]
    E --> F{Anything recognisable found?}
    F -->|No| G[Say so plainly;<br/>ask for another area — mint nothing]
    F -->|Yes| H{Already minted?}
    H -->|Yes| I[Surface existing entity;<br/>no duplicate FR-31]
    H -->|No| J[Propose Tenant / Product / Project<br/>in plain English]
    J --> K{Founder confirms? FR-N6}
    K -->|No| G
    K -->|Yes| L[Mint via validated spine emitters<br/>FR-32 / NFR-DISC-03]
    L --> L2[Complete + PERSIST Product/Project config<br/>Project.source = repo/path/branch<br/>FR-36 / NFR-DISC-06]
    L2 --> M[Board now has a Product + Project — durable]
    I --> M

    %% ---- Start a change from intent (UC-08) ----
    B -->|Yes| N[Founder says intent in plain English]
    M --> N
    N --> O[Classifier resolves primitive + slug<br/>FR-29]
    O --> P[Map Project.source repo/path/branch<br/>to --repo-root FR-29]
    P --> Q{Repo present on machine?}
    Q -->|No| R[Clone from Project.source.repo FR-30]
    R --> S{Clone OK?}
    S -->|No| T[Clear failure; no change started FR-30]
    Q -->|Yes| U{Founder confirms? FR-N6}
    S -->|Yes| U
    U -->|No| V[Nothing started]
    U -->|Yes| W[Run sulis-change start --repo-root ...<br/>FR-29]
    W --> X([New change appears at Recon on the board])

    G --> Y([End])
    G2 --> Y
    T --> Y
    V --> Y
```
