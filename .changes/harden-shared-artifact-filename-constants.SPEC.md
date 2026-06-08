# harden: shared producer-side artifact filenames pinned in the contract WP

Closes #107.

## Problem

During CH-01KSSV, two producer renderers (WP-001 data-contract, WP-002
UI-contract) were designed to share one manifest but **independently
picked different filenames** (`CONTRACT.manifest.json` vs
`manifest.json`). One clobbered the other rather than merging — the
shared manifest split silently. Caught by the Step 10.5 cross-WP review
(the gate worked) and hand-fixed.

The decompose template said nothing about shared-artifact identity, so
each producer's Contract chose its own name in isolation. Mechanical
peer-collision (P6) only checked that two producers don't `Create` the
**same** path; it didn't check the converse — that two producers naming
the **same logical artifact** agree on the spelling.

## Fix

Three coordinated additions, no code paths touched:

1. **CONTRACT_FIRST_STANDARD — new CF-11 (MUST).** When the decomposition
   has ≥2 producer WPs emitting into the same logical artifact (manifest,
   registry, codegen output), the artifact's identity — filename, path,
   schema, and merge semantics — MUST be pinned as an explicit shared
   constant in the contract WP. Producer WPs `dependsOn` the contract and
   reference the constant verbatim; they do NOT independently choose a
   filename. Standard version bumped to 0.2.0.
2. **decompose-validation-rubric — new P6 check 6.06 (MUST).** Scans
   producer Contracts for shared logical outputs; asserts each is sourced
   from a single named constant declared in the contract WP. Cites
   CF-11 + anchor #107.
3. **plan-work SKILL.md — callout under cross-kind decomposition.**
   Right next to the existing CF-05 "producer + consumer dependsOn the
   contract WP" bullet, a new bullet on shared-artifact constants with
   the anchor case (CH-01KSSV) and a pointer to rubric 6.06.

## Tests

Documentation-only doctrine + rubric amendments — no executable test.
Cross-references resolve (CF-11 ↔ 6.06 ↔ plan-work bullet); 64
referential / canonical-drift tests green.
