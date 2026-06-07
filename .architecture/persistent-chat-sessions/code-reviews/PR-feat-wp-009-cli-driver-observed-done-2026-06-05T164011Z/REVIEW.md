# Code Review: feat/wp-009-cli-driver-observed-done — minimal real CLI driver + observed-done gate

> **Timestamp:** 2026-06-05T164011Z (ISO 8601 UTC)
> **Author:** WP-009 executor
> **Branch:** feat/wp-009-cli-driver-observed-done → change/refactor-persistent-chat-sessions
> **Files changed:** 7 (2 source, 3 test, 1 shared test helper, 1 manual evidence doc)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small command-line driver that exercises the warm session manager end-to-end against the real `claude` tool, plus the tests that prove it works without needing `claude` in CI. It is well-scoped, fully tested, and the build is clean. Two small things were found during review; both are already handled (one fixed in place, one is a harmless note). Nothing blocks merge.

The standout: this change is the project's "observed-done" gate, and it did its job — running the driver against the real `claude` tool for the first time surfaced a genuine defect in an earlier piece (a missing required flag) that no existing test could catch, because the existing tests replay recorded output instead of launching the real tool. That defect is fixed and locked in with a new test.

## What to fix

No issues that need attention. The two items found in review:

- **Fixed already:** a small import was written inside a function in one test file instead of at the top. Moved to the top of the file — standard placement.
- **For awareness only:** the driver reads the session's lifecycle state (e.g. "ready") directly off the session object when printing the "open" line. This is the same value the manager's own status check returns, and the session object is the intended place to read it, so it's left as-is.

## How this change is shaped

**Scope — clean.** One concern: the CLI driver, its tests, and the single one-line fix the gate surfaced. No mixed feature/refactor.

**Size — fine.** About 1,000 new lines, but it's one logical unit (a new module plus its tests). Most of the volume is tests and documentation, which is the right shape for a gate WP.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — strong.** Every new source file has tests. The real-tool run was captured as evidence (`tests/manual/session_driver_observed.md`), which is the whole point of this WP.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all 7 changed files read end-to-end; all three lenses produced output; no auto-downgrade trigger fired.

### Summary

- **Build Verification (CR-01):** 0 PR-introduced errors. Checker: `ruff` (the configured linter in `pyproject.toml`; no mypy `[tool.mypy]` gate). `All checks passed`.
- **PR Hygiene (CR-09):** scope low, size low, safety none, completeness none. No PH-03 high → no auto-downgrade.
- **In the changes:** 2 findings (0 critical, 0 high, 1 medium→fixed inline, 1 note).
- **In the neighbours:** 0.
- **Draft fixes:** 0 (the one actionable finding was fixed inline; the other is a note, not a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (note) | 0 | CLI reads `session.state_machine.state.value` directly |
| Security | 0 | 0 | `SULIS_SESSION_CLAUDE_ARGV` is a documented test-only seam; no escalation |
| Quality | 1 (fixed) | 0 | local `import os` inside `_run_demo` → moved to module top |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` on all 7 changed files: `All checks passed!`. Raw output in `tool-outputs/ruff-head.log`. The repo's CI gate is ruff + pytest; mypy is on PATH but not configured as a project gate, recorded as a coverage gap in Methodology.

### PR Hygiene signal table (PH-06)

```
Scope (PH-01):       single concern (CLI driver + tests + 1 adapter fix)   → low
Size (PH-02):        ~1000 added lines, 7 files (mostly tests + docs)        → low
Safety (PH-03):      migrations 0, schema 0, secrets 0, infra 0             → none
Completeness (PH-04):new_source 2, new_tests 3, observed-done evidence 1    → none
```

### Findings in the Changes

#### `plugins/sulis/scripts/tests/integration/test_session_cli_smoke.py` — medium (quality) — RESOLVED inline

**What:** `import os` was placed inside the `_run_demo` helper body.

**Quoted (before):**
```python
    # Inherit PATH/PYTHONPATH from the parent so `uv`/imports resolve.
    import os

    full_env = {**os.environ, **env}
```

**Fix applied:** moved `import os` to the module-level import block; re-ran ruff (clean) + the smoke (3 passed). No delta needed — fixed in the WP.

#### `plugins/sulis/scripts/sulis_session.py:225,281` — note (architecture)

**What:** the demo/open rendering reads `session.state_machine.state.value` directly off the `Session` returned by `open()`.

**Assessment:** `mgr.health(key).state` and `status()` return the identical value (`session.state_machine.state.value`). Contract §2.7 says consumers never *touch* (mutate/drive) the state machine; reading the honest state label off the returned Session for display is consistent with what `health()`/`status()` expose. `resumed` is only available on the Session object, so the rendering already legitimately holds the Session. Left as-is; recorded as a note, not a finding. No delta.

### Findings in the Neighbours

None. The only neighbour file touched is `_session_manager/adapters/claude.py` — the `--verbose` fix the observed-done gate surfaced (already in the diff, with a regression test and finding SF-896624ac registered).

### Watch List

None.

### Cross-Reference

- **Finding registered by this WP:** `SF-896624ac` (.security/persistent-chat-sessions/findings/) — Claude adapter spawn argv missing mandatory `--verbose`, caught by the observed-done gate, fixed + regression-pinned in this same diff.
- No prior security report to cite.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` on all 7 changed files; head: 0 errors. Coverage gap: mypy present on PATH but not a configured project gate (no `[tool.mypy]` in pyproject) → not run; CI gate is ruff + pytest.
- [✓] **CR-02 Dispatch shape.** Diff >200 lines; lenses applied (architecture/security/quality) by the executor reviewer over a single bounded WP authored this session. Single-author scope, all files read end-to-end.
- [✓] **CR-03 Full-file reads.** All 7 changed files read end-to-end (authored + re-read this session). Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** 0 critical, 0 high, 1 medium (fixed inline), 1 note.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; no unread files; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 1 note + reach-through scan. Security: nothing surfaced — checked secrets/eval/exec/os.system/shell=True/credentials + the env-var argv seam. Quality: build-verification (ruff clean), no JSX (Python diff), no dead surface, no contract drift, test-coverage strong (every new source file tested), CR-10 perf scan (the two `mgr.read(follow=True)` loops are bounded live-tail consumption, not N+1; no spawns in loops).
- [✓] **CR-09 PR Hygiene applied.** Scope low, size low, safety none, completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/refactor-persistent-chat-sessions` + untracked source/test files (excludes bookkeeping + .coverage).
- **Neighbour expansion:** the only neighbour is claude.py (already in diff).
- **Scanners run:** ruff (configured linter). Gitleaks/Semgrep/Trivy not installed in this environment — recorded as coverage gap; manual secret/injection grep run instead (clean).
- **Scanners unavailable:** Gitleaks, Semgrep, Trivy (not installed).
