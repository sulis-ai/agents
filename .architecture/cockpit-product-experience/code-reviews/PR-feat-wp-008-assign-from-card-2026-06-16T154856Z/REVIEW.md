# Code Review: WP-008 — Assign a product straight from a board card

> **Timestamp:** 2026-06-16T154856Z (ISO 8601 UTC)
> **Branch:** wp/feat-cockpit-product-experience/wp-008-assign-from-card → change/feat-cockpit-product-experience
> **Files changed:** 12 (3 source, 7 test, 1 new shared test helper, 1 lockfile excluded from commit)
>
> **Outcome:** Approve, but apply small fixes first — and the one fix has already been applied.

---

## At a glance

This change adds the "add a product right from the board card" feature: an unassigned
card shows a quiet "＋ Product" button, and an assigned card shows a small product badge.
The build is clean, the accessibility checks all pass in both light and dark themes, and
the new behaviour is well tested. One housekeeping issue was found and already fixed —
some test helper code was copy-pasted into five files, now shared in one place.

## What to fix

### Worth fixing — test helper duplication (ALREADY FIXED)

**What was happening:** The same small piece of test setup (answering the board's new
"list my products" request) was copy-pasted into five test files.

**Why it matters:** If the product data shape ever changes, you'd have to edit five
places instead of one — easy to miss one and get a confusing test failure.

**What was done:** Pulled the shared setup into one file (`_productsFetch.ts`) that the
five test files now import. This mirrors the existing `_renderWithClient.tsx` pattern.

### For awareness only (not changed here)

Three observations about the assignment flow live in shared code this change reuses, not
in the change itself — so they're noted, not fixed here:

- The assignment doesn't show an error if the save fails (it just goes quiet). This is
  how the existing product picker behaves too; surfacing save errors would be a change to
  the shared product control, a separate piece of work.
- Network calls through the shared data helper have no maximum wait time. Again, shared
  infrastructure, affecting every save in the app.

## How this pull request is shaped

Well-scoped: one feature, three source files plus the tests that prove it. Reasonable
size (~590 lines, mostly test adaptations needed because the board now also loads the
product list). Tests included for every new behaviour. No database changes, no risky
infrastructure changes.

---

## Technical detail

### Verdict

`Approve with fixes` (CR-06). The one in-changes `medium` (F-Q1) is addressed inline;
the remaining findings are neighbour-ring (downgraded) or out of this WP's Contract.
No `critical`/`high` in the diff. Build Verification empty. All three lenses produced
output. → not `Block`, not `Request changes`.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck + lint delta clean.
- **PR Hygiene:** scope low, size medium (~592/-181, 12 files), safety none, completeness low.
- **In the changes:** 1 medium (F-Q1, resolved inline), 1 low (F-A4, out-of-scope).
- **In the neighbours:** 2 (F-A2, F-A3 — downgraded one notch per CR-05).
- **Draft fixes:** 0 (the one in-scope finding was fixed inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 3 | Assign-error/timeout gaps live in the reused primitive + funnel (out of scope) |
| Frontend / a11y | 0 | 0 | Nothing surfaced — all WPF gates pass |
| Quality | 1 (fixed) | 0 | Test-helper duplication across 5 files → extracted |

### Findings in the changes

**F-Q1 — medium (quality) — RESOLVED INLINE.**
`withProductsRoute` / `boardFetch` test doubles were duplicated in Board.test.tsx,
Board.empty.test.tsx, Board.loading.test.tsx, BoardProductScope.test.tsx,
Dashboard.test.tsx. Extracted to `client/src/tests/_productsFetch.ts` (EP-03, mirrors the
existing `_renderWithClient.tsx` convention); all five files import it. Typecheck + lint +
prettier + full suite (1581/1581) green after extraction.

**F-A4 — low (architecture/quality) — out-of-scope.** No assignment-failure test case in
ChangeCard.product.test.tsx. Paired with F-A2: there is no error surface to assert against
yet. WP-008's DoD specifies happy-path assign + chip + a11y. Failure-path testing is a
follow-on once the shared primitive grows an error surface.

### Findings in the neighbours (downgraded per CR-05)

**F-A2 — medium→low — out-of-scope.** The card's `saveState` maps only idle/saving/saved
(no `isError`). This is a property of the reused `ProductControl` + `useAssignChangeProduct`;
the existing `ProductPicker` behaves identically. Surfacing assign errors is a cross-cutting
change to the shared primitive, not in WP-008's Contract.

**F-A3 — medium→low — out-of-scope.** `apiPut` (the shared client funnel) has no request
timeout. Affects every mutation app-wide; pre-existing; not introduced by this WP.

### Methodology — Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server && -p client` + `eslint` on changed files. HEAD: 0 errors. Delta: 0. (Base == change branch; the WP's own Step 6 confirmed clean.)
- [✓] **CR-02 Parallel dispatch used.** Diff > 200 lines / > 5 files → three lenses (architecture, quality, frontend+a11y) dispatched concurrently as sub-agents.
- [✓] **CR-03 Full-file reads.** ChangeCard.tsx, StageColumn.tsx, Board.tsx, ChangeCard.module.css read end-to-end by the relevant lens.
- [✓] **CR-04 Evidence discipline.** Each finding cites file + quoted text.
- [✓] **CR-05 Severity rubric.** Applied; neighbour findings downgraded one notch.
- [✓] **CR-06 Verdict computed.** Approve with fixes. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 4 findings + checklist. Frontend/a11y: nothing surfaced, WPF-01..13 checked. Quality: JSX-ident scan clean, dead-surface clean, contract-drift clean, test-coverage solid, CR-10 performance acceptable (products.find() O(P<10) per virtualised card), 1 style/DRY finding.
- [✓] **CR-09 PR Hygiene applied.** Scope low (single feat), Size medium, Safety none (no migrations/secrets/infra), Completeness low (tests included).

### Run details

- **Diff source:** `git diff change/feat-cockpit-product-experience` (working tree) + 2 untracked new test files.
- **Neighbour expansion:** ProductControl.tsx, useAssignChangeProduct.ts, api/client.ts (read for context).
- **Lenses dispatched in parallel:** yes (3 sub-agents).
- **Disposition:** 1 in-changes medium fixed inline; 3 neighbour/out-of-scope findings noted, not deltas.
