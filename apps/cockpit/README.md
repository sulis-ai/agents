# Cockpit

A local web app that gives you a single screen over every change you
have in flight. It reads what's already on disk — your change store,
your worktrees, your Claude Code session transcripts — and renders
them as a thread-centric review tool.

It is read-only **everywhere except one explicitly-audited file**:
`server/routes/chat.ts`. That file holds every confirm-gated act path — the
chat relay (`POST /api/changes/:id/chat`, WP-005), the cold-start
onboarding route (`POST /api/onboarding/session`, WP-010), and start-from-intent
(`POST /api/changes/start-from-intent`, WP-011) — so the consequential
seam is one audited place, never scattered (ADR-003/006/007). The agent itself
runs the discovery skills and the validated spine emitters inside its session;
the server starts no extra process. Every other route is GET-only and provably
so; the read-only gate allow-lists exactly that one relay file (its write verbs)
and the `SessionBridge` adapter (one process start), and fails the build on any
mutation or process start anywhere else. The interactive terminal is a SECOND
sanctioned write path (ADR-010) — it adds exactly two more named, audited gate
exceptions (the sidecar bridge's WebSocket attachment + the session-manager host
start), detailed in the read-only gate section below. It binds to `127.0.0.1` only.

This README covers the workspace shape, the dev-run flow, and the
HTTP surface that ships with WP-001 + WP-010. The React components
and end-to-end behaviour land in later WPs.

## Starting the dev experience

From this directory:

```bash
npm install            # once, at the repo root
npm run dev            # starts both halves
```

`npm run dev` uses `concurrently` to launch two processes side by
side:

- **Express server** via `tsx watch server/index.ts` on
  `http://127.0.0.1:5174`. Restarts on save.
- **Vite client** on `http://127.0.0.1:5173`. Hot-reloads on save.
  Vite proxies every `/api/*` request to the Express server so the
  browser only sees one origin.

Open `http://127.0.0.1:5173` in your browser. The placeholder client
displays "cockpit booting…" — real UI lands in WP-011 and later.

Both ports are overridable via env (`COCKPIT_SERVER_PORT`,
`COCKPIT_CLIENT_PORT`). The host stays `127.0.0.1`; that is not
configurable.

## The HTTP surface

GET endpoints, JSON only (plus two HTML-serving contract endpoints and
**one** sanctioned write path — the chat relay, which streams SSE), all
bound to `127.0.0.1:5174` by default (TDD §5, ADR-001/002/003). The route
handlers are thin — they delegate to the lib functions (WP-005..WP-009)
and the ports (the change-store reader, WP-003; the `SessionBridge`, WP-005).

| Method + path                        | Purpose                                                                                                                                                                                                                                                             | Wire shape                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `GET /api/changes?product=`          | List the **active Product's** in-flight changes with liveness. Scoped server-side via the `change → Project → Product` roll-up (FR-37, ADR-009); the optional `?product=<id>` selects the active Product (the stateless all-GET scope variant). The single-Product Tenant is the trivial case — every change is in scope (WP-008).                                                                       | `Change[]`                                              |
| `GET /api/products`                  | The Tenant's Products with the active one marked, for the product switcher (FR-38, WP-008). The single-Product Tenant is the trivial case — one Product, shown active (synthesised when the brain has none). Read-only.                                              | `ProductList`                                           |
| `GET /api/changes/:id`               | One change + the resolved transcript file paths.                                                                                                                                                                                                                    | `ChangeDetail`                                          |
| `GET /api/changes/:id/status`        | Read-time plain-English status + needs-attention flag, computed on each read from the record + transcript + liveness (never a stored post).                                                                                                                         | `ChangeStatus`                                          |
| `GET /api/changes/:id/brain`         | The entities the agent created for the change (requirements, designs, decisions, workflows…), grouped by kind off the worktree's `.brain/instances` tree; empty groups omitted; a change with none returns `{ groups: [] }` (WP-006). Reading it starts no process. | `BrainView`                                             |
| `GET /api/search?product=&q=&stage=&needsAttention=` | Search + filter the active Product's changes by **content** (conversation + created entities — not just titles, FR-10), by `stage` (repeatable param → array, FR-11), and by `needsAttention` (blocked / waiting-on-decision / stopped-mid-reply; idle-but-fine is NOT flagged — FR-12, reuses `needsAttention`). The set is scoped to the active Product (`?product=<id>`) BEFORE the content filter, so a filter never surfaces another Product's change (FR-37). Filters compose; same row shape as the board list. Reading it starts no process (WP-007/008). | `{ results: Change[] }`                                 |
| `GET /api/changes/:id/tree?path=...` | One level of the worktree's folder tree. Default = root.                                                                                                                                                                                                            | `TreeNode[]`                                            |
| `GET /api/changes/:id/file?path=...` | Current contents of a file in the worktree (1 MiB cap).                                                                                                                                                                                                             | `FileContents`                                          |
| `GET /api/changes/:id/diff?path=...` | Base (at `baseSha`) + current contents for Monaco's DiffEditor.                                                                                                                                                                                                     | `FileDiff`                                              |
| `GET /api/changes/:id/transcript`    | Chronologically-merged chat messages from the change's transcripts.                                                                                                                                                                                                 | `TranscriptMessage[]`                                   |
| `GET /api/changes/:id/contract`      | Whether the change's rendered contracts are reachable + what they are.                                                                                                                                                                                              | `ContractAvailability`                                  |
| `GET /api/changes/:id/contract/data` | Serves the rendered `CONTRACT.html` (the data-contract preview).                                                                                                                                                                                                    | `text/html`                                             |
| `GET /api/changes/:id/contract/ui`   | Serves the rendered `UI.html`, or a typed JSON note when the change has no UI contract (never a broken link).                                                                                                                                                       | `text/html` or `{ uiContract, note }`                   |
| `POST /api/changes/:id/chat`         | **The one write/act path (WP-005).** Delivers a message to the change's agent (resume-or-spawn) and streams the reply as SSE. Refuses with `SESSION_BUSY` (409), `SESSION_CHANGE_MISMATCH` (422, zero bytes), or `SESSION_UNREACHABLE` (502, not delivered).        | SSE `ChatStreamEvent` (`state` → `chunk*` → `complete`) |
| `POST /api/concierge/query`          | **The concierge front door (WP-009, read-only).** Answers plain-English nav / status / Q&A over the change store + brain, streaming SSE; it rides the SAME bridge as the chat (no second bridge, ADR-006) and performs ZERO writes/mints/starts (FR-N8). Intent is classified by a DETERMINISTIC pre-classifier (`detectRoute`), not the LLM: when intent is consequential (investigate / start-work / empty-world set-up) the inline bridge is **short-circuited entirely** — `complete` carries a `route` hint and the concierge OFFERS the confirm-gated next step, never investigates inline (FR-N9 — investigation is contained in a change, never run loose). The bridge is reached ONLY for a genuine read-only question (`route === null`). 502 `SESSION_UNREACHABLE` if the bridge can't be reached. | SSE `ConciergeStreamEvent` (`state` → `chunk*` → `complete{route}`) |
| `POST /api/onboarding/session`       | **Cold-start onboarding (WP-010, confirm-gated act).** One turn in the setup conversation for an EMPTY graph (UC-07): `phase: "search"` runs discovery in the founder's CHOSEN area only (bounded — `chosenArea` outside the permitted root ⇒ 422 `DISCOVERY_SCOPE_VIOLATION`, FR-N7); `phase: "ask"` answers a clarifying question; `phase: "confirm"` (with the live `confirmToken`) performs the ACT — repo find-or-create (local-only `git init` by default, ADR-008) then mint via the validated spine emitters. Streams SSE `state` → `chunk*` → `proposal` (awaiting confirm) → `minted`. Idempotent (an already-minted entity is surfaced, not duplicated, FR-31); all-or-nothing (a stale confirm ⇒ 422 `DISCOVERY_CONFIRM_STALE`; a failed create ⇒ `REPO_CREATE_FAILED` with NO dangling config, FR-N10/N11); one Product per conversation (409 `SESSION_BUSY` on a second concurrent session, founder-locked). Registered in `chat.ts` so it adds no new write-gate exception (ADR-006). | SSE `OnboardingStreamEvent` (`state` → `chunk*` → `proposal` → `minted`) |
| `POST /api/changes/start-from-intent` | **Start from intent (WP-011, confirm-gated act).** Say what you want in plain English → a change starts at Recon (Journeys H + J). `phase: "propose"` classifies the intent to a change **primitive + slug** via a DETERMINISTIC server-side classifier (the change-primitives vocabulary, FR-29) and streams a `proposal` (mints/starts nothing); an ambiguous intent ⇒ 422 `INTENT_AMBIGUOUS` (asks ONE clarifying question, never guesses). `phase: "confirm"` (with the live `confirmToken`) performs the ACT: it maps the active Product's `Project.source` → `--repo-root`, clones the repo first if absent (local-first, FR-30 — a broken clone ⇒ 502 `REPO_UNREACHABLE` with NO change started), then runs `sulis-change start` so the change lands at Recon. An **investigation** (`kind: "investigation"`) becomes a CONTAINED change, never inline work (FR-34/FR-N9). The change-start is a DETERMINISTIC SERVER action behind the `StartChangeRunner` port (the WP-010 lesson: the act is never delegated to the bridge agent). Stale confirm ⇒ 422 `START_CONFIRM_STALE`; a second concurrent start ⇒ 409 `SESSION_BUSY`. Registered in `chat.ts` so it adds no new write-gate exception (ADR-006). | SSE `StartFromIntentStreamEvent` (`state` → `proposal` → `started`) |

### Two-way chat relay (WP-005)

`POST /api/changes/:id/chat` is the app's first and only write/act path. The
pipeline order is load-bearing (TDD §3.1): acquire the per-change
one-in-flight lock → resolve the session (live / resumable / fresh,
side-effect-free) → **bind** the session to the change (fail-closed; ADR-004)
→ act + stream SSE → release. Resume restarts the change's session from its
persisted transcript; spawn seeds a fresh one grounded in the change's saved
context; neither synthesises a completion, and an incomplete-at-close step is
re-run honestly (FR-26/N5). The founder never chooses resume vs spawn.

The `SessionBridge` port (`ports/SessionBridge.ts`) has two adapters: the
production `StreamJsonSessionBridge` (drives headless `claude -p
--output-format stream-json`) and the test `RecordedSessionBridge` (replays a
recorded real stream-json session — `tests/fixtures/recording-bridge-claude-session.json`
— so send → stream → resume → spawn → mid-step run in CI **without a live
agent**). The full live round-trip is verified on the founder machine (it
needs a real `claude`).

### Contract preview (WP-003)

The three `/contract` endpoints let the founder **see the contracts
before going** — the data contract and the visual/UI contract rendered
from the change's own files. They CONSUME the shared
`CONTRACT.manifest.json` the renderers (`wpx-render-contract`,
`wpx-render-ui`) write into each change's worktree, and serve the named
`CONTRACT.html` / `UI.html` artifacts. The cockpit never parses the
contracts itself — it stays read-only (ADR-001).

Resolution is **generic** (ADR-003): the change is resolved by `:id`
through the same `ChangeStoreReader` port + recreate-on-demand path the
tree/file/diff endpoints use; nothing is hard-wired to a specific
change. A **shipped (tidied) change** has its worktree re-materialised
transparently via the `RecreateRunner` port (WP-004) before its
contracts are served. A malformed change handle is refused by a
defence-in-depth shape-guard (`lib/changeHandleGuard.ts`) **before** it
can reach the recreate spawn (mirrors `CHANGE_ID_PATTERN` + explicitly
rejects a leading `-` to foreclose argparse flag-confusion).

**Two rendering moments, one renderer** (TDD §5):

- **Design-time (pre-dispatch review gate):** after `decompose` and
  before `run-all` dispatch, `plugins/sulis/scripts/wpx-render-review-gate
--worktree <path>` renders the in-flight change's `CONTRACT.html` +
  `UI.html` so the founder can eyeball them before anything is built on
  the contract. It is a thin orchestrator over the two renderers
  (subprocess discipline: argv array, `shell=false`, bounded timeout).
- **On-demand (the testing moment):** the cockpit's per-change "open
  data contract / open UI" links (the `ContractLinks` component, on the
  per-change page) render or re-render via the same renderers when the
  founder clicks. The founder never navigates a worktree.

`ContractAvailability` is `{ status: "ready", present, dataContract,
uiContract }` (the links read this to decide what to show) or
`{ status: "unavailable", note }` (a shipped change that couldn't be
reached). `/contract/data` and `/contract/ui` add `CONTRACT_UNAVAILABLE`
(404) and `CONTRACT_NOT_RENDERED` (404) to the `code` set below.

### Brain + rendered previews (WP-006)

Two read surfaces let the founder **see what the agent created** and
**read a document the way it's meant to look**, both inside the thread
(ADR-005):

- **Brain (`GET /api/changes/:id/brain`).** `lib/readBrain.ts` walks the
  change worktree's `.brain/instances/<domain>/<kind>/<ULID>.jsonld`
  tree, parses each entity, groups them **by kind** (the same kind under
  different domains collapses into one group), omits empty groups, and
  returns a `BrainView`. A change with no brain returns `{ groups: [] }`.
  It is fail-soft: an absent `.brain` is the empty case, and a single
  malformed entity file is skipped rather than sinking the read. Each
  `BrainEntity` carries a resolved `title` (from `title` → `name` →
  `decision`/`intent` → the id) plus the full parsed object as `detail`
  for the readable detail view. The `<BrainView>` component renders the
  groups with a count and an openable per-item detail; an empty brain
  shows a plain note. Reading it starts **no** `claude` process — it
  composes existing reads, no new port.

- **Rendered previews (the Files section).** `<RenderedPreview>` shows a
  renderable document **rendered** with a one-click Rendered ↔ Raw
  toggle: `.md`/`.markdown` via the in-repo `lib/renderMarkdown.ts` (a
  small, dependency-free, **safe** renderer — it HTML-escapes all source
  before emitting any of its bounded tag subset, and drops non-http(s)/
  mailto link schemes, so a document can never inject script), and
  `.html`/`.htm` inside a **sandboxed, script-free iframe**. A code file
  is not renderable — it stays read-only source in the existing Monaco
  viewer (`<MonacoFile>`, reused; EP-03), with no toggle.

### Search + filter (WP-007)

The board's one toolbar lets the founder **narrow the same board** —
there is no separate results screen (ADR-005):

- **Route (`GET /api/search`).** `routes/search.ts` lists the active
  Product's changes (the shared `routes/_product-scope.ts` → the
  `change → Project → Product` roll-up in `lib/products/productScope.ts`;
  trivial single-Product case = all, WP-008), then for each gathers its
  **searchable content** and its
  **attention verdict** via the shared `lib/gatherChangeStatus.ts` (the
  same read-time context the `status` route uses — the FR-12 attention
  verdict is computed in ONE place, reusing `lib/needsAttention.ts`). The
  content scan (`lib/gatherChangeContent.ts`) folds the record's labels +
  the **conversation text** + the **created-entity text** into one string,
  so a term that appears only in a change's conversation or in something
  the agent created still matches (FR-10) — not just titles. The pure
  `lib/searchChanges.ts` filter then applies `q` (content), `stage[]`
  (FR-11, repeatable param → array), and `needsAttention` (FR-12) with AND
  semantics; survivors are shaped to the same `Change` row shape as the
  board list. GET-only; reading it starts **no** `claude` process.

- **Toolbar (`<SearchBar>` in `<Board>`).** The board owns the filter
  state; the toolbar is a controlled `role="search"` component with the
  content-search box, the six stage chips, and the needs-attention chip
  (the SIGNED visual contract). The `useSearch` hook fetches `/api/search`
  only when a filter is active; otherwise the board shows the full
  active-Product list. Clearing every filter restores the full board.
  Consumes `tokens.css` only.

Non-2xx responses use a single envelope:

```json
{ "error": "human-readable message", "code": "TYPED_CODE" }
```

`code` values: `NOT_FOUND` (404), `PATH_OUTSIDE_WORKTREE` /
`NOT_A_DIRECTORY` / `IS_A_DIRECTORY` / `GIT_ERROR` / `BAD_REQUEST`
(400), `NO_BASE_SHA` (422), `TIMEOUT` (504), `METHOD_NOT_ALLOWED`
(405), `INTERNAL_ERROR` (500), the chat-relay codes `SESSION_BUSY`
(409), `SESSION_CHANGE_MISMATCH` (422), `SESSION_UNREACHABLE` (502), and the
onboarding codes `DISCOVERY_SCOPE_VIOLATION` (422), `DISCOVERY_CONFIRM_STALE`
(422), `REPO_CREATE_FAILED` (in-stream). The client renders contextual
messages from `code`.

The server is GET-only by construction **except the one sanctioned chat
relay** (`routes/chat.ts`) and its `SessionBridge` adapter
(`adapters/StreamJsonSessionBridge.ts`). The
`tests/read-only-inventory.test.ts` gate fails the build if any _other_ file
introduces a `.post / .put / .patch / .delete` handler, a filesystem-mutating
call, a mutating git verb, a non-zero process signal, **or a process start**
(the WP-005/ADR-003 rule). The allow-list is a file-path + rule pairing, not a
blanket waiver — the relay may register one write route, the bridge may start
one process, nothing else may do either (TDD §13.7 / ADR-003 — "guarantee,
not convention"). The concierge query (`POST /api/concierge/query`, WP-009) is
read-only and adds **no new** gate exception: it is registered inside the SAME
sanctioned relay file (`routes/chat.ts`) and rides the SAME bridge, so the
write-verb allow-list stays exactly `{chat.ts}` (asserted by the gate, ADR-006).
The cold-start onboarding route (`POST /api/onboarding/session`, WP-010) is the
SECOND act path and follows the same rule: it is registered inside that SAME
file and rides the SAME bridge, so the allow-list is unchanged.

The interactive **terminal** is a SECOND sanctioned write path alongside chat
(ADR-010) — typing into a live PTY is a write, gated at attach authorisation in
the engine, not a read-only bypass. It adds **exactly two** named gate
exceptions, each a single audited file (parity with the chat relay/bridge
pairing, never a blanket waiver):

- the **sidecar bridge** (`adapters/TerminalSidecar.ts`) — the one WS-attachment
  seam. It attaches a WebSocket upgrade handler to the existing HTTP server's
  `upgrade` event (the keystroke → live-PTY transport); it registers no
  `app.post`, so the HTTP surface stays GET-only. The gate's WS-attachment rule
  (`new WebSocketServer` / `.handleUpgrade` / `.on("upgrade"`) flags this shape
  in any _other_ file.
- the **session-manager host start** (`index.ts`) — the one site that spawns the
  Python host owning the pty + AF_UNIX socket. It joins the process-start
  allow-list; the host starts at server boot (one audited site), never on a read.

The terminal is its OWN bridge — added alongside chat's seams, never coupled to
them (it does not import the chat relay or the chat bridge). Run
`npm run check:read-only -- --explain` for the full rule catalogue.

### Cold-start onboarding (WP-010)

When the graph is empty, a form is useless — there's nothing to pick — so setup
is a **conversation that creates the graph** (UC-07, ADR-007). The surface lives
at `/onboarding` (reached from the concierge's confirm-gated offer, or the
product switcher's "Set up a new product").

- **Orchestrator (`lib/discovery/onboardingOrchestrator.ts`).** Sequences
  `search → ask → propose → confirm → mint` over the SAME bridge as the chat
  (FR-27). It reimplements nothing (ADR-007): discovery delegates to the agent
  (which runs the `discover-project` / `discover-context` / `codebase-mapping`
  skills), and the mint delegates to the agent (which runs the validated spine
  emitters). The orchestrator owns only the safety plumbing — scope bound,
  confirm gate, repo find-or-create, idempotency, all-or-nothing. It performs
  no fs write and starts no process.
- **Confirm gate (`lib/discovery/confirmGate.ts`).** A pure module — the
  `sessionBinding` sibling. A read/propose turn mints nothing; only a
  token-matched `confirm` opens the gate. A stale/mismatched token is refused
  (`DISCOVERY_CONFIRM_STALE`).
- **Repo find-or-create (`lib/discovery/repoFindOrCreate.ts`).** A pure decision
  module. The **create-location default is local-only** `git init` (ADR-008,
  founder-locked) — no network, nothing published; hosted-remote (GitHub) is a
  separately-confirmed opt-in, never the default. A failed create yields
  `REPO_CREATE_FAILED` and persists NO `Project.source` (no dangling config,
  FR-N10/N11).
- **UI (`components/OnboardingChat.tsx`).** Reuses the chat composer idiom + the
  SSE funnel (EP-03): choose an area → answer → see the plain-English PROPOSAL →
  confirm. Find-vs-create is explicit with **local-only pre-selected**; the
  Product icon is a **neutral two-letter tile** (reusing `ProductSwitcher`'s
  `monogram`, no logo upload this slice — founder-locked); on success the
  "your product is set up" end state appears and the board takes over.

**Drive it locally (headless, recorded — CI-observable):** boot `npm run dev`,
then POST to `/api/onboarding/session`:

```bash
# 1. search the chosen area (bounded; mints nothing — streams a proposal)
curl -N -X POST localhost:5173/api/onboarding/session \
  -H 'content-type: application/json' \
  -d '{"phase":"search","chosenArea":"/abs/path/to/your/code"}'
# → SSE: state(searching) … chunk* … state(proposing) … proposal{confirmToken,…}

# 2. confirm with the token from the proposal (the ACT — repo + mint)
curl -N -X POST localhost:5173/api/onboarding/session \
  -H 'content-type: application/json' \
  -d '{"phase":"confirm","confirmToken":"<from-the-proposal>","repoChoice":{"mode":"find"}}'
# → SSE: state(confirming) … state(minting) … chunk* … minted{product,projects} … state(complete)
```

The **live** path (a real `claude` running the discover-* skills + the spine
emitters + a real `git init`) is the BLOCK-and-hand-to-founder observation; in
CI the round-trip is exercised against a programmable/recorded bridge.

## Testing

```bash
npm test            # combined unit + integration suite (server + client)
npm run check:read-only   # the workspace-wide read-only guarantee gate
npm run test:e2e    # Playwright end-to-end smoke (browser required)
```

### Combined test run

`npm test` runs `vitest run`, which executes **both** Vitest projects —
the Node-environment server tests and the jsdom/Monaco client tests — in
one pass. The config pins the `forks` pool so the two environments run in
isolated child processes and cannot contend (this is also what CI runs).
Run a single surface with `npx vitest run server` or `npx vitest run
client`.

### Read-only guarantee gate

`apps/cockpit/scripts/check-read-only.sh` statically proves the cockpit
never writes: it greps the active source tree for filesystem-write APIs,
`git` spawns outside the read-only `git show`, mutating git verbs,
non-zero process signals, HTTP mutation verbs, and non-loopback binds
(TDD §13.7, ADR-002, ADR-003). It is the load-bearing read-only proof for
the whole MVP and runs in CI on every change. The HTTP surface stays
GET-only by construction; the gate names a small set of **path-scoped
exceptions** for the sanctioned process-start sites — the chat session
bridge (ADR-003) and, from the production terminal sidecar, the
session-manager host the server entry spawns at boot (ADR-010/ADR-011).
The WebSocket terminal endpoint rides the existing HTTP server's `upgrade`
event, never an `app.post`, so the GET-only guarantee is unaffected. Run it
locally with `npm run check:read-only`; explain every rule with:

```bash
bash apps/cockpit/scripts/check-read-only.sh --explain
```

### End-to-end smoke (Playwright)

The end-to-end smoke under `apps/cockpit/e2e/` boots both halves of the
cockpit against a seeded fixture and drives a real browser through the
founder walkthrough (stage-column board → chat → files → file viewer →
copy path → diff toggle), plus the empty-state. It needs a browser the
first time:

```bash
npx playwright install chromium   # one-time, downloads the browser
npm run test:e2e
```

In CI the browser is installed automatically; if the download is
unavailable on a restricted runner the e2e job is skipped (the read-only
gate + the combined Vitest suite still gate the merge). Visual-regression
comparison is off by default — set `PWTEST_SCREENSHOTS=1` to capture
screenshots on failure locally.

### Live-terminal round-trip (Playwright + real socket)

The live-terminal end-to-end proves the founder's interactive-terminal
journey for real: open a change's **Terminal** tab → see the running session
with its scrollback (not a blank pane) → type a command → see the output →
close the tab and reopen → the session is still alive and scrollback catches
up. It runs under its **own** Playwright config (dedicated ports, so it never
collides with a cockpit you already have running) and a **real** backend — no
mocks:

```bash
npm run test:e2e:terminal
```

How it wires up (all under `apps/cockpit/e2e/`):

- `terminal-backend.py` boots a **real** `SessionManager` serving a **real**
  pty-backed fake child over a **real** AF_UNIX socket, pre-seeded with a
  known scrollback banner.
- `terminal-proxy.ts` bridges the browser's **WebSocket** to that AF_UNIX
  socket (a browser can't open AF_UNIX). It is **harness-only** — the e2e
  proxy/backend pair predate the production sidecar. The real cockpit server
  now ships its own equivalent: `startProductionServer()` (`server/index.ts`)
  spawns the Python session-manager host (`session_manager_host.py`,
  ADR-011), waits for its `READY <socket>` line, then attaches the production
  terminal sidecar (`server/adapters/TerminalSidecar.ts`) to the running HTTP
  server's `upgrade` event — riding the same loopback port, with the binding
  guard ON, Origin validation, and connection/attachment caps. A host crash
  drops live terminals but never the read-only HTTP surface (separate
  processes). Both the host and sidecar are torn down on SIGTERM/SIGINT
  alongside the HTTP server.
- The cockpit's `createTerminalBridge` builds the live `WebSocketTransport`
  when `VITE_TERMINAL_WS_URL` is set (the dedicated config sets it); with no
  endpoint configured the bridge falls back to the "no terminal here" state,
  so a plain build is always safe to mount.

The same run is the **bootstrap-from-zero** proof: from a clean clone it
needs only Python + Node + a Chromium download; the pty fake child has no
external dependency.

## How the workspace is organised

```
apps/cockpit/
├── server/                 # Express + Node — runs the read-only API
│   ├── index.ts            # bootstrap — binds 127.0.0.1:5174
│   ├── app.ts              # createApp(deps) Express factory (testable)
│   ├── config.ts           # CONFIG — bindAddress is hard-coded
│   ├── ports/              # ChangeStoreReader + RecreateRunner (WP-004) + SessionBridge (the chat seam, WP-005) + TerminalBridge (typed terminal socket-client seam, WP-007)
│   ├── adapters/           # SulisChangeStoreReader (Python helper bridge); SulisChangeRecreator + FakeRecreateRunner (WP-004); StreamJsonSessionBridge (prod) + RecordedSessionBridge (recorded fixture) (WP-005)
│   ├── routes/             # GET read handlers + chat relay + concierge query + cold-start onboarding (all POST/SSE in the ONE sanctioned file chat.ts — WP-005/009/010)
│   ├── middleware/         # request-log + typed-error → JSON mapper
│   ├── lib/                # domain logic — no framework imports
│   └── tests/
├── client/                 # React + Vite — runs the UI
│   ├── index.html
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx        # React mount point
│   │   ├── App.tsx         # placeholder root
│   │   ├── pages/          # board (stage columns, WP-003), thread view (WP-013), concierge front door (WP-009)
│   │   ├── components/     # shells, panels (WP-011/013/014), ConciergeChat (the read-only front door, WP-009); LiveTerminal — the xterm.js terminal view (WP-008); ThemeToggle — light/dark control, mounted in WorkspaceTopBar (WP-004)
│   │   ├── terminal/       # client TerminalBridge factory — reuses the WP-007 port (WP-008)
│   │   ├── api/            # TanStack Query hooks (WP-011)
│   │   ├── layouts/        # WorkspaceShell — tabbed top bar (WorkspaceTopBar: product switcher + tab strip + theme toggle) + outlet (#216, WP-004)
│   │   ├── theme/          # ThemeProvider, useTheme(), resolveInitialTheme (WP-003)
│   │   └── tests/
├── shared/                 # types + constants both halves import
│   ├── api-types.ts        # the wire shapes (TDD §5.1)
│   └── dev-ports.ts        # port constants + env-var resolution
├── package.json
├── tsconfig.json           # shared TS settings
├── vitest.config.ts        # one config, two test envs (node + jsdom)
└── .eslintrc.json          # extractability lint rule
```

## The cross-import rule

The cockpit's job is to be liftable into a standalone repo later
without rework. The one boundary that matters: nothing inside
`apps/cockpit/` may import from outside it, and nothing outside it
may import from in.

Two gates enforce this:

1. **ESLint** — `.eslintrc.json` defines `no-restricted-paths` plus
   `no-restricted-imports` patterns that fail the build on any `.ts`
   or `.tsx` import that escapes the workspace. `npm run lint` runs
   it.
2. **CI grep** — `.github/workflows/cockpit-boundary.yml` runs a
   regex sweep on every push that touches `apps/cockpit/`. It
   catches escape patterns in file types ESLint doesn't lint
   (`.json`, `.html`, `.css`, `.md`).

Lift the cockpit later: `cp -r apps/cockpit/ ../sulis-cockpit/`,
swap the adapter, done.

## Read-only guarantees

The cockpit binds to `127.0.0.1` (loopback only) — not `localhost`,
not `0.0.0.0`. Run this from the worktree root to confirm:

```bash
grep -n '127.0.0.1' apps/cockpit/shared/dev-ports.ts
grep -n 'host' apps/cockpit/client/vite.config.ts
```

Both server and client read the host constant from
`shared/dev-ports.ts`; neither accepts a host override.

## What each script does

| Script               | What it does                     |
| -------------------- | -------------------------------- |
| `npm run dev`        | Both halves, in one terminal.    |
| `npm run dev:server` | Just the Express server.         |
| `npm run dev:client` | Just the Vite client.            |
| `npm run typecheck`  | `tsc --noEmit` on both halves.   |
| `npm run lint`       | ESLint over `apps/cockpit/`.     |
| `npm run test`       | Vitest — both test environments. |
| `npm run test:e2e`   | Playwright end-to-end smoke (browser required). |
| `npm run test:e2e:terminal` | Live-terminal round-trip — real socket + pty child (browser required). |
