# Code Review: WP-005 — Refine scope switcher (All products, Unassigned, live counts, header echo)

> **Timestamp:** 2026-06-16T144045Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/feat-cockpit-product-experience/wp-005-refine-switcher → change/feat-cockpit-product-experience
> **Files changed:** 12
>
> **Outcome:** Ready to merge

---

## At a glance

This change reworks the board's product switcher so it speaks one shared
"product" language with the rest of the app, adds an "All products" everything
view and a first-class "Unassigned" view, shows a live count next to every
option, and echoes the current view in the header with a one-tap way back to
"All". The build is clean, the changes are tightly scoped to the switcher and
the board's filtering, and the new behaviour is covered by tests. Two small
things came up in review; both are handled (one fixed here, one is a harmless
note for awareness).

## What to fix

No issues that need attention before merge. The two review notes below are
already resolved:

- **A missing test for an edge case (fixed here).** When the saved view points
  at a product that no longer exists, the switcher correctly falls back to
  "All products" — but that wasn't tested. A test was added so the fallback
  can't silently break later.
- **A counting detail (no action needed).** The per-option counts are computed
  fresh each time the menu draws. For the handful of products and changes a
  real workspace has, this is instant and not worth optimising — noted for
  awareness only.

## How this pull request is shaped

**Size — worth looking at, but fine.** The change is medium-sized; most of the
"lines changed" are (a) deleting now-unused styling that the shared control
replaced, and (b) growing the test files. The actual new logic is small and
lives in one helper.

**Scope — clean.** One concern: refining the switcher. No mixed-in features,
no migrations, no infrastructure changes.

**Completeness — clean.** New behaviour ships with its tests (a new counting
helper with its own test file, plus extended switcher and board tests).

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN) for engineers and
> downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; no auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck + lint + JSX-ident scan all clean.
- **PR Hygiene:** scope low, size medium, safety none, completeness none (CR-09 / PH-01..04).
- **In the changes:** 2 findings (0 critical, 0 high, 0 medium, 2 low) — both resolved.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one actionable finding was fixed inline; the other is a Watch List note).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (sentinel correctly stripped from the wire; counts single-homed; ProductControl stays presentation-only) |
| Security | 0 | 0 | — (URLSearchParams safe encoding; no secrets; no raw HTML; static routes) |
| Quality | 1 | 0 | CR-10 countForScope O(rows×changes) in render — negligible at cockpit scale |

### Build Verification (CR-01)

No PR-introduced typecheck or lint errors. `npm run typecheck` (tsc server +
client) exit 0; `npx eslint <changed>` exit 0. JSX identifier scan over the
diff-introduced `{ident}`/`${ident}` tokens (onManageProducts, onRowSelect,
onSetUpNew, rows, scopeCount, scopeLabel, selectedId) — all resolve in lexical
scope; 0 undeclared. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        single concern (REORGANISE-Refactor)            severity: low
Size (PH-02):         ~1187 lines / 12 files (187-line CSS deletion)  severity: medium
Safety (PH-03):       migrations 0, schema 0, secrets 0, infra 0      severity: none
Completeness (PH-04): new source 1 + new tests 1; tests extended      severity: none
```

### Findings in the Changes

#### Q-1 — `ProductSwitcher.tsx:107-119` — low (quality) — CR-10

`countForScope` is O(changes) and is invoked once per row when building the
`rows` array, making row construction O(rows × changes). Context (CR-03): this
runs once per render (not in a network loop), over sub-linear data (1-20
products, tens of changes per workspace). **Resolution:** accepted as-is — no
measurable cost; memoising would add complexity for no gain (EP-08 no-bloat).
Recorded on the Watch List, no delta.

#### Q-2 — `ProductSwitcher.tsx:88-97` — low (quality)

The stale-`activeProductId` fallback (an id matching no known product reads as
the All scope, keeping the header and the ticked row consistent) was
implemented but untested. **Resolution:** fixed inline — added test
*"a stale activeProductId (no matching product) reads as All — header + the
ticked row agree"* to `ProductSwitcher.test.tsx`.

### Findings in the Neighbours

None. The two consumers of `<ProductSwitcher>` (WorkspaceTopBar, Sidebar) were
updated in-diff to pass the All-scoped change list for counts; no pre-existing
neighbour gap exposed.

### Watch List

- Q-1 (countForScope render cost) — no failing test grounding; benign at scale.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** typecheck (tsc server+client) exit 0; eslint changed exit 0; JSX-ident scan 0 undeclared. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch used.** 3 lenses dispatched concurrently (12 files / 713 insertions > carve-out threshold).
- [✓] **CR-03 Full-file reads.** All 12 changed files read end-to-end by the author (who wrote them); unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + quoted code.
- [✓] **CR-05 Severity rubric.** Applied: 0 critical, 0 high, 0 medium, 2 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read end-to-end; lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Security: nothing surfaced (URLSearchParams encoding, no secrets, no raw HTML, static routes). Quality: 1 finding + jsx-ident-scan + dead-surface (none — onSetUpNew/onManageProducts conditionally rendered) + contract-drift (none — ProductScope vocabulary consistent) + test-coverage (new behaviour covered) + CR-10 (1 benign).
- [✓] **CR-09 PR Hygiene applied.** Scope low / Size medium / Safety none / Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** working-tree diff vs `change/feat-cockpit-product-experience`.
- **Lens dispatch note:** the architecture + quality Explore sub-agents read STALE pre-refactor worktree content (an uncommitted-file visibility gap in the fan-out agents) and described the OLD ProductSwitcher — their findings about "missing productCounts.ts" and "onSetUpNew?.() dead button" do NOT apply to the actual refactored diff and were disregarded. The security lens reasoning holds for the real diff. The author performed the authoritative end-to-end read of all 12 changed files (full context: authored them; typecheck/lint/full vitest suite green against this exact worktree).
- **Full suite:** vitest run — 203 files / 1564 tests pass.
