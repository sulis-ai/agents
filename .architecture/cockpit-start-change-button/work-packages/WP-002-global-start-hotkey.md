---
id: WP-002
title: Global ⌘N / ⌘K start hotkey mounted in WorkspaceShell
status: pending
kind: frontend
sequence_id: WP-002
dependsOn: []
blocks: []
estimated_token_cost:
  input: 6k
  output: 3k
tdd_section: Form — "Global hotkey" seam
adrs: [ADR-002]
primitive: create
group: expand
visual_contract: "exempt — no visual surface (a keyboard accelerant; the only visible artifact is the button's ⌘N hint, owned by WP-001 against the signed-off .design/cockpit-start-change-button/SIGNOFF.md)."
verification:
  adapter: frontend
  artifact: apps/cockpit/client/src/tests/useStartHotkey.test.tsx::cmd_n_navigates_to_start
---

> **Branch note (MUST read before implementing).** This WP builds on
> `change/create-change-owned-terminal-shared-session`, **not** `main`.
> `WorkspaceShell.tsx`, the `ProductSwitcher` keydown idiom this mirrors, and
> the `/start` route only exist on that branch. Do not build against `main`.

## Context

Adds the keyboard accelerant from the SPEC and ADR-002: a single, small global
keydown handler mapping ⌘N (and ⌘K) to `navigate("/start")` — the **same**
destination as the WP-001 button, so the accelerant cannot drift into a second
path (ADR-001). It is **not** a command palette (ADR-002 rejected alternative).

It is a tiny new hook (`useStartHotkey`) mounted once in `WorkspaceShell` so it
is live on every route the chrome wraps. It mirrors the existing keydown idiom
already in the codebase: `ProductSwitcher` adds/removes a `document` `keydown`
listener inside a `useEffect` with cleanup — this hook follows that pattern
exactly. This is a **create** primitive (a net-new hook), the only genuinely
new architecture in the change.

## Contract

```typescript
// apps/cockpit/client/src/api/useStartHotkey.ts (this WP creates)
//
// Mounted once in WorkspaceShell. Mirrors the ProductSwitcher keydown idiom:
// a document "keydown" listener added/removed in a useEffect with cleanup.
export function useStartHotkey(): void
```

Behaviour the contract MUST satisfy:
- On `(metaKey || ctrlKey) && key === "n"` → `navigate("/start")` and
  `e.preventDefault()` (claim the key only when it acts, per ADR-002).
- On `(metaKey || ctrlKey) && key === "k"` → `navigate("/start")` and
  `e.preventDefault()`.
- **No-op when the user is typing:** when `document.activeElement` is an
  `<input>`, `<textarea>`, or a `contenteditable` element, the handler does
  nothing and does NOT call `preventDefault` — typing in the composer or the
  intent box is never hijacked (ADR-002).
- The listener is **removed on unmount** (cleanup in the `useEffect` return).
- Pure client navigation — no network, no timeout/retry/breaker (TDD Armor:
  the hotkey carries no network).

```typescript
// apps/cockpit/client/src/layouts/WorkspaceShell.tsx (exists — this WP edits it)
// Call the hook once inside WorkspaceShell so it is workspace-global.
export function WorkspaceShell(): JSX.Element  // adds: useStartHotkey();
```

## Definition of Done

### Red — Failing tests written
- [ ] `apps/cockpit/client/src/tests/useStartHotkey.test.tsx::cmd_n_navigates_to_start` — firing ⌘N navigates to `/start` (assert via MemoryRouter route probe).
- [ ] `apps/cockpit/client/src/tests/useStartHotkey.test.tsx::cmd_k_navigates_to_start` — firing ⌘K navigates to `/start`.
- [ ] `apps/cockpit/client/src/tests/useStartHotkey.test.tsx::no_op_when_focus_in_textarea` — with a focused `<textarea>`, firing ⌘N does NOT navigate (drive a real focused textarea; assert no route change).
- [ ] `apps/cockpit/client/src/tests/useStartHotkey.test.tsx::no_op_when_focus_in_input` — same for a focused `<input>`.
- [ ] `apps/cockpit/client/src/tests/useStartHotkey.test.tsx::listener_removed_on_unmount` — after unmount, firing ⌘N does nothing (spy on `document.removeEventListener`, or assert no navigation post-unmount).

### Green — Implementation makes tests pass
- [ ] `useStartHotkey.ts` created; `useEffect` adds the `document` `keydown` listener and returns a cleanup that removes it (mirrors `ProductSwitcher`).
- [ ] `WorkspaceShell.tsx` calls `useStartHotkey()` once.
- [ ] All Red tests pass; existing `WorkspaceShell.test.tsx` still passes (regression — shell structure/outlet unchanged).
- [ ] Implementation follows `boring-code.md` — explicit guards, no metaprogramming, no module-level state.

### Blue — Refactor complete
- [ ] The input-focus guard is a single named helper (e.g. `isTypingTarget(el)`) — readable, testable, no duplication.
- [ ] If WP-001 introduced a shared `⌘N` hint constant, this hook references the same source of truth where relevant (ADR-002: button hint + hook stay in sync).
- [ ] No new behaviour introduced in Blue.
- [ ] All tests still green; lint + typecheck clean (WPF-14 workspace-deps-built if required).

## Sequence

- **dependsOn:** none (target branch provides `WorkspaceShell`, `ProductSwitcher`
  idiom, and the `/start` route — satisfied prerequisites).
- **blocks:** none.
- **Parallelisable with:** WP-001, WP-003 (different files / different test scope).

## Estimated Token Cost

- **Input:** ~6k (this WP + `ProductSwitcher.tsx` idiom + `WorkspaceShell.tsx` + ADR-002)
- **Output:** ~3k (the new hook + its test + the one-line shell mount)
- **Total:** ~9k

## Notes

- ⌘N may conflict with the browser's "new window" on some platforms; ADR-002
  accepts this because the handler only claims the key when not typing, and ⌘N
  is the design's primary hint. If conflict proves annoying, dropping to ⌘K-only
  is a one-line change (ADR-002 consequence).
- No new test infrastructure — `@testing-library/react` `renderHook` /
  `fireEvent.keyDown(document.body, ...)` against a MemoryRouter is sufficient.
