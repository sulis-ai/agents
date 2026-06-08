# Recon — refactor-persistent-chat-sessions

Stage 0 completed at: 2026-06-05T06:16:31Z

This marker indicates `/sulis:recon` has been run for this change.

## Key finding (base-branch dependency)

The chat-bridge code this refactor targets does NOT exist on this change's
base branch (`main`, 860b6df). It lives on un-merged feature branches:

- `feat/wp-005-two-way-chat-roundtrip` (30 ahead of main, 0 behind) —
  server bridge: StreamJsonSessionBridge.ts, RecordedSessionBridge.ts,
  inFlightLock.ts, the chat route, streamJsonToEvents, sessionBinding,
  resolveSession, probeLiveness. This is the integration target named
  throughout the DESIGN brief.
- `feat/wp-013-thread-view-and-chat` (12 ahead of main) — client chat UI
  (Chat.tsx, ChatMessage.tsx) — relevant to the client-side queue (RC-5).

The DESIGN brief's entire integration map references files present only on
wp-005. This change must be based on that branch (or wp-005 must merge to
main first) before the refactor can begin.

## Conventions observed (apps/cockpit, @sulis/cockpit)

- Ports-and-adapters: `server/ports/*.ts` interfaces with `adapters/*.ts`
  implementations + a Fake for tests; contract test suites
  (`*.contract.test.ts`) run an adapter against its port contract.
- Tests: vitest (`vitest run`), co-located `server/tests/`.
- The new PersistentSessionManager implements the existing SessionBridge
  port and reuses runSessionBridgeContract — no new test harness.
