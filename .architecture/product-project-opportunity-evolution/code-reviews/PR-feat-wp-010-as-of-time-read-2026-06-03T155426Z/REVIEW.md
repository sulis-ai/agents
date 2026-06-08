# Code Review: feat/wp-010-as-of-time-read — Add as-of-time window read to the read seam

> **Timestamp:** 2026-06-03T155426Z (ISO 8601 UTC)
> **Author:** executor (WP-010)
> **Branch:** feat/wp-010-as-of-time-read → change/feat-product-project-opportunity-evolution
> **Files changed:** 2 (1 production module, 1 new test file)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a single read function that answers "which version of this thing was true at a given moment?" — the read half of the time-travel feature whose write half already shipped. It reuses the existing file-walking code rather than adding a new way to read the store, comes with a full set of tests written before the code, and the build is clean. One small type-checking nit surfaced during review and was fixed on the spot. Nothing left to address.

## What to fix

No issues that need attention.

One thing was found and already fixed during the review: the type checker pointed out that the code compared a timestamp against a value it couldn't prove was non-empty. The fix made the "still-current / open-ended" check explicit, which both satisfied the checker and made the intent clearer. The fix is in the change you're about to merge.

## How this pull request is shaped

**Size — clean.** About 84 lines of production code in one file, plus a new test file. Single concern: the as-of-time read.

**Scope — clean.** One feature, one `feat:` change, one module touched.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — clean.** Tests came first: 11 tests written and seen to fail before the function existed, then made to pass. Several run against a real on-disk store (no fakes), proving the read selects exactly what the write side produces.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty (the one PR-introduced mypy finding was fixed inline before bundle write); both changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 open errors. 1 PR-introduced mypy narrowing warning found and **fixed inline** (`_brain_query.py:184`, `str < None`); head re-verified clean.
- **PR Hygiene:** 0 high/medium findings. Size is over the 200-line line-count carve-out but the excess is a new test file; production change is ~84 lines / 1 module. Single-reader pass justified.
- **In the changes:** 0 open findings (1 fixed inline).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single finding was fixed inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — reuses `iter_entities` read seam, no new infra import / external call / secret |
| Security | 0 | 0 | none — pure local-file read, lexicographic compare, no auth/injection/SSRF surface |
| Quality | 0 open (1 fixed) | 0 | mypy narrowing at `:184` — fixed inline |

### Build Verification (CR-01)

Mechanical baseline ran on BASE and HEAD:

- `ruff check` — BASE clean, HEAD clean.
- `ruff format --check` — HEAD formatted.
- `mypy --ignore-missing-imports _brain_query.py` — BASE clean (0 errors). HEAD initially raised:

  `_brain_query.py:184: error: Unsupported operand types for < ("str" and "None") [operator]`

  Root cause: `valid_to = window.get("valid_to")` is `Any | None`; the open-window guard used `if valid_to in (None, ""):` which mypy does not narrow through, so the subsequent `as_of < valid_to` saw a possible `None`. Runtime-safe (the guard returns before the comparison when `valid_to` is falsy), but a real type-soundness gap.

  **Fix applied inline (Path A):** replaced the membership guard with `if not valid_to:` (covers both sentinels None and "", and narrows `valid_to` to a non-empty `str` in the else branch). Re-ran mypy → 0 errors; ruff + format clean; all 11 tests green. Head is now clean — Build Verification is empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):    commit_type_spread {feat}; module_fan_out 1            → severity none
Size (PH-02):     +89/-1; 2 files; production ~84 lines; test ~348 lines → severity low
                  (over 200-line line threshold, but excess is the new test file)
Safety (PH-03):   migrations 0; schema/idl 0; infra 0; secrets 0         → severity none
Completeness (PH-04): new_source_without_test 0; new tests 1 (TDD-first) → severity none
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

None open. One fixed inline (see Build Verification).

### Findings in the Neighbours

None. Direct neighbours of the touched symbol: `iter_entities` (reused unchanged), `_entity_evolve.evolve_entity` (the write side this read pairs with — unchanged, exercised by the new MEA-09 test). No gaps exposed.

### Watch List

None.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas covering this surface.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check`, `ruff format --check`, `mypy --ignore-missing-imports`. Base mypy: 0 errors. Head: 1 PR-introduced error, fixed inline, re-verified 0. Coverage gap: project does not configure mypy in `pyproject.toml` (stdlib-only CLI contract); ran mypy ad-hoc on the changed module as the typecheck floor.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size: production change ~84 lines / 1 module / 2 files total (test file is the bulk). Both files read end-to-end.
- [✓] **CR-03 Full-file reads.** `_brain_query.py` (read seam, full) and `tests/unit/test_brain_query_as_of.py` (full) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line and the exact mypy error text.
- [✓] **CR-05 Severity rubric.** Applied. The fixed finding was medium (type-soundness gap, runtime-safe). 0 open.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty post-fix; both files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (reuses read seam; no infra import / external call / secret / domain reach-through). Security: nothing surfaced (pure local-file read; lexicographic compare; malformed-file skip inherited from iter_entities; no auth/injection/SSRF/secret surface). Quality: 1 finding (mypy narrowing) fixed inline; tests present (real-adapter MEA-09); no dead surface; no contract drift; CR-10 performance — O(N) walk over one entity type identical to existing `find_entities`, inner window scan bounded by window count, no N+1 introduced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope none; PH-02 Size low; PH-03 Safety none; PH-04 Completeness none (TDD-first). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-product-project-opportunity-evolution` (working tree vs base branch).
- **Neighbour expansion:** git grep on `read_as_of` / `iter_entities` / `_window_contains`; 2 neighbour symbols (iter_entities, evolve_entity), both unchanged.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** ruff, mypy. (Gitleaks/Semgrep/Trivy not run — no new dependency, no secret-shaped string, no Dockerfile/infra in the diff; recorded as scoped-out, not a silent skip.)
- **Lenses dispatched in parallel:** no — single-reader carve-out (small production diff), all three lens checklists applied by the single reader.
