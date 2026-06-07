# Code Review: WP-006 — idle-eviction + LRU memory-cap + dead-process detection

> **Timestamp:** 2026-06-05T151744Z (ISO 8601 UTC)
> **Author:** executor (WP-006)
> **Branch:** feat/wp-006-eviction-memory-cap → change/refactor-persistent-chat-sessions
> **Files changed:** 4 (2 new: maintenance.py, test_session_eviction.py; 2 edited: manager.py, __init__.py)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds resource bounds to the warm-session manager: it reaps sessions that have gone idle, caps how many warm sessions run at once (evicting the least-recently-used when over the cap), and notices when a child process has died during its periodic check. The work is well-scoped to one new module plus the minimal wiring into the manager, with a thorough test file. One performance issue was found during review — a status snapshot would have launched one helper process per session — and it has already been fixed in place by batching it into a single call. Nothing else needs attention.

## What to fix

No issues that need attention. The one performance issue found during review (described below in technical detail) was fixed inline and verified.

## How this pull request is shaped

Well-shaped. It is a single feature (`feat:`), confined to the session-manager package, with no database migrations, no infrastructure changes, and no secrets. It adds one source file and one matching test file (no source-without-test gap). Size is moderate and single-concern.

## Things to take away

Nothing specific — the change follows the established module-per-collaborator pattern of the existing package (lifecycle.py / state.py) and respects the WP boundary cleanly (it consumes the liveness, death-recovery, and activity-tracking seams rather than re-implementing them).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all review files read end-to-end; all three lenses produced output. The single medium quality finding was resolved inline before report write.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01: ruff + py_compile).
- **PR Hygiene:** 0 high, 0 medium (all four primitives low) (CR-09 / PH-01..04).
- **In the changes:** 1 finding (1 medium — RESOLVED inline).
- **In the neighbours:** 1 note (pre-existing WP-005 test flakiness — not introduced).
- **Draft fixes:** 0 (the one lens finding was fixed inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — dependency-inward preserved; seams consumed not forked |
| Security | 0 | 0 | none — stdlib-only, no secrets/network; ps argv from int pids only |
| Quality | 1 (resolved) | 1 note | CR-10: status() forked one ps per session (fixed: one batched ps) |

### Build Verification (CR-01)

Ran the project's configured mechanical checks (`ruff check`, `ruff format --check`, `python3 -m py_compile`) on the four review files against HEAD. **0 PR-introduced errors.** Base is clean; HEAD is clean. Raw output in `tool-outputs/ruff-check-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; module_fan_out: 1 (_session_manager) → severity low
Size (PH-02):         ~700 lines, 4 files; generated_ratio 0; lock_file_ratio 0 → severity low
Safety (PH-03):       migrations 0; schema/IDL 0; infra 0; secret hits 0 → severity low
Completeness (PH-04): new_source 1, new_tests 1, source_without_test 0; no API/schema change → severity low
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

#### `_session_manager/manager.py` — `status()` memory reading — medium (quality, CR-10) — RESOLVED INLINE

**What's happening:** `status()` originally called `session_memory_bytes(session)` inside the per-session loop, and each call forked a `ps` subprocess (with up to a 2s timeout). For a manager holding the RAM-derived cap of warm sessions, a single `status()` call would fork `ps` once per session.

**Quoted text (before fix):**
```python
for session in sessions:
    snapshot.append(SessionStatus(..., memory_bytes=session_memory_bytes(session), ...))
```

**Why it matters:** CR-10 wasted-process-roundtrips / N-subprocess-in-loop. `status()` is documented "side-effect-free" and is the natural observability/diagnostics surface; forking N short-lived `ps` processes (each up to 2s on a slow/hung pid) makes a cheap-looking call expensive and slow precisely when many sessions are warm.

**Resolution (inline, Path A):** Added `memory_bytes_for_pids(pids: list[int]) -> dict[int,int]` to `maintenance.py` which reads **all** pids' RSS in one `ps -o pid=,rss= -p p1,p2,…` call. `status()` now builds the pid list once and forks `ps` exactly once regardless of session count; `session_memory_bytes()` is retained as the single-session convenience (delegates to the batch). Re-ran CR-01 (clean) and the WP-006 suite (15/15, stable across 3 runs); maintenance.py coverage 96%.

### Findings in the Neighbours

#### `tests/integration/test_session_restart_resume.py` (WP-005) — note (not introduced)

The WP-005 restart-detection tests (`test_recovery_budget_exhaustion_disables`, `test_process_death_restarts_same_key_same_log`) are timing-flaky under CPU load: they drive repeated child kills against a 5s `_wait_for` deadline. Observed 1-2 failures in ~1 of every 4 full-suite runs; pass reliably in isolation. **This file is untouched by WP-006** (verified: empty `git diff` vs base) and the flakiness reproduces on the file alone — it is a pre-existing condition, not a WP-006 regression. Surfaced for awareness; out of scope for this WP's contract (another WP's test file). Recommend a separate hardening pass to replace the kill-loop deadline with an event-driven wait if it proves disruptive in CI.

### Watch List

- The conservative tuning constants (`_PER_SESSION_RAM_ESTIMATE` 512 MiB, `_RAM_BUDGET_FRACTION` 0.5, idle 600s) are decided-by-default per the contract (Part 3 Q3) and carry no founder-facing consequence until eviction is observed; they are intentionally generous. No action — noted so a future tuning pass knows where the knobs are.

### Cross-Reference

- No prior `.security/persistent-chat-sessions/` viability report found.
- No existing hardening-deltas to cite.
- Neighbour pattern (WP-005 test flakiness) is localised to two tests — does not warrant a full `/sulis:codebase-audit`.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` + `py_compile` on all 4 review files. Base clean, Head clean. 0 PR-introduced errors. No coverage gap.
- [✓] **CR-02 Dispatch shape.** Single-reader pass: tightly-scoped backend WP authored in this session; every review file read end-to-end during authoring + review. Diff ~700 lines / 4 files; the reviewer (same agent) read all files end-to-end, satisfying CR-03 directly.
- [✓] **CR-03 Full-file reads.** maintenance.py (274→296), manager.py (full), __init__.py (full), test_session_eviction.py (full) all read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file + the quoted loop + the resolution.
- [✓] **CR-05 Severity rubric.** Applied: 1 medium (operational pain on observability path), resolved. Neighbour flakiness recorded as note (would be medium at full severity; it is pre-existing, surfaced not introduced).
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (dependency-inward preserved; consumes is_alive/_on_process_death/last_activity unchanged — verified by grep). Security: nothing surfaced (no secrets, no network; stdlib-only; ps argv assembled from int pids only — no shell, no user input). Quality: 1 finding (CR-10 N-subprocess) + test-coverage observation (new source has matching tests) + dead-surface (none) + contract-drift (none) + CR-10 perf scan (one match, fixed).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single feat, one module). PH-02 Size: low. PH-03 Safety: low (0 migrations/schemas/infra/secrets). PH-04 Completeness: low (1 new source + 1 new test, no gap). PH-03 high → auto-downgrade: did not fire.

#### Run details

- **Diff source:** git diff change/refactor-persistent-chat-sessions vs working tree + 2 untracked new files.
- **Neighbour expansion:** git grep over the _session_manager package; neighbours = manager.py callers of status()/open(), the WP-005 lifecycle (consumed), the WP-004 session (last_activity read). Within 20-file cap.
- **Scanners run:** ruff (lint+format), py_compile; manual secret/network/N+1 greps.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (stdlib-only Python diff, no deps, no IaC; manual secret-pattern grep run instead — 0 hits).
- **Lenses dispatched in parallel:** no — single-reader pass (CR-02 carve-out path; all files read end-to-end).
