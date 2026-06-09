# WP-003 — Apply the dark-mode token changes to `tokens.css`

- **Sequence ID:** WP-003
- **dependsOn:** []
- **kind:** frontend (design tokens)
- **primitive:** REORGANISE-Refactor (token values)
- **group:** reorganise
- **characterisation_test:** `client/src/tests/tokens.dark.test.ts` (asserts current dark token values before the change — proves the edit landed)
- **Estimated token cost:** input ~9k / output ~3k
- **visual_contract:** production-approved (`.design/cockpit-board-refresh/MOCKUP.html`)

## Context

TDD §3 + IDEAS.md "Dark-mode token changes". Pure token edits in
`apps/cockpit/client/src/tokens.css`: dark `:root[data-theme="dark"]` elevation
+ amber, plus one **light** `--warning` darken. The mockup carries every value
verbatim. No component CSS invents a hex.

## Contract

Exactly the edits in TDD §3 (transcribe the three tables). Dark block:
`--background`→`#121419`, `--muted`→`#1b1e24`, `--card`→`#262a32`,
`--border`/`--input`→`#3a3f4a`, `--popover`→`#2b3038`, `--secondary`→`#2f343d`,
`--shadow-float`→`…0.55)`; dark `--warning`→`#ffb627`, `--bg-warning` mix 18→24%,
`--bg-warning-border` mix 45→60%. Light: `--warning`→`#B45309`.

If `DESIGN_TOKENS.json` exists upstream, mirror the same values there
(single source of truth).

## Definition of Done

### Red
- [ ] `client/src/tests/tokens.dark.test.ts` reads the computed/declared values
      and asserts the **new** values (page < lane < card elevation ordering:
      `--card` lighter than `--muted` lighter than `--background`). **Fails**
      against the current (inverted) values.

### Green
- [ ] Token values updated to the TDD §3 tables; test passes.
- [ ] Light mode untouched except the single `--warning` darken.

### Blue
- [ ] Grep: no component CSS file carries a literal hex from these tables (every
      value rides the token).
- [ ] If `DESIGN_TOKENS.json` is present, its dark block matches `tokens.css`.

## Definition of Done — requirements & scenarios

- **Satisfies:** TDD §3 dark elevation tokens; NFR-A11Y-3 (the dark-mode
  contrast half).
- **Makes pass:** **S-31** (dark elevation reads as three distinct layers:
  page → lane → card, card lightest; the luminance-ordering assertion passes
  against the tokens).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/tokens.dark.test.ts
```
