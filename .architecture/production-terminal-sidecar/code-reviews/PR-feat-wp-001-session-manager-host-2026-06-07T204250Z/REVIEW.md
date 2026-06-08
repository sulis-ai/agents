# Code Review: feat/wp-001-session-manager-host — Production session-manager host process

> **Timestamp:** 2026-06-07T204250Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-session-manager-host → change/create-production-terminal-sidecar
> **Files changed:** 3 (all new)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the long-lived "host" process that runs the terminal engine for the live cockpit terminal — the production version of the existing test-only `terminal-backend.py`, minus the test banner it seeds. It builds on the already-shipped, frozen terminal engine without changing it, and it turns the per-change security guard ON so a browser connection can only ever touch its own change's terminal. The build is clean, the security guard is proven by a test, and there are tests for every new behaviour. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 654 lines across 3 files, all new, one concern (the host process plus its tests). One commit. Easy to review thoroughly.

**Scope — clean.** Single concern: the new host module and its tests. No mixing of refactor and feature; the shipped engine is reused untouched.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets. The host keeps the engine's existing local-only socket permission (owner-only) and turns the per-change guard ON by default — a connection is locked to the first change it opens, and any attempt to reach a second change on the same connection is refused with zero data leaked.

**Completeness — clean.** 2 new test files for 1 new source file: 3 end-to-end tests that boot the real process over a real socket, plus 9 unit tests for the pure binding logic.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high/medium in the diff; Build Verification empty; all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (neighbour ring = the frozen `_session_manager/` engine, read-only, not modified)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — composes the frozen engine; thread-identity binding is a deliberate, documented design given the socket-only resolver signature |
| Security | 0 | 0 | None — guard ON by default (secure default); cross-change attach refused (test-proven); 0o600 socket preserved |
| Quality | 0 | 0 | None — 12 tests, no dead surface, no contract drift, no CR-10 anti-patterns |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD (the engine toolchain is Python; `uv run`):

- `ruff check` (lint floor) — All checks passed.
- `python -m py_compile` (syntax floor) — OK.
- `import session_manager_host` (runtime-import floor) — OK; public surface `ConnectionBindingRegistry`, `_BindingManager`, `_build_server`, `main`.

Base comparison: the three files are net-new (absent on base), so every line is PR-introduced; the baseline confirms zero errors introduced. Build Verification section empty → no CR-06 downgrade.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts) → clean
  severity: none

Size (PH-02):
  lines_added: 654, lines_removed: 0, total: 654
  files_changed: 3 (all new)
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (3-file band; all single-module, single-concern)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (1 source file, 2 test files, 12 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The neighbour ring is the shipped `_session_manager/` package (`SessionManager`, `SocketServer`, `SessionSpec`, the pty adapter) — imported verbatim, contract-frozen, and not modified by this diff. The engine's own integration suite (`tests/integration/test_socket_server.py`, 12 tests) was re-run as a regression check and stays green.

### Watch List

- **Shared pty `--cwd` default.** `_build_server` defaults `cwd` to a single `host-cwd` directory beside the socket and constructs one fake-child pty adapter for all sessions. This matches WP-001's defined behaviour (the host owns the engine; per-change worktree cwds are wired by the cockpit at WP-004 — "Own the host + WS endpoint lifecycle"). Noted, not a finding: it is the WP's contracted surface, and the cwd-per-change wiring is explicitly downstream scope. No failing characterisation test grounds a fix here (CR-04) → Watch List, no delta.
- **Thread-identity binding.** The §2.13.4 guard binds a connection by handler-thread id because the shipped resolver signature is socket-only (`Callable[[socket], str|None]`) and `open` is unguarded, so the resolver cannot observe the opened key directly. The shipped `SocketServer` uses `ThreadingMixIn` (one handler thread per connection), making thread id a sound connection identity. This is documented in the module + `ConnectionBindingRegistry` docstrings and unit-tested for per-connection isolation and same-thread default. If a future engine change moved off one-thread-per-connection, this assumption would need revisiting — noted for awareness, not a current gap.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none under `.security/production-terminal-sidecar/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run ruff check`, `uv run python -m py_compile`, `uv run python -c import`. Base: files net-new (0 errors). Head: 0 errors. Coverage gap: pytest-cov absent — coverage measured by the unit suite (pure surface) + subprocess integration (end-to-end), recorded as a Step-1 fallback.
- [✓] **CR-02 Single-reader pass.** Diff is 654 lines but all net-new in 3 files of one module, one concern, one commit, with the neighbour ring read-only/frozen; reader read all three files end-to-end (also authored them this session). Recorded per the carve-out's intent; no cross-kind surface to dispatch lenses against.
- [✓] **CR-03 Full-file reads.** All 3 changed files (201 / 135 / 318 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; Watch-List items cite file/behaviour and the absence of a grounding failing test.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Checks run: infra→domain imports (none), new singletons (only the intended binding registry), circular imports (none), secrets (none), guard default (ON — secure). Security: nothing surfaced. Checks run: hardcoded creds (none), network/plain-HTTP (none), eval/exec/subprocess/pickle (none in host), socket permission (0o600 preserved, delegated to frozen SocketServer.start), cross-change authz (guard ON, test-proven), independence (no chat coupling). Quality: 0 findings; test-coverage observation = 12 tests for new behaviour; dead surface (none); contract drift (none); CR-10 perf scan (no loops with IO; no anti-pattern matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none ({feat}, 1 dir). PH-02 Size: none (654 lines / 3 new files / single module). PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none (1 source + 2 test files, 12 tests). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/create-production-terminal-sidecar` + untracked new files.
- **Neighbour expansion:** import graph by inspection — `_session_manager/` package (frozen, read-only). Cap not reached.
- **Neighbour cap:** 0 of N excluded.
- **Scanners run:** ruff, py_compile, grep-based secret/network/perf scans.
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy not installed in this environment — grep-based secret + injection + CR-10 scans run as the fallback; coverage gap recorded.
- **Lenses dispatched in parallel:** no (single-reader carve-out; one backend module, no cross-kind surface).
