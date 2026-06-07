---
id: SF-6cb9efa7
severity: ADVISORY
signature: 6cb9efa7ea6b
source_wp: WP-003
detected_at: 2026-06-04T10:03:57Z
primitive: —
---

## Summary

StageBadge.module.css uses a raw-hex per-stage palette (#f1f8ff, #fff5b1, ...) that is now parallel to WP-003's canonical --stage-* token scale (ADR-005 'one shared stage scale'; WPF-07 no raw hex). Repoint the badge at the shared scale (via derived badge-tint tokens) so column dot + card badge + thread track draw one palette. Out of WP-003 scope: changes badge appearance app-wide on surfaces this slice does not observe; needs a small token-design pass + a characterisation test on the badge first.

## Evidence

```

```

## Suggested fix

Add --stage-*-tint/-border tokens (color-mix on --stage-*) to tokens.css; repoint StageBadge.module.css; characterise the badge before refactor.

## Cross-references

- Source WP: WP-003
- Auto-draft WP: WP-AUTO-6cb9efa7 (created by this Step 11 run)
- Duplicate observations: none yet
