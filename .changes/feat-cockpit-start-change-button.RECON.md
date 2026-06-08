# Recon — feat-cockpit-start-change-button

Stage 0 completed at: 2026-06-08T20:57:18Z

## What's already here

- Cockpit is a React/Vite app at `apps/cockpit` (client) + Express server (`apps/cockpit/server`).
- Chrome = `layouts/Shell.tsx`: a left `Sidebar` + a routed main outlet. **There is no top bar component.**
- Routes (`client/src/App.tsx`): `/` Dashboard, `/c/:changeId` ThreadView, `*` NotFound. **No start-a-change route/screen exists.**
- Server is **entirely read-only**: every route in `apps/cockpit/server/routes/` is a GET. No POST/create/start route.
- The cockpit MVP spec (`.changes/create-cockpit-mvp.SPEC.md`) deliberately scopes the cockpit as read-only:
  "never write, mutate, restart, or invoke anything outside its own process."
  Starting a change today is a CLI action (`/sulis:change start`); the cockpit's job was to *tell the founder how*, not do it.

## Shaping finding (founder owns this)

The intent names a "top bar" and a "start-a-change screen" — neither exists, and starting a change
from the browser would cross the cockpit's deliberate read-only boundary. Two paths:
1. **Read-only path** — button opens a screen that explains/guides how to start a change via the CLI. Small, stays in-design.
2. **Interactive path** — button + screen + a new server write-route that actually starts the change. Larger; breaks the read-only posture.

## Arrival check
- RC-02: `main` does not require branch-ci (known: private repo / free plan — branch-CI is advisory here).
