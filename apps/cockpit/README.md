# Cockpit

A local web app that gives you a single screen over every change you
have in flight. It reads what's already on disk — your change store,
your worktrees, your Claude Code session transcripts — and renders
them as a thread-centric review tool.

It is **strictly read-only**. It writes nothing, it sends nothing to
any running Claude session, and it binds to `127.0.0.1` only.

This README covers the workspace shape and the dev-run flow that
ships with the foundation work package (WP-001). The HTTP surface,
React components, and end-to-end behaviour land in later WPs.

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

## How the workspace is organised

```
apps/cockpit/
├── server/                 # Express + Node — runs the read-only API
│   ├── index.ts            # placeholder bootstrap (WP-010 replaces it)
│   ├── ports/              # one port: ChangeStoreReader (extractability seam)
│   ├── adapters/           # SulisChangeStoreReader lives here later
│   ├── routes/             # six HTTP handlers (WP-010)
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
