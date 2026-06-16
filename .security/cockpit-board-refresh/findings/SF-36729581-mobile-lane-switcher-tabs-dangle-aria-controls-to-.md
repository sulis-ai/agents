---
id: SF-36729581
severity: CONCERN
signature: 367295812fba
source_wp: WP-010
detected_at: 2026-06-09T22:07:13Z
primitive: —
---

## Summary

Mobile lane-switcher tabs dangle aria-controls to lane-<stage> ids that don't exist on the empty board (WCAG aria-valid-attr-value)

## Evidence

```
{
  "rule": "aria-valid-attr-value (axe 4.9)",
  "violation": "Invalid ARIA attribute value: aria-controls=\"lane-recon\" (and the other five lane-<stage> tabs)",
  "where": "apps/cockpit/client/src/components/SearchBar.tsx lines 199-202 \u2014 the mobile lane-switcher tablist (WP-008, commit 8693f893)",
  "when_surfaced": "Whenever the board is NOT in its populated state (loading OR empty), the StageColumn lanes (id=lane-<stage>) are not rendered, so every tab's aria-controls dangles to a missing id. No prior test ran jest-axe on a non-populated board, so it stayed latent until WP-010 added loading/empty axe coverage.",
  "scope_note": "SearchBar.tsx is WP-008's file, outside WP-010's Contract (which is the SkeletonCard component + the Board loading branch). WP-010 fixes the LOADING board incidentally (it now renders the real lane scaffold, so the lane ids exist), but the EMPTY board still omits lanes by design, leaving the dangling aria-controls."
}
```

## Suggested fix

On the empty/EmptyState board the lane-switcher should not render its tablist (no lanes to switch to) — gate the switcher on a board being present, OR drop aria-controls when the controlled lane isn't in the DOM. Owned by WP-008 (SearchBar).

## Cross-references

- Source WP: WP-010
- Auto-draft WP: WP-AUTO-36729581 (created by this Step 11 run)
- Duplicate observations: none yet
