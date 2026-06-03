---
id: SF-004
severity: ADVISORY
signature: 459cc6a8db3c
source_wp: WP-013
detected_at: 2026-06-03T10:32:12Z
primitive: SEC-03
---

## Summary

PRE-EXISTING: scenario subprocess driver uses shell=True (operator-trust gated; future shell=False hardening, not this change)

## Evidence

```
{
  "detail": "_scenario_dispatch.py:_default_run uses subprocess.run(cmd, shell=True) with a graph-sourced cmd string. PRE-EXISTING (PR #154), NOT introduced by this change. Gated by operator trust (locally-authored committed bundles). Not blocking.",
  "fix": "migrate the scenario subprocess driver to shell=False + argv list if scenario-bundle authorship ever broadens beyond the operator"
}
```

## Suggested fix

shell=False + argv list in the scenario subprocess driver (separate hardening change)

## Cross-references

- Source WP: WP-013
- Auto-draft WP: WP-AUTO-004 (created by this Step 11 run)
- Duplicate observations: none yet
