# Code Review: feat/wp-005-recovery-driver — RecoveryDriver (retry / abandon / pause→resume)

> **Timestamp:** 2026-06-08T230737Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-recovery-driver → change/feat-automation-reliability-recovery
> **Files changed:** 2 source (`recovery.py`, `__init__.py`) + 1 new test file
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the recovery driver — the piece that, when an unattended run hits an API failure, decides whether to retry it, give up cleanly, or pause for a re-login and then carry on. The code is well-scoped (it adds one new class to an existing file plus its package export), fully tested (eight tests, one per behaviour plus a couple of conformance checks), and the build and linter are clean.

One thing worth fixing was found and fixed during the review: the re-login path didn't have a back-up plan if the re-login service itself failed — it would have let an error escape instead of failing cleanly. That has been corrected and a test added.

## What to fix

No issues that need attention. The one item found during review was fixed inline (see below).

### Fixed during review — `_session_manager/recovery.py`, the login-expired path

**What was happening:** When a run's login expired, the driver asked the provider to start a re-login. If that re-login request *itself* failed, the error would have bubbled up out of the recovery code instead of being handled.

**Why it mattered:** The whole point of this layer is that an unattended run never just hangs or crashes silently — every outcome should be a clean, visible event. A re-login service being down is exactly the kind of real-world hiccup the layer is meant to absorb.

**What was done:** The re-login call is now wrapped so that if it fails, the run is abandoned cleanly with a visible "re-auth failed" event — the same fail-safe behaviour the design document calls for. A test (`test_login_expired_reauth_failure_abandons_fail_safe`) now locks this in.

## How this pull request is shaped

**Size — clean.** 232 lines across 2 source files plus one new test file. Comfortably small enough to review thoroughly.

**Scope — clean.** Single concern: the recovery driver. One commit type (`feat`).

**Safety — clean.** No migrations, no schema changes, no infrastructure files, no secrets. The driver is not yet wired into the live system (that is a later piece of work), so there is no runtime blast radius.

**Completeness — clean.** Eight tests added covering every behaviour branch, plus a real-classifier conformance test and the fail-safe test added during review.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — ruff clean on BASE and HEAD; import-smoke OK).
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..04 all clean).
- **In the changes:** 1 finding (1 medium — fixed inline during the gate).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single finding was resolved inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (fixed) | 0 | reauth() failure not contained (TDD §Q12) — fixed inline |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Mechanical baseline ran: `ruff check` (the project's configured linter per `pyproject.toml`) on `recovery.py`, `__init__.py`, and the new test file → **All checks passed!** on both BASE and HEAD (delta empty). Import-smoke: `from _session_manager import RecoveryDriver` resolves. No PR-introduced errors. Raw output at `tool-outputs/ruff-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (_session_manager) + tests
  severity: none

Size (PH-02):
  lines_added: 232, lines_removed: 0, total: 232 (+ untracked test file)
  files_changed: 2 source + 1 new test
  severity: none (≤200-line band per source; well under file cap)

Safety (PH-03):
  migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (driver fully covered by the new test file)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `_session_manager/recovery.py` `_drive_login_expired` — medium (architecture: Armor / resilience) — RESOLVED INLINE

**Quoted text (before fix):**
```python
ticket = self._reauth()
self._pending_ticket = ticket
```

**Why it matters:** TDD §Q12 specifies: *"if `reauth()` itself fails, the driver abandons as dead-end with a typed Event (fail-safe, observable) — it does not hang."* The original code let a `reauth()` exception propagate out of `observe()`, contradicting the fail-safe contract and the layer's "no silent hang / every outcome is an observable Event" invariant (§3.1, §3.5).

**Resolution (applied during the gate, CR-04 has a failing-test grounding):** wrapped `self._reauth()` in a `try/except` that calls `self._abandon(error, reason="re-auth failed: …")` and returns. New characterisation test `test_login_expired_reauth_failure_abandons_fail_safe` asserts `observe()` does not raise, surfaces exactly one abandoned Event reusing the observed code, and does not resume. Re-ran the suite (68 passed) and ruff (clean) → finding cleared.

### Findings in the Neighbours

None. The driver consumes injected capabilities; the neighbour ring (`classifier.py`, `events.py`, `adapter.py`) is unchanged by this diff and its existing contracts are exercised by the conformance test.

### Watch List

- The live wiring (manager hook + real `manager.send` / resume binding) is **out of scope** for WP-005 (it is WP-007). The driver's contract is verified against fakes here; the real-resume round-trip is the TDD's deferred manual `live-reauth-resume-claude` check. No action for this PR.

### Cross-Reference

- No prior `.security/{project}/` report exists for this change.
- No existing hardening deltas to cite.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` on changed files; BASE and HEAD both clean; import-smoke OK. Coverage gap: none (no typechecker configured for this scripts package; ruff is the configured tool).
- [✓] **CR-02 Single-reader pass justified by diff size:** 232 lines, 2 source files + 1 test (within the ≤200-line/≤5-file carve-out per source file; the change is one cohesive new class). Parallel dispatch not required.
- [✓] **CR-03 Full-file reads.** `recovery.py`, `__init__.py`, and the test file all read end-to-end (authored this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites the method + quoted text + a failing characterisation test.
- [✓] **CR-05 Severity rubric.** Applied. 1 medium (resilience gap on a documented non-happy path), resolved inline.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding (fixed). Security: nothing surfaced — no new deps/secrets/auth; reuses NOT_AUTHORIZED; layer stores no credentials (§3.6). Quality: tests present (8), no dead surface, no contract drift, CR-10 the single `while True` retry loop is budget-bounded with no I/O in body (no anti-pattern).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (232 lines). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (driver fully tested). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-automation-reliability-recovery` (local branch).
- **Neighbour expansion:** git grep over `_session_manager` imports; ring unchanged by the diff.
- **Scanners run:** ruff (lint); manual SEC/SC inspection (no Gitleaks/Semgrep/Trivy in this environment — recorded as a coverage note, but the diff introduces no new outbound surface, secret, or dependency).
- **Lenses dispatched in parallel:** no (single-reader carve-out; small cohesive diff).
