# WP-006 — Revive the "Start something new" top-bar button (+ ⌘N/⌘K hotkey + chips)

- **Sequence ID:** WP-006
- **dependsOn:** []
- **kind:** frontend
- **primitive:** SUBSTITUTE-port (ADR-003 — port the parked, reviewed components)
- **group:** substitute
- **subject_ownership:** internal (porting our own already-reviewed components from `change/feat-cockpit-start-change-button`)
- **Estimated token cost:** input ~14k / output ~6k
- **visual_contract:** production-approved (`MOCKUP.html` — `.startNew` button; parked `cockpit-start-change-button` mockup)

## Context

TDD §1 + ADR-003. The `/start` route + `StartFromIntentPage` already exist on
`main` in this worktree; the **TopBar Start button** and **`useStartHotkey.ts`**
do not (they live only on the parked branch). Port them by content (not a branch
merge), re-run their tests here.

## Contract

- `api/useStartHotkey.ts` — port verbatim: global ⌘N / ⌘K keydown → `navigate
  ("/start")`; no-ops in typing targets; `preventDefault` only when it acts.
  Mount once in `WorkspaceShell` (so it is workspace-global on every route).
- `WorkspaceTopBar.tsx` — add the Start button: `PlusIcon` + "Start something
  new" → `navigate("/start")`; export `START_HOTKEY_HINT = "⌘N"` (one source of
  truth for the hint; button + hotkey never drift). Primary fill, pill radius —
  the only filled button up there (stands out by shape + weight, not colour).
- Cold-start chips on the `/start` screen — port the parked approach.

The **responsive collapse** of this button (→ "+ New", full label on the
accessible name) is owned by WP-008, which dependsOn this WP.

## Definition of Done

### Red
- [ ] Port the parked tests: `useStartHotkey.test.tsx` (⌘N/⌘K navigates; no-op
      in inputs), `WorkspaceTopBar` Start-button test (renders, navigates to
      `/start`, has accessible name + `:focus-visible`). **Fail** until ported.

### Green
- [ ] Components ported; hotkey mounted in `WorkspaceShell`; tests pass.
- [ ] `tsc` clean with workspace deps built first (WPF-14).
- [ ] jest-axe on the top bar passes (light + dark).

### Blue
- [ ] One `START_HOTKEY_HINT` constant; no second "⌘N" literal (grep).
- [ ] Button + hotkey both go to `/start` (one destination — ADR-003).
- [ ] Tokens only (`--primary`, pill radius token).

## Definition of Done — requirements & scenarios

- **Satisfies:** UC-5, BR-7 (navigate-never-mutate); NFR-SEC-1 (no write path).
- **Makes pass:** **S-5** (Start button navigates, no mutation), **S-6** (⌘N/⌘K
  hotkey, same navigation).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/useStartHotkey.test.tsx
```
