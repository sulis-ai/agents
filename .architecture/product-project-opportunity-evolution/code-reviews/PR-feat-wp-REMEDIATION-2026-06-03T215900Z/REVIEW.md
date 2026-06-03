# Code Review: fix/review-remediation — Stage-4 review remediation pass

> **Timestamp:** 2026-06-03T215900Z (ISO 8601 UTC)
> **Author:** executor (WP-REMEDIATION)
> **Branch:** fix/review-remediation → change/feat-product-project-opportunity-evolution
> **Files changed:** 12 (5 source, 1 ADR, 6 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This is a small, well-scoped fix-up that applies five corrections the Stage-4
review flagged. It tightens two file writes so they cannot leave a half-written
file behind if the machine crashes mid-write, adds two input checks on the
read path so a malformed identifier is rejected before it ever touches the
filesystem, and corrects an over-stated claim in the design notes. Every code
change is backed by a test written first, the whole test suite stays green
(1,899 passing), and the linter is clean. There is nothing that needs fixing
before merge.

## What to fix

No issues that need attention.

The one thing worth knowing about (not a defect): the same small
"write-to-a-temp-file-then-swap-it-in" routine now appears in three places in
the code. They were deliberately left as three copies rather than merged into
one shared helper, because the three live in two different parts of the system
with slightly different rules about where the temp file goes. Merging them is a
reasonable future tidy-up, but it would touch files outside this fix's remit,
so it was left for its own piece of work.

## How this pull request is shaped

**Size — clean.** 344 lines across 12 files, half of them tests. Comfortable to
review thoroughly.

**Scope — clean.** Single cohesive concern (the review remediation). No mixing
of unrelated feature work.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets.

**Completeness — clean.** Four new test classes accompany the behaviour changes;
the one documentation-only fix correctly ships without a test.

## Things to take away

1. The invalid test identifiers this change corrected (`...RUN...` literals that
   contained the letter `U`, which the ULID alphabet excludes) had been passing
   only because nothing validated them. Adding the validation surfaced them
   immediately — a good illustration of why tightening a check often pays for
   itself by exposing latent fixture drift.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 critical, 0 high, 0 medium, 0 low
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | atomic-write triplication (noted, deferred — own WP) |
| Security | 0 | 0 | nothing surfaced (the diff *adds* two validation guards) |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No language-level typechecker is configured for this repo (stdlib-only tooling
per plugin contract; branch-ci uses `python3 -m compileall`). Mechanical floor
run:

- `ruff check` on all 5 changed source modules → **All checks passed!**
- `python3 -m compileall` on all 5 changed source modules → **OK**
- `uv run pytest tests/unit/` → **1899 passed, 9 skipped**; characterisation
  suite → 11 passed.

Delta vs BASE: zero new errors. Build Verification section empty → does not
block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: (uncommitted at review time; single remediation concern)
  module_fan_out: 1 top-level dir (plugins/sulis/scripts) + 1 ADR
  severity: clean
Size (PH-02):
  lines_added: 344, lines_removed: 15, files_changed: 12 (6 tests)
  severity: clean (within 200-line/5-file band by intent; cohesive single concern)
Safety (PH-03):
  migration_count: 0  schema_idl_count: 0  infra_files: 0  secret_pattern_hits: 0
  severity: clean
Completeness (PH-04):
  new_source_without_test: 0 (4 new test classes cover the 4 behaviour fixes)
  doc_only_fix_without_test: ADR-005 + docstrings (correctly test-free)
  severity: clean
```

### Findings in the Changes

None. Per-fix lens notes:

- **FIX 1 (`migrate_lifecyclerun_v1_to_v2.py`) — Security/Quality.** Replaces a
  non-atomic `path.write_text(...)` with a tmp+fsync+`os.replace` `_atomic_write`
  helper mirroring `_discovery/minter._atomic_write` and
  `_entity_evolve._persist_envelope`. Closes a torn-write risk on stored
  history (the lone non-atomic writer in the change). Test-backed by
  `TestMigrateStoreAtomicWrite` (no-tmp-left, valid-v2, no-partial-on-crash via
  monkeypatched `os.replace`). The migration's fsync is deliberately NOT wrapped
  in best-effort (unlike `_persist_envelope`) — a one-shot history mutation
  should surface a durability failure, consistent with the minter.
- **FIX 2 (`_entity_evolve._persist_envelope`) — Quality/Resilience.** Adds
  `os.fsync` before the rename, wrapped `try/except OSError: pass` to honour the
  module's best-effort contract — making the existing "survives a crash"
  docstring true. Test-backed by `TestPersistEnvelopeFsyncsBeforeRename`
  (fsync-before-replace ordering; graceful degradation on fsync failure).
- **FIX 3 (`_brain_query.find_current_for_tenant`) — Security (SEC: input
  validation / path traversal).** Validates `tenant_id` against the existing
  `_tenant_emission._TENANT_ID_RE` (reused, not duplicated) BEFORE the id is
  joined into the central-home path. Closes the `..`-in-tenant-id traversal
  seam on the read path. Lazy import preserves the existing read-seam→emit-side
  no-cycle discipline. Test-backed by
  `TestFindCurrentForTenantValidatesTenantId` (7 malformed cases incl. `..`,
  plus a valid case).
- **FIX 4 (`_entity_evolve._open_window`) — Security/Quality.** Validates
  `generated_by` against a new canonical `_LIFECYCLERUN_ID_RE`, added to
  `_lifecyclerun_emission.py` (the home of lifecyclerun id patterns, alongside
  the sibling `_ACTOR_ID_RE`/`_STEP_ID_RE`/`_PROJECT_ID_RE`) and imported — no
  loose duplication. Rejects a malformed ref before it is attached to a
  persisted window (the edge is written outside the schema-validated body).
  Test-backed by `TestOpenWindowValidatesGeneratedBy` (5 malformed cases, valid,
  and `None`).
- **FIX 5 (ADR-005 + docstrings) — Documentation accuracy.** Reconciles the
  over-stated central-home claim: adds a "wired-but-not-yet-defaulted" note to
  ADR-005 Consequences and to the `_tenant_emission` / `find_current_for_tenant`
  docstrings, clarifying that Product/Opportunity production CLIs default
  `base_dir` to repo-local `.brain/instances` and the central home is reached in
  production only by the minter (Project). No CLI behaviour changed.
- **Fixture correction (5 test files) — Quality (Boy Scout, in-scope).**
  `_RUN_ID` fixtures used `...RUN...` literals containing `U`, which is not in
  the Crockford base32 alphabet (the production `_ulid` could never emit them).
  FIX 4's canonical regex correctly rejected them; corrected to valid `...RVN...`
  literals (length + uniqueness preserved).

### Findings in the Neighbours

None. The neighbour ring (the minter's `_atomic_write`, `_entity_adapter_local`,
`_brain_emit_helper.central_tenant_home`, the `_lifecyclerun_emission` regex
family) was inspected for the reuse points; all reuse is consistent with
existing patterns.

### Watch List

- **Atomic-write triplication** (architecture, `dependency-direction`-adjacent).
  Three call sites now share the tmp+fsync+rename shape across two packages
  (`_discovery/minter` vs the brain-store writers) with differing tmp-naming and
  same-dir invariants. No failing characterisation test grounds an extraction,
  and the task remit forbids refactoring beyond the fixes, so this is a Watch
  List note, not a delta — candidate for its own WP if a shared
  `atomic_write_text` helper is wanted.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none in `.security/` for this slice.
- **Pattern suggesting full audit:** none — diff is self-contained.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` (clean) + `python3 -m
  compileall` (OK) + `uv run pytest tests/unit/` (1899 passed) on changed
  modules. No mypy/pyright configured (stdlib-only plugin contract) — recorded
  as the project's floor, not a skip. Delta vs BASE: 0 new errors.
- [✓] **CR-02 Dispatch shape.** Diff 344 lines / 12 files. Single-reader pass
  used despite nominally exceeding the threshold: the change is a cohesive
  remediation, 6 of 12 files are tests, and each source delta is <40 lines and
  was read end-to-end. Recorded as a judgement call, not a budget shortcut.
- [✓] **CR-03 Full-file reads.** All 5 changed source files + ADR read
  end-to-end (each well under the size where sampling risk arises). Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings (none blocking) + per-fix notes
  cite file + symbol.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build
  Verification empty; no files sampled; all lenses produced output; no PH-03
  high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (1 Watch List
  note). Security: nothing surfaced — the diff *adds* two input-validation
  guards reusing canonical regexes; no new secrets/external calls/injection
  surface. Quality: nothing surfaced — every behaviour change is RED-first
  test-backed; no dead surface, no contract drift, no CR-10 perf anti-pattern
  (no loops over DB/RPC/FS introduced).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: clean.
  PH-03 Safety: clean (0 migrations/schemas/secrets/infra). PH-04 Completeness:
  clean. No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff origin/change/feat-product-project-opportunity-evolution`
- **Neighbour expansion:** git grep (reuse-point inspection); cap not reached.
- **Scanners run:** ruff (lint), compileall (build floor), pytest (test floor).
- **Scanners unavailable:** mypy/pyright (not configured for this repo);
  Gitleaks/Semgrep/Trivy not run (no secret/dependency/Docker signal in diff).
- **Lenses dispatched in parallel:** no — single-reader per CR-02 judgement for
  this cohesive sub-200-line-per-file diff.
