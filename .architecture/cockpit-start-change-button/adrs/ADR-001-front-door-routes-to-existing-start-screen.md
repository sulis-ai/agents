# ADR-001 — The front door routes to the existing `/start` screen; it does not open a new surface

> Status: accepted · 2026-06-08 · change: cockpit-start-change-button

## Decision

The "Start something new" button (and the ⌘N / ⌘K accelerant) **navigate to the
existing `/start` route**, which already renders `<StartFromIntentPage />` →
`<StartFromIntent />`. We do **not** build a modal, drawer, overlay, or a new
page for the start flow.

- The button lives in `WorkspaceTopBar` and calls the same
  `useNavigate()` → `navigate("/start")` that the top bar already uses for
  `/onboarding`.
- The intent screen, the light-clarify step, the confirm-before-start gate, the
  "Starting…" state, and the honest error/retry are **already implemented** in
  `<StartFromIntent />` + `useStartFromIntent` on the target branch. This change
  consumes them; it adds nothing to the start state machine.
- The server-side confirm gate (`confirmToken`, the `propose` → `confirm`
  funnel in `streamStartFromIntent`) is reused unchanged — there is exactly one
  start path, and it stays server-authoritative.

## Why

- **The SPEC and the design both mandate reuse and one path.** SPEC Constraints:
  *"Wire the front door into the existing start-from-intent flow and its
  server-side confirm gate; don't create a second start path."* JOURNEY: *"One
  destination, several roads in… never a parallel one."* Routing to `/start`
  makes the button and ⌘K provably the same flow — they resolve to the same
  route, the same component, the same hook, the same funnel.
- **`/start` is already a first-class route.** `App.tsx` registers
  `/start → StartFromIntentPage` inside `WorkspaceShell`. A route already exists;
  reusing it is EP-03 (check before building new), not new work.
- **A route keeps the workspace chrome.** `/start` renders inside
  `WorkspaceShell`, so the top bar (and its "Start something new" button) stays
  visible — consistent with the mockup's framing and with the existing
  `/onboarding` and `/concierge` surfaces.
- **Boring beats clever.** A navigation is the most boring, most established way
  to reach a screen that already exists. A modal would duplicate focus
  management, escape handling, and scroll containment that the page already
  gets for free.

## Rejected alternatives

- **Open the start flow in a modal / overlay over the current screen.** Rejected:
  it would re-host `<StartFromIntent />` inside a dialog, duplicating focus-trap
  and dismissal logic, and it diverges from the design's full-screen intent
  surface (MOCKUP states 2–5 are full-screen, not a dialog). It also tempts a
  second, modal-local copy of start state — exactly the parallel path the SPEC
  forbids.
- **A brand-new dedicated start page distinct from `/start`.** Rejected: there
  is already a dedicated start page at `/start`. A second one would be the
  "parallel door" the design explicitly rejects.

## Consequence

- The only client work for the front door itself is: a button in
  `WorkspaceTopBar` that calls `navigate("/start")`, plus the accelerant
  (ADR-002). No start-state code is written in this change.
- The cold-start chips/welcome (the one genuinely new piece of the start screen)
  are added **inside the existing `<StartFromIntent />`**, not in a new surface —
  see the TDD's Form section. They prefill/submit through the existing
  `propose()` entry point, so they ride the same single path.
- Because `/start` requires an active Product (the existing page sends the
  founder to onboarding when there is none), the front door inherits that
  precondition for free — no new guard is written here.
