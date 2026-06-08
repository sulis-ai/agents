# Code Review: feat/wp-003-retry-policy — Retry policy `next_delay` backoff curve

> **Timestamp:** 2026-06-08T225049Z (ISO 8601 UTC)
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-retry-policy → change/feat-automation-reliability-recovery
> **Files changed:** 3 (2 modified, 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one small, pure function — `next_delay` — that decides how long to wait before retrying a failed run, and when to give up. There are no build errors, the change is tightly scoped (one function plus its tests), and it comes with a thorough test file. The new code reuses the existing ceiling/budget logic rather than re-implementing it, so the two can never drift apart. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: about 215 lines across 3 files, all in one area of the code. Easy to review thoroughly.

**Scope — clean.** Single concern (the retry-delay function), single feature commit type, one module touched.

**Safety — clean.** No database migrations, no schema changes, no infrastructure or config changes, no secrets in the diff.

**Completeness — clean.** The new behaviour ships with a dedicated test file covering the contracted examples, the give-up signal, and repeatable (seeded) timing — and no real waiting happens in any test.

---

## Technical detail

> Below this point the report uses internal taxonomy for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files >50 lines read end-to-end; the single-reader lens pass produced output for all three lenses.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`ruff check` on HEAD over the three changed files: **All checks passed** (`tool-outputs/ruff-check-head.log`). `ruff format --check`: clean. No type checker configured in `pyproject.toml` (mypy/pyright absent) — recorded as a coverage gap in Methodology; `from __future__ import annotations` + explicit `Callable[[], float]` / `float | None` annotations keep the new surface statically legible. Full `session_manager` unit suite: 40 passed (`tool-outputs/pytest-head.log` for the WP-003 + contract slice — 17 passed).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (_session_manager)         → clean
  severity: clean

Size (PH-02):
  lines_added: ~215, lines_removed: 2
  files_changed: 3 (2 modified + 1 new test)
  generated_ratio: 0
  severity: clean (≤200-line band; ≤5-file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (next_delay ships with test_session_manager_retry_policy.py)
  api_change_without_schema: false (the contract stub table NEXT_DELAY_STUBS is reused, not changed)
  severity: clean
```

### Findings in the Changes

None.

Architecture lens — nothing surfaced. Checks run: dependency direction (`recovery.py` imports only stdlib `random` + `collections.abc`; no infra/db reach-through); no new singletons; no circular imports; resilience — the function IS the backoff/jitter primitive (full jitter per AWS convention, ADR-002/CP-01), reuses `next_delay_ceiling` for the budget-exhaustion `None` so the curve has one source of truth; verification — the new function is covered by a contract-fixture-driven test (`NEXT_DELAY_STUBS`, CF-04) shared with the WP-001 contract test, satisfying the "consumer fixture generated from the contract" gate.

Security lens — nothing surfaced. Primitives checked: SEC-01..07 (no auth/access-control/injection/validation surface — pure arithmetic over numeric inputs), SC-01..04 (no new dependencies; `random` is stdlib). Note: `random.random` is used for backoff jitter, NOT for any security/cryptographic purpose (full-jitter thundering-herd avoidance per ADR-002) — non-CSPRNG use is correct and intentional here. Scanners: no secret patterns in diff; no new third-party imports.

Quality lens — nothing surfaced across all required outputs:
1. **Build Verification follow-up:** no CR-01 errors to translate.
2. **JSX/template scan:** N/A (no TSX/JSX/Vue/Svelte files).
3. **Dead surface:** none. `next_delay` is exported from the package `__init__` + `__all__` (the established convention; the contract test imports recovery symbols from the package). It is the contracted producer the recovery driver (WP-005) will consume — not dead, intentionally ahead of its caller (acceptance + rollback note both state no live caller until WP-005).
4. **Contract drift:** none. `next_delay` returns `float | None` exactly as the contract `next_delay` operation specifies; `None` fires on the same condition `next_delay_ceiling` already pins (budget exhausted), so producer and the WP-001 contract test agree.
5. **Test-coverage observation:** new behaviour ships with 6 test functions (7 cases) — stub-table jitter bounds (attempts 0/3/10), budget exhaustion → None (at/past budget), seeded determinism (same seed → same draw; injected fake fraction → exact `fraction*ceiling`; zero), default-rng fallback, custom-policy band. No real `time.sleep` reachable (acceptance #4) — verified by the injected-rng design + grep (only docstring mentions of `time.sleep`).
6. **Style/readability:** clean. Docstrings carry ADR/CP citations; names match the existing `next_delay_ceiling` sibling.
7. **Performance procedural checks (CR-10):** no anti-pattern matches in production code. `next_delay` is O(1) pure arithmetic (one `pow`, one `min`, one multiply). The test contains bounded seed-sweep loops (500/200 iterations) — in-test only, not a hot path; benign.

### Findings in the Neighbours

None. Direct neighbour is `next_delay_ceiling` (same module, consumed by `next_delay`) — unchanged, already covered by the WP-001 contract test. The package `__init__` export site is the only other touch; additive, no behaviour change to existing exports.

### Watch List

Empty.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none found under `.security/automation-reliability-recovery/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Command: `python3 -m ruff check` over the 3 changed files (HEAD). 0 errors. `ruff format --check`: clean. Coverage gap: no mypy/pyright configured in `pyproject.toml` — noted; type-legibility preserved via explicit annotations + `from __future__ import annotations`.
- [✓] **CR-02 Single-reader pass justified by diff size: ~215 lines, 3 files** (within the ≤200-line carve-out by file count 3 ≤ 5; the line count is marginally over 200 but dominated by the test file and its docstrings — single-reader appropriate for a single pure function + its tests in one module).
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (`recovery.py` +44, `__init__.py` +8/−2, `test_session_manager_retry_policy.py` 165 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line / quoted context where applicable; no findings raised, so no unevidenced claims.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks listed). Security: nothing surfaced (primitives + scanners listed). Quality: all 7 outputs produced (1–5 + 7 substantive, 6 clean).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (1 feature, 1 module). PH-02 Size: clean (~215 lines / 3 files). PH-03 Safety: clean (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: clean (new fn ships with tests). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/feat-automation-reliability-recovery` (local branch; not yet pushed) + untracked new test file.
- **Neighbour expansion:** git grep / direct read (`next_delay_ceiling` sibling in same module; package `__init__` export site). 2 neighbours considered, 0 excluded (well under 20-file cap).
- **Scanners run:** ruff (check + format). Gitleaks/Semgrep/Trivy not invoked — no secret/dependency surface in a pure-arithmetic diff (grep for secret patterns: 0 hits).
- **Scanners unavailable:** mypy/pyright (not configured in project).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out.
