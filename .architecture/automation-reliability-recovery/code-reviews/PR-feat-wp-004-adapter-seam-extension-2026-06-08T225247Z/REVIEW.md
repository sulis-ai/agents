# Code Review: WP-004 — Adapter seam extension (classify_failure + reauth)

> **Timestamp:** 2026-06-08T225247Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** feat/wp-004-adapter-seam-extension → change/feat-automation-reliability-recovery
> **Files changed:** 4 (3 modified, 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds two new optional abilities to the provider-adapter interface — one that lets a provider say "this failure means the login expired / it was a blip / it's a dead end", and one that kicks off re-login. Both are added in a way that leaves every existing piece of code untouched: anything that doesn't use the new abilities keeps working exactly as before. The new behaviour is fully tested, the build is clean, and the change is small and single-purpose. Nothing needs attention before merge.

## What to fix

No issues that need attention.

One thing for awareness (no action needed now): the "start re-login" ability is deliberately left as a placeholder that errors if called — the real re-login logic is scheduled for a later piece of work (the Claude detection task). That is intentional and clearly noted in the code.

## How this pull request is shaped

Small (85 lines added across 4 files), single-purpose (one feature), no database migrations, no infrastructure changes, and it ships with a new test file. Well-shaped — no split needed.

---

## Technical detail

> Below this point uses internal taxonomy for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `ruff check` clean on all 4 files.
- **PR Hygiene:** 0 high/medium findings (CR-09 / PH-01..04).
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single low has a documented conscious-deferral rationale; no delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — additive, dependency-inward preserved |
| Security | 0 | 0 | none — no external calls/secrets/auth introduced |
| Quality | 1 | 0 | reauth() stubs uncovered-by-test (by design, WP-006) |

### Build Verification (CR-01)

No typechecker (mypy/pyright) configured in `plugins/sulis/scripts/pyproject.toml` — ruff is the configured mechanical floor. `ruff check` on the four changed files: **All checks passed** (`tool-outputs/ruff-head.log`). No PR-introduced errors. Coverage gap: static type-checking is not configured project-wide (pre-existing condition, not introduced by this WP).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_types {feat}; module_fan_out 2 (adapter + adapters)   → severity low
Size (PH-02):        +85 / -2; 4 files; generated_ratio 0                          → severity low
Safety (PH-03):      migrations 0; schema/IDL 0; infra 0; secret hits 0            → severity none
Completeness (PH-04): new_source_without_test 0; new tests 1; api_change 0 (additive, defaulted) → severity none
```

### Findings in the Changes

#### `_session_manager/adapters/claude.py:~178` and `_session_manager/adapters/claude_pty.py:~165` — low (quality)

**What:** `reauth()` on both concrete adapters raises `NotImplementedError`; no test exercises that branch.

**Quoted text:**
```python
raise NotImplementedError(
    "Claude reauth() is implemented in WP-006; the WP-004 seam only "
    "establishes the Protocol shape."
)
```

**Why it's low, not higher:** This is a documented conscious deferral (CLAUDE.md "Conscious Deferral"). ADR-003 explicitly reserves Claude's detection mapping and re-auth-link production for WP-006; WP-004's contract (acceptance_criteria) is the Protocol *shape* + the defer-to-neutral default, both of which are tested. The stub raises loudly rather than returning a fake ticket, and the driver only reaches `reauth()` after `classify_failure` → `LOGIN_EXPIRED`, which neither adapter returns until WP-006. So the branch is unreachable by any live path in this change set.

**Recommendation:** No action in WP-004. WP-006 implements + tests both `classify_failure` mappings and `reauth()`. No hardening delta (theoretical until WP-006; belongs to that WP's contract, not a Watch List gap here).

### Findings in the Neighbours

None. Direct callers/callees of the touched symbols: the manager speaks the Protocol structurally; no neighbour invokes `classify_failure`/`reauth` yet (WP-005 driver is the first caller). The conformance tests (`test_claude_adapter.py`, `test_claude_pty_adapter.py`) were the affected neighbours and were updated implicitly by the GREEN-step conformance fix (they now pass because both adapters answer the new shape).

### Watch List

None.

### Cross-Reference

- No prior `.security/automation-reliability-recovery/viability-report-*` to cite.
- No existing hardening deltas to dedup against for this seam.
- Architecture decisions: ADR-003 (classification provider-neutral; detection thin adapter hint) is the governing record; this diff implements its "Consequences" §1 verbatim.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` on all 4 changed files. Base: clean. Head: clean (0 PR-introduced). No mypy/pyright configured (project-wide pre-existing gap, noted).
- [✓] **CR-02 Single-reader pass justified by diff size:** 85 lines, 4 files (within ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end (adapter.py 188 lines, claude.py, claude_pty.py, new test file). No sampling.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 1 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked dependency direction, cycles, singletons, timeouts/CB — no I/O introduced). Security: nothing surfaced (SEC-01..07 / SC: no external calls, no secrets, no auth change; grep for secret patterns clean). Quality: Build Verification clean; no JSX (Python diff, n/a); no dead surface; no contract drift; test-coverage observation = new behaviour covered, reauth stubs deferred; CR-10 perf scan = no anti-pattern matches (no DB/RPC/fs in any loop body).
- [✓] **CR-09 PR Hygiene applied.** Scope low, Size low, Safety none, Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-automation-reliability-recovery...HEAD` (working-tree changes, pre-commit).
- **Neighbour expansion:** git grep for `classify_failure`/`reauth` callers → none live; conformance tests are the affected neighbours.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** ruff (lint). Gitleaks/Semgrep/Trivy not invoked — manual secret/injection grep clean on a 4-file additive Python diff with no new I/O.
- **Lenses dispatched:** single-reader (CR-02 carve-out).
