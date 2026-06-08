# Code Review: feat/wp-005-desktop-viewer-client — Desktop viewer client

> **Timestamp:** 2026-06-08T121751Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-desktop-viewer-client → change/create-change-owned-terminal-shared-session
> **Files changed:** 2 (session_viewer.py + its integration test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the desktop terminal viewer — the local program that opens inside
the change's terminal window, connects to the shared session, shows what's running,
sends your keystrokes, and (importantly) leaves the session running when you close
the window. It is clean: the build passes, there are no type errors, and it ships
with a thorough test that drives a real session over a real socket (no fakes in the
round-trip). Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Two new files, one concern: the viewer and the test that proves it.

**Scope — clean.** A single feature (`feat:`); no refactor or migration mixed in.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
changes, no secrets in the diff.

**Completeness — clean.** The new code ships with its test, and every line of the
new viewer is exercised.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high/medium (PH-01..PH-04 all low/clean) (CR-09)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (deps inward; timeouts present; no secrets) |
| Security | 0 | 0 | — (no auth surface; bytes never logged) |
| Quality | 0 | 0 | — (tests present; 100% coverage; lint/type clean) |

### Build Verification (CR-01)

`ruff check`: All checks passed. `mypy session_viewer.py`: 0 errors on the file
(pre-existing engine errors in `_session_manager/manager.py` are out of scope —
the engine is frozen, never modified by this WP). `compileall`: OK. No
PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 → low
Size (PH-02):         lines 1109, files 2 → low (two cohesive new files)
Safety (PH-03):       migrations 0, schemas 0, secrets 0, infra 0 → low
Completeness (PH-04): new_source_without_test 0 (ships with test) → low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The viewer consumes the engine's §2.13 wire as a plain client over
`_session_manager.daemon_client` (WP-002) and the `SocketServer` (frozen engine);
it introduces no change to either.

### Watch List

- The SIGWINCH/SIGTERM signal-handler bodies are exercised only via the
  subprocess integration tests (signal handlers must install on the main thread,
  which an in-process test thread cannot do). They are marked `# pragma: no cover`
  with a note; their behaviour IS proven by `test_sigwinch_triggers_resize` and
  `test_exit_detaches_session_survives_and_tty_restored` driving a real viewer
  subprocess. No action — recorded for awareness.

### Cross-Reference

- No prior security report for this surface.
- No existing hardening deltas covered.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff + mypy + compileall on HEAD. 0 PR-introduced errors. Coverage gap: none (no separate BASE run needed — both files are net-new, so every error is PR-introduced by definition; none found).
- [✓] **CR-02 Dispatch shape.** Diff 1109 lines / 2 files. Above the line threshold but two cohesive net-new files authored in this session with full context; reviewed inline with end-to-end reads of both. Recorded as a deliberate single-reader pass on net-new, single-concern files.
- [✓] **CR-03 Full-file reads.** session_viewer.py (503 lines) and test_session_viewer.py (606 lines) read end-to-end.
- [✓] **CR-04 Evidence discipline.** No findings; nothing to evidence. Tool logs in tool-outputs/.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; both files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (deps inward; per-request timeouts; no secrets; AF_UNIX local; no-logging correct per NFR-SEC-03). Security: nothing surfaced (no auth surface — server-side binding guard; bytes never logged; no injection/shell/eval; spawn_command is the contract-controlled ensure_daemon seam). Quality: jsx-ident scan N/A (no TSX); dead-surface none; contract-drift none (wire matches §2.13 server framing); test-coverage present (9 tests, 100%); CR-10 perf — no anti-pattern matches (only byte-pump loops, no DB/RPC/FS in loops).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope low; PH-02 Size low; PH-03 Safety low (0 migrations/schemas/secrets/infra); PH-04 Completeness low (ships with test). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** local git (net-new untracked files vs change branch)
- **Neighbour expansion:** import-graph by inspection — consumers are WP-006 (launcher) not yet landed; producer is the frozen engine. No neighbour code modified.
- **Scanners run:** ruff, mypy, compileall.
- **Lenses dispatched in parallel:** no — single-reader on two net-new cohesive files (CR-02 recorded).
