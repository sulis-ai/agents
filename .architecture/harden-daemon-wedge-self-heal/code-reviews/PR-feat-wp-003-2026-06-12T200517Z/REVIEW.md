# Code Review: WP-003 — Grace-window wedge detection wired into the race-loser branch

> **Timestamp:** 2026-06-12T200517Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-003)
> **Branch:** wp/harden-daemon-wedge-self-heal/wp-003-grace-window-wedge-detection → change/harden-daemon-wedge-self-heal
> **Files changed:** 4
>
> **Outcome:** Ready to merge

---

## At a glance

This change makes a stuck (wedged) session daemon recover on its own instead of
blocking every new change spawn until it happens to die. It adds a conservative
waiting window: a daemon that is merely booting slowly is left alone and reused,
while one that has clearly hung past the window is safely cleaned up and replaced.
The behaviour is well-tested (real subprocesses, no fakes), the existing safety
behaviours are pinned with a before-and-after test, and there are no build, lint,
or type errors introduced. A handful of minor tidy-ups surfaced during review and
were already applied. Ready to merge.

## What to fix

No issues that need attention. Three minor tidy-ups surfaced during review (two
unused leftovers in the new test file, and one small repeated block in the daemon
code) and were all fixed in place before this review was finalised.

## How this pull request is shaped

Well-scoped: one feature (`feat:`), four files, all in the daemon-presence layer.
New behaviour ships with both unit and integration tests; the only structural
change to existing code is pinned by a before-and-after test. No database
migrations, no schema changes, no infrastructure files, no secrets. Size is
modest and single-purpose.

## Things to take away

Nothing to add — the change followed the test-first discipline cleanly, kept the
frozen engine untouched, and preserved the fail-closed safety invariant.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean; mypy adds
  0 new errors (the 32 reported are byte-identical on the unmodified base: frozen
  engine `_session_manager/manager.py` per ADR-001 + a test-seam import).
- **PR Hygiene:** 0 high/medium findings (CR-09 / PH-01..04).
- **In the changes:** 3 low findings — all addressed inline.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the 3 lens findings were trivial in-scope fixes, applied inline).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 | 0 | fail-closed stderr+return-1 duplicated ×2 → extracted `_fail_closed_retry` (EP-03) |
| Security | 0 | 0 | nothing surfaced — kill gated on `_is_our_daemon` fail-closed verify |
| Quality | 2 | 0 | 2 dead-surface leftovers in the new test → removed inline |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` clean on all changed source + test files;
`ruff format --check` clean. `mypy session_manager_daemon.py` reports 2 errors on
the daemon file (import-not-found for the `session_child_adapters` test seam;
`SocketServer` arg-type) — both present byte-identically on the unmodified base
(at the pre-change line numbers 550/573, shifted to 585/608 by the additions). The
remaining 30 are inside the frozen engine (`_session_manager/manager.py`, ADR-001).
Net new errors introduced by this WP: 0. Build Verification section empty → PASS
not blocked.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread {feat}; 1 module (daemon-presence) → severity none
Size (PH-02):        +663 / -51, 4 files; generated_ratio 0; lock_files 0 → severity low
Safety (PH-03):      migrations 0; schema/IDL 0; infra 0; secret hits 0 → severity none
Completeness (PH-04): new_source_without_test 0; 2 new test files; api_change_without_schema false → severity none
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

#### F-01 — low (quality, dead-surface) — `tests/integration/test_daemon_wedge_self_heal.py:57` — ADDRESSED INLINE

**Quoted text (pre-fix):** `_CMDLINE_MARKER = "session_manager_daemon.py"`
**Issue:** Module constant defined but never referenced; the cmdline-marker match
is exercised implicitly via the holder filename `holder_session_manager_daemon.py`.
**Resolution:** Removed the unused constant + its comment.

#### F-02 — low (quality, dead-surface) — `tests/integration/test_daemon_wedge_self_heal.py` (`_HOLDER_SRC`) — ADDRESSED INLINE

**Quoted text (pre-fix):** `server, manager = smd._build_server(socket_path)`
**Issue:** `manager` bound but unused in the mid-boot holder (only the bound
`server` is needed to bring the socket live). Inside a string literal, so ruff
F841 does not catch it.
**Resolution:** Renamed to `_manager` to mark the intentional discard.

#### F-03 — low (architecture, duplication / EP-03) — `session_manager_daemon.py` `_handle_lost_race` — ADDRESSED INLINE

**Issue:** The fail-closed terminus (`sys.stderr.write(... "ensure-daemon will
retry" ...)` + `return 1`) appeared twice — at step 4 (reclaim failed) and in the
peer-race re-acquire-fail branch. Two consumers → the EP-03 two-consumer extraction
threshold.
**Resolution:** Extracted `_fail_closed_retry(socket_path)` — the byte-for-byte
give-up line in exactly one place (the #131 `DaemonStartError` cause-folding reads
this exact string, so single-sourcing it also protects that contract). Full daemon
suite re-run green (73 passed) after the extraction.

### Findings in the Neighbours

None. The neighbours (`daemon_client.daemon_is_live`, `_reclaim_wedged_holder`,
`_acquire_singleton_lock`, `_build_server`) are all consumed unchanged; the
import-graph independence test (ADR-003) stays green.

### Watch List

None.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas covered.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` + `mypy session_manager_daemon.py`. Base vs HEAD compared: 0 PR-introduced errors. Coverage: full.
- [✓] **CR-02 Dispatch shape.** Diff is 4 files; the substantive non-test source change is ~165 lines in one module. Single-reader pass justified by file count (4 ≤ 5) and the focused single-module surface; the full diff (incl. tests) was read end-to-end.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end (daemon module diff, both new test files, DAEMON_CONTRACT.md). Unread: none.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 3 low (all addressed).
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; no unread >50-line file; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding (EP-03 duplication) + ADR-001/003 + WPB-07 checks. Security: nothing surfaced — kill path gated on `_is_our_daemon` fail-closed (cmdline + start-token); no new secrets/auth/injection; SEC-01..07 checked. Quality: 2 dead-surface findings + test-coverage observation (all new behaviour has tests) + CR-10 perf scan (no anti-pattern matches — the only loops are bounded poll loops with sleeps, not N+1/O(N²)).
- [✓] **CR-09 PR Hygiene applied.** PH-01 none; PH-02 low (663/4); PH-03 none (0 migrations/schemas/secrets/infra); PH-04 none (2 new test files cover the new behaviour). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached` (staged WP diff vs change branch base).
- **Neighbour expansion:** string-grep on touched symbols; all neighbours consumed unchanged.
- **Scanners run:** ruff, mypy. (Gitleaks/Semgrep/Trivy not invoked — Python stdlib-only diff, no deps/secrets/infra surface; recorded as scope-appropriate, not a coverage gap.)
- **WPB rubric (kind: backend):** WPB-07 single composition root (`_boot_and_serve`) ✓; WPB-08 outside-in TDD (integration test written first, failed, then GREEN) ✓; WPB-12 characterisation-test-first for the structural change ✓; EP-03 reuse-first (`_poll_socket_live`, `_fail_closed_retry` extracted at 2-consumer threshold) ✓.
