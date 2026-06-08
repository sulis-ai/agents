# Decompose Validation — cockpit-start-change-button

> Applied the Decompose Validation Rubric to the WP set (3 WPs, tier S).
> **Verdict: PASS** — every MUST passes; no SHOULD failures.
> Date: 2026-06-08 · Source: TDD.md, SIZING.md, ADR-001/002, the signed visual contract.

## Inputs read

- `TDD.md` (Form/Armor/Proof + Verification Plan), `SIZING.md` (tier S), `ARCH.yaml`.
- `ADR-001` (front door routes to existing `/start`), `ADR-002` (accelerant = minimal hotkey, not a palette).
- `.changes/feat-cockpit-start-change-button.SPEC.md`.
- Signed visual contract: `.design/cockpit-start-change-button/SIGNOFF.md` (`production-approved` 2026-06-08).
- **Grounding check against the dependency branch** `origin/change/create-change-owned-terminal-shared-session`:
  confirmed `WorkspaceTopBar.tsx`, `WorkspaceShell.tsx`, `StartFromIntent.tsx`,
  `useStartFromIntent.ts`, `ProductSwitcher.tsx`, `StartFromIntentPage.tsx`, and
  the `/start` route all resolve there; confirmed they do **not** resolve on the
  current branch's `main` base. Contracts in the WPs use the real signatures
  read from that branch (`WorkspaceTopBar({ activeChangeId })`, the
  `useStartFromIntent` shape, the `ProductSwitcher` keydown idiom).

## Phase results

### P1 — Inventory completeness · PASS
Every WP carries Context, Contract, Definition of Done (Red/Green/Blue),
Sequence, Estimated Token Cost, and Dependencies. All three carry a valid
`verification:` field (Shape 1 concrete; `adapter: frontend` + a real
`artifact:` test nodeid). All three carry `kind: frontend`, `primitive`, and
`group`.

### P2 — Atomicity · PASS
- Single responsibility per WP: WP-001 = the button; WP-002 = the hotkey;
  WP-003 = the cold-start block. No "and" in any title or purpose.
- Touch surface: WP-001 = 2 files, WP-002 = 3 files, WP-003 = 3 files — all far
  below the ≤15 MUST / ≤8 SHOULD bounds.
- Each is implementable by one agent in one PR without reading another WP.

### P3 — Module naming + clean code · PASS
Descriptive kebab-case slugs (`front-door-button`, `global-start-hotkey`,
`cold-start-chips-welcome`). New symbol `useStartHotkey` follows the codebase's
`useX` hook convention. No jargon prefixes, no single-letter abbreviations.

### P4 — Dependency graph correctness · PASS
- No `dependsOn` edges between WPs → no cycles, valid (trivial) topological
  order, transitive depth 0 (≤ 8).
- **Data-contract wiring check (`wpx-index audit-contracts`):**
  `{"violations": [], "wp_count": 3}` — exit 0. The set is **single-kind**
  (all `frontend`); no producer/consumer seam across {backend, frontend, async},
  so no `kind: contract` (data) WP is required (CF-05 N/A). PASS.

### P5 — Performance + non-functional reqs · PASS (N/A)
No endpoint/handler WPs (all `frontend`, pure client). No measurable
latency/throughput bounds apply — the front door carries no network (TDD Armor:
"the hotkey carries no network"; the button only navigates). The relevant
non-functional bars are accessibility (keyboard reachability, visible focus,
colour-independence, jest-axe) — each WP's DoD names them explicitly.

### P6 — Peer-collision risk · PASS
File Touch Map in INDEX.md confirms **no two WPs create or edit the same file**.
The only shared touch-point is an optional `⌘N` hint constant (WP-001 may
extract; WP-002 references) — a Blue-step nicety, not a create-collision. No
`__init__.py`-class collision.

### P7 — ServiceSpec compliance · PASS (N/A)
The design names no new service — the existing `streamStartFromIntent` funnel is
reused unchanged (SPEC Non-goals; TDD Armor). No new ServiceSpec required.

### P8 — Cross-WP identifier canonicalisation · PASS
Scanned each WP's Contract for cross-WP shared identifiers (ULIDs, slugs,
version literals, namespaces). The only cross-WP shared token is the human
`⌘N` hint string — not an identifier requiring deterministic minting; handled
as an optional shared constant local to the cockpit, named in both WPs and in
ADR-002. No invented-inline identifiers. No route back to draft-architecture
required.

### P9 — Journey scenario coverage · PASS
The journey is the SPEC's Acceptance list; the design covers "the way in only"
(SIGNOFF scope). Mapping every user-facing scenario to a WP or to a conscious
out-of-scope record:

| Journey scenario (plain) | Covered by | Status |
|---|---|---|
| One obvious "Start something new" button in the chrome | WP-001 | planned |
| ⌘N / ⌘K reaches the same flow | WP-002 | planned |
| First-timer sees cold-start help, not a blank wall | WP-003 | planned |
| Describe → clarify → confirm → "Start this work" creates a change | `useStartFromIntent` + `StartFromIntent` on dep branch | already built (green on dep branch) — reused, not rebuilt (ADR-001) |
| Nothing created before "Start this work" (confirm gate) | server-side `confirmToken` funnel on dep branch | already built — reused (TDD Armor) |
| Failed start → plain-language retry/rename, not a dead end | `useStartFromIntent` typed error path on dep branch | already built — reused (TDD Armor) |
| Hand-off → founder lands in the change workspace | `StartFromIntentPage` `onStarted` nav on dep branch | already built — reused |
| Keyboard-reachable, visible focus, colour never the only signal | WP-001 + WP-002 + WP-003 DoD a11y items | planned |
| The in-change experience (chat/terminal/stages/files) | — | **out of scope** (SPEC Non-goals; SIGNOFF; not touched) |

No GAP: every not-already-green scenario is planned by a WP; the in-change
experience is consciously recorded out-of-scope. PASS.

## Mechanical gate results

| Gate | Command | Result |
|---|---|---|
| INDEX shape (step 9.5, MUST) | `wpx-index lint` | `{"header":"canonical","ok":true}` — exit 0 |
| Ready set | `wpx-index list-ready` | 3 ready, `max_parallel: 3`, 0 blocked |
| Data-contract wiring (P4 #48) | `wpx-index audit-contracts` | `{"violations":[],"wp_count":3}` — exit 0 |

## Cross-kind / visual-contract notes

- **Single-kind set** → step 4b cross-kind decomposition does not apply; no
  `kind: contract` (data) WP, no integration WP.
- **Visual contract** is pre-signed (`production-approved`). Per the change
  brief, no visual-contract WP is created and no fresh sign-off is required.
  WP-001 and WP-003 reference the signed `SIGNOFF.md` / `MOCKUP.html` states as
  satisfied; WP-002 is `visual_contract: exempt` (a keyboard accelerant with no
  visual surface of its own — its only visible artifact, the `⌘N` hint, is owned
  by WP-001). This is the honest representation of the brief's "depend on it as
  satisfied; do not require a fresh sign-off."

## Verdict

**PASS.** All nine phases pass (P5/P7 N/A with rationale; the rest substantive).
All MUST mechanical gates green. The breakdown was formally validated, not just
produced. Ready for execution **once implementation starts from the
chat+terminal branch** (the one hard external prerequisite, recorded in the
INDEX and in every WP's branch note).
