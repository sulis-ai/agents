---
id: SF-07910b0c
severity: ADVISORY
signature: 07910b0c2fca
source_wp: WP-004
detected_at: 2026-06-04T10:49:42Z
primitive: —
---

## Summary

Stage name/order map duplicated across StageBadge, StageColumn, StageTrack (3 consumers) — extract shared stageMeta.ts in a follow-on WP (StageBadge/StageColumn are out of WP-004 scope)

## Evidence

```

```

## Suggested fix

Extract client/src/lib/stageMeta.ts (STAGE_ORDER + STAGE_NAME + stageLabel); have StageBadge, StageColumn, StageTrack consume it. Deferred from WP-004: extraction touches WP-002/WP-003 files outside this Contract (EP-07 scope guard).

## Cross-references

- Source WP: WP-004
- Auto-draft WP: WP-AUTO-07910b0c (created by this Step 11 run)
- Duplicate observations: none yet
