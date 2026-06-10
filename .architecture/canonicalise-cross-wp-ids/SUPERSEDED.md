# SUPERSEDED — canonicalise-cross-wp-ids

This effort was parked with no real design (only a stray executor journal and a
code-review bundle — no spec, no TDD, no work package). Its intent — making Work
Package ids unique across changes — is now realised canonically by the change
**`unique-wp-ids` (CH-5DMB1N)**, which mints ids as `{CH-HANDLE}-WP-NNN`,
mirroring the per-change branch namespacing PR #283 introduced.

There is exactly one canonical effort for unique WP ids; this stub is retired so
no work is duplicated. See:

- `.architecture/extend-unique-wp-ids/adrs/ADR-002-additive-backcompat-and-supersession.md` (§4 — supersession)
- `plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md` (WP-01 `id` row)
- `plugins/sulis/references/change-work-standard.md` (CW-04 — WP id labels)
