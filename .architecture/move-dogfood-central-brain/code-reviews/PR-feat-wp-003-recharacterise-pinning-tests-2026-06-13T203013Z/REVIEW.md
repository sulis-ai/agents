# Code Review: feat/wp-003-recharacterise-pinning-tests — Re-characterise pinning tests

> **Timestamp:** 2026-06-13T203013Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-003-recharacterise-pinning-tests → change/move-dogfood-central-brain
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a test that proves Sulis's own captured knowledge will live in the shared central home (next to your other settings) rather than being trapped inside a throwaway working copy. The test is deliberately marked "expected to fail for now", because the old in-place setting hasn't been removed yet — that removal is the next piece of work. The moment that removal happens, this test starts passing, and a built-in safety then forces that next piece of work to clean up the marker. No build errors, well-scoped, and one small consistency fix was already applied during review.

## What to fix

No issues that need attention.

One small consistency improvement was found and already applied during the review: the new test originally used a fixed temporary folder (`/tmp/sulis-dogfood-home`) for isolation, while the existing tests next to it use pytest's per-test temporary folder. Switched it to match the existing pattern so two test runs can never collide on the same folder.

## How this pull request is shaped

**Size — clean.** 96 lines across 2 files — a small, focused change.

**Scope — clean.** Single concern: re-characterising the brain-location tests. One new test file plus a clarifying comment on a kept test.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — clean.** This change *is* tests — it adds a new test and keeps the existing ones. Test-only by design.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output; no auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low) — resolved inline during review
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single finding was fixed inline; no delta queued)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced |
| Security | 0 | 0 | Nothing surfaced |
| Quality | 1 (resolved) | 0 | Test-isolation convention drift (fixed inline) |

### Build Verification (CR-01)

No PR-introduced errors. Commands run on HEAD:

- `ruff check` (the configured linter) → `All checks passed!` (exit 0)
- `ruff format --check` → `1 file already formatted` (exit 0)
- `python3 -m compileall` → exit 0
- Type-checker: N/A — repo-contract `type_check: ""` (stdlib-only tooling per plugin contract; no mypy/pyright configured). Recorded as a deliberate coverage gap, not a skip.

Raw outputs in `tool-outputs/ruff-head.log`, `tool-outputs/compile-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test}                   → clean (single concern)
  module_fan_out: 1 distinct top-level dir      → clean
  severity: none

Size (PH-02):
  lines_added: 96, lines_removed: 3, total: 99
  files_changed: 2
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (≤200 lines, ≤5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the new file IS a test)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/tests/unit/test_dogfood_resolves_central.py:77` — low (quality) — RESOLVED INLINE

**What:** The new test hardcoded `monkeypatch.setenv("SULIS_STATE_DIR", "/tmp/sulis-dogfood-home")` for settings-home isolation.

**Quoted text (before fix):**
```python
    monkeypatch.setenv("SULIS_STATE_DIR", "/tmp/sulis-dogfood-home")
```

**Why it matters:** The sibling tests in `test_brain_location.py` (lines 39, 49, 97, 112) all use pytest's `tmp_path` fixture — `monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "home-sulis"))` — which gives a per-test, auto-cleaned directory. A fixed `/tmp` path diverges from this established convention (CP-01) and is a shared, non-isolated location that could collide between parallel test runs or leak state across runs.

**Resolution:** Fixed inline during review — switched to the `tmp_path` fixture matching the sibling-test convention. Re-verified: ruff/compile clean, test still XFAILs for the right reason, post-pin-removal simulation still passes.

### Findings in the Neighbours

None. The diff touches only test files; the resolver under test (`_brain_location.py`) and `_change_state.sulis_state_base()` are imported (callees), inspected, and unchanged.

### Watch List

None.

### Cross-Reference

- No prior `.security/move-dogfood-central-brain/viability-report-*.md` to cite.
- No existing hardening deltas duplicated.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `compileall`. Head: 0 errors. Type-checker N/A (repo-contract `type_check: ""`) — recorded coverage gap, not silent skip.
- [✓] **CR-02 Single-reader pass.** Justified by diff size: 99 lines, 2 files (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files (88-line new test, 113-line sibling) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low (resolved inline).
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no domain→infra imports, no singletons, no circular imports; test imports its callee in the correct direction). Security: nothing surfaced (no secrets, auth, injection, or network; the SULIS_STATE_DIR setenv is test isolation, not a credential). Quality: 1 finding (test-isolation convention drift, resolved inline) + test-coverage observation (the change IS a test) + CR-10 perf scan (the one `for` loop is a bounded in-memory ancestor walk with a `.is_file()` check — no N+1, no DB/RPC/FS-in-loop).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `test` concern). PH-02 Size: none (99 lines / 2 files). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (the new file is a test). PH-03 high → auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff --cached change/move-dogfood-central-brain` (staged + new file)
- **Neighbour expansion:** git grep — callees (`brain_base_dir`, `sulis_state_base`) inspected, unchanged. 0 neighbour findings.
- **Neighbour cap:** not reached (test-only diff).
- **Scanners run:** ruff (lint + format), compileall. Gitleaks/Semgrep/Trivy not invoked — test-only diff with no secret/dependency/infra surface; recorded as scoped coverage gap.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (99 lines, 2 files).
