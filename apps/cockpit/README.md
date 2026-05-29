# Cockpit

A local web app that gives you a single screen over every change you
have in flight. It reads what's already on disk — your change store,
your worktrees, your Claude Code session transcripts — and renders
them as a thread-centric review tool.

It is **strictly read-only**. It writes nothing, it sends nothing to
any running Claude session, and it binds to `127.0.0.1` only.

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

Six GET endpoints, JSON only, all bound to `127.0.0.1:5174` by default
(TDD §5, ADR-002, ADR-003). The route handlers are thin — they
delegate to the lib functions (WP-005..WP-009) and the change-store
port (WP-003).

| Method + path                                | Purpose                                                       | Wire shape           |
| -------------------------------------------- | ------------------------------------------------------------- | -------------------- |
| `GET /api/changes`                           | List every change with liveness.                              | `Change[]`           |
| `GET /api/changes/:id`                       | One change + the resolved transcript file paths.              | `ChangeDetail`       |
| `GET /api/changes/:id/tree?path=...`         | One level of the worktree's folder tree. Default = root.      | `TreeNode[]`         |
| `GET /api/changes/:id/file?path=...`         | Current contents of a file in the worktree (1 MiB cap).       | `FileContents`       |
| `GET /api/changes/:id/diff?path=...`         | Base (at `baseSha`) + current contents for Monaco's DiffEditor. | `FileDiff`         |
| `GET /api/changes/:id/transcript`            | Chronologically-merged chat messages from the change's transcripts. | `TranscriptMessage[]` |

Non-2xx responses use a single envelope:

```json
{ "error": "human-readable message", "code": "TYPED_CODE" }
```

`code` values: `NOT_FOUND` (404), `PATH_OUTSIDE_WORKTREE` /
`NOT_A_DIRECTORY` / `IS_A_DIRECTORY` / `GIT_ERROR` / `BAD_REQUEST`
(400), `NO_BASE_SHA` (422), `TIMEOUT` (504), `METHOD_NOT_ALLOWED`
(405), `INTERNAL_ERROR` (500). The client renders contextual messages
from `code`.

The server is GET-only by construction. The `tests/read-only-inventory.test.ts`
gate fails the build if any future change introduces a `.post / .put
/ .patch / .delete` handler, a filesystem-mutating call, a mutating
git verb, or a non-zero process signal (TDD §13.7 — "guarantee, not
convention").

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
founder walkthrough (dashboard → chat → files → file viewer → copy path →
diff toggle), plus the empty-state. It needs a browser the first time:

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
│   ├── ports/              # ChangeStoreReader (extractability seam) + RecreateRunner (recreate-on-demand seam, WP-004)
│   ├── adapters/           # SulisChangeStoreReader (Python helper bridge); SulisChangeRecreator + FakeRecreateRunner (recreate-on-demand, WP-004)
│   ├── routes/             # six GET handlers + shared shims
│   ├── middleware/         # request-log + typed-error → JSON mapper
│   ├── lib/                # domain logic — no framework imports
│   └── tests/
├── client/                 # React + Vite — runs the UI
│   ├── index.html
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx        # React mount point
│   │   ├── App.tsx         # placeholder root
│   │   ├── pages/          # dashboard, thread view (WP-012/013)
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
