# Findings Register

Append-only ledger of security findings across all WPs in this project.

| SF ID | Severity | Summary | Source WP | Signature | Target / Disposition |
|---|---|---|---|---|---|
| SF-001 | ADVISORY | source-ref regex uses $ (admits trailing newline) — tighten to \Z to keep the... | WP-002 | b25df1c68ace | WP-AUTO-001 |
| SF-002 | ADVISORY | roadmap_add accepts member_ids without entity-id format validation (data hygi... | WP-005 | 6e45193b92ec | WP-AUTO-002 |
| SF-003 | ADVISORY | sulis-brain-query --domain unvalidated → reads .jsonld outside the store (rea... | WP-008 | ac3336ae6e21 | WP-AUTO-003 |
| SF-004 | ADVISORY | PRE-EXISTING: scenario subprocess driver uses shell=True (operator-trust gate... | WP-013 | 459cc6a8db3c | WP-AUTO-004 |
