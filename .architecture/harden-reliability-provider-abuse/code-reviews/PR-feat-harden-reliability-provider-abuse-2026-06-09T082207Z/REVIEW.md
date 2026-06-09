# Code Review: feat/harden-reliability-provider-abuse — Provider-abuse hardening of the reliability layer

> **Timestamp:** 2026-06-09T082207Z (ISO 8601 UTC)
> **Author:** automated executor (CH-01KTMK ship-gate hardening)
> **Branch:** feat/harden-reliability-provider-abuse → change/harden-reliability-provider-abuse
> **Files changed:** 6 (2 source, 3 test, 1 doc)
>
> **Outcome:** Ready to merge

---

## At a glance

This change hardens the already-shipped reliability layer against a misbehaving
provider — the kind that could either flood the system with errors or quietly
keep a failing job retrying forever. Two fixes land together: a cap so a flood
of errors can only ever spin up one recovery worker at a time per session, and a
hard lifetime limit on retries that a brief recovery can't keep resetting.

The build is clean, the existing safety net (the four recovery behaviours)
still passes end-to-end, and both fixes ship with new tests that prove the abuse
cases are now bounded. There is nothing that needs fixing before merge.

## What to fix

No issues that need attention.

One minor point for awareness (no action needed): the lifetime-retry counter is
read once without the lock just before the retry-count check. This is safe today
because the new one-worker-at-a-time cap means only one piece of code ever
touches that counter at a time — but it's worth a glance if the cap is ever
loosened in future. Documented in the technical detail below.

## How this pull request is shaped

**Size — clean.** Six files, but the bulk is tests and documentation. The actual
logic change is small and lives in two files.

**Scope — clean.** Single concern: the two related provider-abuse fixes from the
ship-gate review, landed together because they share the same retry-driver code.

**Safety — clean.** No database migrations, no schema changes, no infrastructure,
no secrets. The new policy setting is backward-compatible (it has a default, so
existing code keeps working untouched).

**Completeness — clean.** Both fixes ship with new tests (unit, wiring, contract,
and end-to-end regression). The recovery module is at 98% line coverage.

## Things to take away

(omitted — the change is clean and well-tested.)

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed source files (>50 lines) read end-to-end; all three lenses produced
output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean, full
  reliability suite + broad session-manager regression green (45 + 258).
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..PH-04). Single concern,
  small net source delta, tests included, no migrations/schemas/secrets.
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single low finding is benign-under-current-invariant;
  no failing characterisation test can be constructed per CR-04 → Watch List).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced — deadlock invariant + dependency direction preserved |
| Security | 0 | 0 | Nothing surfaced — no secrets/auth/injection/PII/new external calls |
| Quality | 1 | 0 | Unlocked read of `_lifetime_retries` (benign under the FIX-1 one-in-flight cap) |

### Build Verification (CR-01)

No PR-introduced errors. Commands run on HEAD:
- `ruff check _session_manager/recovery.py _session_manager/manager.py` → All checks passed.
- `ruff format --check` (5 changed files) → already formatted.
- `pytest` reliability suite (recovery + wiring + contract + e2e) → 45 passed.
- `pytest tests/unit/ -k "session_manager or claude or session_event or pty"` → 258 passed.

No `[tool.mypy]` config in the package's `pyproject.toml`; the package's type
gate is ruff. Coverage gap: no static type-check delta (recorded, not skipped).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat (hardening)}       → single concern
  module_fan_out: 1 (_session_manager)         → clean
  severity: none

Size (PH-02):
  lines_added: 596, lines_removed: 25, total: 621
  files_changed: 6 (2 source, 3 test, 1 doc)
  net_source_lines: ~165 (rest are tests + docstrings)
  severity: low

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false (RetryPolicy field documented in contract + contract test)
  severity: none
```

### Findings in the Changes

#### `_session_manager/recovery.py:487` — low (quality)

**Quoted text:**
```python
if self._lifetime_retries >= self._policy.max_lifetime_retries:
    self._abandon_sequence(error, reason="absolute retry ceiling exceeded")
    return
```

`_lifetime_retries` is incremented under `_retry_lock` (line 515) but read here
without the lock. **Benign under the current invariants:** FIX 1's
one-recovery-thread-in-flight guard (`try_begin_recovery`/`end_recovery`)
guarantees `_drive_retry` runs single-threaded per driver, so there is no
concurrent writer to race the read. The increment is lock-guarded only for
memory-visibility symmetry with the rest of the driver's shared state.
`note_turn_cleared` (the only pump-thread mutator) does not touch this counter
by design. No fix queued (CR-04: no failing characterisation test can be
constructed because the cap removes the race) → Watch List.

### Findings in the Neighbours

None. The manager wiring (`_on_error_event`) and the session slot-release seam
(`Session.release_turn_for_retry`) are the direct neighbours; both are exercised
by the new wiring + e2e tests and behave unchanged (the slot release stays on
the pump thread; the WP-007/WP-008 deadlock fixes are preserved).

### Watch List

- Unlocked read of `_lifetime_retries` (see above) — re-examine if the one-thread-
  in-flight cap is ever relaxed to allow concurrent recovery threads per session.

### Architecture lens

Nothing surfaced. Checks run:
- No new imports; dependency direction unchanged (driver still consumes only
  injected capabilities).
- No new module-level singletons; the in-flight guard reuses the existing
  `_retry_lock`.
- Resilience: the absolute ceiling is the new give-up backstop (typed,
  observable Event reusing the observed code — no new `events.py` constant
  minted, asserted by `test_no_new_event_code_or_kind_introduced`).
- The WP-007 no-deadlock invariant is preserved: the driver lock is never held
  across an injected call (`_send`, `_reauth`, `_surface`, `_resume`); the
  slot-release stays on the pump thread; the slot is released before the
  fire-and-forget re-submit so a never-clearing sequence cannot stall.

### Security lens

Nothing surfaced. Primitives checked: SEC-01..07 (no access-control / auth /
injection / validation / secrets surface in the diff), SC-01..04 (no dependency
changes). No PII or token-shaped strings newly logged (the re-login link was
already in the shipped notification surface). Scanners: not separately run — the
diff introduces no new I/O, network, filesystem, or credential surface.

### Quality lens

1. **Build Verification follow-up:** none (CR-01 clean).
2. **JSX/template scan:** N/A (Python only).
3. **Dead-surface:** none — `try_begin_recovery`, `end_recovery`,
   `max_lifetime_retries`, `_lifetime_retries`, `_abandon_sequence` all consumed.
4. **Contract-drift:** none — the new `RetryPolicy.max_lifetime_retries` field is
   reflected in both `reliability-layer.contract.md` (new abandon row + hardening
   section) and `test_session_manager_recovery_contract.py` (field-set +
   default assertions).
5. **Test-coverage:** comprehensive. New tests:
   `test_absolute_ceiling_survives_turn_clears_and_abandons`,
   `test_turn_clear_still_refunds_the_per_window_budget_normally`,
   `test_default_policy_has_a_generous_absolute_ceiling`,
   `test_in_flight_guard_admits_one_then_coalesces_until_released`
   (recovery.py); `test_recovery_dispatch_capped_at_one_thread_per_session`,
   `test_in_flight_guard_released_after_recovery_completes` (wiring). recovery.py
   at 98% (3 pre-existing uncovered lines, none in this diff).
6. **Style/readability:** clean; ruff + format pass; BLUE refactor extracted the
   shared `_abandon_sequence` helper at the 2-consumer threshold.
7. **Performance (CR-10):** no anti-pattern matches. No N+1, no unbounded
   materialisation, no hot-loop allocation. `_lifetime_retries` is a bounded int
   counter.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check + ruff format --check + full
  pytest reliability suite + broad regression. Head: 0 new errors. Coverage gap:
  no static type-checker (package has no mypy config; ruff is the gate) — recorded.
- [✓] **CR-02 Dispatch shape.** Diff is 621 total lines / 6 files but net source
  logic is ~165 lines across 2 files I authored this session, single concern.
  Single-reader pass justified by concentrated, self-authored, single-concern
  source delta; both source files read end-to-end.
- [✓] **CR-03 Full-file reads.** Both changed source files (recovery.py,
  manager.py) read end-to-end; test files reviewed in full. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict PASS. No auto-downgrade triggers fired
  (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed.
  Security: nothing surfaced + primitives listed. Quality: all 7 outputs produced
  (1 low finding + the rest clean/empty).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single concern). PH-02
  Size: low (596/25, 6 files, ~165 net source). PH-03 Safety: none (0 migrations/
  schemas/secrets/infra). PH-04 Completeness: none (tests included). No PH-03 high
  → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/harden-reliability-provider-abuse` (working tree)
- **Neighbour expansion:** git grep over `_on_error_event` / `release_turn_for_retry`
  callers/callees; 2 neighbours (manager wiring, session slot-release), both
  covered by new tests.
- **Neighbour cap:** not reached (2 of 2 considered).
- **Scanners run:** ruff (lint + format); pytest (full reliability + regression).
- **Scanners unavailable:** no static type-checker configured for the package.
- **Lenses dispatched in parallel:** no — single-reader pass per the CR-02
  justification above.
