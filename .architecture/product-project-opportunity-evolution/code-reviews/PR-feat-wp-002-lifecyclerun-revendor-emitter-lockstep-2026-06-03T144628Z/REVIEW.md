# Code Review: WP-002 — re-vendor LifecycleRun v2.2.0 + migrate emitter core (atomic lockstep)

> **Timestamp:** 2026-06-03T144628Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-lifecyclerun-revendor-emitter-lockstep → change/feat-product-project-opportunity-evolution
> **Files changed:** 11 (7 modified + 4 new test files)
>
> **Outcome:** Ready to merge

---

## At a glance

This change swaps the lifecycle-run records over from a free-text step name to a
proper reference that points at a named, reusable step definition — and it
re-vendors the matching schema at the same time, in one go, so the two never
disagree. There are no build errors, the full test suite passes (1939 tests),
and every new behaviour is covered by a test. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: ~200 lines across the schema, three emit
modules, and their tests.

**Scope — clean.** One concern only: the step-name → step-reference migration.
No unrelated changes rode along.

**Safety — worth noting.** One vendored schema file was replaced (the
lifecycle-run schema, moved from version 1.0.0 to 2.2.0). The risky part of a
schema swap is the window where the schema and the code that writes records
disagree — every write would be rejected. This change closes that window by
moving both together in a single change, and an end-to-end test proves a
freshly-written record passes the new schema in one pass.

**Completeness — clean.** Four new test files; every new code path has a test.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high/medium in the diff; Build Verification empty;
all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). ruff clean; py_compile clean; pytest 1939 passed / 9 skipped.
- **PR Hygiene:** 0 blocking findings. PH-03 note: 1 vendored schema re-vendored, migrated in lockstep (ADR-004) — no reject-on-invalid window.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings. Downstream callers (`wpx-pipeline`, `wpx-train`, `sulis-change`) call only the high-level helpers whose public signatures are preserved — the `step_name`→`step` swap on the low-level `compose_lifecyclerun`/`emit_lifecyclerun` is transparent to them.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Empty. Commands run on HEAD: `ruff check` (All checks passed), `py_compile` (clean), `uv run pytest tests/` (1939 passed, 9 skipped). Raw outputs in `tool-outputs/`.

### Lens output

**Architecture lens: nothing surfaced.** Checks run: dependency direction (resolver is a pure stdlib lookup, no new infra import); single-source-of-truth for the three Step ULIDs (cite WP-001's `steps.jsonld`, no inline mint — ADR-001/ADR-004); graceful-degradation discipline preserved (`dict | None` + `_safely` unchanged); lockstep atomicity (schema + emitter move in one change — ADR-004 mandate).

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no auth/access surface, no injection, no new external call, no secrets). The schema's `inputs_ref`/`outputs_ref` carry `x-sensitive` but are NOT wired by the emitter (correctly out of scope). No secret-shaped strings in the diff.

**Quality lens: nothing surfaced.**
1. Build Verification follow-up: none (baseline clean).
2. JSX/template scan: N/A (no frontend files).
3. Dead-surface: none — `_resolve_step`, `_NAME_TO_STEP_ULID`, `_STEP_ID_RE`, and `run_id` are all exercised by tests.
4. Contract-drift: verified the emitter's `_STEP_ID_RE` (`^dna:step:[0-9A-HJKMNP-TV-Z]{26}$`) accepts exactly the strings the vendored schema pattern (`^dna:(step):...`) accepts — checked against the 3 canonical ULIDs + reject cases; they agree.
5. Test-coverage observation: 16 new DoD tests + 2 migrated; new emitter file `_lifecyclerun_emission.py` at 100% line coverage; lockstep integration test proves schema+emitter agree in one pass.
6. Style/readability: clean (ruff).
7. CR-10 performance: no anti-pattern matches. Only loops are the bounded `for _ in range(26)` ULID encoder (no IO) and a pre-existing `glob` loop outside this change. Emit path is event-shaped single-entity.

### Findings in the Changes

None.

### Findings in the Neighbours

None. Caller-signature compatibility verified for `wpx-pipeline`, `wpx-train`, `sulis-change`.

### Watch List

None.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff + py_compile + full pytest on HEAD. Base clean, Head clean (0 PR-introduced errors). Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified: cohesive single-concern backend WP, ~200 lines, all changed files <200 lines and read end-to-end. (11 files but 4 are new tests for the 3 source files; the source surface is 3 modules + 1 CLI + 1 schema.)
- [✓] **CR-03 Full-file reads.** All changed files >50 lines read end-to-end (source diff + each test file). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + quoted code where present (none this run).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced explicit "nothing surfaced" with checks enumerated.
- [✓] **CR-09 PR Hygiene applied.** Scope: clean (single feat concern). Size: clean (161+/41-, 11 files). Safety: note (1 vendored schema re-vendored, lockstep per ADR-004 — no reject-on-invalid window; 0 migrations, 0 secrets, 0 infra). Completeness: clean (4 new test files, 0 source-without-test). PH-03 high → not fired.

#### Run details

- **Diff source:** git diff origin/change/feat-product-project-opportunity-evolution
- **Neighbour expansion:** git grep for callers of emit_lifecyclerun / compose_lifecyclerun / emit_change_* / emit_lifecycle_step_event.
- **Scanners run:** ruff (lint), py_compile, pytest. Gitleaks/Semgrep/Trivy not available in this environment — no secret-shaped strings present in the diff by manual inspection.
- **Lenses dispatched in parallel:** no (single-reader, justified above).
