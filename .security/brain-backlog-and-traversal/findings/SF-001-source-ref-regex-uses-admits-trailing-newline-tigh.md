---
id: SF-001
severity: ADVISORY
signature: b25df1c68ace
source_wp: WP-002
detected_at: 2026-06-03T08:11:51Z
primitive: SEC-04
---

## Summary

source-ref regex uses $ (admits trailing newline) — tighten to \Z to keep the no-dangling-ref guarantee

## Evidence

```
{
  "redos": "n/a",
  "detail": "_OPPORTUNITY_REF_RE uses $ which admits a single trailing \\n; a source of dna:opportunity:<26>\\n passes the gate and the schema source pattern, persisting a dangling ref. Not exploitable (no path/inj); data-integrity gap vs the gate's stated no-dangling-ref guarantee.",
  "fix": "anchor with \\Z instead of $"
}
```

## Suggested fix

re.compile(r'^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}\Z')

## Cross-references

- Source WP: WP-002
- Auto-draft WP: WP-AUTO-001 (created by this Step 11 run)
- Duplicate observations: none yet
