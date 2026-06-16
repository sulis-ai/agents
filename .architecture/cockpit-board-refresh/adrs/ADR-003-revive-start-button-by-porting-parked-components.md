# ADR-003 — Revive the "Start something new" button by porting the parked, already-reviewed components

> **Status:** accepted
> **Date:** 2026-06-09
> **Deciders:** SEA (from the signed-off design)

## Context

The signed-off design (IDEAS.md, Concern 3) calls for a single global "Start
something new" primary button in the top bar, plus the ⌘N / ⌘K accelerant and
the cold-start chips on the start screen.

This exact work was **already built and code-reviewed** on the parked branch
`change/feat-cockpit-start-change-button` and shaped in
`.architecture/cockpit-start-change-button/` (TDD + ADR-001/002 + WP-001/002/003).
It comprises:

- a `start-change-button` in `WorkspaceTopBar` → `navigate("/start")`;
- `useStartHotkey()` — a global ⌘N / ⌘K keydown handler mounted in
  `WorkspaceShell` that navigates to the same `/start` route (ADR-002 there: a
  minimal hotkey, *not* a command palette);
- cold-start chips on the `/start` screen.

**State in this worktree:** the `/start` route and `StartFromIntentPage`
already exist on `main`. The TopBar Start button and `useStartHotkey.ts` do
**not** — they live only on the parked branch.

## Decision

**Port the parked components verbatim into this change**, rather than rebuild
them. Specifically:

- Bring `apps/cockpit/client/src/api/useStartHotkey.ts` across unchanged and
  mount it once in `WorkspaceShell`.
- Apply the parked `WorkspaceTopBar` Start-button variant — the `PlusIcon` +
  "Start something new" button + the exported `START_HOTKEY_HINT = "⌘N"`
  constant (one source of truth for the hint) → `navigate("/start")` — adapting
  only the styling to the board-refresh top-bar chrome (the responsive collapse
  to "+ New" is this change's concern; see ADR-004).
- The cold-start chips on `/start` come across with the same approach.

## Why (Convention Preference + check-before-building)

- **Internal prior art is the highest-priority convention (CP-01 priority 0).**
  The decision (route to the existing `/start` screen, hotkey not palette) was
  already made, reviewed, and signed off. Re-deciding it would be novelty by
  silence.
- **Check before building new (EP-03).** The components exist, pass their tests,
  and carry their own code reviews. Rebuilding them would duplicate reviewed
  work and risk drift from the parked design.
- **One destination, one source of truth (their ADR-002).** Button and hotkey
  both navigate to `/start`; the `START_HOTKEY_HINT` constant keeps the visible
  hint and the hotkey in sync. Porting preserves that; a rebuild risks two
  copies of "⌘N".

## Consequences

- This change carries the port as **two WPs**: one for the TopBar Start button
  (+ its responsive collapse, ADR-004), one for the `useStartHotkey` mount. The
  chips ride the start-screen WP. Each re-runs the parked tests in this branch's
  context (WPF-14 — workspace deps built first).
- Because the parked branch may diverge, the port is by **content**, not a merge
  — the executor copies the reviewed source, re-runs the gates here, and the
  board-refresh styling adapts the button to the new chrome.
- The parked branch can be retired once this change merges (its work lands on
  `main` via this change). Recorded for the founder, not a blocker.

## Alternatives rejected

- **Merge the parked branch directly.** Rejected: the parked branch also
  carries unrelated history; this change needs only the three components, and
  the board-refresh top-bar chrome differs (responsive collapse). A content
  port is cleaner than a branch merge.
- **Rebuild from scratch against the new design.** Rejected: duplicates
  already-reviewed, already-tested work (EP-03) and risks drift from the parked
  decisions (route to `/start`, hotkey-not-palette).
