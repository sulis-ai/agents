# Working Set — feat-live-origin-stamping

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Live-stamp change-origin at commit time: chat relay computes conversation-id+turn and stamps assisted Sulis-Origin trailer; thread assisted-origin env through spawn port; flip 'likely->exact'; fix multi-session attribution gap.

## 2. Current best solution  (→ Design)
Wire the *sending* end of origin-stamping onto #216's receiving end, in three seams:
1. **TS port widening** — `spawnBridge(argv,cwd)` → `spawnBridge(argv,cwd,originEnv?)`,
   matching the production default `spawnClaudeBridge` that already accepts the 3rd arg.
   Pure CONTRACT change; the read-only gate already allow-lists chat.ts + the bridge by path.
2. **Relay computes assisted origin — modelled on the communication service.**
   conversation = a **Thread id** (`thread_<…>` shape); turn = the **1-based Message
   ordinal** (`Thread.message_count + 1`). A NEW domain-owned `ConversationIdentity` port
   is the seam; its only adapter THIS change (`LocalTranscriptConversationIdentity`) derives
   the identity LOCALLY/read-only from the resolved session (stem → deterministic `thread_`
   id; ordinal = `groupTurns(transcript)+1`). NO cross-service call now (model-only /
   integration-ready). The live Thread/Message repository adapter is a clean later WP.
   Grammar UNCHANGED — only the computed values change. The session→thread rule is ONE
   shared helper so the inferred read path renders the SAME id (reconcile).
3. **Executor exports autonomous SULIS_ORIGIN** — the executor agent exports
   `SULIS_ORIGIN="autonomous; run=<lifecyclerun-ulid>; confidence=<…>"` in its commit step's
   env (the launcher already wires the hook via enable_origin_hook). Run-ulid is per-run, not
   per-launch, so it CANNOT be a static launch-script export; it is set at commit time by the
   executor (agent step / wpx seam). The hook stamps it; failure stays non-fatal.
Consume #216 unchanged (constructors, format_trailer, parse_origin_env, hook, read path).

## 3. Decisions in flight  (→ Decision; status: proposed → accepted)
- **D1 (REVISED 2026-06-07 per founder steer — accepted) — Conversation = communication-service
  Thread id; turn = Message ordinal (1-based).** Modelled on
  `services/communication/domain/models/{thread,message}.py`. Chose the 1-based ordinal over
  the `msg_<shortuuid>` id because: the `turn=<n>` slot is integer-typed in #216's grammar
  (`Number.parseInt`) — a `msg_` id would force a forbidden grammar change; the ordinal is
  monotonic / = `Thread.message_count`; and it matches the inferred path's existing `idx+1`.
  → ADR-016 (rewritten). SUPERSEDES the prior D1 (transcript stem).
- **D5 (accepted) — Model-only now; `ConversationIdentity` port is the seam; defer the live
  call.** Cockpit has zero reach into the communication service (no client, no platform_id); a
  live call adds an outbound integration + full Armor (timeout/retry/CB/auth) — heavier than the
  steer asked. Local read-only adapter now; `CommunicationServiceConversationIdentity` adapter
  (real Thread/Message repos) is a clean later WP behind the same port. → ADR-018 D1. THE one
  founder scope call (flagged, defaulted to model-only).
- **D6 (accepted) — Reconcile likely→exact by moving the inferred path onto the SAME Thread id.**
  CRUX RE-GROUNDED ON CODE: inferred correlation matches by TIMESTAMP WINDOW (`nearestTurn`), NOT
  by conversation id, and a recorded trailer SHORT-CIRCUITS correlation (`correlate` step 1). So
  the flip never needed ids to "line up" — the prior ADR-016 premise was wrong on mechanism. The
  real need is DISPLAY parity (same id before/after flip). Fix: inferred path uses the shared
  `threadIdentity` helper + indexes turns PER TRANSCRIPT — which also closes the #23 multi-session
  TODO in `InferredOriginAttribution.loadTurns`. → ADR-018 D2. (WP-004, REORGANISE w/ char-test.)
- **D2 (accepted) — Port widening is the contract.** `spawnBridge(argv,cwd,originEnv?)`,
  3rd arg OPTIONAL → the contract suite's stubbed child and concierge/onboarding callers
  that don't compute origin keep working unchanged. CONTRACT_FIRST: pin the signature first.
  → ADR-017.
- **D3 (accepted) — Turn index from the resolved transcript, computed in the relay.** Reuse
  shared `groupTurns`; turn = existing-turn-count + 1 (the in-flight turn). Fresh resolution
  (no transcript) → assisted origin is omitted gracefully (degrade to inferred); the first
  resumable turn stamps from turn 1 onward. No new turn store.
- **D4 (accepted) — Executor sets SULIS_ORIGIN at commit-time, not launch-time.** run-ulid is
  per lifecyclerun, a launched terminal runs many; a static launch export would mis-attribute.

## 4. Open questions / unknowns
- **SCOPE CALL (founder) — integrate live now vs model-only now.** Defaulted to MODEL-ONLY
  (D5/ADR-018 D1). If the founder wants the live communication-service call in THIS change, add
  a `CommunicationServiceConversationIdentity` adapter WP + its Armor (timeout/retry/CB/auth) and
  flip ADR-018 D1. Flagged in TDD §7.
- **confidence value source (executor autonomous origin).** Unchanged / resolved: omit
  `confidence` when absent — constructor + trailer format support `run=`-only. WP-005, not a
  blocker. (Autonomous path; unaffected by the Thread/Message remodel.)

## 5. Rejected so far  (→ Decision.rejected_alternatives)
- **Conversation-id = transcript stem (the ORIGINAL D1) — SUPERSEDED.** Not aligned to the
  communication service → not integration-ready; founder steer requires the Thread shape. (Its
  reconciliation rationale was also moot — inferred matches by timestamp, not id.) → D1 revised.
- **turn = `msg_<shortuuid>` id — REJECTED.** Breaks the integer `turn=<n>` grammar; non-monotonic;
  diverges from the inferred path's ordinal. Use the 1-based Message ordinal. (D1.)
- **Make the live cross-service call now — REJECTED for this change.** Heavier than the steer;
  new outbound integration + Armor with no need now. Seam (D5) makes it a clean later WP.
- **Map session-id→thread-id in a side table — REJECTED.** Second store to drift; deterministic
  derivation needs no store now, live adapter uses the service store later. (D6.)
- **Mint a fresh cockpit-side conversation id (e.g. uuid per relay) — REJECTED.** Bespoke when
  the Thread id convention exists (CP-01); also a second id source to drift. (D1.)
- **Static SULIS_ORIGIN export in the launch script — REJECTED.** run-ulid is per-run; one
  launched terminal serves many runs → systematic mis-attribution. (D4.)
- **Re-implement trailer formatting / a second bridge / amend ADR-003 — REJECTED.** Spec
  non-goals + constraints: consume #216 unchanged; env-to-sanctioned-spawn is read-only.

## 6. Working log  (append-only)
- 2026-06-07T18:46:26Z — Working Set created.
- 2026-06-07T18:46:26Z — RECON: origin foundation (_origin_stamp.py, OriginAttribution port+adapters, routes/origin.ts, client Origin*) is ONLY on change/create-autonomous-delivery-environment (PR #216 MERGED), ABSENT from main. main..ADE=54, ADE..main=0 => ADE strict superset; dev->main repoint did not carry ADE across. Base decision needed before specify.
- 2026-06-07T19:01:49Z — RESOLVED: founder reconciled #216 to main; fast-forwarded change branch onto origin/main. Foundation now present in worktree (_origin_stamp.py, OriginAttribution port+adapters, routes/origin.ts, client Origin*). Branch now 0 behind / 0 ahead. Blocker cleared; proceeding to specify.
- 2026-06-07T19:09:00Z — SPEC written (standard). Foundation #216 built the receiving end (hook+stamper+read path); missing is the SENDING end. Scope: widen spawnBridge port to carry originEnv; relay computes conversation+turn -> assisted env; executor exports autonomous SULIS_ORIGIN; multi-session attribution falls out of per-conversation id. Non-goal: interactive terminal-spawn assisted stamping (boundary, redirectable). Acceptance: likely->exact on real executor + real chat commit; non-fatal degradation. Code's #23 ref = origin-stamping-live (StreamJsonSessionBridge TODO), not the CONTEXT.md mislink.
- 2026-06-07T19:18:49Z — DESIGN LOCKED. 3 seams: (TS) widen spawnBridge port to carry originEnv [CONTRACT]; (TS) relay computes assisted origin: conv-id=stem(lastSessionRef)=Claude session id [matches inferred path → reconciles], turn=groupTurns(transcript)+1, pass via widened port; (PY) executor exports autonomous SULIS_ORIGIN at commit time (run-ulid per-run, NOT launch-time static). Consume #216 unchanged. Conv-id ADR-016, port-widening ADR-017. NFR: conv-id stability/collision-resistance inherited from Claude session id; confidence OPTIONAL (omit when absent). Live round-trip = own WP (CI stubs child). Read-only gate already path-allow-lists chat.ts+bridge → no gate change.
- 2026-06-07T20:32:00Z — REMODEL per founder steer: model the assisted identity on the communication service Thread/Message domain (integration-ready). DECISIONS: (D1 revised) conversation = Thread id (`thread_<…>`), turn = 1-based Message ordinal (chose ordinal not `msg_` id — integer grammar slot + monotonic + matches inferred `idx+1`); grammar UNCHANGED, only computed values change. (D5) MODEL-ONLY now — new domain-owned `ConversationIdentity` port + local read-only adapter; defer the live cross-service call (cockpit has zero reach into the service; live call = new EIF + Armor, heavier than steer). THE one founder scope call, flagged TDD §7, defaulted model-only. (D6) RECONCILE CRUX RE-GROUNDED ON CODE: inferred correlates by TIMESTAMP WINDOW not by id, and recorded SHORT-CIRCUITS correlation → prior reconcile premise was wrong; real need is display parity → move inferred path onto the SAME shared `threadIdentity` helper + index per-transcript, which also CLOSES #23 multi-session TODO. ARTIFACTS: ADR-016 rewritten (→thread-id), ADR-018 added (seam + reconcile), TDD updated (Form/Proof/inventory/§7/Verification Plan/Sizing), WP-003 re-spec'd (port+adapter+helper), WP-004 re-spec'd (relay wiring + inferred reconcile, composite EXPAND+REORGANISE w/ char-test). WP-001/WP-005 untouched (shipped; generic env dict / autonomous path). INDEX canonical header verified via `wpx-index lint` (ok). WP-001/005 step-7-complete; WP-002/003/004/006 pending.
