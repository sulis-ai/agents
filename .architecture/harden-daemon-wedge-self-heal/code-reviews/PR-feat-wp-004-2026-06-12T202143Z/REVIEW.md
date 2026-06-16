# Code Review: WP-004 — End-to-end wedge self-heal integration proof

> **Timestamp:** 2026-06-12T202143Z (ISO 8601 UTC)
> **Author:** autonomous executor (Sulis)
> **Branch:** wp/harden-daemon-wedge-self-heal/wp-004-wedge-self-heal-integration-test → change/harden-daemon-wedge-self-heal
> **Files changed:** 1
>
> **Outcome:** Ready to merge

---

## At a glance

This change strengthens one existing test so it proves the real thing the
whole feature is about: when a stuck background helper is blocking new work,
the system now clears it out and brings up a fresh, genuinely-working one.
The test now confirms that by actually talking to the fresh helper and getting
a reply — not just inferring it from side effects. The change is small
(one test file), well-scoped, and the full helper test suite passes (73 tests).
One small tidy-up was found and fixed during review (a redundant line that
duplicated setup already done elsewhere). Nothing else needs attention.

## What to fix

No issues that need attention. One minor redundancy was found and already
fixed during the review (a duplicate setup line removed to match how the
neighbouring tests are written).

## How this pull request is shaped

Clean and small. One file, test-only, single purpose (it proves the
end-to-end self-heal behaviour). No database changes, no infrastructure, no
secrets, no mixed concerns. This is exactly the shape a focused change should
take.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the
single changed file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean on base and head.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04) — single-file, test-only, no safety signals.
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low) — resolved inline.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one finding was fixed inline, no delta queued).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — ADR-003 independence + ADR-001 engine-unmodified held |
| Security | 0 | 0 | none — test-only, no secrets/auth/external surface |
| Quality | 1 (resolved) | 0 | redundant sys.path.insert vs sibling convention (CP-01) — fixed inline |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` clean on both the base and head versions
of the changed file; `ruff format --check` reports already-formatted. Coverage
gap: no mypy/pyright is configured for the `plugins/sulis/scripts` package, so
the static type-check floor was not run (recorded, not skipped silently).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test}                  → clean
  module_fan_out: 1 top-level dir              → clean
  severity: none

Size (PH-02):
  lines_added: 47, lines_removed: 19, total: 66
  files_changed: 1
  severity: none (well within single-reader carve-out)

Safety (PH-03):
  migration_count: 0, schema_idl_count: 0, infra_files: 0, secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  test_only_change: true (this IS the test deliverable)
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/tests/integration/test_daemon_wedge_self_heal.py` — low (quality) — RESOLVED INLINE

**Evidence (as introduced):**
```python
sys.path.insert(0, str(_SCRIPTS_DIR))
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
```

**Finding:** the first insert is redundant. The root `tests/conftest.py`
(lines 23-28) already inserts `_SCRIPTS_DIR` on `sys.path` for the whole suite,
and the sibling in-process `daemon_client` consumer `test_ensure_daemon.py`
imports `from _session_manager import daemon_client` with no such insert. The
added line diverges from the established convention (CP-01) and is dead under
pytest.

**Resolution:** removed the redundant insert; the `daemon_client` import now
resolves ambiently via conftest, matching `test_ensure_daemon.py`. All 3 tests
stay green (9.78s); ruff clean.

### Findings in the Neighbours

None. The diff touches no production code; the neighbouring daemon helpers
(`session_manager_daemon.py`, `_session_manager/daemon_client.py`) are merged
and unchanged.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable.
- **Existing security report:** none.
- **Pattern suggesting full audit:** none — single-file test change.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` on base and head. Base: 0 errors. Head: 0 errors. Coverage gap: no mypy/pyright configured for the scripts package (recorded).
- [✓] **CR-02 Single-reader pass justified by diff size:** 66 lines, 1 file (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** The one changed file (433 lines) was read end-to-end; the diff hunks and surrounding context reviewed. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low (resolved inline).
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; file read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (ADR-003 independence guard green, ADR-001 engine untouched, no domain→infra import). Security: nothing surfaced (test-only; no secrets/auth/external calls; subprocess args are test-controlled fixture paths). Quality: 1 finding (redundant insert, resolved inline) + daemon_is_live proven load-bearing + test-coverage = this IS the test WP + CR-10 perf: no anti-patterns (test fixture, no hot-path loops).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `test:` concern, 1 dir). PH-02 Size: none (66 lines / 1 file). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (test-only deliverable). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/harden-daemon-wedge-self-heal` (working tree, pre-commit).
- **Neighbour expansion:** git grep on `daemon_client` / `_acquire_singleton_lock` / `_write_pidfile` consumers; sibling daemon test files inspected for convention.
- **Neighbour cap:** not reached (test-only diff).
- **Scanners run:** ruff (lint + format).
- **Scanners unavailable:** mypy/pyright (not configured for the scripts package); Gitleaks/Semgrep/Trivy (not run — test-only diff, no dependency/secret surface).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (66 lines, 1 file).
