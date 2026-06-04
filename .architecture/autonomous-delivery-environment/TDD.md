# Technical Design — the Sulis app: drive a change from the app

**Change:** CH-01KT50 · `create-autonomous-delivery-environment`
**Mode:** brownfield-with-spec — **extend** `apps/cockpit/` (EP-03)
**Tier:** L (see `SIZING.md`; ASR-driven)
**Sources:** `.specifications/autonomous-delivery-environment/{SRD,NFR,GLOSSARY}.md`,
`diagrams/`, `plugins/sulis/docs/sulis-product-ladder.md`,
`plugins/sulis/docs/local-ui-design.md`, existing `apps/cockpit/`.

> **Respect, don't restate.** The cockpit's hexagonal architecture, ports,
> read-only gate, localhost bind, signal-0 liveness, and contract/adapter/
> fake test discipline already exist and are documented in the MVP's
> `apps/cockpit/` source comments (MVP ADR-001..ADR-008). This TDD references
> that established structure and specifies **only** what this change adds.
> New ADRs (ADR-001..ADR-005 in this change's `adrs/`) do not renumber the
> MVP set — they are this change's own namespace.

---

## 1. The shape of the change

The app is a read-only window today. This change makes it a cockpit you can
**steer from**, by adding six surfaces and the app's first write path — all
reaching data through the **one seam** (the local Node/Express server). The
single architectural rule that survives up the product ladder: *design the
seam, not the cloud* — the client touches data only through the server's
HTTP API, never the filesystem (NFR-ARCH-01).

The headline and the risk are the same thing: **two-way chat** is the first
surface that *acts on* a running agent. Most of the Armor and Proof work is
about doing that safely (binding, isolation, no-silent-loss, no fabricated
completion) while keeping every other surface provably read-only.

---

## 2. Form — structural integrity

### 2.1 The seam (unchanged principle, extended surface)

The server is the seam. Today it exposes GET-only read endpoints behind
domain-owned ports (`ChangeStoreReader`, `RecreateRunner`). We keep that
shape and add:

- **read projections** behind the existing `ChangeStoreReader` + transcript
  + brain reads (board grouping, status, brain view, search) — no new port
  needed for reads; they compose existing reads;
- **one new port** — `SessionBridge` (ADR-002) — the only new external
  dependency (the local `claude` process), reached the same way every other
  capability is: through a port the domain owns.

```
            apps/cockpit/
client  ──HTTP──▶  server (THE SEAM)
(React)            │
                   ├─ routes/ (GET reads + 1 POST relay)
                   ├─ ports/ ChangeStoreReader · RecreateRunner · SessionBridge(NEW)
                   └─ adapters/ Sulis* (prod) · Fake*/Recorded* (test)
                                                  │
            change store · brain · worktrees · transcripts · claude session
```

`SessionBridge` is **EXPAND-Create**, not SUBSTITUTE-Wrap: the public face
is the cockpit's own port; the `claude` CLI is *called by* the adapter
(ADR-002). No Band-Aid wrapper, no internal-code wrap.

### 2.2 Component inventory (new / changed)

| Component | Move | Form note |
|---|---|---|
| `ports/SessionBridge.ts` | EXPAND-Create | domain-owned port; resolve + relay |
| `adapters/StreamJsonSessionBridge.ts` | EXPAND-Create | prod adapter over headless `claude` stream-json |
| `adapters/RecordedSessionBridge.ts` | EXPAND-Create | test adapter (recorded fixture) |
| `routes/chat.ts` | EXPAND-Create | the one POST relay (SSE response) |
| `routes/status.ts` `routes/brain.ts` `routes/search.ts` | EXPAND-Create | GET read projections |
| `lib/sessionBinding.ts` | EXPAND-Create | pure binding guard (ADR-004) |
| `lib/inFlightLock.ts` | EXPAND-Create | per-change one-in-flight lock |
| `lib/computeStatus.ts` `lib/needsAttention.ts` | EXPAND-Create | read-time status + attention rule |
| `lib/readBrain.ts` | EXPAND-Create | brain entities grouped by kind |
| `lib/searchChanges.ts` | EXPAND-Create | content search over conversation + entities |
| `shared/api-types.ts` | EXPAND-Extend | add `ChangeStatus`, `BrainView`, `ChatStreamEvent`, chat error codes |
| client `pages/Board.tsx` (was `Dashboard`) | REORGANISE-Refactor | stage columns; needs characterisation test |
| client `pages/ThreadView.tsx` | REORGANISE-Refactor | stage track + status header + brain section + chat dock; characterisation test |
| client `components/{StageColumn,Composer,BrainView,StatusHeader,StageTrack,SearchBar,NeedsAttentionFilter}.tsx` | EXPAND-Create | new components on existing tokens |
| reused: `ChangeCard`, `StageBadge`, `LivenessDot`, Monaco viewer, contract-preview renderer | REUSE | EP-03 — restyle/compose, don't rebuild |

The two `REORGANISE-Refactor` items (Board, ThreadView) each require a
**characterisation test** in their WP Red before refactor (EP-07; catalogue
MUST). The rest are Create or Reuse.

### 2.4 Component inventory — expanded scope (concierge, discovery, multi-product)

The expanded scope (SPEC items 7 + 8; FR-27..38, FR-N6..N11, NFR-DISC-01..06)
adds **no new transport** — the concierge and the discovery agent both ride
the existing `SessionBridge` (ADR-006). The new components are an orchestration
layer plus Product-scoping at the seam.

| Component | Move | Form note |
|---|---|---|
| `lib/concierge/conciergeRead.ts` | EXPAND-Create | read-only nav/status/Q&A over the seam (FR-33); composes existing `ChangeStoreReader` + brain read; **no new write path** (ADR-006) |
| `lib/discovery/onboardingOrchestrator.ts` | EXPAND-Create | sequences existing discovery skills + spine emitters over the bridge (ADR-007); search→ask→confirm→mint (FR-27,28,31,32) |
| `lib/discovery/repoFindOrCreate.ts` | EXPAND-Create | find branch (configure existing) / create branch (local `git init`, confirm-gated); no-dangling-config (FR-35, FR-N10, FR-N11; ADR-008) |
| `lib/discovery/startFromIntent.ts` | EXPAND-Create | intent → primitive+slug (existing `_specify_classifier`); `Project.source`→`--repo-root`; local-first clone-then-start (FR-29, FR-30; ADR-007) |
| `lib/discovery/confirmGate.ts` | EXPAND-Create | the FR-N6 "ask before consequential" gate, reused by mint + start (NFR-DISC-04); shares the chat relay's confirm discipline |
| `lib/products/productScope.ts` | EXPAND-Create | active-Product scope + `change→Project→Product` server-side roll-up (FR-37, FR-38; ADR-009) |
| reused: `discover-project`, `discover-context`, `codebase-mapping` skills | REUSE | EP-03 — orchestrate, don't reimplement (FR-28, FR-N7) |
| reused: `sulis-emit-tenant`/`-product`/`-project` spine emitters | REUSE | the only sanctioned entity-write path (FR-32, NFR-DISC-03) |
| reused: `_specify_classifier` + change-primitives vocabulary | REUSE | intent → primitive (FR-29) |
| reused: `sulis-change start` | REUSE | the change-creation act (FR-29, FR-34) |
| reused: `SessionBridge` (ADR-002) | REUSE | concierge + discovery agent transport — no second bridge (FR-27; ADR-006) |
| `routes/products.ts` | EXPAND-Create | `GET /api/products`, `POST /api/products/active` (or `?product=` variant; ADR-009) |
| `routes/concierge.ts` | EXPAND-Create | read-only concierge query relay over the bridge (FR-33) |
| `routes/onboarding.ts` | EXPAND-Create | discovery session: search/propose/confirm/mint (FR-27,28,35,36) |
| `routes/startChange.ts` | EXPAND-Create | start-from-intent: classify/clone/start, confirm-gated (FR-29,30,34) |
| `routes/chat.ts` `GET /api/changes` `GET /api/search` | EXPAND-Extend | add Product scoping (server-side roll-up, FR-37); chat/discovery share the relay (FR-27) |
| client `components/{ProductSwitcher,ConciergeChat,OnboardingChat}.tsx` | EXPAND-Create | switcher (FR-38) + the concierge/onboarding conversation UI (its own UX/Mobbin pass per SPEC) |

Every consequential act in this inventory is one of exactly **two**: a spine-emitter
mint (FR-28) or a `sulis-change start` (FR-29/FR-34) — both behind the FR-N6 confirm
gate (NFR-DISC-04). The concierge's read path (FR-33) and the product switcher
(FR-38) write nothing, mint nothing, start no session (FR-N8, NFR-DISC-05).

### 2.3 Dependency direction

Client → server (HTTP) only. Server domain logic (`lib/`, routes) depends on
ports, never on adapters. Adapters depend on the outside world (fs, `git`
read, `claude` process). No client filesystem access (NFR-ARCH-01, enforced
by `check-boundary.py`).

---

## 3. Armor — operational hardening

The new write path is where all the hardening concentrates. Existing Armor
(localhost bind NFR-SEC-01, signal-0 liveness NFR-SEC-04, typed error
envelope, read-only gate) is **kept** and extended.

### 3.1 The relay pipeline (order is load-bearing)

For `POST /api/changes/{id}/chat`, in this order:

1. **Acquire the one-in-flight lock** for the change → else `SESSION_BUSY`
   (409) (FR-20, NFR-REL-03). Lock is per-change, in-memory, released on
   complete/break/fail.
2. **Resolve** the session (`SessionBridge.resolveSession`) — live /
   resumable / fresh — without acting, reusing signal-0 liveness +
   transcript location (no new side effects on read; FR-N4).
3. **Bind** (ADR-004, `lib/sessionBinding.ts`): positively prove the
   resolved/target session belongs to this change (carried `change_id` +
   `cwd`-equality). Fail-closed → `SESSION_CHANGE_MISMATCH` (422), **zero
   bytes**, no process touched (FR-21, FR-N2, NFR-SEC-02/06).
4. **Act** (`SessionBridge.relay`): use-live / resume-from-transcript /
   spawn-grounded, on **only** this change's session (NFR-SEC-06). If the
   process can't start → `SESSION_UNREACHABLE` (502), message **not** marked
   delivered (FR-19, FR-N3).
5. **Stream** SSE events (ADR-001): `state` → `chunk*` → `complete`. On
   drop, preserve partial + mark interrupted (FR-22, NFR-REL-02). On resume,
   `complete.resumed=true` and an honest "resumed" indication; an
   interrupted-at-close step is **re-run**, never reported done (FR-26,
   FR-N5, NFR-REL-04).
6. **Release** the lock.

### 3.2 Timeouts & resource bounds

- Bridge process start has a bounded startup timeout (parallel to the
  existing 5s git timeout); failure → `SESSION_UNREACHABLE`.
- The SSE response sets `no-cache` / `keep-alive` / unbuffered; idle-stream
  watchdog closes a stalled bridge so the lock can't leak.
- One session per change at a time (the lock is also a resource bulkhead).

### 3.3 Secrets & transport

Localhost only (NFR-SEC-01); single founder; no tokens cross the seam
(SRD Q11). The only authorization that matters is **session-to-change
binding** (ADR-004) — not network auth.

### 3.4 Observability (NFR-SEC-03)

The relay logs **one structured line per send**: `{changeId, resolution:
live|resume|spawn, outcome: accepted|refused|completed|broken, code?}` —
and **never** the message body or reply text. Reuses the existing
`request-log` discipline (no bodies, no headers).

### 3.5 The read-only gate extension (ADR-003)

`check-read-only.sh` + `read-only-inventory.test.ts` are extended to
allow-list **exactly** the relay route file (for its one mutation verb) and
the bridge adapter file (for its one process start), and to **add a new
rule** flagging any process start elsewhere. Reading any surface starts no
`claude` process (NFR-SEC-05) — asserted by test. This keeps the app
*provably* read-only everywhere except the one audited seam.

---

### 3.6 Armor for the expanded scope (concierge, discovery, multi-product)

The expanded scope adds two consequential acts (mint, change-start) and a
new read surface (concierge). The hardening keeps the same posture: the
consequential acts are confirm-gated and contained; everything else stays
provably read-only.

**Confirm-before-consequential (FR-N6 / NFR-DISC-04).** Minting an entity and
starting a change each require an explicit founder confirmation *before* the
act. A read-and-propose turn needs none. `lib/discovery/confirmGate.ts`
reuses the chat relay's "ask before consequential" discipline — not a new
approval mechanism. The gate is the precondition both the mint and the start
wait on; a declined proposal leaves the graph unchanged.

**Bounded directory search (FR-N7 / NFR-DISC-01).** The discovery agent reads
**only** under the founder's chosen area, via the existing discovery skills
and their `codebase-mapping` skip-list. No whole-disk, home-directory-
wholesale, or parent/sibling roaming. (Search *depth* within the chosen area
is a founder-owned question; recorded safe default: recursive-under-the-
chosen-folder-only.)

**All-or-nothing persistence + no dangling config (FR-N10 / FR-N11; ADR-008).**
`Project.source` and the Product/Project config are persisted **only after**
the repo is found-or-created and reachable and the founder has confirmed. A
confirmed repo-create that **fails** surfaces a clear plain-English failure
and persists **no** config pointing at the missing repo — the graph is left
as it was. The local-first `git init` create target keeps the consequential
act reversible (no network, nothing published).

**Idempotent mint (FR-31 / NFR-DISC-02).** Before minting, onboarding probes
the graph for an existing Tenant / Product / Project and surfaces it rather
than creating a duplicate. Re-running onboarding does not grow the entity
count.

**Local-first reachability + clone bounds (FR-30).** Before starting a change,
the app ensures the Project's repo is reachable; if absent it clones from
`Project.source.repo` first (bounded by the existing 5s-class subprocess
timeout discipline); a clone failure ⇒ visible failure + **no** change
started.

**Concierge containment (FR-N8 / FR-N9 / NFR-DISC-05).** The concierge's
read path (FR-33) performs zero writes / mints / session-starts / signals —
the read-only discipline (FR-N1 / NFR-SEC-05) extended to the front door. Its
**only** consequential acts are the FR-28 mint and the FR-29 change-start,
both behind the confirm gate. An investigation request creates a change
(FR-34); no build/edit/exploration runs inline in the concierge turn.

**Read-only gate extension (ADR-003 + ADR-006 + ADR-009).** The gate keeps the
chat relay as the one sanctioned *write* path; the discovery mint and
change-start reach consequence only through the already-sanctioned
emitter / `sulis-change start` paths (no new file-level write exception for
the concierge). `POST /api/products/active` is classified as a **scope-
selection** verb (no side effect beyond view scope), distinct from both
forbidden mutations and the sanctioned chat write (FR-38 read-only). If the
builder takes the `?product=` query-param variant (ADR-009), no gate change
is needed at all.

**Observability.** The discovery orchestrator logs one structured line per
consequential act — `{act: mint|start, entity?: tenant|product|project,
outcome: proposed|confirmed|completed|declined|failed, code?}` — and **never**
logs directory contents, the founder's prompt, or the agent's reply
(parallel to NFR-SEC-03). Bounded-search violations and dangling-config-
avoidance are observable in the act log.

## 4. Proof — verification protocol

### 4.1 What's reused

The cockpit's contract test + fake-vs-adapter parity + supertest route
tests + Vitest component tests + axe-core a11y e2e all stay and extend.

### 4.2 What's added

- **`SessionBridge` contract test** — one suite the prod adapter and the
  recorded fixture both satisfy (parity discipline; MEA pattern).
- **Recorded-bridge fixture** (`recording-bridge-claude-session`, deferred
  need) — covers **live / resume / spawn / mid-step** so the relay +
  resolution + guards run in CI **without a live agent** (MEA-09: no mocks
  for the integration — a recorded real stream, replayed).
- **Binding guard unit test** — A-request → B-session ⇒ mismatch, zero
  bytes (NFR-SEC-02); passes for resumed + spawned sessions.
- **One-in-flight test** — second send mid-stream ⇒ `SESSION_BUSY`; sending
  succeeds after end (NFR-REL-03).
- **Fault-injection tests** — no session / dead session / broken bridge ⇒
  visible failure, never a false "sent" (NFR-REL-01); mid-stream kill ⇒
  partial preserved + interrupted (NFR-REL-02).
- **No-fabricated-completion test** — resume from a mid-step transcript ⇒
  agent re-runs the step; founder sees "resumed" (NFR-REL-04, FR-N5).
- **Read-only-gate test extension** — exactly one module may start a
  process; loading any read surface starts none (NFR-SEC-05).
- **Component tests** — board stage-columns, stage track, status header,
  brain view groups, search/filter narrowing, chat composer states
  (ready/replying/resuming/could-not-start, FR-23), partial-reply render.
- **a11y** — axe-core on every new surface (per-kind frontend adapter).

The real resume / real spawn path is verified **manually on the founder
machine** (it needs a live `claude`; cannot fully bootstrap in CI).

### 4.3 What's added for the expanded scope

All of the discovery / concierge behaviour rides the same bridge as the chat,
so it has the same CI shape: recorded fixtures replace the live agent.

- **Concierge read-only test (FR-33 / FR-N8 / NFR-DISC-05)** — the nav /
  status / Q&A path performs zero writes / mints / session-starts / signals;
  uses the existing `FakeChangeStoreReader` + brain fixtures, exactly like the
  board/thread read tests.
- **Concierge containment test (FR-34 / FR-N9)** — an investigation request
  results in a change being created (after confirm) and **not** in inline
  investigation work; asserts no concierge path performs build / edit /
  exploration outside a started change.
- **Confirm-gate test (FR-N6 / NFR-DISC-04)** — no entity minted and no change
  started without explicit confirmation; a declined proposal leaves the graph
  unchanged.
- **Bounded-search test (FR-N7 / NFR-DISC-01)** — discovery reads only under
  the chosen root; an attempt to access a path outside the chosen area is not
  performed.
- **Validated-emitter test (FR-32 / NFR-DISC-03)** — minted entities pass the
  spine emitters' schema validation; no onboarding path writes an entity file
  directly.
- **Idempotency test (FR-31 / NFR-DISC-02)** — onboarding run twice against
  the same area does not grow the entity count.
- **Repo find-or-create tests (FR-35 / FR-N10 / FR-N11)** — repos-exist branch
  finds/configures a seeded repo (`fixture-project-directory`, no creation);
  no-repo branch confirm-gated `git init` into `fixture-repo-create-target`;
  a simulated create-failure persists **no** dangling config.
- **Local-first clone-then-start test (FR-30)** — absent repo ⇒ clone from a
  local `fixture-local-repo-for-clone`, then start at Recon; clone-failure ⇒
  visible failure + no change started.
- **Intent → primitive + slug test (FR-29 / FR-34)** — the existing classifier
  resolves a primitive+slug; `sulis-change start` lands the change at Recon.
- **Durable-config round-trip test (FR-36 / NFR-DISC-06)** — mint in one
  test-session, read back `Project.source` in a **fresh** session, start a
  change with no re-discovery; no new config store introduced (NFR-DATA-01).
- **Per-Product board scoping test (FR-37)** — seed two Products; the board
  shows only the active Product's changes; no change rolling up to the other
  Product appears.
- **Product switcher test (FR-38 / UC-11)** — selecting another Product
  re-scopes the board + per-product views (search, stage filter, needs-
  attention); the switch performs zero writes / mints / session-starts.
- **Component tests (frontend)** — product switcher (lists Products, marks
  active, re-scopes on select); concierge chat; onboarding conversation UI
  including the "do you have a repo?" create-vs-find branch; a11y (axe-core)
  on each new surface.

The full live discovery path (real agent, real mint, real `git clone`, real
`sulis-change start`, real hosted-remote create if chosen) is verified
**manually on the founder machine** — it cannot fully bootstrap in CI. The
CI-side guarantees use `recording-bridge-discovery-session` +
`fixture-project-directory` + `fixture-local-repo-for-clone` +
`fixture-repo-create-target`.

---

## 5. The six surfaces → endpoints map

| # | Surface | Endpoint(s) | Requirements |
|---|---|---|---|
| 1 | Stage Kanban board | `GET /api/changes` (grouped client-side) | FR-01,02,03,15 |
| 2 | Plain-English status | `GET /api/changes/{id}/status` (NEW) | FR-04,05 |
| 3 | Brain view (grouped) | `GET /api/changes/{id}/brain` (NEW) | FR-06,07 |
| 4 | Rendered previews | existing `…/file` + `…/contract` (REUSE renderer) | FR-08,09 |
| 5 | Search + filter | `GET /api/search` (NEW) | FR-10,11,12 |
| 6 | Two-way chat | `POST /api/changes/{id}/chat` (NEW, SSE) | FR-16..26, FR-N1..5, NFR-SEC/REL |

Full request/response shapes: `contracts/openapi.yaml`; founder-readable
version: `contracts/DATA-CONTRACT-GUIDE.md`.

### 5.1 The expanded surfaces → endpoints map (concierge, discovery, multi-product)

| Surface | Endpoint(s) | Read / Act | Requirements |
|---|---|---|---|
| Multi-product: list + switch | `GET /api/products`; `POST /api/products/active` (or `?product=` query variant, ADR-009) | read / scope-select (no data write) | FR-37, FR-38, UC-11 |
| Product-scoped board + search | `GET /api/changes` + `GET /api/search` gain Product scope (server-side roll-up) | read | FR-37 (supersedes FR-01/02/03/15 → "active Product") |
| Concierge: nav / status / Q&A | `POST /api/concierge/query` (read-only relay over the bridge, ADR-006) | read-only (zero writes/mints/starts) | FR-33, FR-N8, NFR-DISC-05 |
| Onboarding / discovery session | `POST /api/onboarding/session` — search → propose → confirm → mint (SSE, same bridge) | propose=read; mint=act (confirm-gated) | FR-27,28,31,32,35,36; FR-N6,N7,N10,N11; NFR-DISC-01..04,06 |
| Repo find-or-create | folded into the onboarding session (a confirm step inside it; not a separate top-level endpoint) | act (confirm-gated, local-first) | FR-35, FR-N10, FR-N11; ADR-008 |
| Start a change from intent | `POST /api/changes/start-from-intent` — classify → clone-if-absent → start, confirm-gated (SSE) | act (confirm-gated) | FR-29, FR-30, FR-34; FR-N6 |

Every **act** endpoint above sits behind the FR-N6 confirm gate
(NFR-DISC-04) and reaches consequence only through the two sanctioned paths
(spine-emitter mint; `sulis-change start`). The concierge query and the
product list/switch are **read-only** (FR-N8, FR-38). The onboarding and
start-from-intent endpoints stream via SSE (ADR-001) because they drive the
same headless bridge as the chat (FR-27).

---

## 6. The coherent surface (ADR-005)

The founder's "lumpy → one coherent thing" mandate. Two-level IA: **board
(home)** → **thread (the change)**. One shell, one token system
(`tokens.css`, no raw hex), one stage colour scale (the `StageBadge`
palette reused in columns + track + badge), one state-pattern set (loading
/ empty / error / server-down), chat as a persistent dock in the thread.
The **visual contract** `mockups/SULIS-APP-surface.mockup.html` renders this
with real tokens for founder sign-off **before build**.

---

## 7. Delivery shape — local → binary → web (seam, not cloud)

We build the **local web app** only. The seam discipline is what makes the
later steps cheap and is the *only* thing we build for them now:

- **Local (now):** client → local Express server → on-disk data + local
  `claude`. Server binds `127.0.0.1`.
- **Installable binary (next):** same client + server packaged (e.g. Tauri,
  per `local-ui-design.md`); the seam is unchanged — it's still HTTP to a
  local server.
- **Web (later):** the *same* HTTP seam served from the cloud; the
  `SessionBridge` adapter changes (agent executes remotely), nothing else.

We do **not** build cloud infra. The discipline that protects all three:
the client never cheats past the seam (NFR-ARCH-01), and the one write path
is a port (`SessionBridge`) whose adapter is the only thing that changes
when the agent moves off-box.

---

## 8. Decomposition note

`/sulis:plan-work` will produce atomic WPs. Suggested spine (dependsOn in
parens): shared types → `SessionBridge` port + contract test → recorded
fixture → binding guard + lock (lib) → relay route (SSE) → read projections
(status/brain/search) → read-only-gate extension → client board refactor →
thread refactor (status/track/brain) → chat composer + stream client →
a11y + visual pass. The two REORGANISE-Refactor client WPs (Board,
ThreadView) carry characterisation tests in Red.

---

## 9. Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

> Concretises the SRD's `## Verification Plan` to TDD-level artifacts. Six
> subsections (ADR-001 of the verification standard). The SRD's plan is
> PASS; nothing here contradicts it.

### What user-observable behaviour are we verifying

The founder lands on a stage-column board of their changes; opens one and
reads a marked stage track + plain-English status; sees brain entities
grouped by kind; reads a document rendered (raw one click away); searches
by content and filters by stage / needs-attention; and — the headline —
sends a message to any change and it "just works" (resume-or-spawn,
binding-checked, streamed live), with every other surface read-only and an
interrupted-at-close step re-run honestly.

### Verification environment(s)

- **Local dev + CI** — server route tests (supertest), client component
  tests (Vitest), a11y (axe-core), the read-only gate (`check-read-only.sh`).
  Mirrors the existing cockpit setup.
- **Local (founder machine)** — chat end-to-end against a real `claude`
  (live / real-resume / real-spawn); the stream-json bridge is a local
  process the SRD spike validated.
- The change's **own dogfood path** — taken through specify → design →
  implement → `sulis-verify-acceptance --scenario`; the six emitted scenarios
  exercise this change (the testable-state loop this change road-tests).

### Bootstrap-from-zero case

Read surfaces bootstrap from a fresh clone using the existing
`FakeChangeStoreReader` + fixture transcripts + the new
`seed-brain-entities-fixture` (deferred need). The chat e2e cannot fully
bootstrap in CI (needs a live `claude` + real resume/spawn) → covered by the
`recording-bridge-claude-session` fixture (deferred need: live + resume +
spawn + mid-step), with the full live path verified manually.

### Per-integration verification strategy

| Integration | Boundary | Strategy | Classification | TDD concretion |
|---|---|---|---|---|
| Change store + brain | port (`ChangeStoreReader`, brain read) | fakes/fixtures in tests; real store on founder machine | **existing** | `server/tests/routes.{status,brain,search}.test.ts`; in-memory `FakeChangeStoreReader` (existing class) |
| Claude session bridge (stream-json) | local process / stdio | relay + resolution (incl. resume + spawn) against a **recorded fixture**; full live path manual | **deferred** | seam: `ports/SessionBridge.ts`; concrete WP shape **deferred** — `recording-bridge-claude-session`; resilience: bridge startup timeout + idle watchdog + one-in-flight bulkhead (see `references/architecture-patterns.md` timeout/bulkhead) |
| design-system VIEWER / contract renderer | in-process / subprocess | reuse existing renderer + its tests | **existing** | `…/contract` path (cockpit-contract-preview WP-001/002) |
| Worktree recreate-on-demand | subprocess (`RecreateRunner`) | existing port + tests | **existing** | unchanged |
| Concierge nav / status / Q&A (FR-33) | in-process read over the seam | read-only path against `FakeChangeStoreReader` + brain fixtures; assert zero writes/mints/starts/signals | **existing** | `server/tests/routes.concierge.test.ts`; reuses the board/thread read fixtures (ADR-006) |
| Headless discovery agent (FR-27, same bridge) | local process / stdio | search→ask→confirm→mint + classify→clone→start against a **recorded fixture** | **deferred** | seam: `SessionBridge` (ADR-002, reused); fixture `recording-bridge-discovery-session`; `server/tests/routes.onboarding.test.ts` |
| Discovery skills (`discover-project`/`-context`, `codebase-mapping`) | in-process / subprocess | orchestrate the **existing** skills; reuse their tests; assert orchestration calls them (ADR-007) | **existing** | bounded to `fixture-project-directory`; `server/tests/discovery.orchestrator.test.ts` |
| Spine emitters (Tenant/Product/Project) | in-process (validated emitters) | mint via the **existing** emitters; assert schema-valid + no bypass (FR-32) | **existing** | `server/tests/discovery.emitter-only.test.ts` |
| Project repo local-first / clone (FR-30) | subprocess (`git`) | reachability + clone-from-source on absence; clone-failure ⇒ no change started | **deferred** | fixture `fixture-local-repo-for-clone` (+ broken variant), no network; `server/tests/startFromIntent.clone.test.ts` |
| Repo find-or-create (FR-35) | subprocess (`git` / host) | repos-exist: find/configure (fixture dir); no-repo: `git init` temp dir, confirm-gated; failed-create ⇒ no dangling config | **deferred** | fixtures `fixture-project-directory` + `fixture-repo-create-target`; live hosted-remote create manual; `server/tests/repoFindOrCreate.test.ts` |
| Persisted Product/Project config (FR-36) | in-process (graph via emitters) | mint then read-back across two sessions with `Project.source`; no new config store | **existing** | `server/tests/durableConfig.roundtrip.test.ts` |
| Per-Product board + switcher (FR-37/38) | in-process read over the seam | seed two Products; board shows only active; switch re-scopes; zero writes/mints/starts | **existing** | `server/tests/products.scope.test.ts`; `client/src/tests/ProductSwitcher.test.tsx` |

- *Idempotency/replay (Q10):* a resend after a broken stream is a NEW
  message, not a silent duplicate; the one-in-flight lock is the guard.
- *Auth/authz (Q11):* localhost-only, single founder; the authorization that
  matters is session-to-change binding (ADR-004).
- *Failure if unavailable (Q12):* bridge down ⇒ visible failure + preserved
  partial (FR-19/22); read surfaces unaffected.
- *Observability (Q13):* one structured relay line per send, no bodies.

### Per-kind verification adapter

Spans **two** adapters (the SRD's per-kind rows):

- **`frontend`** — Vitest component tests (board columns, stage track,
  status header, brain view, search/filter, chat composer states, partial
  render); axe-core a11y on each new surface; visual check against
  `tokens.css` + the signed-off mockup. Artifacts:
  `client/src/tests/{Board,ThreadView,Composer,BrainView,SearchBar}.test.tsx`.
- **`backend`** — behavioural API test for the relay against a running test
  server asserting: binding across live/resumed/spawned (FR-21/NFR-SEC-02),
  resume-from-transcript (FR-24), spawn-grounded (FR-25), incomplete-step
  (FR-26/FR-N5), resume/spawn-acts-only-on-target (NFR-SEC-06), one-in-flight
  (FR-20), clear-failure (FR-19), and the read-only gate including the
  sanctioned relay/bridge (FR-N1/NFR-ARCH-02). Artifacts:
  `server/tests/routes.chat.test.ts`, `server/tests/sessionBinding.test.ts`,
  `server/tests/session-bridge.contract.test.ts`,
  `server/tests/read-only-inventory.test.ts` (extended).

Verification frontmatter shapes the WPs will use (ADR-003 of the
verification standard): board/status/brain/search read WPs → **concrete**
(`adapter: backend|frontend` + `artifact:` the named test path); the chat
relay WP → **deferred** (`adapter: backend` +
`deferred-to-follow-on: recording-bridge-claude-session`) for the live
path, **concrete** for the binding/lock/failure logic against the fixture.

### Infrastructure needs surfaced (deferred)

- `recording-bridge-claude-session` — recorded/replayable stream-json
  session; MUST cover **live**, **resume-from-transcript**,
  **spawn-grounded-in-context**, plus a **mid-step** transcript (FR-26/FR-N5).
- `seed-brain-entities-fixture` — fixture brain entities so the brain view
  (FR-06/07) verifies from a fresh clone.
- `recording-bridge-discovery-session` — recorded/replayable discovery-session
  stream-json fixture (mirrors `recording-bridge-claude-session`) covering the
  onboarding orchestration (search → ask → confirm → mint) and the
  start-a-change orchestration (classify → clone → start) (FR-27..32).
- `fixture-project-directory` — a seeded local folder containing a recognisable
  repo (plus an "already-minted" variant) so search-scope (FR-N7), dedupe
  (FR-31), and the discovery skills' orchestration verify from a fresh clone.
- `fixture-local-repo-for-clone` — a local git repo usable as a
  `Project.source.repo` clone target (plus a deliberately-broken variant) so
  local-first clone-then-start and clone-failure (FR-30) verify without network.
- `fixture-repo-create-target` — a writable temp dir as the **local**
  repo-creation target for the onboarding no-repo branch (`git init`, no
  network) plus a deliberately-failing variant, so the confirm-gated create
  (FR-35 / FR-N10) and no-dangling-config-on-failure (FR-N10 / FR-N11) verify
  in CI. The live **hosted-remote** create path (if the founder chooses it) is
  verified manually.

All follow the canonical `{noun}-{noun}-{vendor-or-scope}` identifier
recipe so the slice-end review can aggregate them.

---

## 10. Sizing Report

- **Tier:** L computed; **re-confirmed L** after the expanded scope. The
  expansion adds ~12 FRs (FR-27..38), ~6 negative requirements (FR-N6..N11),
  and 6 NFR-DISC ASRs, plus 4 integrations (discovery agent, discovery skills,
  repo find-or-create, per-Product roll-up). Recomputed ASR ≈ 38 (still
  tier-L; not yet XL — single bounded context, all riding the existing seam +
  bridge). See `SIZING.md`.
- **TDD length:** grew with the expansion but stays at ~tier-L target because
  the new capabilities **reuse** (the bridge, the skills, the emitters, the
  classifier, the gate) rather than introduce new mechanisms — most new
  sections are orchestration + scoping, not new infrastructure. No circuit
  breaker tripped.
- **ADRs produced:** 9 total (5 original + 4 new). New: ADR-006 concierge
  rides the bridge / coordinates only; ADR-007 discovery orchestrates existing
  skills + emitters; ADR-008 repo find-or-create local-first / no dangling
  config; ADR-009 board is Product-scoped / server-side roll-up. Within tier-L
  max. None duplicate the MVP ADR set (referenced as prior art, not
  renumbered).
- **Referenced (not restated):** the cockpit hexagonal seam, read-only gate,
  signal-0 liveness, contract/adapter/fake test discipline, contract-preview
  renderer, `tokens.css`; **and for the expansion:** the existing
  `SessionBridge` (ADR-002), the `discover-project`/`-context`/
  `codebase-mapping` skills, the Tenant/Product/Project spine emitters, the
  `_specify_classifier`, and `sulis-change start` — all reused, not rebuilt
  (EP-03).
- **Sections referencing rather than restating:** §2 (seam), §2.4 (reuse rows),
  §4 (test discipline), §7 (delivery shape).

## 11. Open architecture questions (founder-owned only)

The two genuinely founder-owned items are surfaced for review (not guessed):

1. **"Needs attention" set** — confirmed default is blocked /
   waiting-on-decision / stopped-mid-reply; idle-but-fine excluded. Add
   "idle too long"? (FR-12)
2. **Search scope** — confirmed default searches change *content*
   (conversation + created items), not just titles. Confirm this is the
   expected reach. (FR-10)

3. **Where a newly-created repo lives (the one new founder-owned call in this
   expansion).** When onboarding creates a repo for a founder who has none
   (FR-35 no-repo branch), the **recorded safe default is a local-only git
   repo** (`git init`) in the founder's chosen area — no external account, no
   network, nothing published, fully reversible (ADR-008). The alternative is
   creating the repo on a **hosted remote** (e.g. GitHub) under the founder's
   account, which publishes code and needs the founder's hosting credentials.
   This is a genuine founder/business call — confirm the local-only default or
   ask for hosted-remote (a separately-confirmed step at the design stage).
   (FR-35 / FR-N10; ADR-008)

The two remaining founder-owned questions the SRD parked (recorded with safe
defaults) are **not** re-opened here — they are settled defaults:
**onboarding search depth** within the chosen area (default:
recursive-under-the-chosen-folder-only, skipping the standard noise) and
**single-vs-multiple Product per onboarding** (default: one Product per
conversation). Confirm or change at the design stage.

Everything else is convention-default and recorded in the SRD's
`## Assumptions & decided-by-default` + the ADRs.
