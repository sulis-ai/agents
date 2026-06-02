# Code Review: WP-003 — Author Trigger instances + vendor brain Trigger schema

> **Timestamp:** 2026-06-01T10:18:13Z (ISO 8601 UTC)
> **Branch:** feat/wp-003-author-triggers-instance → change/create-release-train-as-entities
> **Files changed:** 4 (3 source + 1 bookkeeping journal)
>
> **Outcome:** Ready to merge

---

## At a glance

Your change introduces two release-train Trigger entity instances, vendors the brain's Trigger JSON Schema locally so the project can validate them, and adds three unit tests that prove conformance. The build is clean, the tests pass, and the change is well-scoped. Two small style points were caught and fixed before this review was written — nothing left to do before merging.

## What to fix

No issues that need attention. The two small style points (unused import; an awkward inline-binding loop in an assertion's error message) were addressed inline before this review was written; both fixes preserve the same test behaviour and the suite still passes.

## How this pull request is shaped

**Size — clean.** 4 files, ~291 lines added. Most of that is the vendored JSON Schema (a verbatim copy from the brain's build output, ~86 lines) and the JSON-LD entity data itself (~40 lines). The actual reviewable code is ~108 lines of test code.

**Scope — clean.** Single concern: WP-003's Trigger contract. One feature commit; one logical change.

**Safety — clean.** No database migrations, no infrastructure files, no lock files, no secret patterns. The vendored schema is byte-equivalent to the upstream source (provenance preserved).

**Completeness — clean.** Three tests cover the new entity instance — file parses, both Triggers present with expected names + kinds, and each Trigger validates against the brain JSON Schema.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06.

No auto-downgrade triggers fired:
- Build Verification empty (CR-01 baseline clean).
- All files >50 lines read end-to-end (CR-03).
- All three lenses produced output (CR-07).
- PR Hygiene at note severity across PH-01..PH-04; no PH-03 high to trigger CR-06 rule 4.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01).
- **PR Hygiene:** 0 findings; all 4 primitives at note severity (CR-09 / PH-01..PH-04).
- **In the changes:** 2 findings, both low (quality lens; addressed inline before report write).
- **In the neighbours:** 0 findings (neighbour ring empty — no current consumers of the new artifacts).
- **Draft fixes:** 0 (both inline-addressed during the review).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (nothing surfaced) |
| Security | 0 | 0 | — (nothing surfaced) |
| Quality | 2 (both low, addressed inline) | 0 | F-01 unused `import pytest` → fixed by re-purposing via `pytest.fail`; F-02 awkward nested-loop in assertion message → refactored to explicit for-loop |

### Build Verification (CR-01)

No PR-introduced errors.

Checks run:
- `python -m py_compile plugins/sulis/scripts/tests/unit/test_triggers_instance_valid.py` → exit 0
- `json.load` of both new JSON artifacts → exit 0
- `pytest plugins/sulis/scripts/tests/unit/` → 1187/1187 (incl. 3/3 new) → exit 0

Coverage gap: the repo has no ruff / mypy / black config, so no formal lint/typecheck ran beyond `py_compile`. Surrogate-mechanical-baseline approach is documented and consistent with project conventions (matches the actor/credential/tenant entity-instance pattern that ships without a separate lint pass).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean
  module_fan_out: 2 top-level dirs              → clean
  severity: note (single concern, WP-003 Contract)

Size (PH-02):
  lines_added: 291, lines_removed: 0, total: 291
  files_changed: 4
  source_files_excluding_journal: 3
  source_lines_excluding_journal: ~234
  band: small
  severity: note

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 1 (trigger.schema.json — vendored, byte-equivalent to upstream)
  infra_files: 0
  lock_files: 0
  secret_pattern_hits: 0
  severity: note

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  test_file_count: 1
  test_count: 3
  severity: note
```

### Findings in the Changes

#### F-01 — low (quality) — addressed inline

- **File:** `plugins/sulis/scripts/tests/unit/test_triggers_instance_valid.py`
- **Line (original):** 25
- **Evidence:** `import pytest` declared but never used at the symbol level in the original draft.
- **Why it matters:** Dead imports are noise; they hint to future readers that `pytest`'s API is being used somewhere when it isn't.
- **Recommendation:** Either remove the import or introduce a `pytest.*` usage.
- **Fix applied:** Replaced the ad-hoc nested-loop assertion-formatting in `test_each_trigger_passes_brain_schema` (lines 103-110) with `pytest.fail("...")`. The import now has a documented purpose: producing the rich error-message-on-failure path. Two findings, one inline fix.

#### F-02 — low (quality) — addressed inline

- **File:** `plugins/sulis/scripts/tests/unit/test_triggers_instance_valid.py`
- **Line (original):** 103-110
- **Evidence:** `for trg in [triggers[i]] for ...` nested-iterable was used to inline-bind a name without an explicit statement.
- **Why it matters:** Idiomatic-but-clever Python in test code that humans (and AI agents) read under stress. Linter heuristics won't flag this, but the next maintainer will pause.
- **Recommendation:** Use an explicit `for` loop with a `pytest.fail` payload.
- **Fix applied:** Refactored to a plain for-loop accumulating error lines, then `pytest.fail`. Tests still pass; readability up.

### Findings in the Neighbours

None.

Direct neighbours scanned:
- `plugins/sulis/scripts/tests/unit/test_triggers_instance_valid.py` is the only consumer of both new artifacts (`trigger.schema.json` + `triggers.jsonld`).
- The future WP-007 drift detector (per TDD) will be the second consumer; it does not yet exist.
- TDD/ADR/WP markdown files reference the instances by name but are documentation, not code neighbours.

### Watch List

- **Cross-WP coordination — `for_workflow` ULID:** the two Triggers reference `dna:workflow:01KT0RTRA1NWFW00000000000A`. WP-001 must adopt this exact ULID when it authors `workflow.jsonld`. This is documented in the test file's module docstring + in the WP-003 journal's plan approach. No fix needed in this PR; it's a precondition for WP-007's drift detector to resolve cross-entity refs cleanly.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none (no `.security/release-train-as-entities/` viability reports).
- **Pattern suggesting full audit:** none (the diff is data + a unit test; no broader gap pattern surfaced).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python -m py_compile`; `json.load` (twice); `pytest unit/` (1187/1187 inc. 3/3 new). Base: clean. Head: clean. Coverage gap: no project-wide ruff/mypy/black config; surrogate-mechanical-baseline (py_compile + json.load + pytest) used and noted.
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Justification: 4 files / 291 lines on the wire, but 1 file is auto-generated bookkeeping (the journal); 1 file is the verbatim upstream vendor copy (`trigger.schema.json`); 1 file is 40-line pure JSON-LD data; only 1 file (108-line test) carries executable logic. Effective reviewable surface ≈ 108 LOC. Additional constraint: this skill runs inside the executor subagent — the harness's Agent tool (used by /code-review for parallel lens dispatch) is unavailable in this context; the three-lens checklist was applied sequentially against the read files.
- [✓] **CR-03 Full-file reads.** All 3 source files >50 lines read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Both findings cite file:line + quoted evidence.
- [✓] **CR-05 Severity rubric.** 0 critical, 0 high, 0 medium, 2 low. Neighbour ring empty so no downgrade applied.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checklist run; Security: 0 findings + primitive checklist (SEC-01..07, SC-01, INF-04, DAT-03); Quality: 2 findings (both addressed inline) + jsx-scan N/A + dead-surface scan + contract-drift check + test-coverage observation + CR-10 perf checks (no matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note. PH-02 Size: note (small band). PH-03 Safety: note. PH-04 Completeness: note. No auto-downgrade fired.

#### Run details

- **Diff source:** `git diff --staged` against `change/create-release-train-as-entities` (pre-commit state — feature branch tip is the change-branch tip at the time of review; commit happens at Step 7).
- **Neighbour expansion:** `git grep` over `plugins/`, `.github/`, `.architecture/`.
- **Neighbour cap:** 0 of 0 considered, 0 excluded (no current code neighbours).
- **Scanners run:** none (no executable security-sensitive surface in the diff).
- **Scanners unavailable:** gitleaks, semgrep, trivy (not invoked — out of scope for this diff class).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out + subagent constraint (Agent tool unavailable).
