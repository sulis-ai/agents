# Code Review: WP-001 — Daemon writes and removes an identity pidfile

> **Timestamp:** 2026-06-12T185945Z (ISO 8601 UTC)
> **Author:** autonomous executor (Sulis)
> **Branch:** feat/wp-001-daemon-writes-identity-pidfile → change/harden-daemon-wedge-self-heal
> **Files changed:** 4 (2 modified, 2 new test files)
>
> **Outcome:** Ready to merge

---

## At a glance

This change is well-scoped and clean. It teaches the shared session daemon to write a small file recording its own identity (which process it is, plus a fingerprint that a recycled process ID can't fake) when it starts, and to delete that file when it shuts down cleanly. The build passes, the change is stdlib-only as required, and every new behaviour is covered by a test against the real daemon.

The review surfaced three minor points. Two were worth tidying up and have already been applied in this branch: the identity file is now created with the same tight permissions as the lock file beside it, and a docstring was corrected. The third is a pre-existing style choice (plain error text instead of structured logging) that is better left for a separate, module-wide cleanup rather than expanded here.

## What to fix

No issues that need attention before merge. The two worth-tidying items below were already applied in this branch:

### Applied — `session_manager_daemon.py` (identity file permissions)

**What was happening:** The identity file was created with the system default permissions (often readable by anyone on the machine), while the lock file sitting right next to it is locked down to owner-only.

**Why it matters:** This file is the input to a later decision about whether to forcibly stop a process. A file that feeds a "should I kill this?" decision should be at least as protected as the lock beside it — and it should refuse to be redirected through a pre-planted shortcut (symlink).

**What was done:** The file is now created owner-only (matching the lock) and refuses to follow a symlink, mirroring the pattern already used for the lock file in the same module.

### Applied — `session_manager_daemon.py` (docstring accuracy)

**What was happening:** A docstring described catching two kinds of error when the code catches one (the other is a sub-type of it).

**What was done:** Reworded so the description matches the code exactly.

## How this pull request is shaped

Clean across the board. It is a single, focused concern (one feature: the identity file), it is small (about 150 added lines across four files), it touches no database migrations, schemas, or infrastructure, and it ships its own tests — four of them, against the real daemon over a real socket. Nothing here needs splitting.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs, WPB-NN) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high/medium in the changes; Build Verification empty; all four changed files read end-to-end; all three lenses produced output. No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). ruff clean, ruff-format clean, mypy adds 0 new errors (2 pre-existing baseline on unchanged lines: `session_child_adapters` test-seam import-not-found + engine `SocketServer`/`BindingManager` arg-type), full daemon suite 36 passed.
- **PR Hygiene:** 0 high/medium findings (CR-09 / PH-01..04). Single-concern `feat`, ~150 lines / 4 files, no migrations/schemas/secrets/infra, tests included.
- **In the changes:** 3 findings (0 critical, 0 high, 0 medium, 3 low) — 2 addressed inline, 1 deferred-by-convention.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the two actionable LOW findings were fixed inline rather than queued).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 low | 0 | best-effort failure on raw stderr (pre-existing convention, WPB-10) |
| Security | 1 low | 0 | pidfile tmp perms/symlink (addressed inline) |
| Quality | 1 low | 0 | docstring over-specifies caught type (addressed inline) |

### Build Verification (CR-01)

No PR-introduced errors. ruff `All checks passed!`; `ruff format --check` clean on all 3 changed code files; mypy on `session_manager_daemon.py` shows only the 2 pre-existing errors (lines unrelated to this diff — a test-seam lazy import and an engine type quirk under ADR-001's frozen-engine constraint). Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 dir          -> severity none
Size (PH-02):         lines_added ~152; files_changed 4                         -> severity low
Safety (PH-03):       migrations 0; schemas 0; secrets 0; infra 0              -> severity none
Completeness (PH-04): new_source_without_test 0 (4 new test fns); api/schema ok -> severity none
```

### Findings in the Changes

#### F-01 — LOW (security + architecture) — `session_manager_daemon.py` `_write_pidfile`

**Evidence (pre-fix):** `with open(tmp_path, "w", encoding="utf-8") as fh:` created the tmp pidfile under the process umask (commonly 0o644, world-readable) with a predictable name (`<pidfile>.<pid>.tmp`) and symlink-following `open("w")`, whereas the sibling singleton lock is `os.open(lock_path, ..., 0o600)`.

**Why it matters:** The pidfile is the input to a later PID-reuse-safe SIGKILL decision (WP-002). It should be no more permissively scoped than the lock beside it, and the predictable tmp + symlink-follow is a (parent-dir-0o700-contained) defense-in-depth gap that goes live if `--pidfile` is ever pointed at a shared-writable dir.

**Resolution (addressed inline):** tmp now opened via `os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)` + `os.fdopen`, matching `_acquire_singleton_lock`'s 0o600 and refusing to follow/clobber a pre-existing symlink. Suite re-run green.

#### F-02 — LOW (quality) — `session_manager_daemon.py` `_remove_pidfile`

**Evidence (pre-fix):** docstring said *"Catches `FileNotFoundError` / `OSError`"* but the code catches only `except OSError:` (FileNotFoundError ⊂ OSError).

**Resolution (addressed inline):** reworded to *"Catches `OSError` (which covers the already-gone `FileNotFoundError` case)"*.

#### F-03 — LOW (architecture / observability, WPB-10) — `session_manager_daemon.py` `_write_pidfile`

**Evidence:** `sys.stderr.write(f"could not write identity pidfile at {pidfile_path}: {exc} — ...")` is string-interpolated, not structured key-value.

**Disposition: deferred-by-convention.** This matches the module's existing `stderr.write` style for the lock helpers — it is a pre-existing convention, not a regression introduced by this WP. Per WPB-12's bounded boy-scout rule, adopting a structured logger here would unbox a module-wide logging refactor outside this WP's scope. Recommend routing this + the lock-helper diagnostics through a structured logger when one is introduced (stable key e.g. `event=pidfile_write_failed`). No delta queued.

### Findings in the Neighbours

None. The change is additive within the daemon-presence seam; callers/callees (the engine over the socket, `daemon_client`) are untouched.

### Watch List (cross-WP, out of scope here — for WP-002's reviewer)

- WP-002's kill decision MUST treat a null/empty/malformed `start_token` as fail-closed (no token → no PID-reuse anchor).
- WP-002 MUST use exact-equality (not substring) for both `start_token` and `cmdline_marker` matching. The test harness uses `in` for the marker assertion, which is fine for a test but must not become the kill predicate.

### Cross-Reference

- No prior `.security/{project}/` viability report for this change.
- No existing hardening-deltas covering this surface.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff + ruff-format + mypy + pytest on HEAD; mypy baseline confirmed via line-identity of the 2 pre-existing errors. 0 PR-introduced errors.
- [✓] **CR-02 Parallel dispatch used.** Diff ~382 lines incl. new tests (>200) → three lenses dispatched concurrently as sub-agents.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end by each relevant lens (each <200 lines). No sampling.
- [✓] **CR-04 Evidence discipline.** All findings cite file + quoted text. No theoretical deltas queued (the two actionable findings were fixed inline; CR-04's failing-test requirement is moot for inline fixes validated by the existing green suite).
- [✓] **CR-05 Severity rubric.** Applied objectively: 0 critical, 0 high, 0 medium, 3 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 1 low + checks-run table. Security: 1 low + primitives-checked list. Quality: all 7 outputs (build follow-up, dead-surface clean, contract-drift clean, test-coverage complete, style 1 low nit, CR-10 clean).
- [✓] **CR-09 PR Hygiene applied.** PH-01 none, PH-02 low, PH-03 none, PH-04 none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/harden-daemon-wedge-self-heal` + 2 untracked new test files.
- **Neighbour expansion:** git grep on the touched symbols; the seam is leaf (engine reached only over the socket wire). 0 neighbour findings.
- **Neighbour cap:** not hit.
- **Scanners run:** ruff, ruff-format, mypy, pytest (project-configured toolchain). No JS/secret scanners applicable (Python stdlib-only diff, no secrets surface).
- **Lenses dispatched in parallel:** yes (3 concurrent sub-agents).
- **Post-review:** F-01 + F-02 addressed inline; suite re-run green (36 passed); ruff/format/mypy re-confirmed clean.
