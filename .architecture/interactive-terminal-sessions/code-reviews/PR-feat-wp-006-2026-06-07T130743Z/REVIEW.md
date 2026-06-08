# Code Review: PR-feat-wp-006 — PTY-capable fake child (test infra)

> **Timestamp:** 2026-06-07T130743Z (ISO 8601 UTC)
> **Author:** executor (WP-006)
> **Branch:** feat/wp-006-pty-capable-fake-child → change/extend-interactive-terminal-sessions
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a new "PTY" mode to the existing fake test assistant so that
later pieces of work can test the live-terminal feature against something that
behaves like a real terminal, rather than a fake stand-in. It is small, focused,
and well-tested: one existing test file gained the new mode, one new test file
proves it works, and all the existing tests that depend on the older modes still
pass unchanged. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Two files, about 170 lines, a single concern. Easy to review
thoroughly.

**Scope — clean.** One purpose: extend the fake child with a terminal-echo mode.
No mixed feature/refactor bundling.

**Safety — clean.** No database changes, no schema changes, no infrastructure or
secret-bearing files.

**Completeness — clean.** The new behaviour ships with two tests that exercise it
end-to-end against a real pseudo-terminal.

## Things to take away

(omitted — the change is clean and well-shaped)

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; the one
file >50 lines (the new test, 145 lines) was read end-to-end; all three lenses
produced output. No auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 1 finding addressed inline during review (1 low → resolved), 0 remaining
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single finding was fixed inline; no deltas queued)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 (resolved inline) | 0 | duplicated spawn/teardown across 2 tests — extracted to `_spawned_pty_child` CM |

### Build Verification (CR-01)

Mechanical baseline: `uv run ruff check` (pyproject ruff config) on BASE and
HEAD-equivalent (changed files). HEAD: `All checks passed!`. `ruff format
--check`: both files already formatted. No mypy/pyright config present for this
scripts package (stdlib-only test infra) — typecheck coverage gap recorded
below. Full suite for the fixture's consumers (test_session_cli,
test_session_manager_core) + the new tests: 32 passed. No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test} (single concern: extend test fixture)  → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts/tests)      → clean
  severity: none

Size (PH-02):
  lines_added: ~60 (lib) + ~145 (new test), lines_removed: 2
  files_changed: 2
  severity: none (well within carve-out: <=200 lines AND <=5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the new source IS test infra; it ships with 2 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

**Q-1 (low, resolved inline) — `tests/unit/test_fake_child_pty_mode.py`** —
The two test functions originally duplicated ~20 lines of spawn-under-pty +
guaranteed-teardown boilerplate (openpty → disable ECHO → Popen → terminate/
wait/kill → close fds). At the 2-consumer threshold (EP-03), the shared setup
was extracted into a `_spawned_pty_child(tmp_path)` context manager in the same
PR. Each test body is now write-then-assert. Re-reviewed: zero findings remain.
Lens: quality.

### Findings in the Neighbours

None. The only neighbour is the fixture's existing consumers (test_session_cli,
test_session_manager_core, the integration suites). The change is additive — the
`pty` branch returns before the existing stream-json loop — so the echo/memory
modes are byte-unchanged; verified by running those consumers (32 passed).

### Watch List

None.

### Cross-Reference

- No prior security report under `.security/interactive-terminal-sessions/`.
- No existing hardening deltas covered.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `uv run ruff check` + `ruff format
  --check` on both changed files: clean. Fixture-consumer + new tests: 32 passed.
  Coverage gap: no mypy/pyright configured for this stdlib-only scripts package
  (typecheck floor is ruff's lint rules only).
- [✓] **CR-02 Single-reader pass justified by diff size: ~170 lines, 2 files**
  (within the ≤200-line AND ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** The new test file (145 lines, >50) read
  end-to-end. The lib diff (32 lines) read in full. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file + the specific
  duplicated boilerplate; resolved inline with the extracted CM named.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low
  (resolved).
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers
  fired (Build Verification empty; all >50-line files read; all lenses produced
  output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no domain/infra
  imports; no singletons; no external calls — test fixture; CR-10 perf: the
  child read-loop is the intended byte pump, no N+1/O(N²)). Security: nothing
  surfaced (verbatim byte pass-through is correct per contract §2.12.4; no
  secrets/network/injection; sentinel is a literal byte compare). Quality: 1
  finding (duplication) resolved inline; test coverage present (2 tests); no
  dead surface; no contract drift (the `pty` mode matches WP Contract + §2.14).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03
  Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none.
  No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** git diff change/extend-interactive-terminal-sessions vs working tree
- **Neighbour expansion:** git grep for fixture consumers (child_argv/write_child/fake_claude_child) — 8 consumer files identified; relevant unit consumers run
- **Neighbour cap:** not reached (well under 20)
- **Scanners run:** ruff (lint + format)
- **Scanners unavailable:** mypy/pyright (not configured for this package), gitleaks/semgrep/trivy (no signals in a stdlib test-fixture diff)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out
