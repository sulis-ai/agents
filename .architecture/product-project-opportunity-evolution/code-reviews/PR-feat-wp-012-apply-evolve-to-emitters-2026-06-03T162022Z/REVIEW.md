# Code Review: feat/wp-012-apply-evolve-to-emitters — Apply evolve to Product/Opportunity emitters

> **Timestamp:** 2026-06-03T162022Z (ISO 8601 UTC)
> **Author:** WP-012 executor
> **Branch:** feat/wp-012-apply-evolve-to-emitters → change/feat-product-project-opportunity-evolution
> **Files changed:** 7 (2 source, 4 tests, 1 work-package doc)
>
> **Outcome:** Ready to merge

---

## At a glance

This change turns on version history for the Product and Opportunity records the
system writes. Instead of overwriting the latest snapshot each time, each save now
opens a dated "window" — closing the previous one and stamping the new one with the
run that produced it. The change is well-scoped, every new behaviour has a test, the
full test suite (1,844 tests) passes, and there are no build errors. Nothing needs
to be fixed before merge.

## What to fix

No issues that need attention.

One minor thing for awareness (not a blocker): when saving a record fails, the code
quietly moves on without writing a note anywhere about what went wrong. That is the
intended behaviour here — saving these records is a "nice to have" that must never
break the main operation — and it matches how the rest of the codebase already
handles these background saves. If save problems ever need diagnosing later, adding
a short log line at that point would help; it is not needed now.

## How this pull request is shaped

**Size — clean.** Small and focused: ~250 lines added across 7 files, all part of one
logical change.

**Scope — clean.** A single behaviour-preserving-where-it-should refactor, with the
test baseline updated in lockstep to prove the intended behaviour change.

**Safety — clean.** No database migrations, no schema files, no infrastructure
changes, no secrets.

**Completeness — clean.** New behaviour ships with a new test file plus updated
characterisation and integration tests.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high/medium in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output. No auto-downgrade
triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). ruff check pass; py_compile
  pass; full unit+characterisation suite 1844 passed, 9 skipped.
- **PR Hygiene:** 0 findings (PH-01 low, PH-02 low, PH-03 none, PH-04 none).
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single low is awareness-only and matches an established
  convention; no delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — evolve delegation is clean (no dependency inversion) |
| Security | 0 | 0 | none — no secrets/auth/injection/dependency/network surface |
| Quality | 1 (low) | 0 | silent best-effort swallow (matches `_brain_emit_helper._safely` convention) |

### Build Verification (CR-01)

Nothing surfaced. Commands run on HEAD over the changed `.py` files:
`ruff check` → "All checks passed!"; `python -m py_compile` → OK; behaviour
verification `uv run pytest tests/unit/ tests/characterisation/` → 1844 passed, 9
skipped. ruff is the project's configured linter (no mypy/pyright config present —
coverage gap recorded in Methodology). Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {refactor}              → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts)
  severity: low (single concern: apply-evolve refactor)

Size (PH-02):
  lines_added: 250, lines_removed: 102, total: 352
  files_changed: 7 (2 source, 4 test, 1 doc)
  generated_ratio: 0
  severity: low (≤350 line band; ≤10 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (new behaviour wired via new test_emitters_evolve.py)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/_product_emission.py:175` (and `_opportunity_emission.py:174`) — low (quality / architecture)

**Quoted text:**
```python
        try:
            evolve_entity(
                repo=repo,
                entity_type="product",
                entity_id=product["id"],
                new_fields=product,
                generated_by=generated_by,
            )
        except Exception:
            # Best-effort emit — never raise into the host operation.
            continue
```

**Observation:** the bare `except Exception` swallows every failure silently with no
log line. This is intentional (the WP Contract requires graceful degradation — the
host operation must never fail on an emit failure) and it matches the established
codebase convention (`_brain_emit_helper._safely` likewise swallows to `None` with no
log). Surfaced for awareness only: if persistence faults ever need diagnosis, a debug
log at the swallow point would help. Not a blocker; no delta drafted (CR-04 — no
failing characterisation test grounds it, and it conforms to convention).

### Findings in the Neighbours

Nothing surfaced. The direct neighbours — `_entity_evolve.evolve_entity` (callee, the
shared helper this change now delegates to), `_entity_adapter_local.LocalFileEntityAdapter`
(the file-backed port), and the test callers — are exercised end-to-end by the updated
test suite and carry no PR-exposed gaps.

### Watch List

- **`generated_by` has no production caller yet.** Both emit functions accept
  `generated_by: str | None = None`, but no production call site threads a real
  LifecycleRun ref in today (the emit-context wiring is future work; tests pass it
  explicitly). Intentional per the WP — recorded so a future reviewer does not read the
  default-`None` as dead code.
- **Project emit path deliberately not swapped.** Project still mints through
  `_discovery/minter.write_project_entity` (a `.sulis/projects` bag), not the
  EntityRepository port, so `evolve_entity` is not applied to it here. This is the
  ADR-006 reconciliation owned by WP-015 (gated by WP-014). The Project windows-only /
  no-prov contract is pinned at the helper seam (`generated_by=None`) in
  `test_emitters_evolve.py::TestProjectEvolvesWithoutProv`.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check <changed .py>`;
  `python -m py_compile <changed .py>`. Base behaviour confirmed green pre-refactor
  (WP-011 baseline 3 passed); Head: 0 new lint/compile errors; full suite 1844 passed.
  Coverage gap: no mypy/pyright config in the project — type-level checking limited to
  ruff's lint rules. Recorded.
- [✓] **CR-02 Single-reader pass.** Diff is 352 lines / 7 files — marginally over the
  5-file carve-out on file count but a single tightly-coupled logical refactor (one
  source change replicated across two sibling emitters + their tests). Read all changed
  files end-to-end rather than parallel-dispatching; recorded as a deliberate carve-out
  given the homogeneity and small line count.
- [✓] **CR-03 Full-file reads.** All changed source + test files read end-to-end
  (diffs reviewed in full; the two source files are <200 lines each). Unread: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired
  (Build Verification empty; all files read end-to-end; all lenses produced output;
  PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency direction
  clean, resilience swallow matches convention, proof via real-adapter tests). Security:
  nothing surfaced (primitives SEC-01..07 / SC-01..04 N/A — no auth/injection/secret/
  dependency/network surface in the diff). Quality: 1 finding + dead-surface (none) +
  contract-drift (none, default-None param is intentional, on Watch List) + test-
  coverage observation (new behaviour fully tested) + CR-10 perf (no anti-pattern: the
  per-item emit loop runs over size-1 product/opportunity lists, one file read + write
  each, no N+1 over a large collection).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single refactor). PH-02 Size:
  low (352 lines / 7 files). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets /
  0 infra). PH-04 Completeness: none (new test file accompanies new behaviour). PH-03
  high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff <base-sha 3908602>` (working tree vs the recorded
  worktree base; branch not yet pushed at review time — Step 6.5 runs pre-commit).
- **Neighbour expansion:** git grep / direct-import inspection (`evolve_entity`,
  `LocalFileEntityAdapter`). Within 20-file cap (3 neighbours considered).
- **Scanners run:** ruff (lint), py_compile. Gitleaks/Semgrep/Trivy not invoked — no
  secret/dependency/container surface in the diff to warrant them.
- **Scanners unavailable:** mypy/pyright (not configured in project).
- **Lenses dispatched in parallel:** no (single-reader carve-out, see CR-02).
