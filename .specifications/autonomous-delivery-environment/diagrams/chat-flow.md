# Two-way chat: send and stream

This shows what happens when the founder sends a message to a change's agent from
the app. It **just works**: if no session is live, the server resumes the change's
last session from its saved transcript, or spawns a fresh one grounded in the
change's saved context — the founder never chooses. The load-bearing safety steps
are the **session-to-change match** (the server refuses if it can't prove the
resolved session belongs to the named change), the **one-in-flight guard** (a second
message is refused until the first finishes), and **acting on only the targeted
change's session** when resuming/spawning.

```mermaid
%% Two-way chat send/stream flow: resume-or-spawn session resolution + safety + failure paths.
sequenceDiagram
    participant F as Founder (app UI)
    participant S as App server (the seam)
    participant C as Claude session (agent)

    F->>S: send message for change A
    activate S
    alt a reply is already streaming for change A
        S-->>F: refuse — SESSION_BUSY (FR-20)
    else
        Note over S: resolve a session for change A (founder never chooses)
        alt change A has a live session
            Note over S: use the live session
        else change A has a prior (closed) session
            S->>C: resume from saved transcript (FR-24)
            activate C
            Note over C: agent wakes with full memory; re-runs any step left incomplete at close (FR-26/FR-N5)
        else change A never had a session
            S->>C: spawn fresh, grounded in change A's saved context (FR-25)
            activate C
            Note over C: agent re-reads the change before acting
        end
        alt session could not be resumed/spawned
            S-->>F: fail — could not start a session (FR-19)
        else resolved session does not belong to change A
            S-->>F: refuse — SESSION_CHANGE_MISMATCH (FR-21, NFR-SEC-06)
        else delivered
            S->>C: relay prompt to change A's session
            loop reply streams back
                C-->>S: reply chunk
                S-->>F: stream chunk (FR-17)
            end
            alt stream completes
                C-->>S: end of reply
                deactivate C
                S-->>F: complete — exchange joins the conversation (FR-18)
            else stream breaks mid-reply
                S-->>F: interrupted — keep partial text (FR-22)
            end
        end
    end
    deactivate S
```
