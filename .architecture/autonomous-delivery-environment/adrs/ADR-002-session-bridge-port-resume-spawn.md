# ADR-002 — The SessionBridge port: resume-or-spawn via the stream-json bridge

- **Status:** accepted
- **Date:** 2026-06-03
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA

## Context

"It just works" (UC-06, FR-24/FR-25) means the founder never chooses
resume vs. spawn. The server resolves a session for the named change:

- live session present → use it;
- no live session but a prior one existed → **resume** from the persisted
  transcript (FR-24);
- never had a session → **spawn** fresh, grounded in the change's saved
  context (FR-25).

The validated mechanism (`local-ui-design.md`, spike 2026-05-26) is the
**headless stream-json bridge**: `claude -p "<prompt>" --output-format
stream-json --include-partial-messages …`, with multi-turn via
`--resume`/`--continue` or the Agent SDK. The interactive-TUI/pty path is
explicitly rejected (it is where the earlier attempt churned).

This is a new outbound dependency on a **local process**. Per MECE-3 Form
(MEA-01), the cockpit reaches every external capability through a
domain-owned port. The change store, recreate-runner, and transcript
locator already follow this; the session bridge must too.

## Decision

**Introduce one new domain-owned port, `SessionBridge`, defined by the
cockpit server, with a single production adapter (`StreamJsonSessionBridge`)
that drives the headless `claude` stream-json interface, and a recorded
fixture adapter for tests.** This is an **EXPAND-Create** move (we author
an adapter for a port *we* own), not a SUBSTITUTE-Wrap of the `claude` CLI:
the public face is the cockpit's `SessionBridge` interface; the CLI is
*called by* the adapter.

The port carries the resolve-then-deliver responsibility as explicit
operations, so the safety guards (ADR-003) sit at the seam, not scattered:

```
interface SessionBridge {
  // Side-effect-free: which resolution path applies, without acting.
  // Reuses probeLiveness (ADR-005, signal-0) + transcript location.
  resolveSession(changeId): Promise<SessionResolution>
    // → { kind: "live", session } | { kind: "resumable", lastSessionRef }
    //   | { kind: "fresh" }   (never had a session)

  // The single act. Resumes / spawns as resolution dictates, binds to the
  // named change, then streams. Emits lifecycle + chunk events.
  relay(changeId, prompt, sink): Promise<RelayOutcome>
}
```

- **Resume** = restart the change's most recent session from its persisted
  transcript (the JSONL the existing `locateTranscripts` already finds),
  via the bridge's restart-from-transcript capability. The agent wakes
  with full memory. A step left incomplete at the prior close is **re-run**
  from the restored state, never reported as done (FR-26 / FR-N5 /
  NFR-REL-04) — the adapter does not synthesise a completion; it hands the
  restored transcript to the agent and lets it act.
- **Spawn** = start a fresh session seeded with the change's saved context
  (CONTEXT.md / change manifest / stage / prior decisions) so the agent
  re-reads the change before its first action (FR-25).
- The founder is never prompted; `resolveSession` is internal.

## Alternatives considered

- **Attach to the already-spawned terminal session (rejected).** A change
  may already have a `claude --agent sulis` running in a real tty
  (open question 7 in `local-ui-design.md`). Driving that interactive
  session means pty-scraping — the rejected path. The bridge starts/uses
  its **own headless** session per change instead; liveness of the tty
  session is still *observed* (signal-0) but never *driven*.
- **No port — call the CLI inline from the route (rejected).** Violates
  MEA-01; makes the relay untestable without a live agent; scatters the
  binding/lock/timeout guards into the handler.
- **WebSocket duplex bridge (rejected).** See ADR-001; the bridge's reply
  is one-way.

## Consequences

- One new file each: `ports/SessionBridge.ts`,
  `adapters/StreamJsonSessionBridge.ts`,
  `adapters/RecordedSessionBridge.ts` (fixture).
- The recorded fixture (`recording-bridge-claude-session`, deferred need
  from the SRD) covers all three resolution paths plus a mid-step
  transcript, so the relay + resolution + guards are CI-testable.
- The real resume/real spawn path is verified manually on the founder
  machine (SRD bootstrap-from-zero note) — it cannot fully bootstrap in CI.
- Lifting to cloud later (ADR-008 of the MVP set) means a different
  `SessionBridge` adapter (the agent executing remotely), the rest
  unchanged — the seam holds.
