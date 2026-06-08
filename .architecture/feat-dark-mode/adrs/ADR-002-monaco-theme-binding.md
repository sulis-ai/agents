# ADR-002 — Monaco editor theme binds to the active app theme

> Status: accepted · Date: 2026-06-07 · Change: CH-01KTHP

## Context

Monaco (the code + diff viewer) is hardcoded `theme="vs-dark"` in both
`MonacoFileInner.tsx` and `MonacoDiffInner.tsx`. Today that produces a dark
editor inside a light app — the exact "dark code in a light app" mismatch
the spec calls out. Monaco is **not** styled by CSS custom properties; it
renders into its own canvas/DOM and takes a `theme` prop with a Monaco theme
id. So Monaco cannot ride the `[data-theme]` cascade — it must be told which
theme to use explicitly.

## Decision

Both Monaco wrappers **read the active app theme from `useTheme()`** and pass
the corresponding Monaco built-in theme id:

| App theme | Monaco theme id |
|---|---|
| dark | `vs-dark` (Monaco's built-in dark) |
| light | `vs` (Monaco's built-in light) |

The mapping is a single shared helper (e.g. `monacoThemeFor(theme)`) so both
wrappers and any future Monaco surface use one source of truth. When the
founder flips the toggle, the context value changes, the wrappers re-render,
and Monaco receives the new `theme` prop — the editor restyles live, with no
remount.

## Why the built-in Monaco themes (CP-01)

`vs` and `vs-dark` are Monaco's **shipped, established** light/dark themes —
the boring, zero-maintenance choice. They are well-contrasted and familiar
(they are VS Code's defaults). Authoring a custom Monaco theme to colour-match
the cockpit tokens exactly is possible but is out of scope: the spec is
"colours only, follow the active theme," not "pixel-match the editor to the
brand palette." A custom Monaco theme is recorded below as a deliberately
deferred enhancement.

## Alternatives considered and rejected

- **Keep `vs-dark` always; only theme the app chrome.** Rejected — it is the
  current bug; the spec's whole point is no light-app/dark-code mismatch.
- **Author a custom Monaco theme from the cockpit tokens** (define editor
  token colours from `--background`, `--foreground`, etc.). Rejected for now:
  more surface area, more to maintain, and not required by the spec. Deferred
  as a future enhancement; recorded so it is a conscious deferral, not an
  omission.
- **Drive Monaco from a CSS variable.** Not possible — Monaco does not read
  page CSS variables for its editor colours; it requires a theme id or a
  registered theme object.

## Consequences

- `MonacoFileInner.tsx` and `MonacoDiffInner.tsx` each change one line: the
  hardcoded `theme="vs-dark"` becomes `theme={monacoThemeFor(theme)}` where
  `theme` comes from `useTheme()`.
- Existing read-only guarantees (ADR-001/ADR-006 in the cockpit's own TDD,
  `options.readOnly === true`) are untouched — only the `theme` prop changes.
- The existing `MonacoFile.test.tsx` / `MonacoDiff.test.tsx` assertions on
  `readOnly` continue to hold; a new assertion covers theme-follows-app.
