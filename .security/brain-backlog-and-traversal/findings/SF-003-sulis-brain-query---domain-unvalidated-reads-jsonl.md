---
id: SF-003
severity: ADVISORY
signature: ac3336ae6e21
source_wp: WP-008
detected_at: 2026-06-03T09:28:07Z
primitive: SEC-04
---

## Summary

sulis-brain-query --domain unvalidated → reads .jsonld outside the store (read-only, operator-only; defence-in-depth)

## Evidence

```
{
  "detail": "sulis-brain-query passes --domain straight into base/domain path join; a crafted --domain (../.. or absolute) reads .jsonld outside .brain/instances. Read-only, operator-supplied CLI arg (not attacker input). Pre-existing, surface widened this batch.",
  "fix": "validate --domain against {foundation,product-development,insurance-broking} or reject path separators \u2014 one-line guard"
}
```

## Suggested fix

validate --domain against the known domain set or reject path separators

## Cross-references

- Source WP: WP-008
- Auto-draft WP: WP-AUTO-003 (created by this Step 11 run)
- Duplicate observations: none yet
