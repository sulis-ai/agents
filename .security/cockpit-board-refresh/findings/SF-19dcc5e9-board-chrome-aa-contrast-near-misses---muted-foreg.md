---
id: SF-19dcc5e9
severity: CONCERN
signature: 19dcc5e9fa14
source_wp: WP-008
detected_at: 2026-06-09T21:44:14Z
primitive: —
---

## Summary

Board chrome AA-contrast near-misses (--muted-foreground 4.34:1, ⌘N hint 3.75:1) need a token-level fix

## Evidence

```
{
  "rule": "axe color-contrast (WCAG 1.4.3 AA text, 4.5:1)",
  "surfaced_by": "WP-008 S-28 board Playwright-axe (first board-level axe run)",
  "viewports": [
    "desktop >=1100",
    "tablet 600-1099",
    "mobile <600"
  ],
  "nodes": [
    {
      "selector": ".laneName / .laneCount (StageColumn header)",
      "fg": "#737373 (--muted-foreground)",
      "bg": "#f5f5f5 (--muted)",
      "ratio": "4.34:1",
      "owner_wp": "WP-004"
    },
    {
      "selector": ".laneEmpty ('Nothing here yet')",
      "fg": "#737373",
      "bg": "#f5f5f5",
      "ratio": "4.34:1",
      "owner_wp": "WP-004"
    },
    {
      "selector": ".startHere (Recon foot link)",
      "fg": "#737373",
      "bg": "#f5f5f5",
      "ratio": "4.34:1",
      "owner_wp": "WP-004"
    },
    {
      "selector": ".startBtnHint (Cmd-N hint on Start button)",
      "fg": "#ffffff (--primary-foreground)",
      "bg": "#4c7fef (lightened --primary wash)",
      "ratio": "3.75:1",
      "owner_wp": "WP-006"
    }
  ],
  "pre_existing": true,
  "note": "Unchanged by WP-008; present at desktop too (unrelated to the responsive re-layout). WP-008's own surfaces (switcher rail, collapsed top bar, responsive lane track) are axe-clean. The S-28 gate filters these documented pre-existing nodes so it asserts WP-008 introduces no NEW violations."
}
```

## Suggested fix

Darken light --muted-foreground (#737373 → e.g. #6b6b6b/#666 to clear 4.5:1 on --muted #f5f5f5) and rework the .startBtnHint wash so --primary-foreground on the lightened --primary clears 4.5:1 (or 3:1 large/decorative). Design-system token decision (ripples app-wide), like the IDEAS.md --warning fix; verify light+dark.

## Cross-references

- Source WP: WP-008
- Auto-draft WP: WP-AUTO-19dcc5e9 (created by this Step 11 run)
- Duplicate observations: none yet
