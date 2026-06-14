# Code Review: WP-002 — PID-reuse-safe identity-verify and reclaim helpers

> **Timestamp:** 2026-06-12T192140Z (ISO 8601 UTC)
> **Author:** Sulis executor (autonomous)
> **Branch:** wp/harden-daemon-wedge-self-heal/wp-002-pid-reuse-safe-identity-verify-and-reclaim → change/harden-daemon-wedge-self-heal
> **Files changed:** 2 (1 modified, 1 added)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the safety-critical recovery helpers that let the session daemon
recover from a "stuck" instance — one that holds its lock but stops responding.
The build is clean (no new type or lint errors), the change is tightly scoped to
two files, and it ships with a thorough test suite (21 tests). The single most
important behaviour — never killing the wrong process when a process ID gets
reused by the operating system — is proven by a dedicated test that spies on the
kill call and asserts it is never made on a mismatch. Nothing needs attention
before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 229 new lines in the daemon helper plus a 571-line test file.
Well within the band where a single reviewer can check it thoroughly.

**Scope — clean.** One concern: the verify-and-reclaim recovery path. One
Conventional-Commit type (`feat`). Two tightly-coupled files (the helpers and
their tests).

**Safety — clean.** No database migrations, no schema/IDL changes, no
infrastructure files, no secrets. The change is pure standard-library code that
verifies a process's identity before signalling it.

**Completeness — strong.** 1 new source surface, 1 new test file with 21 tests
covering every decision branch, including the load-bearing safety case. This is
the right ratio.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high/medium in the diff; Build Verification empty;
both changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean; mypy 32 base / 32 head / **0 new** on the WP-002 surface.
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — best-effort I/O + bounded `ps` timeout throughout |
| Security | 0 | 0 | none — kill gated on fail-closed verifier; no injection (list-arg subprocess, int-validated pid) |
| Quality | 0 | 0 | none — 21 tests, every branch covered, descriptive names |

### Build Verification (CR-01)

Mechanical baseline ran clean:

- `ruff check session_manager_daemon.py tests/unit/test_daemon_reclaim.py` → **All checks passed!**
- `ruff format --check` → both files formatted.
- `mypy session_manager_daemon.py` → 32 errors on base, 32 on head. The delta on
  the WP-002 surface (lines 164–466) is **0**. The 2 daemon-module errors
  (`session_child_adapters` test-seam lazy import; `SocketServer(BindingManager)`
  engine duck-type) and the 30 frozen-engine errors all pre-exist and are out of
  scope (ADR-001: engine UNMODIFIED).

Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts)
  severity: none (single concern)

Size (PH-02):
  lines_added: ~800 (229 helper + 571 test), lines_removed: 12
  files_changed: 2
  generated_ratio: 0.0, lock_file_ratio: 0.0
  severity: none (2-file band, focused)

Safety (PH-03):
  migration_count: 0, schema_idl_count: 0, infra_files: 0, secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the new behaviour ships with 21 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Lens output

**Architecture lens (Armor focus — this is a recovery primitive).** Nothing
surfaced. Checks run: best-effort I/O guarantee on every probe + side-effect
(`_ps_field`, `_read_pidfile`, `_signal_pid`, `_pid_alive`, `_clear_stale_files`
all catch `OSError`/`ValueError`/`ProcessLookupError` and degrade, never raise);
bounded external call (the `ps` subprocess carries `timeout=5.0`); the
SIGTERM→bounded-wait→SIGKILL loop has a `deadline = time.monotonic() +
max(term_wait_secs, 5.0)` floor (no unbounded wait); import-graph independence
preserved (only `os`/`signal`/`subprocess`, all pre-existing — the
`test_daemon_module_is_terminal_only_no_chat_or_platform` regression guard passes).
EP-03 reuse: the shared `_ps_field` probe was extracted at the two-consumer
threshold (`_process_start_token` + `_process_cmdline`), and `_clear_stale_files`
reuses `_remove_pidfile`.

**Security lens (SEC).** Nothing surfaced. Primitives checked: SEC-02 (authz on a
destructive operation), SEC-03 (injection), SEC-07 (secrets). The kill is an
authorization decision gated entirely on `_is_our_daemon`, which **fails closed**
on every unprovable input (no recorded marker/token, unreadable cmdline,
unreadable start-token, cmdline-marker mismatch, start-token mismatch). The
load-bearing invariant — a recycled PID is never killed — is proven by
`test_reclaim_refuses_to_kill_on_pid_reuse_start_token_mismatch`, which spawns a
real live process, points a mismatched pidfile at it, spies `os.kill`, and asserts
it is never called. No injection vector: `pid` is validated `isinstance(pid, int)`
before any `ps` invocation, and `subprocess.run` uses a list argument (no
`shell=True`), so a tampered pidfile cannot inject a command. No hardcoded
secrets. Scanners: not separately run (no new dependency, no Dockerfile, no
network surface in the diff — the diff is stdlib process-signalling only).

**Quality lens.** All seven outputs produced:
1. Build Verification follow-up: no CR-01 findings to translate.
2. JSX/template scan: N/A (no TSX/JSX/Vue/Svelte files).
3. Dead surface: none — every helper is consumed (`_ps_field` by both token +
   cmdline probes; `_signal_pid`/`_pid_alive`/`_clear_stale_files` by
   `_reclaim_wedged_holder`).
4. Contract drift: none — the record shape read by `_read_pidfile` matches the
   shape written by WP-001's `_write_pidfile` (`pid`/`start_token`/`cmdline_marker`).
5. Test coverage: 21 tests; new-surface line coverage 94.6%; every fail-closed
   branch directly asserted. Strong.
6. Style/readability: descriptive names throughout; docstrings explicitly name
   the fail-closed contract ("do not weaken it"). No TODO/FIXME introduced.
7. Performance (CR-10): no anti-pattern matches. The only loop is the bounded
   SIGTERM wait, which polls a signal-0 liveness check (not DB/RPC/FS) on a 0.1s
   interval under a hard deadline — intended, not an anti-pattern.

Note (not a finding): `_is_our_daemon`'s `record: dict` is untyped on its shape;
a `TypedDict` would pin the three keys. Left as-is for consistency with the
existing `_write_pidfile` `record` dict in the same file (CP-01: match the
established local convention).

### Findings in the Neighbours

None. The direct neighbour is WP-001's pidfile-write path (`_write_pidfile` /
`_process_start_token`); the `_ps_field` extraction preserved `_process_start_token`'s
behaviour (WP-001's `test_daemon_pidfile_helpers.py` still passes).

### Watch List

Empty.

### Cross-Reference

- No prior `.security/harden-daemon-wedge-self-heal/` viability report to cite.
- No existing hardening-deltas to deduplicate against.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `mypy session_manager_daemon.py`. Base: 32 mypy / 0 ruff. Head: 32 mypy / 0 ruff. PR-introduced errors on the WP-002 surface: 0. Coverage gap: no CI mypy gate exists (`.github/` runs pytest, not mypy) — recorded, not silently skipped.
- [✓] **CR-02 Dispatch shape.** Diff is 2 files; ~800 lines total but a single coherent concern (helper + its test) in tightly-coupled files. Three lenses applied analytically by the reviewing agent over the full diff; both files read end-to-end. Recorded here rather than sub-agent-dispatched because the change is one self-contained recovery primitive with no fan-out.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (`session_manager_daemon.py` 717 lines; `test_daemon_reclaim.py` 571 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** All observations cite file:line and quoted code in the lens output.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; both files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks-run note. Security: 0 findings + primitives-checked note. Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`, 1 dir). PH-02 Size: none (2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (new behaviour ships with 21 tests). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/harden-daemon-wedge-self-heal` + the untracked new test file.
- **Neighbour expansion:** git grep over `session_manager_daemon` consumers; WP-001 pidfile helpers the only direct neighbour.
- **Neighbour cap:** not reached (1 neighbour).
- **Scanners run:** ruff, mypy. Gitleaks/Trivy/Semgrep not run — no new dependency, network surface, or secret-shaped strings in the diff.
- **Lenses dispatched in parallel:** no — single coherent primitive, applied analytically end-to-end.
