---
id: SF-002
severity: ADVISORY
signature: 6e45193b92ec
source_wp: WP-005
detected_at: 2026-06-03T08:40:30Z
primitive: SEC-04
---

## Summary

roadmap_add accepts member_ids without entity-id format validation (data hygiene; no security impact)

## Evidence

```
{
  "detail": "roadmap_add merges member_ids without validating dna:<type>:<ulid> shape (reader enforces _ENTITY_ID_RE; writer does not). No security impact \u2014 values are JSON data, never path segments.",
  "fix": "validate member_ids against _ENTITY_ID_RE at the write boundary for data hygiene"
}
```

## Suggested fix

validate each member_id against _ENTITY_ID_RE at the write boundary

## Cross-references

- Source WP: WP-005
- Auto-draft WP: WP-AUTO-002 (created by this Step 11 run)
- Duplicate observations: none yet
