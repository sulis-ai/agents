# ADR-002 — The ⌘N / ⌘K accelerant is a minimal global hotkey, not a command palette

> Status: accepted · 2026-06-08 · change: cockpit-start-change-button

## Decision

The keyboard accelerant is a **single small global keydown handler** that maps
⌘N (and ⌘K) to `navigate("/start")` — the same destination as the button
(ADR-001). It is **not** a command palette, fuzzy search, or recents list.

- Implemented as one tiny hook (e.g. `useStartHotkey()`) mounted once in
  `WorkspaceShell`, so it is active on every route the chrome wraps.
- It follows the existing keydown idiom already in the codebase
  (`ProductSwitcher` adds/removes a `document` `keydown` listener in a
  `useEffect` with cleanup; the handler mirrors that pattern).
- It **ignores the keystroke when focus is in a text input / textarea /
  contenteditable**, so typing in the composer or the intent box is never
  hijacked.
- It calls `e.preventDefault()` only when it acts, to avoid stomping the
  browser's native ⌘N where the handler chose not to fire.

## Why

- **The design scopes ⌘K as an accelerant to the same flow, with a future
  palette, not a palette now.** JOURNEY §1: *"⌘N / ⌘K → 'Start something new' —
  keyboard users and power users get there faster, but land on the identical
  intent screen."* The Mobbin palette references (Linear, Todoist) shaped the
  *idea* of a fast route; the SPEC's scope is the front door, not a palette.
  Building a palette now would be scope the founder did not sign off.
- **No palette infrastructure exists today.** A search of the target branch
  finds no `cmdk`, no command registry, no global palette — only per-component
  `keydown` handlers. Introducing a palette would be a new subsystem
  (registry, search, recents) for a feature whose only command today is "start".
- **One destination, provably.** Because the hotkey and the button both call
  `navigate("/start")`, they cannot drift into two paths — which is the SPEC's
  central reuse constraint.
- **YAGNI / boring code.** A 20-line hook with an input-focus guard is the
  smallest thing that satisfies the requirement. A palette is the position that
  would need defending.

## Rejected alternatives

- **Build a full ⌘K command palette (cmdk-style) now.** Rejected: out of the
  signed-off scope, new subsystem, and a palette with a single command is
  worse UX than a direct hotkey. The design names a palette only as a *future*
  road in.
- **Bind the hotkey inside `WorkspaceTopBar` next to the button.** Rejected: the
  top bar is not guaranteed to be the right ownership boundary for a *global*
  shortcut, and binding there couples the shortcut to the button's render. The
  shortcut is workspace-global, so it belongs at the `WorkspaceShell` level
  (where other always-present chrome lives).

## Consequence

- Choosing **both** ⌘N and ⌘K to the same destination matches the design's
  "⌘N / ⌘K" phrasing. ⌘N may conflict with the browser's "new window" on some
  platforms; the handler claims it only when not typing, and we accept that
  trade-off because the design explicitly lists ⌘N as the primary hint shown on
  the button (`⌘N`). If platform conflict proves annoying in practice, dropping
  to ⌘K-only is a one-line change — recorded here so the future edit is cheap.
- When the cockpit later grows a real command palette, this hook is the natural
  thing it supersedes; the palette would register "Start something new" as its
  first command and the standalone hook would be removed. No lock-in.
- The button's visible `⌘N` hint (JetBrains Mono, per the design tokens) and the
  hook must stay in sync — the TDD's contract section names both so they ship
  together.
