---
id: WP-001
title: Front-door "Start something new" button in WorkspaceTopBar
status: pending
kind: frontend
sequence_id: WP-001
dependsOn: []
blocks: []
estimated_token_cost:
  input: 7k
  output: 3k
tdd_section: Form — "Front-door button" seam
adrs: [ADR-001]
primitive: extend
group: expand
visual_contract: ".design/cockpit-start-change-button/SIGNOFF.md (production-approved 2026-06-08) — signed-off mockup MOCKUP.html state 1; no separate visual-contract WP per change brief (contract already signed)."
verification:
  adapter: frontend
  artifact: apps/cockpit/client/src/tests/WorkspaceTopBar.test.tsx::renders_start_button_and_navigates_to_start
---

> **Branch note (MUST read before implementing).** This WP builds on
> `change/create-change-owned-terminal-shared-session`, **not** `main`. The
> file it edits (`WorkspaceTopBar.tsx`), the `/start` route, and the
> `StartFromIntent` surface only exist on that branch. Do not attempt this
> against today's `main` — start from the in-flight branch (or its merge).

## Context

Adds the single, unmistakable primary action the SPEC calls for — a "Start
something new" button — into the existing `WorkspaceTopBar` (the always-present
workspace chrome). The button **navigates** to the existing `/start` route
(ADR-001: one front door, no new surface). It introduces no start-flow state:
`/start` → `StartFromIntentPage` → `StartFromIntent` → `useStartFromIntent`
already exist on the target branch and are reused unchanged. This is the Form
section's "Front-door button" seam. The button carries a quiet `⌘N` hint
(JetBrains Mono via the design tokens) that the accelerant in WP-002 fulfils.

This is an **extend** primitive: a new control added through the existing
component's established `navigate()` entry point — no new layer, no new route,
no new port.

## Contract

The button is a new control inside the existing component. The component
signature is unchanged.

```typescript
// apps/cockpit/client/src/components/WorkspaceTopBar.tsx (exists — this WP edits it)
//
// Already imports useNavigate and calls navigate(...) (e.g. navigate("/onboarding")).
// This WP adds a primary button to the existing <header> that calls:
//
//   navigate("/start")
//
// rendered as the single primary action in the top bar, with a visible
// "⌘N" hint span (the hint string is shared with WP-002's hotkey — keep them
// in sync per ADR-002).
export function WorkspaceTopBar({ activeChangeId }: Props): JSX.Element
```

Invariants the contract must preserve:
- The button is the **single** primary action in the top bar (exactly one
  primary; the existing tabs/ProductSwitcher/ThemeToggle stay as they are).
- Clicking it calls `navigate("/start")` and nothing else — no network, no
  mutation, no start-state (ADR-001; SPEC "nothing is created before Start
  this work").
- It is a real `<button>` (or link) — keyboard-focusable, with the cockpit's
  `--ring` focus treatment; never `outline:none`.
- Design tokens only — no raw hex/px (WPF-07). The `⌘N` hint uses the
  existing JetBrains-Mono token; no Satoshi assumed (the SPEC font flag).

## Definition of Done

### Red — Failing tests written
- [ ] `apps/cockpit/client/src/tests/WorkspaceTopBar.test.tsx::renders_start_button_as_single_primary_action` — the "Start something new" button renders and is the only primary action in the bar.
- [ ] `apps/cockpit/client/src/tests/WorkspaceTopBar.test.tsx::renders_start_button_and_navigates_to_start` — clicking navigates to `/start` (assert via a MemoryRouter route probe — render a `/start` element and confirm it appears after click).
- [ ] `apps/cockpit/client/src/tests/WorkspaceTopBar.test.tsx::start_button_is_keyboard_focusable_with_visible_focus` — Tab reaches the button; it shows the focus ring (assert focus-visible class/`:focus-visible` style hook, not `outline:none`).
- [ ] `apps/cockpit/client/src/tests/WorkspaceTopBar.test.tsx::start_button_shows_cmd_n_hint` — the `⌘N` hint is present in the button.
- [ ] jest-axe assertion on the rendered top bar with the new button (WPF-06) — no violations.

### Green — Implementation makes tests pass
- [ ] Button added to `WorkspaceTopBar.tsx`; `onClick` → existing `navigate("/start")`.
- [ ] All Red tests pass; existing `WorkspaceTopBar.theme.test.tsx` still passes (regression — the bar's existing controls unchanged).
- [ ] Styles consume design tokens only (WPF-07); the `⌘N` hint uses the JetBrains-Mono token; headings/labels degrade to Inter (no Satoshi dependency added).
- [ ] Implementation follows `boring-code.md` — explicit, no metaprogramming, no new module-level state.

### Blue — Refactor complete
- [ ] If the `⌘N` hint string would be duplicated by WP-002, extract a single shared constant (e.g. `START_HOTKEY_HINT`) so the button hint and the hotkey stay in sync (ADR-002). Otherwise, no refactor needed.
- [ ] No new behaviour introduced in Blue.
- [ ] All tests still green; lint + typecheck clean (build workspace deps first per WPF-14 if the monorepo requires it).

## Sequence

- **dependsOn:** none (the target branch provides `WorkspaceTopBar`, the
  `/start` route, and the signed visual contract; all are satisfied prerequisites).
- **blocks:** none.
- **Parallelisable with:** WP-002, WP-003 (different files / different test scope).

## Estimated Token Cost

- **Input:** ~7k (this WP + `WorkspaceTopBar.tsx` + the TDD Form section + ADR-001)
- **Output:** ~3k (the button edit + the new/extended test file)
- **Total:** ~10k

## Notes

- The button label is "Start something new" (SPEC; design state 1).
- `/start` already guards for an active Product (sends to onboarding when none) —
  no new guard here (ADR-001 consequence).
