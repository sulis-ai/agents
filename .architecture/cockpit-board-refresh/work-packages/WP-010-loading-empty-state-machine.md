# WP-010 — Loading/empty state machine: per-card skeletons + no-layout-jump + first-run

- **Sequence ID:** WP-010
- **dependsOn:** [WP-004, WP-005]
- **kind:** frontend
- **primitive:** REORGANISE-Refactor (`Board` loading/empty branches) + EXPAND-Create (per-card skeleton component)
- **group:** reorganise
- **characterisation_test:** `client/src/tests/Board.test.tsx` (pins the current `isLoading` skeleton vs `isSuccess && empty` → `<EmptyState>` branches before tightening them)
- **Estimated token cost:** input ~14k / output ~6k
- **visual_contract:** production-approved (`MOCKUP.html` — skeleton card + empty guide)

## Context

SRD §7c CS-3 + AF-1 + UC-8. The board's loading state must be **distinct from**
its empty state, render **per-card skeletons** (not one block per column), and
the swap from skeleton → real data must produce **no layout jump** (BR-24 /
NFR-PERF-5). Depends on WP-004 (the lane scaffold the skeletons sit in) and
WP-005 (the real card box metrics the skeleton must match). This WP also pins the
first-run empty render (S-9).

## Contract

- **Loading ≠ empty (FR-52).** *loading* = feed not yet resolved (`isLoading`);
  *empty* = feed resolved with zero in-flight changes (`isSuccess &&
  inFlightCount === 0 && !filtering`). A loading board **never** shows the
  "start a change" guide; an empty board **never** shows skeletons. (The branch
  exists in `Board.tsx` today — this WP pins and tightens it.)
- **Per-card skeletons (FR-53, NEW).** While loading, each lane renders **N
  card-shaped skeleton placeholders** (a small fixed count), not a single block
  per column. The lane scaffold (six lanes, sticky headers, internal-scroll
  containers) is **identical** in loading and loaded states.
- **No layout jump (BR-24 / NFR-PERF-5 — MUST).** Skeleton cards occupy the
  **same box metrics** (width, card height/clamp, lane structure, sticky header)
  as real cards, so the swap is in-place: zero card box moves; Cumulative Layout
  Shift contribution ≈ 0; no long-frame > 50 ms on the swap.
- **Reduced motion (BR-25).** Any shimmer respects `prefers-reduced-motion:
  reduce` → static placeholder fill. The loading board carries `aria-busy="true"`
  (already present). Skeletons are **inert** (not focusable, content
  `aria-hidden`) per the §7c precedence table (no real card exists yet).
- **First-run empty (AF-1 / UC-8 / S-9).** Zero changes + no filter → the
  `<EmptyState>` guide renders and the six-lane board does not. (Q-3 default:
  the revived Start button sits **beside** the CLI hint — wire the button in if
  WP-006 has landed; otherwise the existing guide stands.)
- **Applies on first load only.** Not on a background poll refetch — EF-3 keeps
  last-good data and never flickers to skeletons (asserted in WP-007; this WP
  asserts the skeleton path is *not* re-entered on refetch).

## Definition of Done

### Red
- [ ] Characterisation `Board.test.tsx` pins the current loading vs empty
      branches → passes before.
- [ ] `client/src/tests/Board.loading.test.tsx`:
  - feed pending → **per-card skeletons** render (not the empty guide), board
    carries `aria-busy`; skeletons are inert (**S-34** part 1).
  - on resolve with real changes, real cards replace skeletons with **no layout
    jump** — same lane scaffold + card box metrics; a PW spec asserts no card box
    moves, CLS ≈ 0, no long-frame > 50 ms (**S-34** part 2 / **NFR-PERF-5**).
  - a forced background refetch does **not** re-enter the skeleton path.
  **Fails** (skeletons are per-column, no box-metric guarantee).
- [ ] `client/src/tests/Board.empty.test.tsx`: zero changes + no filter →
      `<EmptyState>` renders, six-lane board does not; loading never shows the
      guide (**S-9 / AF-1**). **Fails / under-asserted.**

### Green
- [ ] Per-card skeletons implemented sharing the real card's box metrics; the
      loading/empty distinction tightened; both tests pass.
- [ ] jest-axe on the loading board (light + dark); reduced-motion path covered.
- [ ] PW layout-shift trace across pending→resolved passes (no box moves).

### Blue
- [ ] Skeleton shares the card's box CSS via tokens (no duplicated magic
      dimensions — the box metrics are one source of truth, EP-03).
- [ ] No literal px colour; shimmer via token; static fill under reduced motion.
- [ ] Characterisation test still green.

## Definition of Done — requirements & scenarios

- **Satisfies:** CS-3 (FR-52, FR-53, BR-24, BR-25), AF-1, UC-8; NFR-PERF-5,
  NFR-A11Y-1, NFR-A11Y-7.
- **Makes pass:** **S-9** (first-run empty board), **S-34** (loading shows
  per-card skeletons, then no jump on resolve).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/Board.loading.test.tsx
```
