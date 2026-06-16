# Code Review: WP-001 — Resolve the installed-plugin scripts dir for the spawned viewer exec line + origin hook

> **Timestamp:** 2026-06-13T164758Z (ISO 8601 UTC)
> **Author:** autonomous executor (Sulis)
> **Branch:** feat/wp-001-resolve-installed-scripts-dir-for-spawn → change/fix-spawn-machinery-from-installed-plugin
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change is clean and well-scoped. It adds one small helper that decides
which copy of the project's scripts a freshly-opened change window should run —
preferring the properly-installed copy over the in-progress working copy — and
points the two places that needed it at that helper. No build errors, the
change is tightly focused on a single fix, and it comes with seven new tests
that cover every branch plus the security and no-regression cases. Nothing
needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small, single-purpose, and fully tested. One source file plus its two test
files; 266 lines added (most of it tests). One kind of change (a fix), no
database migrations, no infrastructure or configuration files, no secrets. New
behaviour ships with new tests. Nothing about the shape of this change raises a
flag.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (clean leaf-helper composition, guaranteed-non-raising) |
| Security | 0 | 0 | — (resolved path flows through existing shlex.quote sites unchanged) |
| Quality | 0 | 0 | — (8 tests, all ACs mapped, characterisation test pins no-regression) |

### Build Verification (CR-01)

Mechanical baseline (Python; no mypy/pyright config — the project's configured
floor is `compileall` + `ruff check`, plus the unit suite):

- `ruff check` on the 3 modified files: **All checks passed!** (exit 0)
- `python3 -m compileall` on the 3 modified files: clean (exit 0)
- `pytest` launcher unit suite: **108 passed** (100 prior + 8 new)

No PR-introduced errors. Build Verification section empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type {feat}; module_fan_out 1 dir      → severity none
Size (PH-02):         +266 / -4; 3 files (mostly test code)         → severity none
Safety (PH-03):       migrations 0; schemas 0; secrets 0; infra 0   → severity none
Completeness (PH-04): new_source_without_test 0; api_change 0       → severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring inspected: `_prune_cache.py`, `_version_pick.py` (the two
leaf helpers the resolver composes), `session_viewer.py` /
`session_manager_daemon.py` (the spawned chain the resolved path feeds — out of
scope per DD-3, internal self-location deliberately untouched). No gaps the
diff exposes.

### Watch List

None.

### Cross-Reference

- No prior security report in `.security/fix-spawn-machinery-from-installed-plugin/`.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `compileall` + `pytest` on HEAD; all clean. No mypy/pyright configured for this stdlib-only tooling (per plugin contract) — recorded, not skipped silently. Coverage gap: no static type checker (project has none).
- [✓] **CR-02 Single-reader pass justified.** Diff: 266 lines / 3 files; production surface is 72 lines (one ~50-line resolver + two 1-line call-site swaps), the remainder hermetic unit tests. Single-purpose fix; single-reader full-read pass used. (Marginally above the 200-line line-count but only 3 files and a single logical change; recorded.)
- [✓] **CR-03 Full-file reads.** Both >50-line changed files (`_terminal_launcher.py`, both test files) read end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** No findings; nothing to evidence. Scan logs in `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every tier.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checked dependency-direction (leaf-helper composition, no infra reach), resilience (guaranteed-non-raising, `.is_dir()` guards + final fallback, no network/timeout surface), verification (8 tests incl. characterisation). Security: nothing surfaced — primitives checked SEC-04 (injection: resolved path through existing shlex.quote, AC-6 bash -n parse test), path-handling (`.resolve()`, existing-dir validation of override), no secrets/auth surface. Quality: nothing surfaced — build verification clean; JSX scan N/A (no JSX); dead-surface none (resolver + both imports referenced); contract-drift none (builder signatures unchanged); test-coverage strong (8 tests, all ACs); style clean; CR-10 performance — only loop is a bounded `iterdir()` comprehension mirroring `_prune_cache.plan_prune`'s own pattern, no N+1/hot-path concern.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, 1 dir). PH-02 Size: none (266/3, mostly tests). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (new behaviour fully tested). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/fix-spawn-machinery-from-installed-plugin` (local worktree, pre-commit)
- **Neighbour expansion:** git grep + direct read of the composed leaf helpers
- **Neighbour cap:** 4 of 4 considered, 0 excluded
- **Scanners run:** ruff, compileall, pytest
- **Scanners unavailable:** mypy/pyright (none configured); gitleaks/semgrep/trivy (no new dependency / secret / infra surface to warrant)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (small, single-purpose diff)
