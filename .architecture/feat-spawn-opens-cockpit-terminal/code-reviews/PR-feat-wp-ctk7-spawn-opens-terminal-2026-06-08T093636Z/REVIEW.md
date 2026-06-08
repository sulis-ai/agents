# Code Review: PR-feat-wp-ctk7-spawn-opens-terminal — start opens a terminal by default

> **Timestamp:** 2026-06-08T093636Z (ISO 8601 UTC)
> **Author:** executor (CH-01KTK7)
> **Branch:** feat/wp-ctk7-spawn-opens-terminal → change/feat-spawn-opens-cockpit-terminal
> **Files changed:** 4 (1 source, 2 tests, 1 doc)
>
> **Outcome:** Ready to merge

---

## At a glance

This change makes starting a piece of work open a real terminal window again —
straight away, with no extra setting required and no "go open the cockpit
instead" message. It does this by removing the one branch of code that used to
suppress the terminal, and by updating the wording around it so the terminal
launcher reads as the supported way to start work (which it now is). All the
proven, safe machinery that actually opens the window — the security scrubbing,
the safe handling of the briefing text, the file-permission checks — is left
exactly as it was. The tests that used to assert the old "suppressed" behaviour
were deliberately flipped to assert the new "opens by default" behaviour, and
the whole test file passes (83 tests), as does the wider test suite (2,096).

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — fine.** 241 lines across 4 files, only one of which is product code.
A focused, single-purpose change.

**Scope — fine.** One concern: restore the default-on terminal for the
change-start flow. No mixed feature/refactor bundling.

**Safety — fine.** No database migrations, no schema/contract files, no
infrastructure files, no secrets. The change removes a behavioural branch and
re-words documentation; it does not touch the security-hardening lines.

**Completeness — fine.** The behaviour reversal is covered test-first: the
existing suppression tests were characterised and flipped, and new tests assert
the default-on spawn on both macOS and Linux, the override flag still
dispatching, and headless being unaffected.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the
single source file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

- `ruff check _terminal_launcher.py tests/unit/test_terminal_launcher.py` →
  All checks passed (base + head identical: 0 errors).
- `python3 -m py_compile` on both changed Python files → OK.
- `pytest tests/unit/test_terminal_launcher.py` → 83 passed.
- Full unit suite (`pytest tests/unit/`) → 2096 passed, 9 skipped.

No PR-introduced errors. Build Verification section empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → single concern
  module_fan_out: 1 top-level dir (plugins/)   → focused
  severity: none

Size (PH-02):
  lines_added: 127, lines_removed: 114, total: 241
  files_changed: 4 (1 source, 2 test, 1 doc)
  severity: none (small, mostly test/doc churn)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (no new source files; behaviour change is test-first)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

**Architecture lens:** nothing surfaced. Checks run: dependency-direction (no
new imports; the change deletes a branch and rewords docstrings), resilience
(env-scrub, validators, shlex-quoting, chmod, OSError→_failed guards all
verified present and unchanged via diff inspection), observability (logging
unchanged). The removed branch was a behavioural suppression returning a
pointer dict — not a resilience or security primitive.

**Security lens:** nothing surfaced. Primitives checked: SEC-01..07 (no new
input surface; entry_command/env-key/worktree/pre_prompt validators untouched),
SC-01..04 (no dependency changes), DAT-03 (env-scrub line unchanged; no PII in
new log lines). No secrets introduced (grep clean). The pre_prompt sidecar
delivery (#86) and env-scrub hardening (MUC-2) are byte-unchanged.

**Quality lens:**
1. Build Verification follow-up — no CR-01 findings to translate.
2. JSX/template scan — N/A (no TSX/JSX/Vue/Svelte files in diff).
3. Dead-surface — `_os_window_enabled()` is retained intentionally as a
   documented override knob and remains referenced by tests; not dead. No
   unused imports introduced.
4. Contract-drift — the returned dict shape is unchanged; the only removed
   producer path was the suppression `_failed` branch, which had no consumer
   depending on its specific message (grep confirmed: only a manual smoke doc
   referenced it, and that doc was updated in this diff).
5. Test-coverage — behaviour reversal covered test-first; 4 new/flipped
   default-on tests + override-flag + headless coverage. 94% coverage on
   `_terminal_launcher.py`.
6. Style/readability — docstrings reframed off the deprecated-fallback posture;
   no complexity added (net deletion of a branch).
7. CR-10 performance — no anti-pattern matches. The two loops in the file
   (extra_env items; the 3-entry Linux terminal-app list) are pre-existing,
   bounded, and not touched by this diff.

### Findings in the Neighbours

None. The one neighbour — `sulis-change` `start --spawn`, which calls
`launch_change_terminal(...)` with the default `visible=True` — now reaches the
spawn dispatch by default, which is the intended behaviour. No code change
required there; its pre-existing ruff warnings are unrelated and out of scope.

### Watch List

None.

### Cross-Reference

- No prior security report for this project.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: ruff, py_compile, pytest.
  Base + Head: 0 ruff errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass: 241 lines but only one
  ~640-line source file with a localised diff (one branch removed + docstring
  rewording); remaining churn is test + doc. Source file read end-to-end.
- [✓] **CR-03 Full-file reads.** `_terminal_launcher.py` (641 lines) read
  end-to-end; test file read end-to-end; both docs read in full. Unread files:
  none.
- [✓] **CR-04 Evidence discipline.** Findings: none. Hardening-preservation
  verified by targeted diff grep (only the suppression `_failed` removed).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical/high/medium/low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks
  listed. Security: nothing surfaced + primitives/scanners listed. Quality:
  all seven outputs produced (items 2/6/7 explicitly N/A or empty).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (241
  lines / 4 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra).
  PH-04 Completeness: none (test-first behaviour change). No auto-downgrade.

#### Run details

- **Diff source:** git diff change/feat-spawn-opens-cockpit-terminal...HEAD
- **Neighbour expansion:** git grep for `launch_change_terminal` consumers +
  the removed suppression message.
- **Neighbour cap:** not reached (1 neighbour considered).
- **Scanners run:** ruff (lint), grep-based secret + CR-10 pattern scan.
- **Scanners unavailable:** gitleaks/semgrep/trivy not installed; mitigated by
  grep-based secret scan + the fact that no dependency or config files changed.
- **Lenses dispatched in parallel:** no (single-reader pass per CR-02 carve-out).
