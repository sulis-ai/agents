# Cockpit Board Refresh — Existing-vs-Gap Map

> The founder asked for this explicitly: **which hop does the current code already
> serve, and what is genuinely net-new.** Walked outside-in, journey by journey.
> Every "EXISTS" cites the real file. Grounding principle: reuse/extend, don't reinvent.

**Build-state note (important):** as of this worktree the **design and architecture
exist but the build has NOT landed**. `Change.health`, `Change.lastActivityAt`, and
`Change.needsAttention` are **not yet on the wire type** (`api-types.ts` carries
`needsAttention` only inside `ChangeStatus`, not `Change`); `computeHealth`,
`readRigorForStage`, `readTestsState`, `WaitingOnYou`, `ChangeHealthBadge`,
`LivenessProbe`, and the Start button + hotkey **do not exist yet**. So everything in
the GAP column is real net-new work, not already-done.

## Per-hop map

| Journey hop | Status | Grounded in / what's needed |
|---|---|---|
| **J-1.1** Fetch the change feed, scoped to active Product | **EXISTS** | `changes.ts` (`GET /api/changes`), `_product-scope` roll-up, `useChangesWithLiveness.ts` (10s poll). |
| **J-1.2** Probe liveness per change | **EXISTS** | `probeLiveness.ts` (signal-0 probe; produces running / not-running / unknown). |
| **J-1.3** Enrich the feed row with attention + health + last-activity | **GAP** | `toWireChange` (`_change-lookup.ts`) gains the enrichment; `changes.ts` gathers the cheap signals. Wire fields NEW (`api-types.ts`). ADR-002. |
| **J-1.4** Group changes into six fixed lanes | **EXISTS** | `groupChangesByStage` (`BOARD_STAGES`); `Board.tsx` renders columns. |
| **J-1.5** Lanes render full-height (sticky header + internal scroll) | **GAP** | `StageColumn.tsx` is content-height today; refactor to full-height lane. ADR-004 / IDEAS Concern 1. |
| **J-2.1** Compute "needs attention" verdict (flagged + why) | **EXISTS (logic)** | `needsAttention.ts` + `detectOpenBlocker.ts` — the predicate + the blocker source already exist. |
| **J-2.2** Surface that verdict on the **board** feed (not just `ChangeStatus`) | **GAP** | Lift `{flagged, reason}` onto the `Change` row. *No new detection logic* — exposing an existing verdict. IDEAS "build note". |
| **J-2.3** Render the full-width centered "Waiting on you — why" foot | **GAP** | NEW `WaitingOnYou.tsx`; `ChangeCard` foot branch. |
| **J-2.4** Click a card → open the change | **EXISTS** | `ChangeCard.tsx` is already a `<Link to=/c/:id>` with an aria-label. |
| **J-3.1** Read CI / test state (green/red) | **GAP** | NEW `readTestsState.ts` (best-effort, never-throws). IDEAS: tests is the "most available" input but no reader exists yet. |
| **J-3.2** Check rigor-for-stage (required artifacts present) | **GAP** | NEW `readRigorForStage.ts`. Stage is known; artifact presence is checkable; the *rule* is new. |
| **J-3.3** Roll up into a single health verdict | **GAP** | NEW pure `computeHealth.ts`; NEW `Change.health` field. ADR-001 (two states now; third deferred). |
| **J-3.4** Render the health badge (word + shape) | **GAP** | NEW `ChangeHealthBadge.tsx`. |
| **J-3.5** Health-**unknown** state (fresh/degraded change) | **GAP (and not in the design)** | FR-31 — the design only drew On/Off track. NEW honest unknown read. |
| **J-4.1** Liveness running/idle/unknown on the feed | **EXISTS** | `Change.liveness` already carries running / not-running / unknown. |
| **J-4.2** Split "Working" (live+moving) from "Live" (live+quiet) | **GAP** | Needs `lastActivityAt` + a freshness window; `running` is binary today. IDEAS "build note". |
| **J-4.3** Recency text (`now`/`12m`/`6h`/`1w`) | **GAP** | Needs NEW `lastActivityAt` ISO field on the feed. |
| **J-4.4** Probe renders by fill/motion/shape + SR label | **GAP** | NEW `LivenessProbe.tsx` (was `LivenessDot.tsx` — restyle/refactor). |
| **J-4.5** Liveness-**unknown** + **no-recency** distinct renders | **GAP (and not in the design)** | FR-41 / FR-42 — design drew only Working/Live/Idle. NEW honest reads. |
| **J-5.1** Start-from-intent flow (propose → confirm → start at Recon) | **EXISTS** | `StartFromIntent.tsx`, `useStartFromIntent`; the `/start-from-intent` route mounted in `server/app.ts` (the confirm-gated change-start act; tests `routes.startChange.test.ts`, `startFromIntent.classify.test.ts`). |
| **J-5.2** "Start something new" button in the top bar | **GAP (parked)** | Port the parked, already-reviewed button into `WorkspaceTopBar.tsx`. ADR-003. |
| **J-5.3** ⌘N / ⌘K hotkey → start | **GAP (parked)** | Port the parked `useStartHotkey.ts`; mount once in `WorkspaceShell`. ADR-003. |
| **J-6.1** Content search (conversations + created items) | **EXISTS** | `SearchBar.tsx`, `useSearch`, `searchChanges.ts` (pure filter), `/api/search`. |
| **J-6.2** Stage-filter chips | **EXISTS** | `SearchBar.tsx` chips → `stages[]` → `searchChanges`. |
| **J-6.3** "Needs attention" filter | **EXISTS** | `SearchBar.tsx` chip → `searchChanges` reuses `needsAttention` verdict server-side. |
| **J-6.4** Filtered results render in the SAME board | **EXISTS** | `Board.tsx` renders search results in the same six-lane layout (ADR-005). |
| **J-7.1** Responsive breakpoints (desktop / tablet / mobile) | **GAP** | NEW CSS media queries; `Board.module.css` + `StageColumn`. ADR-004. |
| **J-7.2** Mobile: one full-width lane, snap track | **GAP** | NEW layout. |
| **J-7.3** Stage chips become an ARIA tablist lane switcher | **GAP** | Dual-role the existing chips (`SearchBar` chips → tablist on mobile). ADR-004. |
| **J-7.4** Top bar condenses ("+ New", icons) at narrow widths | **GAP** | `WorkspaceTopBar.tsx` responsive collapse. |
| **J-8.1** Empty-board guide | **EXISTS** | `EmptyState.tsx`. (Open: Q-3 — replace CLI string with the revived button?) |
| **J-8.2** Empty-lane "Nothing here yet" | **EXISTS** | `StageColumn.tsx` `colEmpty` note (kept; now inside a full-height lane). |
| **Dark-mode** elevation tokens (page→lane→card) + sharper amber | **GAP** | `tokens.css` dark `:root` edits + one light `--warning` darken. Token change, not per-component. IDEAS Concern 2/dark-mode tables; TDD §3. |
| **Feed degrade-gracefully / never-500** discipline | **EXISTS (pattern)** | `detectOpenBlocker.ts` / `probeLiveness.ts` already model best-effort never-throws; the new reads MUST follow it (BR-11 / A-1). |

## Headline

- **Plumbing is mostly built.** The feed, scope, liveness, attention logic, grouping,
  search/filter, card-navigation, empty state, and the start-from-intent flow all exist.
- **The net-new is concentrated** in: three wire fields, three server reads
  (`computeHealth` / `readRigorForStage` / `readTestsState`), the feed enrichment, four
  new/reworked client components (card, waiting chip, health badge, liveness probe), the
  full-height lane layout, the revived Start button + hotkey, the dark token edits, and
  the responsive + mobile-tablist layer.
- **The unknown states are net-new AND absent from the signed-off design** — they are the
  requirements pass's most important contribution, because without them a fresh or
  degraded change would falsely read as "On track / Idle".
</content>
