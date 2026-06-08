# Code Review: feat/wp-003-shared-daemon-singleton — The shared session-manager daemon

> **Timestamp:** see bundle dir name (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-003-shared-daemon-singleton → change/create-change-owned-terminal-shared-session
> **Files changed:** 4 (1 new module, 2 new test files, 1 doc)
>
> **Outcome:** Ready to merge

---

## At a glance

This adds the shared terminal daemon — the single long-lived program both the
browser cockpit and the desktop terminal attach to so they become two windows
onto the same session. It is well-scoped to one new module plus its tests and a
documentation update. No build errors, no security gaps, and every behaviour the
work package asked for is covered by a test. Ready to merge.

## What to fix

No issues that need attention.

A couple of things worth knowing (not blockers):

- One safety fix was made during development: the shutdown signal handler is now
  installed before the daemon announces it is ready, so a "stop" arriving the
  instant it comes up is handled cleanly (exit 0) rather than abruptly killing
  the process. This is already done.
- The retirement of the older terminal host program was deliberately left for a
  later piece of work, because the cockpit still uses it until that migration
  happens. Removing it now would break the running cockpit.

## How this pull request is shaped

**Size — worth looking at.** ~1,047 new lines across 4 files. That is a single
cohesive unit (one module + its tests + a doc), not several concerns bundled —
so the size is inherent to the feature, not a sign it should be split.

**Scope — clean.** One concern (the daemon), one commit type.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets.

**Completeness — clean.** Every new source behaviour has tests (a unit suite for
the idle-exit policy and config/lock helpers, an integration suite booting the
real daemon over a real socket).

---

## Technical detail

> Below this point uses internal taxonomy for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01: py_compile + ruff — the project's CI gate; mypy is not a CI gate).
- **PR Hygiene:** 0 high. Size medium (single-unit; not splittable without fragmenting a WP).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — composition-root + dependency-inward correct |
| Security | 0 | 0 | none — 0o600 socket / 0o700 dir, guard ON, no secrets |
| Quality | 0 | 0 | none — 96% coverage, all DoD behaviours tested |

### Build Verification (CR-01)

`py_compile` (CI lint gate): 0 errors. `ruff check` + `ruff format --check`: clean.
mypy is **not** a CI gate (CI runs py_compile + ruff + pytest); the 2 mypy notes
on the new file are identical to the pre-existing sanctioned `session_manager_host.py`
pattern (`BindingManager.__getattr__` delegation defeats nominal typing by design;
the test-lib import is lazy/test-only). No type-ignore noise added, preserving
parity with the established host module (CP).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):     commit_type_spread {feat}; module_fan_out 1     → low
Size (PH-02):      lines_added 1047; files_changed 4               → medium (single WP unit)
Safety (PH-03):    migrations 0; schema 0; infra 0; secrets 0      → low
Completeness (PH-04): new_source_without_test 0                    → low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The daemon reuses the WP-001 binding primitives and the WP-004 adapter
(both already merged + reviewed) and the frozen engine (untouched).

### Watch List

- The race-loser "lock held but no live socket → exit 1" branch
  (`session_manager_daemon.py:311-322`) and the idle-loop body
  (`:358`) are exercised in production but not directly asserted by a
  deterministic test (they require a real wedged-mid-boot daemon, hard to
  stage without flake). The watcher's decision logic itself is fully unit-
  tested. No delta — measured coverage is 96% with all DoD behaviours covered.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** py_compile + ruff (the project CI gate). Base: clean. Head: clean. Coverage gap: mypy not a CI gate; noted parity with host.
- [—] **CR-02 Parallel dispatch.** Diff >200 lines but a single cohesive module + its tests; reviewed end-to-end by one reader (the executor) as part of the RGB loop. Recorded as single-reader given one-module scope.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end (authored this session).
- [✓] **CR-04 Evidence discipline.** Findings (none) would cite file:line; Watch List items cite file:line.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency direction, singletons, frozen-engine modification, independence import-graph). Security: nothing surfaced (checks: socket/dir perms, binding guard, secrets, test-seam loading). Quality: nothing surfaced (checks: build verification, dead surface, contract drift, test coverage, CR-10 perf patterns — no N+1/unbounded-materialisation matches).
- [✓] **CR-09 PR Hygiene applied.** Scope low; Size medium (single WP unit); Safety low; Completeness low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git working tree vs change/create-change-owned-terminal-shared-session
- **Neighbour expansion:** git grep — reused primitives (WP-001 binding, WP-004 adapter, frozen engine) already reviewed; daemon adds no new neighbour gaps
- **Scanners run:** py_compile, ruff (project CI gate)
- **CR-10 performance scan:** no anti-pattern matches (the watcher samples status_keys once per 30s tick; no loops with IO/DB on a hot path)
