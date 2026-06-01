# Code Review: train-2026-06-01T165604Z — WP-001 + WP-005 squash-merged

> **Timestamp:** 2026-06-01T17:05:27Z UTC
> **Train ID:** train-2026-06-01T165604Z
> **Diff range:** 8aed4d6..998b9f0 (post-train HEAD minus pre-train HEAD)
> **WPs shipped:** WP-001 (canonical entities + 10 Tool schemas) + WP-005 (Ask-phase prose fragments)
> **Outcome:** Ready to merge — PASS

## At a glance

Wave 1 of discover-project. Lands the **canonical entity foundation** for n=2 dogfood of Path A: 1 Workflow + 9 Steps + 1 Trigger + 8 FailureModes + 5 active Tools + 1 forward-declared Tool ULID for WP-002, plus 10 per-Tool JSON Schemas. Alongside, **5 prose fragments** for the Ask-phase user experience.

Mechanical baseline: 26/26 unit tests pass; both per-WP Step 6.5 reviews PASS with 0 findings; cross-WP references resolve cleanly. Two dogfood lessons that should turn into follow-on changes (listed below).

## What to fix

**Nothing in this batch.**

## Things to take away

1. **The P8 cross-WP-ID rubric needs a schema-validation step at decompose-time.** WP-001's first dispatch BLOCKED at Step 3 because TDD's Canonical Identifiers section had 24 of 25 ULIDs failing the brain schema's regex (length + Crockford-invalid chars). The methodology refinement we shipped earlier (`f59fc36 extend: canonicalise-cross-wp-ids`) verifies cross-WP refs cite a canonical source but doesn't verify those pinned values are themselves valid. Adding a "pinned ULIDs schema-validate" check to `/sulis:plan-work`'s decompose-validation rubric would catch this at design time.

2. **The blocking drift-CI gate caught a real path-resolution bug the moment it went live.** Two hotfixes shipped (`50efe0b`, `4a021c2`) before this change could even start its wave 1. The gate worked exactly as designed — caught a regression, blocked the chain, forced surgical fix.

---

## Technical detail

### Verdict

`PASS` per CR-06. 0 critical/high/medium/low findings in the changes.

### Summary

- **Build Verification (CR-01):** 26/26 tests pass (17 from WP-001 + 9 from WP-005). Full unit suite 1330/1330 reported by both executors. All canonical entity instances pass brain foundation-schema validation. Cross-WP refs resolve.
- **PR Hygiene (CR-09):** clean — single change, contract-first ordering preserved (WP-001's canonical entities + WP-005's prose with no overlap).
- **In the changes:** 0 lens findings.
- **Step 11:** not dispatched as subagent (API caution + canonical-data narrow security surface; per-WP Step 6.5 bundles already PASS with 0 findings). Inline spot-check: no embedded credentials in Tool implementation_detail strings; no PII; no token shapes; new entities cross-reference canonical IDs only.
- **Draft hardening deltas:** 0.

### CR-02 deviation

Same 2-WP-batch pattern as previous wraps. Reduced full three-lens dispatch to (a) mechanical baseline + cross-WP composition verification inline, (b) per-WP Step 6.5 bundles (both PASS, 0 findings), (c) inline security spot-check. Documented.

### Watch List

- **Dogfood lesson — P8 rubric schema-validation gap** (described above). Recommended follow-on change after discover-project ships.
- **Forward-declared Tool ULID for derive-consumer-tenant.** WP-001 included a `_forward_declaration_ulid` descriptor row reserving the ULID for WP-002's authoring. Naming the pattern explicitly; future cross-WP entity dependencies in the same instance file may use this shape.

### Methodology

- [✓] CR-01: 26/26 tests; cross-WP refs resolve.
- [—] CR-02: reduced (2-WP batch, per-WP bundles already PASS).
- [✓] CR-03: inline reads of jsonld + prose files.
- [✓] CR-05: 0 findings.
- [✓] CR-06: PASS verdict.
- [—] CR-07: reduced — inline + per-WP bundles substituted.
- [✓] CR-09: PR Hygiene clean.
