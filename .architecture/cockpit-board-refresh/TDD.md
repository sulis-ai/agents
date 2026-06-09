# Cockpit Board Refresh — Technical Design

> **Change:** CH-084CAN · `change/feat-cockpit-board-refresh` · `feat`
> **Tier:** M (see `SIZING.md`) · **Mode:** brownfield refresh
> **Visual contract:** `.design/cockpit-board-refresh/MOCKUP.html` —
> **production-approved** (founder signed off; no new visual-contract WP).
> **Design rationale:** `.design/cockpit-board-refresh/IDEAS.md`.

This TDD realises the signed-off mockup. The mockup is the contract; this
document specifies *how* the implementation lands it against the real code,
not *whether* it should look that way (that is decided).

---

## 0. What we're building (outcomes)

Six changes the refresh delivers, all per the signed-off design:

1. **Full-height lanes** — each stage column fills the viewport: sticky header,
   internal scroll, independent per lane (no single page scroll).
2. **Redesigned change card** — top line `handle · probe+time`; slim `·N/6` step
   dots; intent; slug; a **single foot verdict** — full-width centered "Waiting
   on you — why" XOR a quieter left-aligned change-health badge, **never both**.
   No stage-name pill, no top banner, no left colour stripe.
3. **Change-health signal (cheap first step)** — On track / Off track from
   **tests (CI state)** + **rigor-for-stage**. "Worth a look" and scope-drift
   are deferred to the OODA-spiral signal (ADR-001).
4. **Attention + health on the board feed** — surface the existing
   `needsAttention()` verdict and the new health read on the board list, by
   enriching the one feed (ADR-002).
5. **Revive "Start something new"** — port the parked, reviewed top-bar button +
   ⌘N/⌘K hotkey + cold-start chips (ADR-003).
6. **Dark-mode token changes + responsive** — the explicit `tokens.css` dark
   edits from IDEAS.md; three responsive breakpoints with a stage-chip lane
   switcher on mobile (ADR-004).

---

## 1. Form — Structural Integrity

**Fully covered by the existing cockpit architecture — referenced, not
restated.** The board follows the established hexagonal structure: a
typed-client seam on the client (no `fetch` in components, WPF-02), the
`ChangeStoreReader` port on the server (the one and only path to the change
store, ADR-008), the six-column board IA (ADR-005), and server-side Product
scope (ADR-009). None of that changes.

**New / modified components only** (the delta this change introduces):

### Server (`apps/cockpit/server/`)

| Component | Move | Notes |
|---|---|---|
| `lib/computeHealth.ts` | **EXPAND-Create** (new pure fn) | `{ testsState, rigorForStage } → { state: "on-track" \| "off-track" \| "worth-a-look", reason }`. Emits only the first two until the OODA signal lands (ADR-001). Pure, no I/O. |
| `lib/readRigorForStage.ts` | **EXPAND-Create** (new read) | Best-effort, read-only check of the change worktree for the artifacts a stage should have. Mirrors `detectOpenBlocker`'s discipline: never throws on absence. |
| `lib/readTestsState.ts` | **EXPAND-Create** (new read) | Best-effort read of the change's CI / test state (green/red/unknown) from the change's own recorded signals. Never throws. |
| `routes/_change-lookup.ts` (`toWireChange`) | **REORGANISE-Refactor** | Gains the attention + health + last-activity enrichment. Characterisation test first (it has consumers: list + detail + search). |
| `routes/changes.ts` | **SUBSTITUTE-none / wire-through** | Gathers the same cheap signals the status route gathers (open-blocker probe, last-turn shape) and passes them into the enriched `toWireChange`. |

### Shared (`apps/cockpit/shared/api-types.ts`)

The wire `Change` interface gains three forward-compatible fields (CF-02 — the
contract is the single source of truth; producer + every consumer import them
verbatim, none redeclare):

```ts
export type ChangeHealthState = "on-track" | "off-track" | "worth-a-look";

export interface ChangeHealth {
  state: ChangeHealthState;        // producer emits only on/off-track for now (ADR-001)
  /** plain-English reason behind the verdict (e.g. "tests failing", "no design recorded"). */
  reason: string;
}

// added to interface Change:
//   needsAttention: { flagged: boolean; reason: "blocked" | "waiting-on-decision" | "stopped-mid-reply" | null };
//   health: ChangeHealth;
//   liveness: Liveness;                         // unchanged union…
//   lastActivityAt: string | null;              // …+ ISO last-activity for the relative time & working/live split
```

> **Note on `needsAttention` shape reuse.** The `{ flagged, reason }` shape is
> already defined inside `ChangeStatus.needsAttention` (api-types.ts). Lift it
> to a named `NeedsAttention` type and reuse it in both places — do not declare
> a second copy (CF-02 / DRY).

### Client (`apps/cockpit/client/src/`)

| Component | Move | Notes |
|---|---|---|
| `pages/Board.tsx` + `Board.module.css` | **REORGANISE-Refactor** | Full-height lane layout + the three responsive breakpoints (CSS-media-query-driven). Characterisation test first (`Board.test.tsx` pins the three async states + filter behaviour). |
| `components/StageColumn.tsx` + css | **REORGANISE-Refactor** | Full-height lane: sticky `laneHead`, internal-scroll `laneList`, optional `laneFoot` (Recon "Start here" hint only). Drops nothing the lane already announces. |
| `components/ChangeCard.tsx` + css | **REORGANISE-Refactor** | The whole card redesign: top line, step dots, single foot verdict (waiting XOR health). Characterisation test first (`ChangeCard.test.tsx`). |
| `components/LivenessProbe.tsx` (was `LivenessDot`) | **REORGANISE-Refactor** | Three states by fill/motion/shape (working=pulse, live=solid, idle=hollow) + an `.sr` label; `aria-hidden` dot. Reduced-motion → static ring. |
| `components/ChangeHealthBadge.tsx` | **EXPAND-Create** | word + shape (check / dash / warning) + `.sr` reason. Renders all three states; data drives which. |
| `components/WaitingOnYou.tsx` | **EXPAND-Create** | full-width centered chip: triangle icon + bold "Waiting on you" + truncating `why`. |
| `components/StageChips` (in `SearchBar`) | **REORGANISE-Refactor** | Dual role: desktop filter chips; mobile ARIA tablist lane switcher (ADR-004). |
| `components/WorkspaceTopBar.tsx` | **SUBSTITUTE-port** (ADR-003) | Revive Start button (+ responsive collapse to "+ New"). |
| `api/useStartHotkey.ts` | **SUBSTITUTE-port** (ADR-003) | ⌘N/⌘K → `/start`; mount once in `WorkspaceShell`. |
| `tokens.css` | **REORGANISE-Refactor** | Dark `:root` block edits + the light `--warning` darken — see §3. |

**Dependency direction holds:** the new server libs are pure/read-only and sit
behind the route layer; the client components consume the typed client only.
No domain → infrastructure import is introduced.

---

## 2. Armor — Operational Hardening

**Read-only refresh — most of the Armor surface is unchanged and referenced.**
The board introduces **no new write path**, **no new mutating endpoint**, **no
new external service call**, **no new secret**, and **no new service-to-service
traffic**. The start button *navigates*; it does not mutate (ADR-003 / their
ADR-001). So the classic Armor primitives (timeout/retry/circuit-breaker on
external calls, secret management, mTLS) have **nothing new to protect** here.

**The one Armor concern this change does introduce** — and the gap SIZING.md
flagged — is the discipline around the **new server-side reads** that enrich
the feed:

### A-1 — New reads are best-effort, read-only, never-throw (MUST)

`readRigorForStage`, `readTestsState`, and the open-blocker / last-turn signals
the feed now gathers per record are **filesystem / recorded-state reads**. They
MUST follow the exact discipline `detectOpenBlocker` already established:

- **Read-only** — no file written, no process started (NFR-SEC-05).
- **Best-effort** — a missing worktree, missing artifact dir, or permission
  error resolves to a safe default (`unknown` test state, `rigor ok` absent →
  not-off-track-on-absence-alone), **never throws**. A board must never 500
  because one change's worktree is gone.
- **Bounded** — the per-record fan-out runs inside the existing `Promise.all`
  over the in-flight change set (small, bounded by board size). No new
  unbounded loop. If the fan-out ever becomes hot, that is a separate
  optimisation WP (ADR-002), not a reason to change the shape now.

### A-2 — Observability discipline preserved (MUST)

The established **no-reply-body-leakage** rule (NFR-SEC-03) holds: the health
`reason` and the attention `reason` describe the *shape* of what's happening
("tests failing", "no design recorded", "waiting on a decision") and **never
echo the agent's reply text or any transcript body**. `computeHealth`'s reason
strings are a fixed, enumerable set — not interpolated from change content.

### A-3 — The 10s board poll is unchanged

The board's single 10s polling read (ADR-007's one permitted exception) stays
exactly one feed call. Enriching the feed (ADR-002) keeps it one call — it does
**not** add a second poll or an N+1 per-card request.

> Everything else in the Armor pillar (the cockpit's read-only gate, the
> existing error envelope, the typed-Result error model) is established and
> referenced, not restated.

---

## 3. Dark-mode token changes (`tokens.css`)

These are **real `tokens.css` edits**, verbatim from IDEAS.md "Dark-mode token
changes". They are **dark `:root[data-theme="dark"]` only** plus **one light
`--warning` darken**. The mockup carries every value; the WP transcribes them
to `tokens.css` (and upstream `DESIGN_TOKENS.json` if present).

**Dark `:root` — surface elevation (page → lane → card) + border:**

| Token | From | To |
|---|---|---|
| `--background` | `#16181d` | `#121419` |
| `--muted` (lane) | `#20232a` | `#1b1e24` |
| `--card` | `#1e2127` | `#262a32` |
| `--border` | `#343842` | `#3a3f4a` |
| `--input` | `#343842` | `#3a3f4a` |
| `--popover` | `#23262e` | `#2b3038` |
| `--secondary` | `#2a2e36` | `#2f343d` |
| `--shadow-float` | `0 6px 20px rgba(0,0,0,0.45)` | `0 6px 20px rgba(0,0,0,0.55)` |

**Dark `:root` — sharper waiting amber:**

| Token | From | To |
|---|---|---|
| `--warning` (dark) | `#f5b342` | `#ffb627` |
| `--bg-warning` (dark) | `color-mix(--warning 18%, --card)` | `color-mix(--warning 24%, --card)` |
| `--bg-warning-border` (dark) | `color-mix(--warning 45%, --card)` | `color-mix(--warning 60%, --card)` |

**Light `:root` — graphical-contrast fix (light-only):**

| Token | From | To |
|---|---|---|
| `--warning` (light) | `#F59E0B` | `#B45309` |

The card's dark drop-shadow reuses the existing `--shadow-float` token (no new
value). The waiting chip's `.why` uses `--foreground` (not `--text-secondary`)
in dark so it clears AA against the louder tint — a component CSS choice that
rides these tokens, not a new token.

> **Boring-code note:** every value here is a token change recorded in this
> table and the mockup. No invented one-off hex sits in any component CSS.

---

## 4. Proof — Verification Protocol

The contract-test + in-memory-adapter + jest-axe/Playwright-axe discipline is
established (WPF-06/10) — referenced. The **new** verification surface:

- **Pure-function tests** for `computeHealth` (every input combination →
  expected state + reason), `readRigorForStage` (each stage's required-artifact
  rule + the best-effort absence path), `readTestsState` (green/red/unknown +
  absence). These are unit-level, no I/O for the pure fn; the readers test
  against a temp-dir fixture.
- **Characterisation tests before each REORGANISE-Refactor** (`toWireChange`,
  `Board`, `StageColumn`, `ChangeCard`, `LivenessProbe`) — pin current
  behaviour, refactor, confirm still green. This is the MUST gate on every
  REORGANISE WP.
- **jest-axe on every changed/new component, in BOTH light and dark** — the
  card, the health badge, the waiting chip, the probe, the lane, the mobile
  switcher tablist. The mockup's AA contrast table (IDEAS.md §Accessibility) is
  the design-time target; the axe audit is the build-time gate.
- **Playwright-axe on the board page** at all three breakpoints (desktop /
  tablet / mobile), plus a journey test that the mobile stage-chip tablist
  switches lanes and that "Waiting on you" XOR health renders (never both).
- **No chaos test required** — there are no new resiliency primitives (no new
  external call, timeout, retry, or breaker). The best-effort readers' failure
  path is covered by the absence-path unit tests above.

---

## 5. The card's single-foot-verdict rule (the founder's load-bearing rule)

The foot shows **exactly one** of:

- **Waiting** (full-width, centered, 1.5px warning border, bold label, triangle
  icon, truncating why) — when `needsAttention.flagged === true`. Health hidden.
- **Health** (quieter, left-aligned, content-width, word + shape + `.sr` reason)
  — when `needsAttention.flagged === false`.

This is enforced in `ChangeCard` by a single branch (`flagged ? <WaitingOnYou>
: <ChangeHealthBadge>`), never two siblings. A test asserts the two are
mutually exclusive in the DOM. Reading order is identical on every card:
handle → probe state + time → step dots → intent → slug → the one foot verdict.

---

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

## 6. Verification Plan

> This change is `kind: frontend` (the dominant surface) with a `kind: backend`
> slice (the feed enrichment + new server reads). Per the canonical kind→adapter
> table: frontend → Vitest/RTL + Playwright(-axe) specs; backend → pytest-
> equivalent (here Vitest server tests / `*.test.ts` nodeids).

**1. User-observable behaviour being verified.** A founder opening the board
sees: full-height lanes that scroll internally; cards with the new top line +
single foot verdict; a card waiting on them shows the loud centered "Waiting on
you", others show a quiet health badge; a "Start something new" button in the
top bar (and ⌘N opens it); the board re-lays-out correctly at tablet and phone
widths with the stage chips switching lanes on mobile; dark mode reads as three
distinct elevations.

**2. Verification environments.** Local (Vitest + RTL + jest-axe, `apps/cockpit`)
and CI (same + Playwright/Playwright-axe). Monorepo: workspace deps built before
local verify (WPF-14).

**3. Bootstrap-from-zero.** A fresh clone at the merge SHA must `pnpm --filter
"@sulis/cockpit..." build` then run `apps/cockpit` Vitest + Playwright green,
with the board rendering against the in-memory `FakeChangeStoreReader` (no real
worktrees needed for the component + feed tests).

**4. Per-integration verification strategy.**

| Integration | Strategy | Classification | Concretion |
|---|---|---|---|
| Board feed read (`GET /api/changes`) enriched | in-memory adapter (`FakeChangeStoreReader`) | existing | concrete — `server/tests/changes.*.test.ts` against the fake; assert enriched fields present |
| `needsAttention()` onto the feed | reuse existing pure fn + its tests | existing | concrete — `server/tests/needsAttention.test.ts` unchanged; new feed test asserts wire-through |
| `computeHealth` | pure fn unit test | existing pattern | concrete — `server/tests/computeHealth.test.ts` |
| rigor-for-stage / tests-state reads | temp-dir fixture (best-effort + absence path) | existing pattern (mirrors `detectOpenBlocker.test.ts`) | concrete — `server/tests/readRigorForStage.test.ts`, `readTestsState.test.ts` |
| Start button + ⌘N hotkey | RTL + jsdom keydown (ported tests) | existing | concrete — `client/src/tests/WorkspaceTopBar.*.test.tsx`, `useStartHotkey.test.tsx` |
| Responsive layout + mobile tablist | Playwright (viewport) + Playwright-axe | existing | concrete — board page spec at 3 viewports |

**5. Per-kind verification adapter.** frontend → RTL/Vitest component specs +
jest-axe (light AND dark) + Playwright(-axe) page specs. backend → `*.test.ts`
nodeids against `FakeChangeStoreReader` + pure-fn unit tests.

**6. Infrastructure needs surfaced (deferred).**

- `health-drift-ooda-signal` — the scope-drift + "worth-a-look" inputs that
  consume `change-stage-ooda-spiral`'s drift signal (ADR-001). Deferred to a
  follow-on change; the wire type already carries the third state.

---

## 7. Sizing Report

- **Tier:** M (computed sFPC 9 / ASR 10 → higher band; see `SIZING.md`). Not
  overridden.
- **TDD length:** within the tier-M target (~250-400 lines); Form referenced
  rather than restated, so toward the lower end. No circuit breaker triggered.
- **ADRs:** 4 produced (tier-M range 3-5). Each records a real cross-component
  decision (health scope, feed shape, start-button revival, responsive
  switcher). No quota padding.
- **Authoritative sources referenced (not restated):** the existing cockpit
  Form architecture (ADR-005/007/008/009), `WP_FRONTEND_STANDARD`,
  `detectOpenBlocker`'s read discipline, the parked
  `cockpit-start-change-button` TDD/ADRs.
- **Sections that referenced rather than restated:** Form (existing hexagonal
  structure), most of Armor (read-only — nothing new to protect).
