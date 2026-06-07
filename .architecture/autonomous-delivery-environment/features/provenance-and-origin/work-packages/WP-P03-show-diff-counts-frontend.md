---
id: WP-P03
title: 'Show "+N −N" on files and folders (frontend)'
kind: frontend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Extend
group: expand
estimate: 3h
blast_radius: low
dependsOn: [WP-P01]
visual_contract: "contracts/visual/files-redesign/files-B-repo-browser.contract.md (SIGNED)"
adr: [ADR-010]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ChangedList.test.tsx"
estimated_token_cost: { input: "~22k", output: "~11k" }
status: pending
---

## Context
Render `+N −N` on changed-file rows and roll the counts up onto folders, in the
already-shipped repo browser (`ChangedList.tsx`, `FolderOverview.tsx`). Consumer
side of the seam; builds against the WP-P01 mock in parallel with WP-P02 (CF-05).
Build target: the **SIGNED** `files-B` contract.

## Contract (the code this WP changes)
- `ChangedList.tsx` — render `+added −removed` on file rows (mono face,
  `--positive`/`--destructive` per the signed token set); fold child counts into
  the existing folder rollup (extend `countFiles` to sum added/removed too).
- `FolderOverview.tsx` — `+N −N` on overview rows.
- Binary/unknown (`added===null`) → render **no** count (not `+0 −0`).
- Consumes the WP-P01-extended `ChangedFile`; no reshaping caller-side (CF-06).

## Definition of Done
### Red
- [ ] `ChangedList.test.tsx` — assert `+N −N` on a row + folder rollup = sum of descendants **fails** (not rendered yet).
### Green
- [ ] File rows show `+N −N`; folder rows show the rolled-up sum; binary rows show no count.
- [ ] Worded/colour treatment matches the signed contract (`--positive`/`--destructive`, never colour-alone meaning).
- [ ] axe-core passes on the Files view (no a11y regression).
### Blue
- [ ] Count rollup reuses/extends `countFiles` (EP-03 — one tree-walk, not a second).
- [ ] Tokens only, no raw hex (UX_VISUAL); matches `files-B` (L-13 running-surface check).
