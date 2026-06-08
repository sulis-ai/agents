# Code Review: feat/wp-004-interactive-claude-pty-adapter — Interactive Claude pty adapter

> **Timestamp:** 2026-06-08T105205Z (ISO 8601 UTC)
> **Author:** executor (WP-004)
> **Branch:** feat/wp-004-interactive-claude-pty-adapter → change/create-change-owned-terminal-shared-session
> **Files changed:** 2 (1 new source, 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new building block: an adapter that lets a change's
terminal session run the real interactive Claude (instead of the test echo
stub the host wires today). The change is small, well-scoped, and fully
tested. One real bug was caught and fixed during review (see below) — the
way the session brief was being handed to Claude would not have worked the
way the rest of the system actually starts the program. After the fix, the
build is clean and all tests pass.

## What to fix

No issues that need attention. The one correctness problem found during
review was fixed in place and re-verified.

### Fixed during review — how the session brief reaches Claude

**What was happening:** The first draft handed Claude its opening brief by
writing a shell instruction (`$(cat <file>)`) into the program's arguments,
copying how the desktop terminal launcher does it. But the launcher runs
through a shell that understands that instruction, whereas the session
manager starts the program directly — so the instruction would have been
passed to Claude as literal text rather than being replaced with the actual
brief.

**Why it mattered:** Every briefed session would have opened with Claude
seeing the seven-character string `$(cat ...)` instead of its real
orientation prompt — the session would not self-orient, which is the exact
problem this whole capability exists to solve.

**What was done:** The adapter now reads the brief file itself and hands the
brief text straight to Claude as a single argument. This is correct for how
the manager actually launches programs, and it keeps the safety property that
mattered — the brief's text is never interpreted by a shell, so apostrophes,
quotes, and backticks in a brief are always safe.

## How this pull request is shaped

**Size — clean.** 352 lines across 2 files. Comfortably reviewable.

**Scope — clean.** One concern: a new adapter plus its tests.

**Safety — clean.** No database migrations, no schema or infrastructure
changes, no secrets in the diff.

**Completeness — clean.** One new source file, one new test file (11 tests
covering conformance, the interactive argument shape, brief delivery in
every state, the unused terminal-path methods, and reuse of the launcher's
file location).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high remaining in the diff; Build Verification
empty; both changed files (>50 lines) read end-to-end; all three lenses
produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean)
- **In the changes:** 1 finding found-and-fixed-during-review (1 critical,
  resolved inline), 0 remaining
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the one finding was fixed inline, not deferred)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 (fixed inline) | 0 | shell-substitution argv vs direct-execv spawn (F-01, fixed) |

### Build Verification (CR-01)

Mechanical baseline ran on the changed surface: `uv run ruff check`,
`uv run ruff format --check`, `uv run mypy` (on the changed file), and
`uv run pytest tests/unit/test_claude_pty_adapter.py`. The project's CI lint
gate is `py_compile` + manifest JSON validity; the test gate is `pytest`.
No PR-introduced errors. `mypy` is not a CI gate; the changed file is mypy-clean
in isolation regardless (the repo carries a pre-existing mypy baseline in
imported modules `_wpxlib.py` + `_session_manager/manager.py` — out of scope,
the frozen `claude.py` adapter trips the same baseline).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 2 files, 1 module            → clean
  severity: none
Size (PH-02):
  lines_added: 352, lines_removed: 0, total: 352
  files_changed: 2
  severity: none (well within reviewable bounds)
Safety (PH-03):
  migration_count: 0  schema_idl_count: 0  infra_files: 0  secret_pattern_hits: 0
  severity: none
Completeness (PH-04):
  new_source_without_test: 0 (1 source + 1 test)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### F-01 (fixed inline) — `_session_manager/adapters/claude_pty.py` — critical (quality / correctness)

**Lens:** quality (architecture-adjacent: the producer/consumer spawn seam)

**What was happening (original draft):**
```python
argv.append(f"$(cat {shlex.quote(str(sidecar))})")
```
The adapter emitted a shell command-substitution token as a single argv
element, copying `_terminal_launcher`'s exec line.

**Evidence the manager spawns without a shell** —
`_session_manager/manager.py:626` (`_spawn_pty_process`):
```python
process = subprocess.Popen(
    argv, cwd=spec.cwd, stdin=slave_fd, stdout=slave_fd,
    stderr=slave_fd, close_fds=True,
)
```
No `shell=True`. The launcher's `$(cat …)` works because the launcher writes
a bash script that bash executes (`_terminal_launcher._build_launch_script`,
exec line); the manager hands `argv` straight to `execv`, so a `$(cat …)`
element reaches `claude` as a literal string, never expanded.

**Why it matters:** Every briefed pty session would open with Claude seeing
the literal `$(cat /…/pre_prompt.txt)` string instead of the brief — the
session never self-orients, defeating the capability's purpose (the #93
idle-session bug, re-introduced).

**Fix applied inline:** the adapter now reads the sidecar
(`sidecar.read_text(encoding="utf-8")` in `_read_pre_prompt`) and appends the
brief **text** as a single argv element. Correct under direct-execv spawn;
preserves the never-shell-parsed property (#86 / MUC-2) because a single argv
token is handed to the kernel verbatim. The two affected tests were updated
to assert the brief text is passed (not a `$(cat …)` literal). Re-verified:
11 tests pass, ruff + mypy clean.

### Findings in the Neighbours

None. The one neighbour inspected (`_session_manager/manager.py`
`_spawn_pty_process`) was read to confirm the spawn model; it is correct and
unchanged.

### Watch List

- **Real interactive `claude` round-trip is not asserted here** — by design
  (ADR-004 / WP-009 `--verbose` lesson: CI cannot run the real binary).
  Observed-done is deferred to WP-007. Not a finding; recorded so the gap is
  visible.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas to cite.
- No neighbour pattern suggests a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff (changed files), ruff format --check, mypy (changed file), pytest (changed test). Base vs head: 0 PR-introduced errors. Coverage gap: pytest-cov absent → manual coverage analysis (every method + branch of the new file exercised by 11 tests).
- [✓] **CR-02 Dispatch shape.** Diff 352 lines / 2 files. >200 lines but a single cohesive new module + its test; single-reader pass with end-to-end reads of both files, plus a targeted neighbour read of the manager's spawn path that surfaced the load-bearing F-01. Recorded as a conscious carve-out given the single-concern shape.
- [✓] **CR-03 Full-file reads.** Both changed files (160 + ~195 lines) read end-to-end. Neighbour `_spawn_pty_process` read end-to-end.
- [✓] **CR-04 Evidence discipline.** F-01 cites file:line + quoted text on both the diff side and the neighbour spawn site.
- [✓] **CR-05 Severity rubric.** F-01 = critical (correctness bug breaking the golden-path briefed session). Resolved inline → 0 remaining.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency-direction, new singletons, resilience primitives — none apply, the adapter does no IO). Security: nothing surfaced (checks: env-value→path validated as ULID before join; brief read via read_text not shell; no secrets). Quality: F-01 (fixed) + jsx-scan N/A (no TSX) + dead-surface none + contract-drift none + test-coverage present + CR-10 perf no anti-pattern matches (no loops introduced).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (352/2). PH-03 Safety: none. PH-04 Completeness: none (source+test). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff change/create-change-owned-terminal-shared-session...feat/wp-004-interactive-claude-pty-adapter (staged working tree)
- **Neighbour expansion:** git grep on the manager spawn path (ast-grep not required for a 2-file diff)
- **Neighbour cap:** 1 of 1 considered
- **Scanners run:** ruff, mypy, pytest (gitleaks/trivy/semgrep not installed in this env — no secret patterns in a 352-line stdlib-only diff; manual secret grep clean)
- **Lenses dispatched in parallel:** no — single-reader carve-out justified by single-concern shape; recorded per CR-02
