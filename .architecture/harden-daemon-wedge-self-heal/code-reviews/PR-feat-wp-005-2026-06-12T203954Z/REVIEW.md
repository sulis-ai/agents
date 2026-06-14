# Code Review: WP-005 — Re-verify daemon identity before SIGKILL escalation

> **Timestamp:** 2026-06-12T203954Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/harden-daemon-wedge-self-heal/wp-005-reverify-before-sigkill-escalation → change/harden-daemon-wedge-self-heal
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change closes a rare but real safety gap in how the terminal background helper shuts down a stuck copy of itself. Before, the last-resort forced shutdown only checked "is something still alive at this process number?" — not "is that still *our* process?". In the unlikely event the stuck helper died on its own and the operating system handed its number to an unrelated program in the meantime, the forced shutdown could have hit the wrong program. The fix re-checks identity at the last moment and skips the forced shutdown if it is no longer ours. The change is small, well-targeted, and comes with a test that fails without the fix and passes with it. No issues to fix before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: 116 lines across 2 files (one source file, one test file), one logical change. No database changes, no configuration changes, no new dependencies. A new test was added for the new behaviour. This is the ideal shape for a review.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean at head; mypy 32 errors on both base and head (pre-existing, none in the changed region).
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04) — all primitives `none`.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — pure additive guard, reuses `_is_our_daemon` (EP-03), no new imports (ADR-003 independence preserved) |
| Security | 0 | 0 | none — the change IS the security fix (closes verify→SIGKILL TOCTOU wrong-kill window, ADVISORY-2) |
| Quality | 0 | 0 | none — new behaviour has a dedicated RED-proven characterisation test; docstring updated to match |

### Build Verification (CR-01)

Empty. Commands: `ruff check` (clean on both changed files); `mypy session_manager_daemon.py` — 32 errors on BASE, 32 on HEAD → 0 PR-introduced. The 32 pre-existing errors live in `_session_manager/manager.py`, a missing `session_child_adapters` stub, and a `SocketServer` binding type — all outside the changed region (out-of-scope pre-existing type debt). Raw deltas in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 dir        → none
Size (PH-02):         +109 / -7; files_changed 2                            → none
Safety (PH-03):       migrations 0; schema/idl 0; infra 0; secrets 0        → none
Completeness (PH-04): new_source_without_test 0; api_change_without_schema false → none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: callers/callees of `_reclaim_wedged_holder` — the daemon main path (`_acquire_or_reclaim` caller around line 780) and the helpers it calls (`_is_our_daemon`, `_signal_pid`, `_pid_alive`, `_clear_stale_files`). The diff does not modify any of them; the only behavioural delta is the added re-verify gate on the SIGKILL escalation. All daemon tests (66, unit + integration) pass, including the ADR-003 import-graph independence assertion in `test_daemon_singleton.py` and the integration wedge-self-heal e2e.

### Watch List

None.

### Cross-Reference

- Source finding: pre-ship security review ADVISORY-2 (verify→SIGKILL TOCTOU). This WP is its remediation.
- No prior `.security/` viability report for this change; no existing hardening deltas to cite.

### Lens detail

**Architecture lens: nothing surfaced.** Checks run: dependency-direction (no new imports; ADR-003 independence test green), singletons/getInstance (none added), circular imports (none), resilience primitives (the guard tightens an existing best-effort kill path; no new external call), verification (new behaviour has a contract test). WPB-12 boy-scout: docstring updated in-scope to match behaviour.

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (access control / injection / validation / secrets) — no new surface; the change strictly *reduces* the risk of signalling an unrelated process. SC-01..04 — no dependency change. No new Dockerfile/logging/infra signals in the diff.

**Quality lens (all 7 outputs):**
1. Build Verification follow-up — empty (no CR-01 findings).
2. JSX/template identifier scan — N/A (no TSX/JSX/Vue/Svelte files in diff).
3. Dead-surface — none; the added `if _is_our_daemon(...)` branch is reachable and exercised by both the True path (existing `test_reclaim_escalates_to_sigkill_when_holder_outlives_term_wait`) and the False path (new `test_sigkill_escalation_reverifies_identity_and_skips_on_pid_reuse`).
4. Contract-drift — none; the `_reclaim_wedged_holder` docstring was updated to state the re-verify-before-SIGKILL behaviour, so doc matches code.
5. Test-coverage — new behaviour covered by a dedicated RED-proven test; full reclaim suite 20/20; load-bearing `test_reclaim_refuses_to_kill_on_pid_reuse_start_token_mismatch` stays green.
6. Style/readability — clear names; the inline comment explains the "why" (TOCTOU wrong-kill window) not the "what". Clean.
7. Performance (CR-10) — no anti-pattern matches. The added `_is_our_daemon` call (one `ps` probe) runs only on the cold SIGKILL-escalation path (holder outlived a ≥5s SIGTERM wait), never in a hot loop. Benign.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check (clean, both files); mypy base=32 / head=32 → 0 PR-introduced. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 116 lines, 2 files** (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files (the daemon module's reclaim region + the test file) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings: none; the one structural assertion (no new imports) is grounded in the green `test_daemon_singleton` independence test.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** `PASS`. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: 0 + checks listed. Security: 0 + primitives listed. Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (116 lines / 2 files). PH-03 Safety: none (0 migrations / 0 schema / 0 secrets / 0 infra). PH-04 Completeness: none (0 new source without test). PH-03 high → auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/harden-daemon-wedge-self-heal` (working-tree, pre-commit).
- **Neighbour expansion:** git grep on `_reclaim_wedged_holder` callers/callees within `session_manager_daemon.py`.
- **Neighbour cap:** not reached (all neighbours in one module).
- **Scanners run:** ruff, mypy.
- **Scanners unavailable:** gitleaks/semgrep/trivy not invoked — diff introduces no secrets, no dependency change, no new external surface (recorded as scoped-out, not a silent skip).
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02).
