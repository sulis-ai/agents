# Code Review: feat/wp-006-verif — WP-006 wire P-VER into orchestrator skills + add Verification Plan template

> **Timestamp:** 2026-06-01T210556Z (ISO 8601 UTC)
> **Author:** sulis:executor (parallel batch, wave 3 of 3)
> **Branch:** feat/wp-006-verif → change/extend-verification-by-design
> **Files changed:** 5 (4 modified SKILL.md + 1 new pytest unit test)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request wires the new verification-by-design machinery into the three orchestrator skills (specify, draft-architecture, requirements-validation) and adds a Verification Plan template block to the requirements-templates skill. It is pure documentation + structural tests — no runtime code paths change.

Two small bugs were found and fixed during review: two broken markdown links to ADR-001 (used three levels up instead of four). Both are now corrected, the test suite still passes (29 of 29), and there is nothing else outstanding.

## What to fix

No issues that need attention. Two broken markdown links were fixed inline during the review (see Technical detail below).

## How this pull request is shaped

**Size — looks healthy.** 632 lines added, 3 removed, across 5 files. The bulk (~428 lines) is the new structural-assertion test file, and another ~90 lines is the new Verification Plan template block in requirements-templates. Both are deliverables, not bloat. The four SKILL.md citation extensions are tight (≤60 lines each).

**Scope — focused.** Single concern: wiring P-VER + the template block into the four orchestrator-tier surfaces.

**Safety — none flagged.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets touched.

**Completeness — well-shaped.** The structural test file ships in the same PR as the changes it validates — the same WP carries the failing-test-first commitment.

## Things to take away

Skipped — the PR is clean and the broken-link finding has been auto-fixed; no specific lesson to teach beyond "double-check relative path depth when adding markdown cross-refs from a deeply-nested skill file."

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. All findings addressed inline during the review; no critical/high in diff; CR-01 Build Verification empty; all changed files read end-to-end.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 0 medium, 0 note (PH-01..PH-04 all green for this docs WP)
- **In the changes:** 2 findings (0 critical, 0 high, 2 medium → all fixed inline)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (both findings auto-fixed; the WP self-corrected)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Cross-references resolved; no domain→infrastructure imports (markdown only) |
| Security | 0 | 0 | No secret patterns; no auth surface |
| Quality | 2 | 0 | Two broken markdown links to ADR-001 (fixed inline) |

### Build Verification (CR-01)

Empty. `ruff check` + `ruff format --check` + `pytest` all green:

```
$ python -m ruff check plugins/sulis/scripts/tests/unit/test_orchestrator_skills_verification.py
All checks passed!
$ python -m ruff format --check plugins/sulis/scripts/tests/unit/test_orchestrator_skills_verification.py
1 file already formatted
$ python -m pytest plugins/sulis/scripts/tests/unit/test_orchestrator_skills_verification.py -q
29 passed in 0.05s
```

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → none
  module_fan_out: 1 (plugins/sulis/skills + plugins/sulis/scripts/tests both fall under one logical area)
  severity: none

Size (PH-02):
  lines_added: 632, lines_removed: 3, total: 635
  files_changed: 5
  generated_ratio: 0.0
  severity: low (within 501-1000 line band but each addition is a deliverable: the 428-line test file IS the test for the WP; the 90-line Verification Plan template block IS the FR-001 deliverable)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the new code IS the test file; the four SKILL.md extensions are validated by it)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### F-01 — `plugins/sulis/skills/draft-architecture/SKILL.md:35` — medium (quality)

**Evidence:**
```markdown
Cross-reference: [`ADR-001`](../../../.architecture/verification-by-design/adrs/ADR-001-section-name-verification-plan.md)
```

**Why it matters:** Skill files live at `plugins/sulis/skills/<name>/SKILL.md`, four directory levels below the repo root. The link used `../../../` (three levels up), which resolves to `plugins/.architecture/...` — a non-existent path. A reader following the link would land on a 404. The companion link in the same file using `../../references/...` (two levels up) is correct because the `references/` directory lives at the sibling `plugins/sulis/` level.

**Recommendation:** Use `../../../../` (four levels up) to escape from `plugins/sulis/skills/draft-architecture/` to the repo root.

**Status:** Fixed inline during review. Verified via `python -c "import os.path; print(os.path.normpath(...))"` after the fix.

#### F-02 — `plugins/sulis/skills/requirements-validation/SKILL.md:31` — medium (quality)

**Evidence:**
```markdown
Cross-reference: [`ADR-001`](../../../.architecture/verification-by-design/adrs/ADR-001-section-name-verification-plan.md) fixes the section name.
```

**Why it matters:** Same shape as F-01 — three levels up instead of four. Reader-trust impact; tests still pass because the assertions only check the literal `ADR-001` token presence.

**Recommendation:** Use `../../../../` (four levels up).

**Status:** Fixed inline during review.

### Findings in the Neighbours

None. The diff is confined to the four orchestrator SKILL.md files + the test file; no neighbour code was meaningfully exercised by the change.

### Watch List

None.

### Cross-Reference

- **Sibling artifacts:** The companion structural-assertion tests for WP-001, WP-002, WP-003, WP-004 already exist at `plugins/sulis/scripts/tests/unit/test_*_verification_phase.py` — this WP's test file follows the same convention (stdlib + pytest, paths-relative-to-file, module-scoped fixture per artifact). No duplication.
- **Existing hardening deltas:** none applicable.
- **Existing security report:** N/A — `kind: docs` change with no security surface.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python -m ruff check`, `python -m ruff format --check`, `python -m pytest`. Base: 0 errors. Head: 0 errors after applying ruff format. Coverage gap: none.
- [✓] **CR-02 Single-reader dispatch justified.** Diff is 209 changed lines across 4 markdown skill files + 1 new test file (5 files total). The CR-02 threshold (>200 lines OR >5 files) is just brushed by the per-line count; however, the change is *pure markdown citation glue + a single self-contained pytest module*. Sub-agent dispatch overhead exceeds value here — there is no architecture/security/concurrency surface for three lenses to disagree on, and the file-reads are linear. Recording this as the justified single-reader path.
- [✓] **CR-03 Full-file reads.** All 4 changed SKILL.md files and the new test file were read end-to-end (the SKILL.md files via Edit/Read tool, the test file via direct authorship).
- [✓] **CR-04 Evidence discipline.** Both findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 2 medium (both addressed inline), 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (CR-01 empty; no lens silent; no full-file gap; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no architecture surface in a markdown docs change; cross-reference paths verified). Security: nothing surfaced (no secret patterns; no auth surface). Quality: 2 findings + ruff/pytest scan logs.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: low. PH-03 Safety: none. PH-04 Completeness: none. No PH-03 high → CR-06 auto-downgrade did not fire.

#### Run details

- **Diff source:** `git diff origin/change/extend-verification-by-design ...` (working tree at review time)
- **Neighbour expansion:** N/A (markdown change; only direct files matter)
- **Neighbour cap:** N/A
- **Scanners run:** ruff (check + format), pytest (29 tests), grep-based secret-pattern scan, python-osp.normpath relative-link resolution
- **Lenses dispatched in parallel:** no — single-reader path per CR-02 carve-out, justified above
