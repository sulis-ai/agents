---
id: WP-P10
title: 'Show the origin badge, "how it came to be" panel + lens (frontend)'
kind: frontend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Create
group: expand
estimate: 7h
blast_radius: low
dependsOn: [WP-P08]
visual_contract: "contracts/visual/brain-redesign/origin-badge-and-lens.html (approved)"
adr: [ADR-012]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/OriginBadge.test.tsx"
estimated_token_cost: { input: "~28k", output: "~16k" }
status: pending
---

## Context
The worded origin badge + the open-file "How this file came to be" panel + the
Provenance "How it came to be" lens — per the approved `origin-badge-and-lens.html`.
Consumer side; builds against the WP-P08 mock parallel to WP-P09 (CF-05).
Governed by `cognitive-load.md`; honesty banner for inferred origin.

## Contract (the components this WP adds)
- `OriginBadge.tsx` — worded **Autonomous** / **Assisted·likely** /
  **Origin-unknown** (never colour-alone); the "·likely" hedge + honesty banner
  appear when `attribution==="inferred"`, drop when `"recorded"`. On Files rows
  and the open-file panel.
- `HowThisFileCameToBe.tsx` — the open-file panel beside the diff (per the
  end-to-end-journey spec): the badge + trace targets — for autonomous, the run
  (+confidence) jumping to the run-log; for assisted, the Turn Card summary +
  an "Open conversation" jump.
- `HowItCameToBeLens.tsx` — a Provenance lens grouping files by Autonomous /
  Assisted with counts (per the lens in the prototype).
- `api/useOrigin.ts` — typed client over `GET …/origin` (+ `?path=`).
- Wire the badge into `ChangedList` rows + `FilePane`/`FileToolbar` (the open-file panel).

## Definition of Done
### Red
- [ ] `OriginBadge.test.tsx` etc. **fail** (components absent).
### Green
- [ ] Badge renders worded Autonomous / Assisted·likely / Origin-unknown; inferred shows the honesty banner, recorded drops the hedge.
- [ ] Open-file panel: autonomous → run+confidence trace to run-log; assisted → Turn Card summary + "Open conversation".
- [ ] Lens groups Autonomous/Assisted with counts.
- [ ] axe-core passes; worded status never colour-alone (WCAG 1.4.1).
### Blue
- [ ] Tokens only; matches the approved prototype (L-13).
- [ ] Reuses the existing Turn Card + `turnSummaries` for the assisted summary (EP-03).
- [ ] Conforms to WP-P08 shapes verbatim (CF-06); `attribution` drives the hedge (no client-side guessing).
