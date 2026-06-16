# Code Review: WP-001 — Stamp SULIS_CHANGE_ID per spawn; harden daemon startup

> **Timestamp:** 2026-06-16T140051Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/fix-daemon-spawn-change-binding-leak/wp-001-stamp-change-id-per-spawn → change/fix-daemon-spawn-change-binding-leak
> **Files changed:** 4 (155 insertions, 6 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes a bug where every session the daemon started inherited the
daemon's own change id, so a session opened for change X could report change Y.
The fix stamps each session with its own target change at the point it is
launched, and removes the value entirely when a session has no target — so a
session can never silently pick up a stale one. It also clears the daemon's own
copy at startup as a second line of defence. The work is well-scoped, every new
behaviour is covered by a test, and nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: four files, 155 lines added, one logical change
threaded through its two existing callers plus a startup guard. No database
migrations, no schema or infrastructure changes, no secrets. Six new tests were
added alongside the three source changes, so new behaviour is protected.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (pure-policy single-source-of-truth preserved) |
| Security | 0 | 0 | — (brief_change_id already shape-validated in SessionSpec.__post_init__) |
| Quality | 0 | 0 | — (both branches + seam + Armor path tested) |

### Build Verification (CR-01)

Mechanical baseline: `python3 -m compileall` on the three changed source files
(exit 0); `ruff check` on all four files (All checks passed). The repo
configures no type-checker (`branch-ci.yml`: "no type-checker configured for
this repo"); the CI floor is manifest-validity + compileall + routing-coverage,
all green. No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        single logical change (fix); 1 top-level dir → clean
Size (PH-02):         155 insertions / 6 deletions, 4 files → clean (<200 lines, <5 files)
Safety (PH-03):       migrations 0, schema/IDL 0, infra 0, secret hits 0 → clean
Completeness (PH-04): new source 0 (all modified); 6 new tests for new behaviour → clean
```

### Findings in the Changes

None.

#### Architecture lens

Nothing surfaced. Checks run: domain→infrastructure import scan (none — change
is inside the existing `_session_manager` package and `session_manager_daemon`);
new module-level singleton / getInstance scan (none); circular import scan
(none — additive kwarg + existing `SessionSpec` import already present in
`manager.py`); resilience primitives (the change adds no external call/retry/
timeout — it sets/removes an env var in a pure dict). `child_spawn_env` remains
a pure policy (data-in/data-out, no I/O, no global state), preserving the
module's documented single-source-of-truth design.

#### Security lens

Nothing surfaced. Primitives checked: SEC-04 (injection/validation), DAT-03
(sensitive value in env/logs), SEC-06 (secrets exposure). `SULIS_CHANGE_ID`
flows downstream into a filesystem path (`~/.sulis/changes/{brief_change_id}/`);
`SessionSpec.__post_init__` already validates `brief_change_id` (rejects a
leading `-` and control characters), so stamping it into the child env adds no
new injection vector. The change is a net security improvement: it *removes* a
stale change binding rather than leaving one to leak (defence in depth at the
daemon-startup boundary, ADR-001). No credential-handling code touched; the
credential-exclusion dict-comp is unchanged. No secrets in the diff (Gitleaks-
style grep clean).

#### Quality lens (CR-07 — seven outputs)

1. **Build Verification follow-up:** none (CR-01 empty).
2. **JSX/template identifier scan:** N/A (no TSX/JSX/Vue/Svelte files).
3. **Dead-surface findings:** none. The new `change_id` kwarg is consumed by
   the sole production caller (`manager.py` `_child_env`); the new `spec`
   parameter is used in the body and passed by both `_spawn_process` branches.
4. **Contract-drift findings:** none. `child_spawn_env`'s documented behaviour
   gains point 4 (the stamp/remove) matching the implementation exactly.
5. **Test-coverage observation:** new behaviour fully covered — 3 pure-policy
   tests (override / remove / defaulted-None back-compat lock), 2 seam tests via
   the existing `_PopenSpy` (stamps target / removes when None), 1 daemon Armor
   test (startup clear). No mocking of the unit under test (WPB MEA-09 respected;
   real spy on the Popen seam, real daemon `main` with stubbed lock+boot).
6. **Style/readability:** clean; docstrings updated in step with behaviour;
   ruff clean.
7. **Performance (CR-10):** no anti-pattern matches. No loops added; no DB/RPC/
   filesystem calls introduced; the two grep hits for external-call keywords are
   a code comment and a test CLI-arg string, not call sites.

### Findings in the Neighbours

None. Neighbour ring: `_session_manager/adapter.py` (`SessionSpec.brief_change_id`
already exists and is validated — not modified), `_spawn_process` callers (both
updated within the diff). No pre-existing gap exposed.

### Watch List

Empty.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this change.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m compileall`
  (3 source files, exit 0); `ruff check` (4 files, All checks passed). No
  type-checker configured per repo contract (`branch-ci.yml`). Coverage gap:
  type-checking — repo configures none; recorded, not silent.
- [✓] **CR-02 Single-reader pass justified by diff size:** 155 insertions /
  4 files — within the ≤200-line, ≤5-file carve-out.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end (the
  three source files are ≤1000 lines in the touched regions; the test file
  diff read in full). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens checks
  cite the scanned constructs.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed.
  Security: 0 findings + primitives listed. Quality: 0 findings + all seven
  outputs produced (2,4,6 N/A or empty as permitted; 1,3,5,7 explicit).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: clean
  (155 lines / 4 files). PH-03 Safety: clean (0 migrations/schema/infra/
  secrets). PH-04 Completeness: clean (6 tests for new behaviour). PH-03
  high → CR-06 auto-downgrade: no.

#### Run details

- **Diff source:** git working-tree diff vs `change/fix-daemon-spawn-change-binding-leak`.
- **Neighbour expansion:** git grep (ast-grep not required at this size).
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** compileall, ruff; secret-pattern grep.
- **Scanners unavailable:** type-checker (none configured), Gitleaks/Trivy/
  Semgrep binaries (substituted with grep-based secret/dependency scan — no
  dependency changes in diff).
- **Lenses dispatched in parallel:** no (single-reader carve-out per CR-02).
