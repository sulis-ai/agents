# Code Review: WP-007 — Sulis-Origin is a formal git trailer (blank-line separator)

> **Timestamp:** 2026-06-08T082531Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** feat/wp-007-trailer-blank-line-separator → change/feat-live-origin-stamping
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes a real bug: commit-origin stamps were being attached in a way
that git's own tools couldn't see. The fix is small, well-targeted, and fully
backed by tests — including a test that makes a real commit and confirms git now
recognises the stamp. No build errors, nothing risky, and the existing tests all
still pass. Ready to merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — looks good.** Small and focused: 189 lines across 3 files (one source
file, its test file, and a one-line correction to the verification runbook).

**Scope — looks good.** Single concern: one bug fix, its tests, and the matching
doc update. Nothing unrelated bundled in.

**Safety — looks good.** No database changes, no infrastructure or config files,
no secrets. The change is confined to how a commit message string is assembled.

**Completeness — looks good.** New behaviour comes with new tests. The headline
test makes a real git commit and asks git itself whether it recognises the stamp
— which is exactly the right way to prove this fix works.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high findings in the changes; Build Verification
empty; the diff is within the single-reader carve-out and was read end-to-end;
all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 — all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none surfaced |
| Security | 0 | 0 | none surfaced |
| Quality | 0 | 0 | none surfaced |

### Build Verification (CR-01)

Mechanical baseline ran on the changed Python (`_origin_stamp.py`,
`tests/unit/test_origin_stamp.py`):

- `ruff check` — All checks passed (HEAD). Base was already clean → 0 delta.
- `python3 -m compileall` — exit 0, clean.
- `python3 -m pytest tests/unit/test_origin_stamp.py` — 19 passed.

No PR-introduced errors. Build Verification section is empty → does not block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {fix}                    → clean (single concern)
  module_fan_out: 2 top-level areas (scripts, architecture doc) → clean
  severity: none

Size (PH-02):
  lines_added: 189, lines_removed: 13, total: 202
  files_changed: 3
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (within ≤5 files; ~200 line band, single-reader justified)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (no new source files; modified file gains tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None. Each lens output below.

**Architecture lens: nothing surfaced.** Checks run: no new imports (the fix is
two pure helper functions + one changed local variable assignment, all within the
existing `_origin_stamp` module); no new I/O, network, or external calls; no new
singletons; dependency direction unchanged. The two new helpers
(`_is_trailer_line`, `_ends_in_trailer_block`) are pure string predicates with no
side effects.

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no new
inputs, no auth/access path, no injection sink — the change only decides a `\n`
vs `\n\n` separator on an already-validated message string), SC-01..04 (no
dependency changes). The pre-existing trailer-injection defenses
(`_has_control_char` in `format_trailer` / `parse_origin_env`) are untouched and
still on the path. The new code introduces no way to smuggle a forged trailer:
the trailer text still comes from `format_trailer`, which this change does not
modify. Scanners: none available in-environment (Gitleaks/Semgrep/Trivy absent);
no secret patterns in a 202-line string-handling diff (manual inspection).

**Quality lens output (CR-07, all required items):**

1. **Build Verification follow-up:** none (CR-01 clean).
2. **JSX / template identifier scan:** N/A — no TSX/JSX/Vue/Svelte files in diff.
3. **Dead-surface:** none. Both new helpers are consumed: `_ends_in_trailer_block`
   by `append_trailer_to_message`; `_is_trailer_line` by `_ends_in_trailer_block`.
   No unused imports (test adds `os`, `Path`, `append_trailer_to_message` — all
   used).
4. **Contract-drift:** none. `format_trailer`, the env grammar, and the cockpit
   reader are untouched per the WP Contract; the trailer VALUE is unchanged. The
   only behavioural change is the separator, verified against git's own parser.
5. **Test-coverage observation:** strong. The diff adds a real-git round-trip test
   (`test_conventional_subject_yields_git_recognised_formal_trailer`) that drives
   the actual `prepare-commit-msg` hook and asserts via
   `git log --format='%(trailers:key=Sulis-Origin,valueonly=true)'` AND
   `git interpret-trailers --parse` — proving git-native recognition, not just the
   regex reader. Plus the three Contract cases (bare subject, subject+body,
   Co-Authored-By join) and idempotency at the unit level.
6. **Style / readability:** clear. Helpers are small, single-purpose, and
   documented with the why (the Conventional Commit defect). No TODO/FIXME added.
7. **Performance procedural checks (CR-10):** no anti-pattern matches. The added
   code is O(n) over the lines of one commit message (a handful of lines); no
   loops over collections, no DB/RPC/filesystem calls, no quadratic scans.

### Findings in the Neighbours

None. Direct consumers of `append_trailer_to_message` are the
`prepare-commit-msg` hook and `stamp_origin` — both re-tested green (34 passed
across origin/hook/executor suites at Step 4 BLUE). The change is behaviour-
preserving for all cases the old heuristic already handled correctly (subject+body,
existing trailer block, idempotency) and only corrects the misdetection of bare
Conventional Commit subjects.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none found under `.security/feat-live-origin-stamping/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check _origin_stamp.py tests/unit/test_origin_stamp.py` (the project's configured linter per pyproject.toml); `python3 -m compileall`; `pytest tests/unit/test_origin_stamp.py`. Base: 0 errors. Head: 0 errors. Coverage gap: no mypy/pyright configured in project (recorded, not skipped silently).
- [✓] **CR-02 Single-reader pass justified by diff size: 202 lines, 3 files** (≤200-line band, ≤5 files — within carve-out).
- [✓] **CR-03 Full-file reads.** Changed region of `_origin_stamp.py` (the two new helpers + `append_trailer_to_message`) and the full new test section read end-to-end. The runbook doc change is a 1-paragraph callout. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; lens outputs cite the specific functions/behaviours examined.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed. Security: 0 findings + primitives listed. Quality: 0 findings + all 7 required outputs produced (including CR-10 = no matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `fix` concern). PH-02 Size: none (202 lines / 3 files). PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none (modified file gains tests). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff change/feat-live-origin-stamping` (uncommitted working tree on the WP branch).
- **Neighbour expansion:** git grep for callers of `append_trailer_to_message` — `hooks/prepare-commit-msg` and `stamp_origin` (same module).
- **Neighbour cap:** 2 of 2 considered, 0 excluded.
- **Scanners run:** ruff, compileall, pytest. Gitleaks/Semgrep/Trivy unavailable in-environment.
- **Scanners unavailable:** Gitleaks, Semgrep, Trivy (not installed) — explains absence of automated secret/CVE scan; manual inspection of a 202-line string-handling diff found no secrets and no dependency changes.
- **Single-reader pass:** justified by diff size (CR-02 carve-out).
