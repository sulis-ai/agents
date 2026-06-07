# Board → thread navigation

This shows how the founder gets from the landing board into a single change's
thread, and what each view reads. Every arrow that fetches data goes through the
one API boundary (the seam) — never the filesystem directly. The board is **scoped to
one active Product** (FR-37); a **product switcher** (FR-38) changes which Product is
active and re-scopes the board.

```mermaid
%% Board → thread navigation: the founder's path from landing to a single change (per active Product).
flowchart TD
    A([Founder opens the app]) --> A1[Product switcher: active Product marked<br/>FR-38]
    A1 --> A2{Switch Product?}
    A2 -->|Yes| A3[Re-scope to chosen Product<br/>board + per-product views FR-37 / FR-38]
    A2 -->|No| B
    A3 --> B[Board: active Product's changes as cards in stage columns<br/>FR-37]
    B --> C{Any changes in flight?}
    C -->|No| D[Empty state: how to start a change]
    C -->|Yes| E[Cards show handle, intent, stage, liveness]
    E --> F{Founder narrows the view?}
    F -->|Search text| G[Board filtered by content]
    F -->|Stage filter| H[Board filtered to chosen stage]
    F -->|Needs attention| I[Board filtered to flagged changes]
    F -->|No| J[Founder clicks a card]
    G --> J
    H --> J
    I --> J
    J --> K[Thread view for that change]
    K --> L[Stage track + plain-English status]
    K --> M[Brain view: entities + workflows, grouped]
    K --> N[Files: rendered preview with raw toggle]
    K --> O[Chat: send a message, watch the reply stream]
    L --> P([Founder understands and can steer the change])
    M --> P
    N --> P
    O --> P
```
