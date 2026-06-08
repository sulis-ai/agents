# Working Set — refactor-persistent-chat-sessions

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Build a generic, provider-neutral session/process manager as a Sulis FOUNDATION capability (Python), consumed by the long-running Python plugin CLI (in-process) and the Node cockpit (over a local socket). Replaces the cockpit's stateless spawn-per-message chat bridge. Adapt the proven AE groundwork (terminal_pool/claude_session/monitored_claude_session).

## 2. Current best solution  (→ Design)
Locked model formalised in two artifacts (interface locked; scope/phasing open):
- ADR: `.architecture/persistent-chat-sessions/adrs/ADR-001-provider-neutral-foundation-session-manager.md`
- CONTRACT: `.architecture/persistent-chat-sessions/contracts/SESSION_MANAGER_CONTRACT.md`
Provider-neutral Python foundation SessionManager; session-as-offset-addressed-event-log; six-method surface (open/send/read/health/status/close) with send/read decoupled; provider adapter seam (spawn_argv/encode/decode/turn_complete/capabilities), Claude=adapter #1; event vocab chunk/tool_use/result/error; dual consumers (Python CLI in-process, Node cockpit over Unix-domain socket NDJSON); cockpit SessionBridge.ts becomes a thin socket client (resolveSession→health; relay→open+send+read(follow)).

## 3. Decisions in flight  (→ Decision; status: accepted)
- D1 [ACCEPTED] Home+language = Python in foundation. Decisive: confirmed long-running Python plugin CLI consumer consumes in-process; cross-language tax paid only by cockpit, over a local socket. (ADR-001 §Decision)
- D2 [ACCEPTED] Interface = six methods, send/read decoupled, offset-addressed log. One read() serves live-tail/catch-up/multi-viewer/history. (CONTRACT §2.2/§2.5)
- D3 [ACCEPTED] Cockpit binding = Unix-domain socket + NDJSON (LSP-style), not TCP/WebSocket. (ADR-001 alt 5; CONTRACT §2.8)
- D4 [ACCEPTED] Resume = provider capability, never assumed; honest `resumed` flag. (CONTRACT §2.7)

## 4. Open questions / unknowns
- OQ1 Phasing of the two consumers + whether socket server ships in slice 1 or cockpit consumes via in-process shim first. (decomposition — `/sulis:plan-work`)
- OQ2 Log retention default (events/bytes per session) — recommend retain whole live session.
- OQ3 Memory-cap default (max concurrent warm sessions) — derive from host RAM.
- OQ4 Socket path + manager process lifecycle/stale-socket reclaim — take convention, confirm vs cockpit process model.
(All four recorded in CONTRACT §Part 3.)

## 5. Rejected so far  (→ Decision.rejected_alternatives)
- R1 Python core serving ONLY the Node cockpit — cross-language tax, no in-language benefit (flipped once Python CLI confirmed).
- R2 Port design to TypeScript in the cockpit — correct only under single-Node-consumer assumption, broken by Python CLI; also couples a foundation capability to the cockpit.
- R3 Lift-and-shift AE code as-is — AE is a task pool, no event log/provider seam/decoupled send-read/tests; adapt mechanisms not code. (Named files cli_command_runner/cli_progress_tracker are NOT the groundwork.)
- R4 PTY-hijack of founder's tty — scraping a session we don't own; manager owns its own headless processes.
- R5 WebSocket/TCP duplex bridge — network port where a local file socket suffices.
- R6 One-process-per-message (status quo) — the cause being removed.
(Full rationale in ADR-001 §Alternatives considered.)

## 6. Working log  (append-only)
- 2026-06-05T12:14:14Z — Working Set created.
- 2026-06-05T12:14:15Z — LOCKED MODEL: SessionManager owns warm sessions keyed by caller-supplied key. Each session is an ordered, offset-addressed EVENT LOG. Surface: open(key,spec)->Session; send(key,command)->offset (submit only); read(key,since,follow)->events (get content: live tail, reconnect catch-up, multi-viewer, history via since=0); health/status/close. Provider behind a small adapter (spawn_argv/encode/decode/turn_complete/capabilities). Shared event vocab: chunk/tool_use/result/error. Claude = adapter #1; Codex/Gemini future adapters, zero change to manager or consumers.
- 2026-06-05T12:14:16Z — DECISIVE FACT (flipped language choice): the Sulis plugin CLI is LONG-RUNNING/agentic and Python — a real in-process consumer of warm sessions. Therefore the core is Python in the foundation (not TS in the cockpit). Cross-language cost is paid only by the cockpit, justified by a genuine Python consumer.
- 2026-06-05T12:14:17Z — REJECTED (with why): (a) Python core serving ONLY the Node cockpit = cross-language tax with no benefit [rejected until Python consumer confirmed]. (b) Lift-and-shift AE code as-is = wrong, the two NAMED files (cli_command_runner=one-shot, cli_progress_tracker=gutted shim) are not the groundwork; real groundwork is terminal_pool/claude_session/monitored. (c) Port design to TS = correct ONLY under single-Node-consumer assumption, which the Python CLI fact broke. (d) pty-hijack of user terminals = rejected in brief; manager-owned PTY is fine. Per 3 critical-thinking spiral runs.
- 2026-06-05T12:21:12Z — CRYSTALLISED: ADR-001 + SESSION_MANAGER_CONTRACT.md written under .architecture/persistent-chat-sessions/. Interface locked; scope/phasing deferred to plan-work (OQ1-4 recorded in contract Part 3).
- 2026-06-05T12:24:53Z — PHASING DECIDED (founder): Core + CLI FIRST. Phase 1 = the Python foundation SessionManager core + Claude adapter + in-process library binding + a minimal real CLI driver (observable end-to-end: open/send/read --follow/close). Phase 2 (captured, deferred) = the Unix-socket server (cross-process binding) + cockpit migration (SessionBridge -> socket client). Consequence acknowledged: cockpit chat keeps its 40-60s lag until phase 2.
- 2026-06-05T12:24:53Z — DECIDED-BY-DEFAULT (3 tuning OQs from contract, all HOW/no founder consequence): (OQ2) log retention = retain whole live session (full 'see what you missed'); revisit only on memory pressure. (OQ3) memory cap = derive from host RAM with conservative floor. (OQ4) socket path = well-known runtime-dir path, manager auto-started by first consumer, stale-socket reclaim on bind. Founder owns only OQ1 (phasing, decided above).
- 2026-06-05T12:24:53Z — ARTIFACTS: ADR-001 + SESSION_MANAGER_CONTRACT.md written under .architecture/persistent-chat-sessions/. Interface locked; dispatching plan-work for phase 1.
