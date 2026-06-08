---
id: WP-P02
title: "Count what changed in each file (backend)"
kind: backend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Extend
group: expand
estimate: 3h
blast_radius: low
dependsOn: [WP-P01]
adr: [ADR-010]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/gitShow.test.ts"
estimated_token_cost: { input: "~20k", output: "~10k" }
status: pending
---

## Context
Per-file `+N −N` counts, via `git diff --numstat`, added to the **one** sanctioned
git site (ADR-010) and merged onto each `ChangedFile`. Producer side of the
files-diff seam; runs parallel to WP-P03 against the WP-P01 contract (CF-05).

## Contract (the code this WP adds)
- `lib/gitShow.ts` → `gitDiffNumstat({cwd, baseSha, timeoutMs?}) → {path, added, removed}[]`
  reusing `runGit` (spawn, shell:false, 5s SIGKILL). Binary `-\t-` → `{added:null, removed:null}`.
- `lib/readChangedFiles.ts` → merge counts onto each `ChangedFile` (one extra
  numstat call alongside the existing name-status call).
- `routes/changed.ts` → returns the enriched `ChangedFile[]` (GET-only, unchanged shape otherwise).

## Definition of Done
### Red
- [ ] `gitShow.test.ts` — a new test for `gitDiffNumstat` parsing + binary-null + non-zero→`GitError` **fails** (function absent).
### Green
- [ ] `gitDiffNumstat` parses `added\tremoved\tpath`; binary → null counts; non-zero exit → `GitError`; timeout → `TimeoutError`.
- [ ] `readChangedFiles` merges counts; `baseKnown:false` legacy path unchanged.
- [ ] `routes.changed.test.ts` (extend): 200 with counts; binary null; clean `[]`.
### Blue
- [ ] `gitDiffNumstat` reuses `runGit` — **no** second `spawn` site (gate stays green; ADR-010).
- [ ] Matches the WP-P01 stubs exactly (CF-06 — conform to the contract).
