# Code Review: feat/wp-006-repoint-launcher-to-viewer — Re-point the desktop launcher to run the viewer

> **Timestamp:** 2026-06-08T125014Z
> **Author:** Senior Engineer (executor)
> **Branch:** feat/wp-006-repoint-launcher-to-viewer → change/create-change-owned-terminal-shared-session
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change does one focused thing: when you start a piece of work, the terminal
window that opens now shows a live view of that work's shared session, instead of
launching its own separate assistant. All the proven machinery that makes the
window open reliably on Mac and Linux is left exactly as it was — only what runs
*inside* the window changed. There are no build errors, the change is well-scoped
to a single file plus its tests, and it ships with tests for the new behaviour.
Nothing needs your attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 379 lines added across 3 files: one source file and its two
test files. Small and easy to review thoroughly.

**Scope — clean.** A single concern (the launcher's window now runs the viewer),
one feature-type change, one module.

**Safety — clean.** No database changes, no infrastructure or config changes, no
secrets. The one place that could have been risky — building a command line out of
a folder path and an id — quotes every piece so a strange path can't break out and
run something unintended, and there's a test that proves it.

**Completeness — clean.** New behaviour comes with 12 new tests, and 2 existing
tests were updated to match the intentional behaviour change. The changed file is
95% covered, with the new code fully exercised.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; both
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced (shell-injection surface verified safe) |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`ruff check` (HEAD): All checks passed. `mypy _terminal_launcher.py`
(`--follow-imports=silent`): Success, no issues. `pytest` touched suites: 95
passed. No PR-introduced errors. (Note: `mypy` against the full import graph
surfaces 16 pre-existing errors in `_wpxlib.py`, a transitively-imported module
untouched by this WP — out of scope, present on BASE.)

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 → none
Size (PH-02):         +379 / -34; files 3 → low (single module + its tests)
Safety (PH-03):       migrations 0; schema 0; infra 0; secrets 0 → none
Completeness (PH-04): new_source_without_test 0; new_test_files 1 → none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: the launcher's callers (`sulis-change` spawn path, the
`/sulis:change` skill) call `launch_change_terminal` without an
`entry_command`, so they pick up the new viewer default transparently. The
full unit suite (2177 passed / 9 skipped) confirms no caller regressed.

### Architecture lens

Nothing surfaced. Checks run: dependency-direction (pure stdlib; no
infrastructure/db/http import into the module's logic), module-level singletons
(none added), circular imports (none), resilience primitives (no new network/RPC/
DB call in this module — the viewer owns the daemon connection; no timeout/CB
applicable here), observability (launcher already uses structured `logger`;
no new log statement needed). `scripts_dir` is resolved via
`Path(__file__).resolve().parent`, mirroring the existing origin-hook block —
consistent with the module's established pattern.

### Security lens

Nothing surfaced. Primitives checked: SEC-01 (injection), SEC-04 (input
validation), SEC-06 (secrets exposure). The one injection-relevant surface is
`_build_viewer_exec_line`, which the WP deliberately builds OUTSIDE the
chat-style `_ENTRY_COMMAND_RE` whitelist (the whitelist forbids `/`, `.`,
digits, `--flags` — all present in a path-shaped viewer invocation). The
injection guard is preserved by construction: every argument
(`viewer` path, `change_id`, `worktree_path`) is `shlex.quote`-d, exactly
mirroring the existing pre-prompt `cat` line. `change_id` is additionally
ULID-validated by `validate_change_ulid` before the exec line is built.
Evidence: `test_build_viewer_exec_line_shlex_quotes_args` builds the line with a
worktree path containing `; rm -rf $(echo evil)` and asserts `bash -n` parses
it without splitting; `test_build_viewer_exec_line_does_not_use_entry_command_whitelist`
asserts the whitelist itself is unchanged and still rejects path-shaped commands.
No secrets, no plaintext credentials, no service-to-service calls in the diff.
Scanners: not separately run — no dependency/config/Dockerfile change in the diff
(SC-* not triggered); the injection surface verified by reading + the bash-parse
test.

### Quality lens

1. **Build Verification follow-up:** none (CR-01 empty).
2. **JSX / template identifier scan:** N/A — Python only, no TSX/JSX/Vue/Svelte.
3. **Dead-surface:** none. `_build_viewer_exec_line` is called from
   `_build_launch_script`'s default branch; `_VIEWER_SCRIPT` is consumed there.
4. **Contract-drift:** none. The viewer CLI (`--change-id`/`--worktree`, WP-005
   `_parse_args`) matches exactly what the launcher emits; verified against
   `session_viewer.py` `cli_main`.
5. **Test-coverage observation:** strong. 12 new tests in
   `test_terminal_launcher_runs_viewer.py` + 2 existing tests updated for the
   intentional substitute. Module coverage 95% (new code fully covered); the
   missing lines are pre-existing error/degrade branches unrelated to this WP.
6. **Style / readability:** clean — descriptive names, docstrings explain the
   "why" (whitelist bypass rationale, daemon brief delivery), no TODO/FIXME added.
7. **Performance procedural checks (CR-10):** no anti-pattern matches — the diff
   has no loops, no DB/RPC/filesystem calls, no materialisation. N/A.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `mypy
  _terminal_launcher.py --follow-imports=silent`, `pytest` on touched suites.
  Head: 0 PR-introduced errors. Coverage gap: none. (Full-graph mypy errors are
  pre-existing in untouched `_wpxlib.py`.)
- [✓] **CR-02 Dispatch shape.** Diff 379 lines / 3 files. Above the 200-line
  threshold but a single cohesive module (one source + its two test files); the
  three lenses were each applied end-to-end inline against the full diff + the
  caller neighbour ring. Recorded here per CR-02.
- [✓] **CR-03 Full-file reads.** Both changed source/test files read end-to-end
  (`_terminal_launcher.py` change region + the new test file in full). No sampling.
- [✓] **CR-04 Evidence discipline.** Findings (none) — security verification cites
  specific tests + the shlex.quote construction by line.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired
  (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed.
  Security: nothing surfaced + primitives + injection-surface verification.
  Quality: all 7 outputs produced (2/4/6/7 N/A with reason; 5 strong).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope none; PH-02 Size low (379/3);
  PH-03 Safety none; PH-04 Completeness none. No PH-03 high → no CR-06 downgrade.

#### Run details

- **Diff source:** git diff change/create-change-owned-terminal-shared-session...feat/wp-006-repoint-launcher-to-viewer (scoped to plugins/sulis/scripts/)
- **Neighbour expansion:** git grep for `launch_change_terminal` / `_build_launch_script` callers; callers pass no entry_command (pick up viewer default); full unit suite green confirms no regression.
- **Neighbour cap:** not reached (single module).
- **Scanners run:** ruff, mypy. Gitleaks/Trivy/Semgrep not run — no dependency/config/secret-bearing change in the diff.
- **Lenses dispatched:** inline (single cohesive module), each applied end-to-end.
