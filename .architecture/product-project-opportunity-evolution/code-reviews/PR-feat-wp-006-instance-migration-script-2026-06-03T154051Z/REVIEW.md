# Code Review: PR feat/wp-006-instance-migration-script — Build migrate_lifecyclerun_v1_to_v2 + migrate marketplace store

> **Timestamp:** 2026-06-03T154051Z (ISO 8601 UTC)
> **Author:** executor (WP-006)
> **Branch:** feat/wp-006-instance-migration-script → change/feat-product-project-opportunity-evolution
> **Files changed:** 6 (1 new module, 2 new test files, 2 migrated data instances, 1 doc note)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a one-shot script that rewrites the old LifecycleRun records (which named their step with a free text string) into the new shape (which points at a fixed step definition by its identifier). It is well-scoped, fully tested, and the two existing on-disk records were migrated cleanly. Two minor code-tidiness items were found and fixed in place during review; nothing remains to address.

## What to fix

No issues that need attention. Two small tidy-ups were found and already applied during the review:

- The migration was rebuilding its validation helper once for every file it walked. For the two files here that is harmless, but it is wasteful work repeated in a loop, so the helper is now built once and reused.
- One leftover unused import was removed.

Both are already fixed in the code under review.

## How this pull request is shaped

**Size — clean.** The substantive change is one ~190-line module plus its two test files. The tracked diff is tiny (the data files shrank as redundant fields were dropped).

**Scope — clean.** Single concern: the v1→v2 instance migration. One `feat` primitive, one module fan-out.

**Safety — clean.** No database migrations, no schema/IDL files, no infrastructure, no secrets. The two `.brain/instances` data files are the migration's own eager-for-our-own output; both validate against the vendored v2 schema. The migration is idempotent and validates each record before writing (never writes an invalid record).

**Completeness — clean.** One new source file, two new test files (9 unit + 6 integration cases). New behaviour is covered, including idempotency, reject-on-invalid, unmapped-name fallback, and the missing-store no-op.

---

## Technical detail

> Internal taxonomy below for engineers + downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all changed source files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01: `python3 -m compileall` — the repo's lint floor; no type-checker configured per plugin contract).
- **PR Hygiene:** 0 high, 0 medium (PH-01..PH-04 all clean/low).
- **In the changes:** 2 findings (0 critical, 0 high, 0 medium, 2 low) — both addressed inline.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (both findings fixed inline, no deltas queued).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — reuses `_resolve_step` + `LocalFileEntityAdapter` validator |
| Security | 0 | 0 | none — local-file data rewrite, reject-on-invalid |
| Quality | 2 (both low, fixed) | 0 | per-iteration validator construction (fixed via lru_cache) |

### Build Verification (CR-01)

No PR-introduced errors. `python3 -m compileall` clean on all three new Python files; full scripts suite green (1969 passed, 9 skipped); branch-ci unit gate green (1804 passed).

### Findings in the Changes

#### F-01 `plugins/sulis/scripts/migrate_lifecyclerun_v1_to_v2.py:130-152` — low (quality, CR-10) — ADDRESSED INLINE

**What:** `migrate_store` loops over `*.jsonld` and calls `migrate_instance` per file; each call invoked `_validator()`, constructing a fresh `LocalFileEntityAdapter` (a loop-invariant). Repeated invariant construction in a loop.

**Fix applied:** `@lru_cache(maxsize=1)` on `_validator()` — built once, reused across the walk. Benign at current scale (eager store = 2 files; downstream = 1 at a time) but correct.

#### F-02 `plugins/sulis/scripts/migrate_lifecyclerun_v1_to_v2.py` (imports) — low (quality, dead-surface) — ADDRESSED INLINE

**What:** unused `import sys` (the CLI uses the builtin `SystemExit`, not `sys`).

**Fix applied:** import removed.

### Findings in the Neighbours

None. The change reuses two existing symbols (`_resolve_step` from `_brain_emit_helper`; `LocalFileEntityAdapter` from `_entity_adapter_local`) without modifying them.

### Watch List

None.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `python3 -m compileall` (repo lint floor; no type-checker configured per plugin contract). Base: clean. Head: clean. 0 PR-introduced errors. Coverage gap: type-checker n/a (recorded).
- [✓] **CR-02 Dispatch shape.** 6 files / 577 new lines is above the single-reader carve-out; the substantive surface is one module + two test files, all authored and read end-to-end by the reviewer. Single-reader read justified by the data/doc files being mechanical migration output + a 7-line note.
- [✓] **CR-03 Full-file reads.** All 3 new Python files (197/197/183 lines) read end-to-end. The 2 data `.jsonld` (≤10 lines each) and README note read in full.
- [✓] **CR-04 Evidence discipline.** Both findings cite file:line + the loop / import site.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 2 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; no unread >50-line file; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (reuse-only, no new gaps). Security: nothing surfaced (no auth/injection/secrets surface; local-file rewrite with reject-on-invalid). Quality: 2 findings (per-iter validator, dead import) + test-coverage observation (covered) + contract-drift (none) + dead-surface (1, fixed).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (1 feat, 1 dir). PH-02 Size: low. PH-03 Safety: clean (0 migrations/schemas/secrets/infra; 2 data instances migrated + re-validated). PH-04 Completeness: clean (1 source / 2 tests). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff origin/change/feat-product-project-opportunity-evolution` + untracked new files.
- **Neighbour expansion:** git grep on `_resolve_step` / `LocalFileEntityAdapter` — both reused unmodified, 0 neighbour findings.
- **Scanners run:** compileall (lint floor), jsonschema validation of migrated instances.
- **Scanners unavailable:** type-checker (none configured — plugin contract is stdlib-only tooling); Gitleaks/Semgrep/Trivy (not in env) — no secret/injection surface in a local-file data rewrite.
