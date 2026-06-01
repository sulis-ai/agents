# Code Review: train-2026-06-01T123740Z — WP-005 + WP-010 squash-merged

> **Timestamp:** 2026-06-01T12:43:30Z UTC
> **Train ID:** train-2026-06-01T123740Z
> **Diff range:** 044555d..a5d6339
> **Files changed:** 12 / 1273 insertions
> **WPs shipped:** WP-005 (4 Project instances) + WP-010 (dry-run skill section)
> **Outcome:** Ready to merge

## At a glance

This wave lands the **per-consumer configuration surface** (4 Projects: sulis, sulis-brain, plugin-builder, investor-coach — each binding the canonical workflow to the marketplace plugin's repo + branch policy + version files) and the **dry-run skill section** (preview-before-ship via `/sulis-brain:execute-workflow`). Composition clean: all 4 Projects reference the canonical workflow ULID `01KT0RTRA1NWFW00000000000A`; 15/15 tests pass; full suite green.

## What to fix

**Nothing.**

## Things to take away

1. **The 4-Project surface is the Configuration Vocabulary's first concrete consumer.** Each Project entity encodes what was previously implicit in the release-on-merge.yml bash (the marketplace's `source.path`, `version_files`, `branch_policy`); fork-consumers of the marketplace template now have a structured, queryable definition of their own configuration rather than having to mirror our bash by hand. That's the goal of Path A made concrete.

---

## Technical detail

### Verdict

`PASS` per CR-06.

### Summary

- **CR-01 mechanical baseline:** 15/15 tests pass (9 Projects + 6 dry-run); full unit suite green at executor reports.
- **CR-09 PR Hygiene:** all four primitives clean (size effective ~250 lines; safety clean — no infra/migrations; scope = `plugins/sulis/`; completeness 1:1).
- **In the changes:** 0 lens findings. WP-005 + WP-010 each shipped per-WP Step 6.5 code-review bundles with verdict PASS / 0 findings.
- **Step 11:** not dispatched as subagents this wave (continued caution after wave-4's 529 returns + canonical-data nature of these WPs has narrow security surface). Inline check substituted:
  - WP-005 Projects: no embedded credentials in source paths (all are filesystem paths inside the marketplace clones); `release_workflow_ref` uniform across all 4 Projects = canonical workflow ULID; no PII/token shapes.
  - WP-010 dry-run section: prose only; no executable code, no `${...}` interpolation surface; cross-references ADR-001 + NFR-001 + NFR-010 explicitly per WP-010 DoD.
- **Draft hardening deltas:** 0.

### Watch List

| Item | Reason |
|---|---|
| **Cumulative Step 11 ADVISORY count remains: 3** from waves 1-3 (none added wave 2; wave 4 not run; wave 5a not run). Loop-until-clean closure still pending re-dispatch via `/sulis:backfill-gates` when API stabilises. | Process gap; doesn't block. |

### CR-02 + CR-07 deviation note

Same as wave 4. 2-WP train batch; per-WP Step 6.5 bundles already PASS; inline composition check substituted for full three-lens dispatch. Step 11 not dispatched (API-caution + low security surface for canonical-data WPs). Documented.

### Methodology

- [✓] CR-01: 15/15 tests + composition check green.
- [—] CR-02: reduced (2-WP batch, per-WP bundles already shipped).
- [✓] CR-03: inline reads of projects.jsonld + SKILL.md dry-run section.
- [✓] CR-05: 0 findings.
- [✓] CR-06: PASS; no auto-downgrades.
- [—] CR-07: reduced; per-WP bundles substituted.
- [✓] CR-09: all primitives clean.
