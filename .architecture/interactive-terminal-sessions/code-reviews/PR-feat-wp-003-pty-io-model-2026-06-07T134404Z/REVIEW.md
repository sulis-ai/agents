# Code Review: WP-003 — Add the PTY io-model at the single spawn seam

> **Timestamp:** 2026-06-07T134404Z (ISO 8601 UTC)
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-pty-io-model → change/extend-interactive-terminal-sessions
> **Files changed:** 6 (5 modified + 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a second way to run a background session — on a real terminal
(a "PTY") instead of plain pipes — so the cockpit can later show and type into a
live terminal. It is built as an opt-in: existing sessions keep working exactly
as before because the new setting defaults to the old behaviour. The build is
clean, the change is well-scoped to one area of the engine, and it ships with
tests for the new behaviour plus a regression check proving the old chat path is
untouched. One internal consistency issue was found during review and fixed in
place before this report was written. No issues remain that need attention.

## What to fix

No issues that need attention. One consistency issue was found and fixed during
the review (see the technical detail below).

## How this pull request is shaped

**Size — looks good.** About 244 net lines across 6 files, all in one engine
area (`_session_manager/`). Comfortably reviewable.

**Scope — looks good.** A single concern: add the PTY io-model branch at the one
shared spawn point. No mixed refactor-plus-feature.

**Safety — looks good.** No database migrations, no schema/IDL changes, no
infrastructure files, no secrets. The change does add raw file-descriptor
handling (allocating and freeing terminals), which is the one place to be careful
— and the review confirmed every path that allocates a terminal also frees it,
including the failure paths.

**Completeness — looks good.** Three new tests cover the new behaviour: the
terminal read loop, the "couldn't open a terminal" error, and a hardening test
proving no file-descriptor leak when the spawn fails.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high findings (PH-01..PH-04 all low/clean)
- **In the changes:** 1 finding (0 critical, 0 high, 1 medium — fixed inline)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the one finding was fixed inline, not deferred)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (fixed inline) | 0 | pty pump passed `self.process` instead of its captured process to `_handle_eof_death` |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No type-checker (mypy/pyright) configured for the project — coverage gap noted.
`ruff check` (the configured linter) ran on all 6 changed files: **All checks
passed.** `python -m py_compile` on all 6 files: **OK.** Build Verification
section is empty → no PASS block.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):     commit_type_spread: {feat}  module_fan_out: 1 (_session_manager) → low
Size (PH-02):      +288 / -44 (244 net), 6 files → low (≤500 line band, ≤15 file band)
Safety (PH-03):    migrations: 0  schema_idl: 0  infra: 0  secret_hits: 0 → low
Completeness (PH-04): new_source_without_test: 0 (the new file IS the test) → low
```

### Findings in the Changes

#### `_session_manager/session.py` — `_pty_master_pump` → `_handle_eof_death` — medium (architecture) — FIXED INLINE

**What was happening:** the pty master-reader pump called
`self._handle_eof_death(self.process, generation)` on EOF, passing `self.process`
(which a concurrent restart may have already swapped to the *new* process) rather
than the process the pump captured at launch. The stdout pump passes its own
captured `process` arg.

**Why it matters:** the generation guard inside `_handle_eof_death` made this
currently harmless (a stale pump skips every guarded step). But it broke the
"a stale pump never touches the restarted session's fresh process" invariant the
pump's own docstring claims, and was a latent bug if the guard logic ever
changed — `process.wait()` could be invoked on the wrong process.

**Fix applied:** `_pty_master_pump` now captures `process` at launch (passed from
`_start_pty_pumps`, parity with `_stdout_pump`/`start_pumps`) and hands it to
`_handle_eof_death`. Re-verified: `ruff`, `ruff format`, the 3 pty unit tests,
and `test_session_restart_resume.py` all green after the fix.

`lens: architecture`

### Findings in the Neighbours

None. The diff touches the spawn seam (`manager._spawn_process`), the session
pumps (`session.py`), the spec (`adapter.py`), the error vocabulary
(`events.py`), and the package re-exports (`__init__.py`). The direct neighbours
— `lifecycle.py` (`_respawn` caller), the contract suite, the core/restart tests
— were exercised by the regression run (45 session integration tests + 54
session unit tests green) and surfaced no exposure.

### Watch List

- The pty **restart** path (`replace_process` re-creating the PTY) and the pty
  master pump's **EOF death discipline** are unit-exercised indirectly but their
  dedicated integration proof is `tests/integration/test_terminal_lifecycle.py::
  test_restart_recreates_pty` — owned by a later WP per TDD §6.4. Not a gap in
  this WP's contract (its verification artifact is
  `test_pty_session.py::test_master_read_appends_scrollback`).

### Cross-Reference

- No prior `.security/interactive-terminal-sessions/` viability report to cite.
- No existing hardening deltas to dedup against.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `py_compile` on all 6 changed files. Base (change branch): clean. Head: clean. Coverage gap: no mypy/pyright configured (project lints with ruff).
- [✓] **CR-02 Dispatch shape.** Diff 244 net lines / 6 files — at the threshold. Reviewed as a focused single-reader pass with full author context of the just-written code; all three lenses run explicitly below. Recorded per the carve-out note.
- [✓] **CR-03 Full-file reads.** All changed source files read end-to-end (the reviewer authored them this session and re-read the final state).
- [✓] **CR-04 Evidence discipline.** The one finding cites file + method + quoted behaviour.
- [✓] **CR-05 Severity rubric.** Applied: 1 medium (fixed inline). No critical/high.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read; every lens produced output).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding (fd-lifecycle traced; fixed inline). Security: nothing surfaced (no auth/injection/secret surface — attach/feed is WP-004; pty bytes are read-only into scrollback). Quality: jsx scan N/A (no JSX); perf CR-10 — no anti-pattern matches (only loop is the bounded `os.read` pump); dead-surface none; contract-drift none; test-coverage present (3 new tests).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope low; PH-02 Size low; PH-03 Safety low (fd handling reviewed, all paths free their fds); PH-04 Completeness low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/extend-interactive-terminal-sessions` (working tree; changes not yet committed at review time)
- **Neighbour expansion:** git grep for `_spawn_process` / `replace_process` callers — only `manager.open`, `manager._respawn`; both in the diff
- **Scanners run:** ruff (lint), py_compile (build floor)
- **Scanners unavailable:** mypy/pyright (not configured); gitleaks/semgrep/trivy (not required — no secrets/deps/infra in diff)
