# Cockpit Board Refresh — Decompose Validation

> Validates the **revised** WP set against the Work Package Standard +
> WP_FRONTEND_STANDARD before the work queues. Change CH-084CAN, tier M,
> **13 WPs** (revised from 8 after the requirements pass completed).
> The original 8 were decomposed from the design alone; this set adds the
> unknown/degraded states, the five alternate card states (§7c), the
> empty/loading/error behaviour, never-500 degradation, and the NFRs.

## 0. Why the re-plan (provenance)

The first plan covered the **happy path** the signed-off design drew. The
completed SRD added requirements the design omitted: the unknown reads
(FR-31/41/42), the five alternate card states (CS-1..5), the error/failure
flows (EF-1..5), never-throw-never-500 (BR-11), and measurable NFRs
(NFR-PERF-5 no-layout-jump, NFR-DEGRADE, NFR-A11Y across all variants).
Each became either an extension to an existing WP (where it belongs to that
WP's seam) or a new WP (where it is an independently-shippable card state /
behaviour).

## 1. Atomicity (each WP implementable without reading another)

| WP | Atomic? | Evidence |
|----|---------|----------|
| WP-001 | ✓ | Type-only edit to one file; self-contained contract (now incl. the `unknown` members). |
| WP-002 | ✓ | New libs + feed shaping + degradation suite; reads WP-001's contract (a dependency, not a co-read). |
| WP-003 | ✓ | Token values from TDD §3 — no cross-WP knowledge. |
| WP-004 | ✓ | Lane layout + empty-lane note; excludes card internals (WP-005). |
| WP-005 | ✓ | Card + sub-components (4-state probe/health) against the contract mock; needs only WP-001's type. |
| WP-006 | ✓ | Port of three named components; the parked source is the spec. |
| WP-007 | ✓ | Integration seam + board async behaviour; deps listed, not re-described. |
| WP-008 | ✓ | Responsive CSS + dual-role chips + mobile empty-lane; deps listed. |
| WP-009 | ✓ | Selected (route-derived) + focus ring on the card; needs only WP-005's card. |
| WP-010 | ✓ | Loading/empty branches + per-card skeleton; skeleton box metrics reuse WP-005's card CSS (a dependency). |
| WP-011 | ✓ | Card-level degraded composition; reuses WP-005's unknown reads + WP-002's best-effort feed (deps). |
| WP-012 | ✓ | Shipped card variant behind the existing terminal predicate; needs only WP-005's card. |
| WP-013 | ✓ | Perf budget on the lane scroll; needs WP-004's lane + WP-007's live cards (deps). |

No WP bundles two logical changes. Each alternate card state (CS-1..5) is its own
WP precisely because each is an independently-shippable, independently-testable
state with its own scenario (S-32..S-36) — bundling them would break atomicity.

## 2. Dependency graph is a DAG (no cycles, ordering expresses merge safety)

```
WP-001 → WP-002, WP-005
WP-004 → WP-007, WP-008, WP-010, WP-013
WP-005 → WP-007, WP-009, WP-010, WP-011, WP-012
WP-002 → WP-007, WP-011
WP-006 → WP-008
WP-007 → WP-013
```

Acyclic. Ready set `{001, 003, 004, 006}` has zero inbound edges → genuinely
parallel. File-contention check (no two parallel WPs touch the same file):
- 001 → `shared/api-types.ts`
- 003 → `tokens.css`
- 004 → `StageColumn.*`, `Board.module.css` (layout)
- 006 → `WorkspaceTopBar.tsx`, `useStartHotkey.ts`, `WorkspaceShell`, `/start` chips

Sequenced (never concurrent) where files overlap:
- WP-004 ↔ WP-008/WP-010/WP-013 all touch `Board.*` — each dependsOn WP-004, so
  sequenced after it.
- WP-005 ↔ WP-009/WP-011/WP-012 all touch `ChangeCard.*` — each dependsOn WP-005,
  so sequenced after it. **The four card-state WPs (009/011/012 + 010's skeleton)
  serialise on `ChangeCard`/`Board`** — they are NOT mutually parallel; they queue
  after WP-005 and after each other where they touch the same file, or land as
  small sequential PRs. Flagged below as a trade-off.
- WP-007 ↔ WP-013 touch `Board.*` — WP-013 dependsOn WP-007, sequenced.

## 3. Red-Green-Blue present on every WP

Every WP (001–013) carries Red (named failing test), Green (named passing
condition), Blue (named refactor/cleanup check). No WP skips Blue. ✓

## 4. Characterisation-test-before-refactor (MUST) on every REORGANISE WP

| REORGANISE WP | characterisation_test declared? |
|---|---|
| WP-002 (`toWireChange`) | ✓ `_change-lookup.test.ts` |
| WP-003 (tokens) | ✓ `tokens.dark.test.ts` |
| WP-004 (`StageColumn`/`Board`) | ✓ `Board.test.tsx` + `StageColumn.test.tsx` |
| WP-005 (`ChangeCard`) | ✓ `ChangeCard.test.tsx` |
| WP-007 (board seam) | ✓ `Board.test.tsx` |
| WP-008 (`StageChips`) | ✓ `SearchBar.test.tsx` |
| WP-009 (`ChangeCard` focus) | ✓ `ChangeCard.test.tsx` |
| WP-010 (`Board` loading/empty branches) | ✓ `Board.test.tsx` |
| WP-011 (`ChangeCard` degraded composition) | ✓ `ChangeCard.test.tsx` |
| WP-013 (lane scroll harden) | ✓ `StageColumn.test.tsx` |

WP-012 is EXPAND-Create (a new shipped variant branch — a card *state*, not a
refactor of the existing render) so it carries the card characterisation test as
a guard but is not gated as a REORGANISE.

## 5. No band-aid wrappers / ports-not-wrappers check

- WP-006 is `SUBSTITUTE-port` with `subject_ownership: internal` — porting our
  own already-reviewed components (ADR-003), a content port + re-verify.
- The new server libs (`computeHealth`, the readers) are **EXPAND-Create** — new
  pure/read-only functions behind the route layer, not wrappers.
- The new card-state WPs (009/011/012) and the skeleton (010) are
  **EXPAND-Create** of new states/components composed onto the card, not wrappers
  over `ChangeCard` — they extend the card's render, reusing its existing reads
  (the unknown reads from WP-005, the selection pattern from the shell). No
  Wrap-over-internal anywhere. No wrapper-rot escalation triggered. ✓

## 6. WP_FRONTEND_STANDARD conformance (frontend WPs: 003,004,005,006,007,008,009,010,011,012,013)

| Gate | Covered |
|---|---|
| WPF-02 typed client, no `fetch` in component | Board/card consume `useChangesWithLiveness` only; no new `fetch`. ✓ |
| WPF-03 mock-first (contract mock) | WP-005/009/011/012 build against the WP-001 contract mock, parallel to WP-002. ✓ |
| WPF-05 loading/error/empty | WP-010 owns the loading/empty distinction (FR-52); WP-007 owns the error/poll-failure behaviour. ✓ |
| WPF-06 a11y gated automatically | jest-axe on every changed component **in light AND dark**, across **all content + alternate-state variants** (waiting/on/off/unknown health, unknown liveness, no-recency, selected, focused, loading, degraded, shipped); Playwright-axe on the board at 3 viewports (WP-008). ✓ |
| WPF-07 tokens never hardcoded | Every WP's Blue has a "tokens only / no literal hex" grep check; WP-003 is pure tokens; the unknown reads use neutral tokens. ✓ |
| WPF-11 done means reachable | WP-007 is the explicit "reachable in the running app" seam. ✓ |
| WPF-12 agentic-interface | The board surfaces honest, server-derived verdicts; the unknown/degraded reads make uncertainty visible rather than masking it (FR-31/41/42 — the honest-interface requirement). ✓ |
| WPF-14 build workspace deps first | Called out in WP-001/006 Green; applies to all local verifies. ✓ |
| Visual contract signed (WPF-11) | `production-approved` — no new visual-contract WP; every frontend WP cites `MOCKUP.html`. The mockup carries the unknown/empty + five alternate states (founder-signed). ✓ |

## 7. Verification frontmatter (every WP)

Each WP carries a `verification:` block — all **Shape 1 (concrete)**: an adapter
(frontend/backend) + a real test artifact path. None deferred at the WP level.
The one design-level deferral (`health-drift-ooda-signal`) is a follow-on
**change**, recorded in ARCH.yaml + TDD §6.6, not a WP here.

## 8. Scenario coverage (MUST — every S-1..S-36 maps to ≥1 WP)

All 36 scenarios map; the full table is in `INDEX.md`. No scenario is orphaned.
Spot-check of the scenarios the original 8 **did not** cover, now closed:

| Previously-uncovered | Now owned by |
|---|---|
| S-9 first-run empty (FR-52) | WP-010 |
| S-15 large lane scroll (NFR-PERF-2) | WP-013 |
| S-16/17/18 unknown health/liveness/recency | WP-002 (produce) + WP-005 (render) |
| S-19 computeHealth unknown combo | WP-002 |
| S-20/22 feed-fail / poll-fail | WP-007 |
| S-21/23/24/25/26 partial / worktree-gone / malformed / scale / reason-leak | WP-002 (+WP-011 render for S-21) |
| S-32 selected card (CS-1) | WP-009 |
| S-33 keyboard focus (CS-2) | WP-009 |
| S-34 loading skeletons + no-jump (CS-3) | WP-010 |
| S-35 degraded card (CS-4) | WP-011 (+WP-002 server-200) |
| S-36 shipped card (CS-5) | WP-012 |

## 9. Scope guard — what this decomposition deliberately does NOT include

- A scope-drift detector or the "Worth a look" middle state (ADR-001 — deferred
  to consume the OODA-spiral signal). The wire type carries the third state so
  the follow-on is additive, not a re-layout.
- A new health/attention endpoint (ADR-002 — the one feed is enriched).
- A rebuild of the start button (ADR-003 — ported).
- A new visual-contract sign-off (mockup is production-approved, incl. the
  unknown/empty + five alternate states).
- **Speculative virtualisation** (WP-013 virtualises only if the 200-card budget
  is breached — Q-6 default is plain scroll).

## 10. Genuine trade-off surfaced

**The four card-state WPs (009, 010-skeleton, 011, 012) plus WP-005 all touch
`ChangeCard` / `Board`, so they serialise after WP-005 rather than running in
parallel.** They cannot be made mutually parallel without merge conflict on the
card. Two honest options:

- **(taken) Keep them as separate atomic WPs, sequenced** — each ships as a small
  PR after WP-005, in any order among themselves (they touch overlapping card
  regions, so land one-at-a-time). Pro: every alternate state is independently
  reviewable + revertible, each maps to one scenario. Con: less parallelism in
  the card tier.
- **(rejected) Fold CS-1/2/4/5 into WP-005** — one big card WP. Pro: no card-file
  serialisation. Con: a ~6-scenario mega-WP that violates atomicity and makes the
  single-foot-verdict rule + unknown reads + four alternate states one
  unreviewable change.

Atomicity + reviewability won. The card tier is the throughput bottleneck by
design, not by accident — the card is one file and its states compose on it.

## Verdict

**PASS.** 13 atomic WPs, acyclic dependency graph, parallel-ready set of 4, every
REORGANISE gated by a characterisation test, frontend WPs conform to
WP_FRONTEND_STANDARD with dual-theme + 3-viewport a11y across all content +
alternate-state variants, no wrapper rot, **all 36 scenarios mapped to ≥1 WP**,
never-500 degradation gated in WP-002, and the deferred scope recorded as a
follow-on change rather than smuggled in. The card-tier serialisation is an
honest, recorded trade-off.
