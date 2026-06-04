# Cockpit

A local web app that gives you a single screen over every change you
have in flight. It reads what's already on disk — your change store,
your worktrees, your Claude Code session transcripts — and renders
them as a thread-centric review tool.

It is read-only **everywhere except one explicitly-audited seam**: the
chat relay (`POST /api/changes/:id/chat`, WP-005) is the single sanctioned
write/act path — it delivers a message to a change's agent and streams the
reply back (resume-or-spawn; ADR-001/002/003). Every other route is GET-only
and provably so; the read-only gate allow-lists exactly the relay (one write
verb) and the `SessionBridge` adapter (one process start), and fails the
build on any mutation or process start anywhere else. It binds to
`127.0.0.1` only.

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
| `GET /api/changes`                   | List every change with liveness.                                                                                                                                                                                                                                    | `Change[]`                                              |
| `GET /api/changes/:id`               | One change + the resolved transcript file paths.                                                                                                                                                                                                                    | `ChangeDetail`                                          |
| `GET /api/changes/:id/status`        | Read-time plain-English status + needs-attention flag, computed on each read from the record + transcript + liveness (never a stored post).                                                                                                                         | `ChangeStatus`                                          |
| `GET /api/changes/:id/brain`         | The entities the agent created for the change (requirements, designs, decisions, workflows…), grouped by kind off the worktree's `.brain/instances` tree; empty groups omitted; a change with none returns `{ groups: [] }` (WP-006). Reading it starts no process. | `BrainView`                                             |
| `GET /api/changes/:id/tree?path=...` | One level of the worktree's folder tree. Default = root.                                                                                                                                                                                                            | `TreeNode[]`                                            |
| `GET /api/changes/:id/file?path=...` | Current contents of a file in the worktree (1 MiB cap).                                                                                                                                                                                                             | `FileContents`                                          |
| `GET /api/changes/:id/diff?path=...` | Base (at `baseSha`) + current contents for Monaco's DiffEditor.                                                                                                                                                                                                     | `FileDiff`                                              |
| `GET /api/changes/:id/transcript`    | Chronologically-merged chat messages from the change's transcripts.                                                                                                                                                                                                 | `TranscriptMessage[]`                                   |
| `GET /api/changes/:id/contract`      | Whether the change's rendered contracts are reachable + what they are.                                                                                                                                                                                              | `ContractAvailability`                                  |
| `GET /api/changes/:id/contract/data` | Serves the rendered `CONTRACT.html` (the data-contract preview).                                                                                                                                                                                                    | `text/html`                                             |
| `GET /api/changes/:id/contract/ui`   | Serves the rendered `UI.html`, or a typed JSON note when the change has no UI contract (never a broken link).                                                                                                                                                       | `text/html` or `{ uiContract, note }`                   |
| `POST /api/changes/:id/chat`         | **The one write/act path (WP-005).** Delivers a message to the change's agent (resume-or-spawn) and streams the reply as SSE. Refuses with `SESSION_BUSY` (409), `SESSION_CHANGE_MISMATCH` (422, zero bytes), or `SESSION_UNREACHABLE` (502, not delivered).        | SSE `ChatStreamEvent` (`state` → `chunk*` → `complete`) |

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

Non-2xx responses use a single envelope:

```json
{ "error": "human-readable message", "code": "TYPED_CODE" }
```

`code` values: `NOT_FOUND` (404), `PATH_OUTSIDE_WORKTREE` /
`NOT_A_DIRECTORY` / `IS_A_DIRECTORY` / `GIT_ERROR` / `BAD_REQUEST`
(400), `NO_BASE_SHA` (422), `TIMEOUT` (504), `METHOD_NOT_ALLOWED`
(405), `INTERNAL_ERROR` (500), and the chat-relay codes `SESSION_BUSY`
(409), `SESSION_CHANGE_MISMATCH` (422), `SESSION_UNREACHABLE` (502). The
client renders contextual messages from `code`.

The server is GET-only by construction **except the one sanctioned chat
relay** (`routes/chat.ts`) and its `SessionBridge` adapter
(`adapters/StreamJsonSessionBridge.ts`). The
`tests/read-only-inventory.test.ts` gate fails the build if any _other_ file
introduces a `.post / .put / .patch / .delete` handler, a filesystem-mutating
call, a mutating git verb, a non-zero process signal, **or a process start**
(the WP-005/ADR-003 rule). The allow-list is a file-path + rule pairing, not a
blanket waiver — the relay may register one write route, the bridge may start
one process, nothing else may do either (TDD §13.7 / ADR-003 — "guarantee,
not convention").

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
the whole MVP and runs in CI on every change. Run it locally with
`npm run check:read-only`; explain every rule with:

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

## How the workspace is organised

```
apps/cockpit/
├── server/                 # Express + Node — runs the read-only API
│   ├── index.ts            # bootstrap — binds 127.0.0.1:5174
│   ├── app.ts              # createApp(deps) Express factory (testable)
│   ├── config.ts           # CONFIG — bindAddress is hard-coded
│   ├── ports/              # ChangeStoreReader + RecreateRunner (WP-004) + SessionBridge (the chat seam, WP-005)
│   ├── adapters/           # SulisChangeStoreReader (Python helper bridge); SulisChangeRecreator + FakeRecreateRunner (WP-004); StreamJsonSessionBridge (prod) + RecordedSessionBridge (recorded fixture) (WP-005)
│   ├── routes/             # GET read handlers + the one chat relay (POST, SSE) + shared shims
│   ├── middleware/         # request-log + typed-error → JSON mapper
│   ├── lib/                # domain logic — no framework imports
│   └── tests/
├── client/                 # React + Vite — runs the UI
│   ├── index.html
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx        # React mount point
│   │   ├── App.tsx         # placeholder root
│   │   ├── pages/          # board (stage columns, WP-003), thread view (WP-013)
│   │   ├── components/     # shells, panels (WP-011/013/014)
│   │   ├── api/            # TanStack Query hooks (WP-011)
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
