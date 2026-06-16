# WP-004 — Full-height lanes: sticky header, internal scroll, independent per lane

- **Sequence ID:** WP-004
- **dependsOn:** []
- **kind:** frontend
- **primitive:** REORGANISE-Refactor (`StageColumn`, `Board` layout)
- **group:** reorganise
- **characterisation_test:** `client/src/tests/Board.test.tsx` + `tests/StageColumn.test.tsx` (pin current async states, card grouping, count rendering)
- **Estimated token cost:** input ~16k / output ~7k
- **visual_contract:** production-approved (`MOCKUP.html` — `.lane` / `.laneHead` / `.laneList`)

## Context

TDD §1 (Client) + IDEAS.md Concern 1. Each stage column becomes a full-height
lane: sticky `laneHead`, internal-scroll `laneList`, the whole board no longer
scrolls as one page — each lane scrolls on its own. An optional `laneFoot`
"Start here" hint renders under **Recon only** (the rest have no foot).

## Contract

- `StageColumn.tsx` + `.module.css`: `laneHead` (dot + name + count) is
  `position: sticky; top: 0`; `laneList` is the internal scroll container,
  keyboard-reachable (tabbable), focus never trapped. The lane stays a labelled
  region (`aria-label="Recon — N changes"` preserved).
- `Board.module.css`: the board is a full-viewport-height row of equal-height
  lanes (desktop); lanes fill top-to-bottom regardless of card count (kills the
  ragged short-lane dead space).
- Recon lane only: a quiet `laneFoot` with a "Start here" secondary affordance
  (outline style, `:focus-visible` ring) → `/start`. Other lanes: no foot.
- Card internals are **out of scope** here (WP-005); this WP is layout only.

## Definition of Done

### Red
- [ ] Characterisation tests (`Board.test.tsx`, `StageColumn.test.tsx`) pin the
      three async states, grouping into six columns, and counts — pass before.
- [ ] New test: each lane header is sticky-positioned and the lane region label
      is preserved; the Recon lane (and only Recon) renders the "Start here"
      affordance. **Fails.**

### Green
- [ ] Full-height lanes implemented; per-lane internal scroll; Recon-only foot.
- [ ] jest-axe on `StageColumn` passes in **light and dark**.

### Blue
- [ ] No card-internal markup changed (WP-005 owns that).
- [ ] Tokens only — no literal hex/px-colour; spacing via tokens.
- [ ] Characterisation tests still green.

> **Empty-lane note (AF-2 / S-12):** the lane's existing `colEmpty` "Nothing here
> yet" note + count `0` is **kept** and now lives inside the full-height lane —
> assert a zero-change lane still renders full-height with its sticky header,
> count `0`, and the note. This WP owns the desktop empty-lane render; the mobile
> empty-lane snap (S-13) is WP-008's.

## Definition of Done — requirements & scenarios

- **Satisfies:** UC-1's full-height-lane hop (FR layout); AF-2 (empty lane);
  the lane half of NFR-RESPONSIVE-1 desktop; NFR-A11Y-1 (lane axe).
- **Makes pass:** **S-1** (six lanes render full-height with sticky headers —
  layout side), **S-12** (empty lane renders full-height with count `0` +
  "Nothing here yet").

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/StageColumn.test.tsx
```
