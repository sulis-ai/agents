# Cockpit Board Refresh — Software Requirements Document

> **Change:** CH-084CAN · `change/feat-cockpit-board-refresh` · `feat`
> **Method:** outside-in (journeys first; requirements derived to make each hop true).
> **Grounding:** every requirement cites the real code or the signed-off design.
> **Visual contract:** `.design/cockpit-board-refresh/MOCKUP.html` + `IDEAS.md` (founder-approved).
> **Status:** retrofit spec — the design went straight to a build plan; this fills the requirements gap so the plan (`.architecture/cockpit-board-refresh/`) can be revised off a complete spec.

## Summary

The board is six lanes (Recon → Specify → Design → Implement → Review → Ship) the
founder reads to triage everything in flight. This refresh makes the lanes full-height
with internal scroll, redesigns the change card around a single at-a-glance triage
verdict per card, revives a "Start something new" front door, fixes dark-mode surface
elevation at the token level, and makes the board work on tablet and phone.

The refresh adds **three derived reads** to each card — *waiting on you*, *change-health*,
and a *liveness probe + recency* — and the whole spec turns on one founder rule: **the
card foot shows exactly one verdict** — a loud full-width "Waiting on you" **or** a quiet
health badge, **never both**.

Most of the board already exists and works (the feed, the six-lane layout, the
liveness probe, the attention predicate, the stage-filter chips, the start-from-intent
flow). The genuinely new surface is small and named explicitly in [§9 Existing-vs-Gap](#9-existing-vs-gap-map).
The sharpest new requirements are the **unknown / degraded states** the design never drew
(health-unknown, liveness-unknown, no-recency, partial enrichment, feed failure), because
the design only specified the healthy On/Off-track + Working/Live/Idle ends.

Identifiers: journeys `J-NN`, use cases `UC-NN`, functional requirements `FR-NN`,
business rules `BR-NN`, non-functional requirements `NFR-NN`, misuse cases `MUC-NN`,
alternate card states `CS-N` (§7c), open founder decisions `Q-NN`. Verifiable scenarios live in
[`SCENARIOS.md`](SCENARIOS.md); the existing-vs-gap headline in
[`EXISTING_VS_GAP.md`](EXISTING_VS_GAP.md).

---

## 1. Actors

| Actor | Description |
|---|---|
| **Founder** | The single human user. Opens the cockpit, triages the board, starts changes, reads health. The only direct actor. |
| **Cockpit client** | The React SPA (`apps/cockpit/client`). Renders the board, polls the feed, lays out responsively. |
| **Cockpit server** | The Express read seam (`apps/cockpit/server`). Lists changes, scopes to the active Product, derives liveness / attention / health, enriches the feed. **Read-only — no write path.** |
| **Change store / worktrees (read source)** | The on-disk truth the server reads best-effort: `session.json` (liveness), `.architecture/**/BLOCKER-*.md` (blocked), transcripts (last-turn shape), stage artifacts (rigor-for-stage), CI/test state. |

There is **no adversarial human actor** in the normal sense — the cockpit is a
single-founder, localhost, read-only tool. The relevant "abuse" surface is
**malformed / pathological data** from the change store (see [§8 Misuse](#8-misuse--abuse)).

---

## 2. The journeys (outside-in)

Each journey starts at the founder's first action and ends at a **final observable
result**. The requirements in §4–§7 are derived to make every hop true.

| ID | Journey | First action → final observable result |
|---|---|---|
| **J-1** | Open the board | Founder opens the app → sees every in-flight change laid out in six full-height stage lanes. |
| **J-2** | Triage "which need me" | Founder scans the board → the cards waiting on them stand out (loud full-width foot) → clicks one → that change opens. |
| **J-3** | Spot drift | Founder scans the resting cards → reads each card's health verdict → finds the off-track ones. |
| **J-4** | Read "is it alive, and how stale" | Founder glances at a card's top-right → reads the probe state (working/live/idle) + the bare recency (`now`/`12m`/`6h`/`1w`). |
| **J-5** | Start something new | Founder clicks "Start something new" (or presses ⌘N / ⌘K) → lands on the start-from-intent flow. |
| **J-6** | Filter / search | Founder taps a stage chip, "Needs attention", or types in search → the same board narrows in place. |
| **J-7** | Use it on a phone | Founder opens the board at < 600px → sees one full-width lane → taps a stage chip or swipes → switches lane. |
| **J-8** | First run / empty | Founder opens the board with zero changes → sees a guide on how to start one. |

---

## 3. Glossary (the locked vocabulary)

| Term | Meaning | Also known as / not |
|---|---|---|
| **Change** | One unit of work flowing through the six stages. The wire `Change` (`apps/cockpit/shared/api-types.ts`). | NOT "ticket", NOT "card" (a *card* is the change's on-board rendering). |
| **Lane / stage column** | One of the six fixed stage containers (`StageColumn.tsx`). | "column", "lane" — same thing. |
| **Card** | A change's rendering inside a lane (`ChangeCard.tsx`). | — |
| **Foot verdict** | The single triage read at the bottom of a card: *Waiting on you* XOR *change-health*. | — |
| **Waiting on you** | The flag that a change is blocked on the founder's input. Surfaces the existing `needsAttention()` verdict. | Shares the warning vocabulary of the "Needs attention" filter — same idea, two surfaces. |
| **Change-health** | A per-change verdict — *On track* / *Off track* (and a deferred *Worth a look*) — derived from tests + rigor-for-stage. NEW. | NOT activity volume; NOT a diff size. |
| **Liveness probe** | The top-right dot whose fill/motion/shape encodes the session state: **Working** (pulsing), **Live** (solid), **Idle** (hollow). | Extends the existing binary `liveness`. |
| **Recency** | The bare relative time beside the probe (`now` / `12m` / `6h` / `1w`). NEW (needs `lastActivityAt`). | — |
| **Rigor-for-stage** | Does the change have the artifacts it should for its stage (spec before design, design/plan before implement, tests with code). NEW server read. | — |
| **Enriched feed** | `GET /api/changes` widened to carry `needsAttention`, `health`, `lastActivityAt` per row (ADR-002). | NOT a new endpoint. |

---

## 4. Use cases — primary flows

### UC-1 — Open the board (J-1)

- **Actor:** Founder.
- **Precondition:** Cockpit server is reachable; an active Product is resolved server-side.
- **Trigger:** Founder navigates to the board route (`/`).
- **Main flow:**
  1. Client fetches `GET /api/changes` (scoped to active Product) via `useChangesWithLiveness` — **exists** (`useChangesWithLiveness.ts`).
  2. Server lists records, scopes to the active Product, and enriches each row with liveness + `needsAttention` + `health` + `lastActivityAt` (**enrichment is NEW**, per ADR-002; liveness + scope **exist**).
  3. Client groups the scoped set into the six fixed lanes (`groupChangesByStage`) — **exists**.
  4. Each lane renders full-height: sticky header (dot + name + count) + internally-scrolling card list — **NEW layout** (`StageColumn` today is content-height).
  5. Each change renders as a card with the new shape (§5).
- **Postcondition:** The founder sees every in-flight change in its lane; shipped changes are excluded (FR-15); the board fills the viewport.

### UC-2 — Triage "which need me" (J-2)

- **Trigger:** Founder scans the board.
- **Main flow:**
  1. For each change the server has already computed `needsAttention.flagged` + `reason` (lift the existing `needsAttention()` onto the feed — **logic exists**, surfacing is NEW).
  2. A flagged card renders the **full-width centered "Waiting on you — <why>"** foot (BR-1), making it stand out by weight in any lane.
  3. Founder clicks the card → navigates to `/c/:changeId` (**exists** — the card is already a `<Link>`).
- **Postcondition:** The change opens; the founder knows *what kind* of input is owed (the `why`) before opening.

### UC-3 — Spot drift via health (J-3)

- **Trigger:** Founder scans resting (non-waiting) cards.
- **Main flow:**
  1. Server derives `health` per change from `{ testsState, rigorForStage }` via `computeHealth` (**NEW pure fn**, ADR-001).
  2. A **non-flagged** card renders the health badge: word + shape (check = On track / warning = Off track; dash = Worth a look, deferred) (BR-1, BR-2).
  3. Founder reads the badges across resting cards and finds the off-track ones.
- **Postcondition:** The founder can see which changes are drifting without opening them.

### UC-4 — Read liveness + recency (J-4)

- **Trigger:** Founder glances at a card's top-right.
- **Main flow:**
  1. Server reports `liveness` (running / not-running / unknown — **exists**) and `lastActivityAt` (**NEW** ISO timestamp).
  2. The probe renders by **fill / motion / shape**: pulsing (Working) / solid (Live) / hollow (Idle), never colour, never a word (BR-3).
  3. The bare relative time renders beside it (`now` / `12m` / `6h` / `1w`), derived client-side from `lastActivityAt`.
- **Postcondition:** The founder reads "is anything running here, and how stale" in one glance.

### UC-5 — Start something new (J-5)

- **Trigger:** Founder clicks "Start something new" in the top bar, or presses ⌘N / ⌘K.
- **Main flow:**
  1. The top-bar button (and the hotkey) navigate to the start-from-intent flow (**the flow exists** — `StartFromIntent.tsx`, the `/start-from-intent` route mounted in `server/app.ts`; the **button + hotkey are parked components to revive**, ADR-003).
  2. The founder describes the work; the existing propose→confirm flow starts a change at Recon.
- **Postcondition:** A new change exists at Recon and appears in the board's Recon lane on the next poll. **The button navigates; it never mutates** (BR-7).

### UC-6 — Filter / search (J-6)

- **Trigger:** Founder types in search, taps a stage chip, or taps "Needs attention".
- **Main flow (all exist — `SearchBar.tsx`, `useSearch`, `searchChanges.ts`):**
  1. The board owns the filter state; the toolbar is controlled.
  2. When any filter is active, the board renders `GET /api/search` results in the **same** six-lane layout (ADR-005), never a separate screen.
  3. Clearing every filter restores the full board.
- **Postcondition:** The same board narrows in place; zero matches shows an empty (but still six-lane) board, not the first-run state (BR-5).

### UC-7 — Use it on a phone (J-7)

- **Trigger:** Founder opens the board at < 600px.
- **Main flow (NEW — responsive, ADR-004):**
  1. The board becomes a horizontally-snapping track of one-lane-wide panels.
  2. The existing stage chips become an ARIA `tablist` lane switcher; the active chip is the selected tab; each chip shows its lane's count.
  3. Tapping a chip snaps that lane into view; swiping moves between lanes and the selected chip follows.
  4. "Needs attention" stays in the rail as a toggle; search collapses to an icon target.
- **Postcondition:** One stage at a time, full width, with the chips as the switcher — same cards, same tokens.

### UC-8 — First run / empty board (J-8)

- **Trigger:** Founder opens the board with zero in-flight changes (and no filter active).
- **Main flow:** The board renders `<EmptyState>` guiding how to start one (**exists**).
- **Postcondition:** The founder is told how to begin. (Open decision Q-3: should the revived Start button replace the CLI-string guide here?)

---

## 5. The redesigned card — structure & rules

Every card has the **identical** structure top-to-bottom, so the founder reads each
signal in the same place on every card:

```
top line:   [CH-handle (left, muted)]            [probe dot ● + recency (right)]
step dots:  · N/6
intent:     <one-line summary, clamped>
slug:       <slug>
foot:       EITHER  full-width centered  ▲ Waiting on you — <why>
            OR      left-aligned          ✓ On track   /  ▲ Off track  /  – Worth a look
```

- **FR-20** The card top line carries the `CH-XXXXXX` handle (small, muted) on the left and the probe + recency on the right. *(Today: handle left + StageBadge right — `ChangeCard.tsx`. Change: drop the StageBadge, add probe+recency.)*
- **FR-21** The card drops the stage-name pill entirely (the lane already says the stage). The slim `· N/6` step dots are kept. *(Today: `StageBadge` shows "RECON · 1/6".)*
- **FR-22** The card foot renders **exactly one** of: the Waiting element, or the health badge (BR-1).
- **FR-23** The full `CH-…` handle and intent stay on the card link's accessible name: `aria-label="Open CH-… : <intent>"` *(today's aria-label is preserved and extended — `ChangeCard.tsx` line 39)*.
- **FR-24** Whichever foot read is shown, its trailing `why` / `reason` text truncates first and never wraps.
- **FR-15** Shipped (terminal-stage) changes are excluded from the board — only in-flight changes render. *(Today: `Board.tsx` / `groupChangesByStage` already exclude shipped; preserved.)*
- **BR-7** The "Start something new" button (and the ⌘N/⌘K hotkey) **navigate** to the start-from-intent flow and never mutate state directly — the change-start act happens only inside that confirm-gated flow (UC-5). The board introduces no write path.

### Business rules

- **BR-1 (the load-bearing rule).** A card shows **Waiting on you** when `needsAttention.flagged === true`, in which case health is **hidden**. Otherwise it shows the **health** badge. Never both, never neither (a non-flagged card always shows *some* health verdict — including an unknown one, FR-31). Enforced as a single branch in `ChangeCard`, asserted mutually-exclusive in the DOM.
- **BR-2 (health weight).** Waiting is **full-width, centered, heavier** (1.5px warning border, bold label, triangle icon). Health is **quieter, left-aligned, content-width** (1px border, word + shape).
- **BR-3 (no colour-alone).** Every signal is carried by **word + shape/icon** (health, waiting) or **fill/motion/shape + an SR label** (probe) — never colour alone (WCAG 1.4.1). Colour is reinforcement only.
- **BR-4 (recency thresholds).** Recency renders from `lastActivityAt`: `now` (< 60s while Working), then `Nm` / `Nh` / `Nd` / `Nw`. *(Open decision Q-2: exact buckets.)*

---

## 6. Change-health derivation (NEW — the most ambitious signal)

- **FR-30** The server derives `health: { state, reason }` per change via a **pure** `computeHealth({ testsState, rigorForStage })` (ADR-001). `state ∈ { on-track, off-track, worth-a-look }`; the producer emits only `on-track | off-track` until the OODA-spiral drift signal lands (deferred, `health-drift-ooda-signal`).
- **BR-10** **Off track** when `testsState === "red"` **OR** a required-for-stage artifact is missing. **On track** otherwise. *(ADR-001.)*
- **FR-31 (health-unknown — the sharpest gap, NEW).** When the change has **no CI/test state recorded AND rigor-for-stage cannot be determined** (e.g. a brand-new Recon change with no artifacts and no test run yet), health resolves to a **`unknown` read**, not falsely "On track" and not "Off track". The card shows a neutral, honest "Health unknown" / "Not enough signal yet" badge (word + neutral shape), and `health.reason` says why ("no tests run yet", "too early to tell"). *(The design only drew On/Off track; this state must exist so a fresh change does not masquerade as healthy.)*
- **BR-11 (degrade gracefully — MUST).** Health derivation is **best-effort, read-only, never-throws**, mirroring `detectOpenBlocker`'s discipline. A missing worktree, missing artifact dir, or unreadable CI state resolves to the `unknown` read (FR-31) — **never** an exception, and **never blocks the feed** (A-1 in TDD). The board must never 500 because one change's health could not be derived.
- **FR-32** `health.reason` is drawn from a fixed, enumerable set of plain-English strings ("tests failing", "no design recorded", "no tests run yet") and **never echoes transcript or reply text** (NFR-SEC carry-over).
- **BR-12 (rigor-for-stage rule, NEW).** The per-stage required-artifact rule: Specify⇒spec exists; Design⇒spec exists; Implement⇒a design or plan exists; Review/Ship⇒tests exist alongside code. Absence of a required artifact pulls health to Off track. Recon has no required artifact (so a Recon change is never Off-track on rigor alone — only tests can pull it down).

---

## 7. Liveness + recency derivation (NEW sub-states)

- **FR-40** The feed carries `liveness` (existing union: running / not-running / unknown) **and** a NEW `lastActivityAt: string | null` (ISO) used both for the recency text and to split Working from Live.
- **BR-13 (the three probe states).** **Working** = session running **AND** `lastActivityAt` within a short freshness window (e.g. < 60s) → pulsing dot, recency `now`. **Live** = running but quiet (last activity older than the window) → solid dot. **Idle** = not running → hollow dot. *(Open decision Q-1: the freshness window.)*
- **FR-41 (liveness-unknown, NEW).** When `liveness.status === "unknown"` (no session record / malformed / no pid — all already produced by `probeLiveness`), the probe renders a **distinct unknown shape** (e.g. a dotted/ghost ring), not a hollow "Idle" dot and not a filled dot. Its SR label says "liveness unknown". *(The design drew only Working/Live/Idle; unknown must be visually distinct so the founder isn't told "idle" when the truth is "we can't tell".)*
- **FR-42 (no-recency, NEW).** When `lastActivityAt === null` (a legacy or never-active change), the recency text is **omitted or shown as "—"**, not rendered as "now" or a bogus age. The probe still renders its liveness state.
- **BR-14 (probe SR labels).** The probe is `aria-hidden`; an `.sr` label carries the state word ("actively working" / "session live" / "idle, not running" / "liveness unknown"), so assistive tech announces the state even though no state word is visible. Reduced-motion replaces the Working pulse with a static ring (the SR label still names it).

---

## 7a. Alternate flows (the founder named these explicitly)

| ID | Alternate flow | Required behaviour |
|---|---|---|
| **AF-1** | **Empty board** (zero in-flight, no filter) | `<EmptyState>` guide (UC-8). NOT shown when filtering (BR-5). |
| **AF-2** | **Empty lane** (a stage with zero changes) | Lane still renders full-height with its sticky header + count `0` + a quiet "Nothing here yet" note (today's `colEmpty`, kept). |
| **AF-3** | **Waiting AND off-track** at once | Waiting **wins the foot** (BR-1); the hidden health verdict moves to the card detail / hover. The foot never shows both. |
| **AF-4** | **Mobile switch to a zero-change stage** | The chosen lane snaps in, shows its sticky header + "Nothing here yet"; the chip count reads `0`; no error, no blank screen. |
| **AF-5** | **Terminal / shipped change** | Shipped changes are excluded from the board (FR-15, existing). A change that ships *during* a session disappears on the next poll — no card error. |
| **AF-6** | **A huge number of changes in a lane** | The lane's internal scroll absorbs it (full-height lane is the point). Cards virtualise or paginate only if NFR-PERF-2 is breached (see §10); default is plain internal scroll. The lane header count still reflects the true total. |

## 7b. Error / failure states (the founder named these explicitly)

| ID | Failure | Required behaviour |
|---|---|---|
| **EF-1** | **Board feed fails to load** (`GET /api/changes` errors) | The existing error box + **Retry** button renders (today's `Board.tsx` `isError` branch — kept). No partial board. |
| **EF-2** | **Partial enrichment** — some changes have health/attention, some don't | Each card degrades **independently**: a change whose enrichment fields are absent/unknown shows the unknown health (FR-31) and/or unknown liveness (FR-41); it never blocks or hides the other cards. The feed returns 200 with best-effort fields (BR-11). |
| **EF-3** | **Liveness / recency poll fails** mid-session | The 10s poll is the existing one (`LIVENESS_POLL_MS`); on a failed refetch TanStack Query keeps the **last good data** and retries on the next interval. Cards keep their last-known probe/recency; no flicker to error. The manual **Refresh** remains available. |
| **EF-4** | **Stale data** | The board is a 10s-polled read (ADR-007's one permitted poll). Data is "as of last successful poll"; the design accepts this. **No new poll** is introduced (A-3). *(Open decision Q-4: do we surface a "last updated" / stale hint, or stay silent?)* |
| **EF-5** | **One change's worktree is gone** | Its liveness → unknown, health → unknown, attention → not-flagged — all best-effort defaults (BR-11). The card renders with unknown reads; the board does not 500. |

---

## 7c. Alternate card states (the founder named these explicitly)

§5 specified the card's **content** states (waiting / on-track / off-track / unknown
health, and the three probe states). This section specifies five **alternate states** the
card can be in **regardless of its content verdict** — selection, interaction, loading,
degraded, and terminal. They are first-class: each has a rule, a trigger (when it
applies), and a verifiable scenario. Most are net-new; selected and shipped partly exist
in adjacent surfaces (the Sidebar) and are lifted onto the board card.

### CS-1 — Selected / currently-open card

- **FR-50 (selected card marker, partly exists).** When a change is open in a tab — i.e.
  the active route is `/c/:changeId` for that change — **its board card is marked as the
  selected/active one**. The marker is **not colour-alone**: it carries a non-colour
  signal (e.g. `aria-current="true"` + a persistent inset ring / left edge marker), so it
  is distinguishable in greyscale and announced by assistive tech (BR-3 carry-over).
- **BR-20 (selection source).** The selected change id is derived from the **open-tabs /
  active-route state**, never stored on the card or the feed. The board reads it the same
  way the rest of the shell does: `useMatch("/c/:changeId")` resolves `activeChangeId`
  (`WorkspaceShell.tsx` line 18–19), and tab membership is tracked in `openTabs.tsx`
  (`useOpenTabs().openChangeIds`). A card is selected when `change.changeId ===
  activeChangeId`. *(Today: the **Sidebar** already does exactly this —
  `useParams().changeId` → `active` prop on `SidebarItem` (`Sidebar.tsx` line 26, 92).
  The board card has **no** selection awareness yet — net-new on the card, existing
  pattern to reuse.)*
- **BR-21 (at most one selected).** At most one board card is selected at a time (a single
  active route). When the active route is the board itself (`/`) or any non-change route,
  **no** card is selected. Selection survives a feed re-poll (it is route-derived, not
  data-derived) (carry-over of EF-3's last-good discipline).
- **When it applies:** whenever a change is open in a tab and its card is visible on the
  board (e.g. the board tab is viewed alongside an open change, or the founder returns to
  the board with a change still open).
- **Existing-vs-gap:** **partly exists** — the route/tab selection state and the
  Sidebar's active-item treatment exist; the board **card** selection marker is net-new.

### CS-2 — Interaction states (focus / keyboard / hover / pressed)

- **FR-51 (keyboard-operable card, partly exists).** The card-as-link is **fully keyboard
  operable**: it is in the natural tab order, shows a **visible focus ring** on
  `:focus-visible`, and **Enter activates** it (opening `/c/:changeId`). *(Today: the card
  is a real `<Link>` (`ChangeCard.tsx` line 35–40), so it is already focusable, in tab
  order, and Enter-activates natively — the **visible focus ring is the net-new
  requirement**, asserted, not assumed. NFR-A11Y-5 already requires a `:focus-visible`
  ring; this FR pins it to the card specifically.)*
- **BR-22 (Enter and Space).** Activation follows the link convention: **Enter** activates
  (native anchor behaviour). **Space** is not required to activate a link by the ARIA
  link pattern and the card MUST NOT trap or swallow it; if a Space-activation is wanted
  for parity with button-like affordance it is a presentational add-on, not a
  requirement. *(The load-bearing requirement is Enter + visible focus, per the ARIA link
  role; Space is optional.)*
- **BR-23 (hover / pressed are presentational).** Hover and pressed/active styling are
  **reinforcement only** (BR-3): no signal, state, or affordance may depend on hover or
  on the pressed state alone — everything reachable on hover is also reachable by keyboard
  focus and is present without pointer input (NFR-A11Y-5 carry-over). The inner "Open
  terminal" action (when present, `ChangeCard.tsx` line 58–75) keeps its own focusable
  control and `stopPropagation`, so card-link focus and the inner button's focus are
  distinct tab stops.
- **When it applies:** every card, always (interaction is intrinsic to the card-as-link).
- **Existing-vs-gap:** **partly exists** — focusability, tab order, and Enter-activation
  are native to the `<Link>`; the **visible focus ring** and the no-hover-dependence
  assertion are the net-new pinned requirements.

### CS-3 — Loading / skeleton card

- **FR-52 (loading distinct from empty, partly exists).** The board has a **loading**
  state that is **distinct from the empty state**: *loading* = the feed has **not yet
  resolved** (`active.isLoading`); *empty* = the feed **resolved with zero** in-flight
  changes (`isSuccess && inFlightCount === 0`). The two MUST NOT be conflated — a loading
  board never shows the "start a change" empty guide, and an empty board never shows
  skeletons. *(Today: `Board.tsx` already branches `isLoading` → `board-loading`
  skeleton vs `isSuccess && inFlightCount === 0 && !filtering` → `<EmptyState>` (lines
  90–127) — the distinction **exists**; this FR pins it and tightens the skeleton to be
  **per-card**, FR-53.)*
- **FR-53 (per-card skeletons, NEW).** While loading, each lane renders **per-card
  skeleton placeholders** (a small number of card-shaped blocks), not just a single block
  per column. *(Today the skeleton is one `skeletonHead` + one `skeletonCard` per column
  (`Board.tsx` line 97–102) — net-new: render N card-shaped skeletons per lane so the
  loading board reads as "cards arriving", and so the swap to real data is shape-stable.)*
- **BR-24 (no layout jump on resolve, NEW — MUST).** When the real feed replaces the
  skeletons, there MUST be **no layout jump**: the skeleton cards occupy the same box
  metrics (width, card height/clamp, lane structure, sticky header) as real cards, so the
  swap is in-place. The lane scaffold (six lanes, sticky headers, internal-scroll
  containers) is identical in the loading and loaded states. *(Ties to NFR-RESPONSIVE-3 —
  no long-frame jank on the swap — and is the new card-level guarantee behind it.)*
- **BR-25 (reduced motion on skeletons).** Any shimmer/pulse on the skeleton respects
  `prefers-reduced-motion: reduce` — the shimmer is replaced by a static placeholder fill
  (NFR-A11Y-7 carry-over). The loading board carries `aria-busy="true"` (already present,
  `Board.tsx` line 94).
- **When it applies:** the first feed load (and any hard refetch that returns to
  `isLoading`); **not** on a background poll refetch (EF-3 keeps last-good data and never
  flickers to skeletons).
- **Existing-vs-gap:** **partly exists** — the loading/empty distinction and `aria-busy`
  exist; **per-card skeletons (FR-53) and the no-layout-jump guarantee (BR-24) are
  net-new.**

### CS-4 — Degraded / partial card

- **FR-54 (per-field degraded render, NEW).** When a change's record is **malformed or
  partial** (some fields readable, some not), its card renders **per-field**: each
  readable field renders normally; each unreadable field falls to its **unknown** read —
  health → "Health unknown" (FR-31), liveness → the distinct unknown shape (FR-41),
  recency → "—" (FR-42). The card MUST still render and **still link** to `/c/:changeId`.
  This is the **card-level composition** of the already-specified field-level unknown
  rules — a single card can be in several unknown reads at once and remain usable.
- **FR-55 (degraded notice, NEW).** A degraded card shows a **quiet, fixed-string**
  notice that some details couldn't be read (e.g. "some details couldn't be read"),
  drawn from the fixed enumerable string set (FR-32 / MUC-3) — **never** echoing the
  malformed content. The notice is reinforcement; the per-field unknown reads carry the
  primary signal (BR-3). The notice is `aria`-announced so it isn't colour-/placement-
  alone.
- **BR-26 (the board is unaffected — MUST).** A degraded card **never drops, never
  breaks the lane, and never 500s the board**: it degrades **independently** (EF-2 /
  NFR-DEGRADE-2), the rest of the board renders normally, and the feed returns 200 with
  best-effort fields (BR-11 / NFR-DEGRADE-1). A change whose worktree is entirely gone is
  the extreme case: all reads unknown, not-flagged attention, still a linking card
  (EF-5).
- **When it applies:** any change whose feed row is partially unreadable — a malformed
  `session.json`, a missing artifact dir, a gone worktree, or absent enrichment fields
  (EF-2, EF-5, MUC-1).
- **Existing-vs-gap:** the **field-level** unknown reads exist as requirements (FR-31 /
  FR-41 / FR-42 / BR-11); the **card-level** "render per-field, show a quiet notice, keep
  linking, never break the board" composition is the **net-new** state. It is the
  rendering contract that makes BR-11's never-throw discipline visible and usable on the
  card.

### CS-5 — Shipped / terminal card

- **FR-56 (shipped reads as archived, partly exists).** A change in a **terminal stage**
  (`stage === "shipped"`) reads as **archived**, not active: the card is **muted**, its
  **liveness probe is replaced by a static "Shipped" marker** (no Working/Live/Idle
  probe, no pulse), it shows **no waiting foot and no change-health foot** (the live
  triage verdicts don't apply to a shipped change), and recency reads as a **shipped
  recency** ("shipped Nd ago") rather than a live-activity age. *(Today the board
  **excludes** shipped changes entirely (FR-15, `groupChangesByStage`), so shipped cards
  do not appear on the board at all; `StageBadge` already renders `shipped` as a muted,
  name-only badge (`StageBadge.tsx` line 17–18, 42–47) and the **Sidebar** already groups
  shipped under a collapsed "Shipped" section (`Sidebar.tsx` line 41, 97–120). So the
  **archived treatment exists in the Sidebar**; whether a shipped card ever renders on
  the **board** — and if so, in this archived treatment — is the net-new question.)*
- **BR-27 (terminal detection).** "Shipped/terminal" is detected from the **change
  stage** (`stage === "shipped"`), the same predicate the Sidebar split and `StageBadge`
  already use (`Sidebar.tsx` line 41; `StageBadge.tsx` `stageLabel` treats stages outside
  the six-stage order as terminal name-only). No new terminal-detection logic is
  introduced.
- **BR-28 (no live signals on a shipped card — MUST).** A shipped card MUST NOT show any
  **live** signal: no liveness probe motion/state, no "Waiting on you", no change-health
  badge, no live recency. These are read-states for an *in-flight* change; a shipped
  change is past the workflow. The static "Shipped" marker and the shipped recency are
  the only status reads. *(This is why FR-15 excludes shipped from the in-flight board by
  default — CS-5 specifies the treatment **if and where** a shipped card is shown, e.g.
  an "include shipped" view or the moment a change ships mid-session before the next poll
  drops it, AF-5.)*
- **When it applies:** wherever a shipped change's card is rendered — the Sidebar's
  Shipped section today, and any future board view that opts to include shipped (the
  board's default still excludes them, FR-15). It also bounds AF-5: a change that ships
  mid-session is in this terminal read until the next poll removes it from the in-flight
  board.
- **Existing-vs-gap:** **partly exists** — the terminal stage, its muted badge, and the
  Sidebar's archived grouping exist; the **card-level archived treatment** (probe replaced
  by a static "Shipped" marker, no live feet, shipped recency) as a **defined card
  state** is the net-new specification. Founder-owned wording of the shipped recency is a
  new open decision (Q-7).

### Card-state precedence

When more than one alternate state is true at once, they compose by these rules (no
state silently overrides another's accessibility contract):

| Combination | Resolution |
|---|---|
| Loading (CS-3) | While loading, no real card exists yet — selection/interaction/degraded/shipped do not apply to a skeleton. Skeletons are inert (not focusable, `aria-hidden` of content). |
| Selected (CS-1) + any content/degraded/shipped state | Selection is **additive** — it adds the selected marker on top of whatever the card already shows; it never hides health, waiting, the probe, or the degraded notice. |
| Interaction (CS-2) | Always additive — focus/hover are orthogonal to every other state and never suppress a signal. |
| Degraded (CS-4) + Shipped (CS-5) | Shipped wins the **foot/probe** treatment (static "Shipped", no live feet, BR-28); any unreadable *identity* fields (handle/intent/slug) still fall to their unknown reads + the degraded notice (FR-54/55). |
| Shipped (CS-5) + Waiting/Health | Shipped suppresses both live feet (BR-28) — a shipped change shows neither "Waiting on you" nor a health badge. |

---

## 8. Misuse / abuse

The cockpit is single-founder, localhost, **read-only** — there is no auth surface, no
write path, no external call this change introduces. The real abuse surface is **bad data
from the change store** and **pathological scale**. Detailed in [`MISUSE_CASES.md`](MISUSE_CASES.md); headline:

| ID | Misuse | Required system response |
|---|---|---|
| **MUC-1** | **Malformed feed row** (a record with garbage stage, missing fields, malformed `session.json`) | The server's best-effort reads already resolve malformed inputs to safe defaults (`probeLiveness` → unknown on malformed JSON). The new reads MUST do the same (BR-11). A malformed row degrades to unknown reads; it MUST NOT throw or 500 the whole feed. |
| **MUC-2** | **Oversized / pathological change count** (hundreds of changes in one lane) | The per-record enrichment fan-out stays inside the existing bounded `Promise.all` over the in-flight set; no unbounded loop (A-1). The lane's internal scroll absorbs the count. Server MUST NOT block the feed on fan-out cost (NFR-PERF-3). |
| **MUC-3** | **`reason` text injection** — a change's transcript/content containing markup or secrets | Health `reason` and attention `reason` are drawn from a **fixed enumerable set**, never interpolated from change content (FR-32 / A-2). No transcript body reaches the board. |
| **MUC-4** | **Symlink / path escape** in a worktree read | The new rigor/tests reads MUST stay within the change's own worktree (reuse `safeJoin`'s discipline) and be read-only — no write, no process spawn (A-1, NFR-SEC). |

---

## 9. Existing-vs-Gap map

The full hop-by-hop table is in [`EXISTING_VS_GAP.md`](EXISTING_VS_GAP.md). Headline:

- **Already served by existing code:** the feed + Product scope (`changes.ts`, `_product-scope`), the liveness probe (`probeLiveness.ts`), the attention *logic* (`needsAttention.ts` + `detectOpenBlocker.ts`), the six-lane grouping (`groupChangesByStage`), the stage-filter + search + needs-attention filter (`SearchBar.tsx`, `searchChanges.ts`, `useSearch`), the card-as-link navigation (`ChangeCard.tsx`), the empty state (`EmptyState.tsx`), the 10s poll (`useChangesWithLiveness.ts`), the start-from-intent flow (`StartFromIntent.tsx`, `/api/changes/start`).
- **Net-new (must be built):** `Change.health` + `Change.lastActivityAt` + `Change.needsAttention` on the wire (`api-types.ts` — **not present yet**); `computeHealth`, `readRigorForStage`, `readTestsState` server libs (**absent**); feed enrichment in `toWireChange` + `changes.ts`; the redesigned card (top line, single-foot-verdict, probe with three states + unknowns); `WaitingOnYou` + `ChangeHealthBadge` + `LivenessProbe` components (**absent**); full-height lanes; the revived Start button + ⌘N/⌘K hotkey (parked components to port); dark-mode token edits; responsive breakpoints + mobile tablist switcher.
- **The unknown states** (FR-31, FR-41, FR-42) are net-new **and** absent from the design — they are the spec's most important addition.
- **The five alternate card states** ([§7c](#7c-alternate-card-states-the-founder-named-these-explicitly)): **selected** (CS-1, partly exists — the route/tab selection + Sidebar active-item exist; the board-card marker is net-new), **interaction** (CS-2, partly exists — the `<Link>` is focusable + Enter-activates natively; the visible focus ring is net-new), **loading/skeleton** (CS-3, partly exists — the loading/empty distinction + `aria-busy` exist; per-card skeletons + no-layout-jump are net-new), **degraded/partial** (CS-4, net-new card-level composition of the existing field-level unknown rules), and **shipped/terminal** (CS-5, partly exists — the muted `shipped` badge + Sidebar's archived grouping exist; the card-level archived treatment is net-new).

---

## 10. Non-functional requirements

Detailed with targets in [`NFR.md`](NFR.md). Headline measurable targets:

- **NFR-PERF-1 (board render):** the board renders the first paint of lanes + cards within **150 ms** of the feed response on a realistic in-flight set (**≤ 50 changes**), measured client-side.
- **NFR-PERF-2 (lane scale):** a single lane holding **up to 200 cards** scrolls at 60fps with no jank; beyond 200 the lane MAY virtualise (not required at ≤ 200).
- **NFR-PERF-3 (feed enrichment cost):** the added server-side per-change derivation (health + recency reads) keeps the enriched `GET /api/changes` p95 within **+50%** of today's liveness-only feed for **≤ 50 changes**, and the fan-out stays bounded (A-1). Payload growth per row is bounded (three small fields + one ISO string).
- **NFR-A11Y (accessibility, testable):** every changed/new component passes **jest-axe in both light and dark**; the board page passes **Playwright-axe at all three breakpoints**; all text labels clear **WCAG AA (4.5:1)** and graphical signals clear **1.4.11 (3:1)** against the real tokens (the IDEAS.md table is the design-time target, axe is the build-time gate); touch targets ≥ **44px** on mobile; the mobile switcher is a real ARIA `tablist`; reduced-motion replaces the pulse with a static ring.
- **NFR-RESPONSIVE:** the board re-lays-out correctly at the three breakpoints (≥1100 / 600–1099 / <600) with no horizontal overflow of the top bar at **390px**; lane switch and breakpoint change produce no layout jank.
- **NFR-DEGRADE (MUST):** every derived read is best-effort and never-throws; a single bad record degrades to unknown reads and never 500s the feed (BR-11).
- **NFR-POLL:** exactly **one** 10s feed poll (ADR-007's permitted exception); no second poll, no N+1 per-card request (A-3).

---

## 11. Founder-owned open decisions

These are genuinely the founder's to settle (not derivable from design + code). Collected in [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md):

- **Q-1 — Working/Live freshness window.** What recency counts as "Working" (actively moving) vs a quiet "Live"? Suggested default: **< 60s = Working → `now`**. Confirm or set.
- **Q-2 — Recency buckets.** Exact thresholds for `now` / `Nm` / `Nh` / `Nd` / `Nw`. Suggested: minutes < 60m, hours < 24h, days < 7d, then weeks.
- **Q-3 — Empty-board CTA.** Should the revived "Start something new" button (now that it exists) **replace** the CLI-string guide in `<EmptyState>`, or sit beside it?
- **Q-4 — Stale-data hint.** Should the board show a quiet "updated Ns ago" / stale indicator when a poll fails, or stay silent and just keep last-good data (current behaviour)?
- **Q-5 — Health-unknown wording.** The exact label for the new unknown-health state ("Health unknown" / "Too early to tell" / "No signal yet") — a founder-voice call.
- **Q-6 — Lane-overflow policy.** At what change-count (if any) does a lane switch from plain internal scroll to virtualisation/pagination? Default: plain scroll to 200, then revisit.
- **Q-7 — Shipped-card recency wording (CS-5 / FR-56).** The exact phrasing for a shipped change's static recency. Default: **"shipped Nd ago"**. Confirm or reword.

---

## 12. Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

The architecture's TDD §6 already carries a populated Verification Plan; this spec's plan
aligns to it and adds the **unknown/degraded-state** verification the design omitted.

### What user-observable behaviour are we verifying?
A founder opening the board sees full-height internally-scrolling lanes; cards with the
new top line and a single foot verdict (loud Waiting XOR quiet health, never both); a
probe + recency top-right that reads working/live/idle and how stale; a working Start
button (and ⌘N); correct re-layout at tablet and phone with the chips switching lanes;
three distinct dark-mode elevations. **And** — critically — a fresh/degraded change shows
**honest unknown reads** (health-unknown, liveness-unknown, no-recency) rather than
masquerading as healthy, and a single bad record never breaks the board.

### Verification environment(s)
Local (Vitest + RTL + jest-axe in `apps/cockpit`) and CI (same + Playwright / Playwright-axe).
Component + feed tests run against the in-memory `FakeChangeStoreReader` — no real
worktrees needed.

### Bootstrap-from-zero case
A fresh clone at the merge SHA builds the cockpit workspace, then runs the `apps/cockpit`
Vitest + Playwright suites green with the board rendering against `FakeChangeStoreReader`
seeded with: at least one waiting change, one off-track change, one healthy change, **one
health-unknown change, one liveness-unknown change, one no-recency change**, and one empty
lane — so the unknown/degraded states are exercised from zero.

### Per-integration verification strategy

| Integration | Strategy | Classification |
|---|---|---|
| Enriched `GET /api/changes` | in-memory `FakeChangeStoreReader`; assert the three new fields present + degrade to unknown on absence | existing adapter |
| `needsAttention()` onto the feed | reuse the existing pure fn + tests; new feed test asserts wire-through | existing |
| `computeHealth` | pure-fn unit test — every `{testsState, rigorForStage}` combo → state + reason, **including the unknown combination** | new (pattern existing) |
| `readRigorForStage` / `readTestsState` | temp-dir fixture; best-effort + **absence → unknown** path asserted (mirrors `detectOpenBlocker.test.ts`) | new (pattern existing) |
| Start button + ⌘N/⌘K | RTL + jsdom keydown (ported tests) | existing (ported) |
| Responsive + mobile tablist | Playwright at 3 viewports + Playwright-axe | existing pattern |

### Per-kind verification adapter
`kind: frontend` (dominant) → RTL/Vitest component specs + jest-axe (light AND dark) +
Playwright(-axe) page specs. `kind: backend` (feed slice) → `*.test.ts` against the fake +
pure-fn unit tests.

### Infrastructure needs surfaced (deferred)
- `health-drift-ooda-signal` — the scope-drift + "Worth a look" inputs consume
  `change-stage-ooda-spiral`'s drift signal (ADR-001). Deferred; the wire type already
  carries the third state so no re-layout is needed when it lands.
</content>
</invoke>
