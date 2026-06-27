# ADR-004 — The status-line colours land in modules already (or newly) under no-raw-colours coverage

> Status: accepted · 2026-06-27 · Change CH-9642DA · Tier S
> Decision owner: engineering-architect · Scope: Armor (theming), Proof

## Context

The hard constraint: no raw colour literals — tokens only, theme-aware. The
existing characterisation test `tests/no-raw-colours.thread-chat.test.ts`
enforces this and must stay green. That test today scans exactly two modules:
`Thread.module.css` and `Chat.module.css`. The status line introduces new
coloured surfaces:

- Working line: `--accent` text + a 9%/28% `--accent`-over-`--card` tile.
- Finished line: `--bg-positive` / `--bg-positive-border` with a neutral
  `--foreground` label and the green carried only by the `--positive` tick.

These colours will live in the CSS module(s) that style the shared
`ChatStatusLine` and the composer/dock bottom region — i.e. `Composer.module.css`
and the universal `ProductChatDock.module.css` (plus a dedicated status-line
module if the shared component gets its own). None of these are in the
thread-chat test's `MODULES` array. The `ProductChatDock.axe.test.tsx` already
guards `ProductChatDock.module.css` against raw hex; `Composer.module.css` is
currently guarded by no characterisation test.

## Decision

**Every new coloured surface introduced by this change is brought under
no-raw-colours coverage, using the exact tokens named in the signed contract.**

Concretely:

1. The shared status-line styles use only the contract-named tokens
   (`--accent`, `--card`, `--bg-positive`, `--bg-positive-border`,
   `--foreground`, `--positive`) — directly via `var(--*)` or via `color-mix`
   over them for the 9%/28% tint. No hex, no named colour, no `rgb()`.
2. The status-line CSS module is added to the no-raw-colours coverage. The
   cheapest, lowest-drift way is to put the shared component's styles in a
   module the existing `thread-chat` test already scans, **or** extend that
   test's `MODULES` array to include the new module. The decision: **extend the
   `MODULES` array** of `no-raw-colours.thread-chat.test.ts` to include the
   status-line module and `Composer.module.css`, so the same characterisation
   test that "must stay green" now also covers the new surfaces. (Extending the
   array is additive — the two existing modules stay covered, so the test stays
   green for them and gains the new surfaces.)
3. The universal dock's status line is already covered for hex by
   `ProductChatDock.axe.test.tsx`; that guard is retained.

## Consequences

- "The existing no-raw-colours test stays green" is satisfied *and* its scope
  grows to the new colour surfaces — the constraint is honoured in spirit, not
  just letter (a status line that introduced an untested raw colour would
  otherwise slip past the named test).
- The "references only EXISTING tokens" assertion in that test means the
  status-line styles may use only tokens already defined in `tokens.css`. The
  contract confirms all named tokens (`--accent`, `--bg-positive`,
  `--bg-positive-border`, `--positive`, `--card`, `--foreground`) exist in
  tokens.css v4.2.0 — a precondition the implementing WP verifies in its Red.
- The finished-label contrast decision (neutral label, green only on the tick +
  tint) is a contract-level WCAG AA decision carried verbatim into the CSS;
  the implementing WP does not re-derive it.
