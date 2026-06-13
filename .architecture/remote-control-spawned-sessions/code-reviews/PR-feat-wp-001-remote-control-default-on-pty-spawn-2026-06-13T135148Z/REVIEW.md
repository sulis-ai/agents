# Code Review: WP-001 — Remote Control on by default in the interactive PTY spawn argv

> **Timestamp:** 2026-06-13T135148Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/feat-remote-control-spawned-sessions/wp-001-remote-control-default-on-pty-spawn → change/feat-remote-control-spawned-sessions
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change does exactly one thing: a spawned interactive session now comes up with
Remote Control already switched on, named after the change so you can spot it in your
Remote Control list, with a simple environment-variable off-switch. The code is small,
well-scoped, and fully tested — every branch (on by default, named after the change,
off-switch, and the rule that the background/headless path must never get the flag) has
a test pinning it. No build errors, no security concerns, nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

Clean and well-shaped. Two files (the one source file the change targets plus its new
test file), a single concern (turn Remote Control on by default), one logical commit's
worth of work. New behaviour ships with tests. Nothing about the size, scope, safety, or
completeness raised a flag.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the changes; Build Verification empty; the one
changed file >50 lines (`claude_pty.py`) read end-to-end; all three lenses produced
output. No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — reuses established seam, pure argv builder |
| Security | 0 | 0 | none — name token is validated + non-shell-parsed |
| Quality | 0 | 0 | none — full branch coverage on new code |

### Build Verification (CR-01)

Mechanical baseline: `ruff check` + `ruff format --check` on both changed files — both
exit 0 (`tool-outputs/ruff-check.log`, `tool-outputs/ruff-format.log`). No mypy/pyright
is configured in `plugins/sulis/scripts/pyproject.toml` (coverage gap noted in
Methodology, not a skip). Build Verification section empty → no CR-06 block.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: none

Size (PH-02):
  lines_added: 273, lines_removed: 1, total: 274
  files_changed: 2  (1 source, 1 test)
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (well under the 200-line/5-file single-reader threshold for source;
            the line count is dominated by tests + docstrings)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0  (the source change ships with test_pty_remote_control.py)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: `_session_manager/adapters/claude.py` (sibling adapter — pinned
unchanged by the regression test, byte-for-byte identical), `_terminal_launcher.py`
(the `_os_window_enabled` knob this change mirrors — unchanged), `_wpxlib.ulid_handle` /
`validate_change_ulid` (reused, unchanged), `_session_manager/adapter.py` `SessionSpec`
(consumed, unchanged). No gap exposed.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`
  on both changed files. Both exit 0. Coverage gap: no mypy/pyright configured in
  pyproject — type-checking floor unavailable for this repo (recorded, not skipped).
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size: 2 files
  (≤5), source change 73 added lines (≤200). Within carve-out.
- [✓] **CR-03 Full-file reads.** The one changed file >50 lines
  (`claude_pty.py`) read end-to-end via the full staged diff; the test file read
  in full as authored. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; mechanical scans logged.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired
  (Build Verification empty; full-file read satisfied; all lenses produced output;
  PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: infra→domain
  import scan, singleton/getInstance scan, circular-import scan, purity of `spawn_argv`
  (no subprocess/env-write introduced), reuse-vs-duplication of ULID validation.
  Security: nothing surfaced — secret-pattern grep + detect-secrets scan (results: {}),
  injection surface (name token → Popen argv, no shell=True; validated via
  validate_change_ulid before use). Quality: Build Verification follow-up (empty);
  JSX scan N/A (Python); dead-surface (none — constant + helper both wired in);
  contract-drift (none — `spawn_argv(spec) -> list[str]` signature unchanged);
  test-coverage observation (17 tests, all branches incl. default-on, change-named,
  bare-when-no-ref, malformed-id degrade, falsey opt-out ×5, truthy/empty present ×5,
  headless regression guard ×3 — 100% on new lines); CR-10 perf (no anti-pattern
  matches — pure argv builder, no loops/DB/RPC/FS).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat concern). PH-02 Size:
  none (2 files / 274 lines, test+docstring dominated). PH-03 Safety: none (0 migrations,
  0 schema, 0 secrets, 0 infra). PH-04 Completeness: none (source ships with tests).
  PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff --cached change/feat-remote-control-spawned-sessions`
- **Neighbour expansion:** git grep / direct caller-callee inspection (sibling adapter,
  launcher knob, _wpxlib helpers, SessionSpec)
- **Neighbour cap:** 4 of 4 considered, 0 excluded
- **Scanners run:** ruff (check + format), detect-secrets, manual secret-pattern grep,
  CR-10 procedural greps
- **Scanners unavailable:** mypy/pyright (not configured); Gitleaks/Semgrep/Trivy
  (not in local env — detect-secrets + ruff + manual greps cover the diff's surface)
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02), 2-file diff
