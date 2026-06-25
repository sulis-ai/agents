# Code Review: hotfix — durable-context wiring must never stall the live terminal open

> **Timestamp:** 2026-06-25T143927Z (ISO 8601 UTC)
> **Author:** autonomous executor (CH-GJ9KQR hotfix)
> **Branch:** change/create-portable-agent-context (local working-tree diff)
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes a regression where opening a terminal could hang forever. The cause: when a terminal opens, the system now also writes a durable record of the session to disk under `~/.sulis`. That disk write ran in the middle of the open, with no time limit and no protection if the disk was slow or unavailable — so on a busy or restricted machine, the terminal open never finished.

The fix puts a strict time limit and a safety net around that disk work: if it fails or takes too long, the terminal still opens normally and the durable record is simply skipped for that session. The live terminal is never held hostage to the record-keeping. Four new tests prove the open completes even when the disk write throws an error or hangs. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

One thing for awareness (not a blocker): if the disk genuinely hangs (not just slow), the helper that enforces the time limit leaves a background worker behind to finish on its own. In normal operation this is invisible and self-cleaning, but if the disk were stuck for a very long time across many terminal opens, those background workers would accumulate until the disk recovered. This is an acceptable trade — the alternative is letting the terminal hang, which is the bug we are fixing — and it is bounded in practice. Worth keeping in mind if `~/.sulis` is ever on a network filesystem.

## How this pull request is shaped

**Size — clean.** 369 lines across 3 files; the production change is one well-scoped file (~157 lines), the rest is tests (199 lines) and a one-line test-budget revert.

**Scope — clean.** Single concern: isolate the durable side-channel on the open/restart path. One `fix:` type.

**Safety — clean.** No migrations, no schema, no infra, no secrets.

**Completeness — clean.** Four new regression tests added for the new behaviour (error path, hang path, degraded-seam path, restart path).

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty (no PR-introduced error *class*); all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced error classes (CR-01). Ruff lint + format clean. Mypy: 32 head vs 31 base — the +1 is `float(self._tuning.get("durable_attach_timeout", ...))`, byte-identical to 3 pre-existing accepted `_tuning.get`→`float` casts in the same constructor (`turn_timeout`/`idle_timeout`/`scrollback_capacity_bytes`); none of those are `# type: ignore`d, so matching them is CP-01 convention-consistency, not a new defect.
- **PR Hygiene:** 0 high, 0 medium. Scope low, size low, safety none, completeness none.
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one low finding is an inherent trade-off of the chosen isolation primitive, grounded by no failing test → Watch List, not a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (low) | 0 | Abandoned worker-thread ceiling under sustained `~/.sulis` FS hangs |
| Security | 0 | 0 | None — `change_id`/`key` path traversal guarded by `validate_store_id` (unchanged) |
| Quality | 0 | 0 | None — 4 regression tests cover the four failure paths |

### Build Verification (CR-01)

No PR-introduced error class. `tool-outputs/ruff-head.log` clean; `tool-outputs/mypy-head.log` shows 32 errors, all but one pre-existing in the module (baseline 31). The single delta line (`durable_attach_timeout` float cast) reproduces the exact `_tuning: dict[str, object]` → `float()` arg-type pattern the constructor already carries 3×.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread {fix}; module_fan_out 2 → severity low
Size (PH-02):        +369 / -20; files 3; prod 157, tests 199 → severity low
Safety (PH-03):      migrations 0; schema 0; infra 0; secrets 0 → severity none
Completeness (PH-04):new_source_without_test 0; tests_added 4 → severity none
```

### Findings in the Changes

#### `plugins/sulis/scripts/_session_manager/manager.py` — `_run_isolated_bounded` — low (architecture)

**What:** On the timeout branch the worker thread is abandoned (daemon, holds no lock) rather than cancelled — Python has no thread cancellation. Under a *sustained* `~/.sulis` filesystem hang across many opens, abandoned `durable-attach` workers accumulate until the FS recovers.

**Quoted text:**
```python
worker = threading.Thread(target=_runner, name="durable-attach", daemon=True)
worker.start()
worker.join(timeout)
if worker.is_alive():
    _log.warning(...); return None
```

**Why it matters:** Bounded thread leak only under a degenerate, sustained-hang condition. The alternative (no bound) is the regression being fixed — a stalled live terminal. The trade favours the live session, which is correct (WP-004 ADV-1 intent).

**Recommendation:** Accept as-is. `signal.alarm` is unusable here (main-thread-only; daemon serves on worker threads), and a process-level FS watchdog is out of scope for a hotfix. Watch-list it; revisit only if `~/.sulis` moves to a network mount.

### Findings in the Neighbours

None. Direct callers of `_attach_durable_sink` (`open`) and `_respawn` were read; the change is additive isolation around existing seams and the live-tail `on_event` fan-out is untouched (the durable observer is chained only on successful attach).

### Watch List

- Abandoned-worker ceiling under sustained FS hang (see the low finding) — no failing characterisation test constructs a *sustained* multi-open hang, so no delta per CR-04.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` clean; `mypy` base 31 / head 32, the delta consistent with the file's established cast pattern (no new error class). Logs in `tool-outputs/`.
- [✓] **CR-02 Single-reader pass justified by diff size:** 3 files, production surface 157 lines in 1 file — within the ≤200-line / ≤5-file carve-out.
- [✓] **CR-03 Full-file reads.** `manager.py` change region + both callers (`open`, `_respawn`) and the durable-sink/store/readers modules read end-to-end; the test file read end-to-end.
- [✓] **CR-04 Evidence discipline.** The one finding cites file + symbol + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 1 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty, no unread >50-line file, all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding. Security: nothing surfaced (path traversal guarded by `validate_store_id`, unchanged; no new auth/injection/secret surface). Quality: 0 findings — build verification clean, no JSX (backend Python), no dead surface, no contract drift, 4 tests added for new behaviour, CR-10 no anti-pattern matches (the daemon thread is the intended fix, not a hot-loop).
- [✓] **CR-09 PR Hygiene applied.** Scope low, size low, safety none, completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** local working-tree diff vs `change/create-portable-agent-context` (hotfix, not a PR branch).
- **Neighbour expansion:** git grep on `_attach_durable_sink`, `_run_isolated_bounded`, `_respawn`, `durable_attach_timeout`. 0 neighbour findings.
- **Scanners run:** ruff, mypy. Gitleaks/Semgrep/Trivy not run (no new dependency/secret/infra surface; manual secret-pattern grep on the diff: 0 hits).
