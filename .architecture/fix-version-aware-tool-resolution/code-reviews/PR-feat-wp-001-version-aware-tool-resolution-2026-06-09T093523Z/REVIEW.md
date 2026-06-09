# Code Review: PR-feat-wp-001 — Version-aware tool resolution + cache pruning

> **Timestamp:** 2026-06-09T093523Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-version-aware-tool-resolution → change/fix-version-aware-tool-resolution
> **Files changed:** 24 (code) + 1 journal
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes a real, confirmed bug: every Sulis skill found its scripts by
listing the cached plugin versions and sorting them as text — which puts
"0.98.0" above "0.126.0" because the character "9" is greater than "1". Skills
were binding to a 28-versions-stale copy of their tools.

The fix is clean and well-scoped. Instead of just patching the sort, it removes
the whole class of bug: skills now read the version that's actually running
(its folder is on the system path), real scripts find their siblings relative to
themselves, and a small, fully-tested helper does numeric version comparison
where one is genuinely needed. There's also a new tidy-up tool that trims old
cached versions. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

One thing worth knowing (not a blocker): the new tidy-up command's
argument-handling has no direct automated test. Its actual logic — deciding
which versions to keep and deleting the rest — is fully tested against a fake
folder, and the command itself was run by hand this session (dry-run lists
correctly; the delete path keeps the newest 3 and removes the rest). The
untested part is just the thin layer that reads command-line flags and prints
output.

## How this pull request is shaped

**Size — worth knowing**

877 lines added across 24 files. That sounds large, but the bulk is the *same*
small edit repeated 18 times: each skill's tool-finding snippet gets the
identical replacement. The genuinely new logic is concentrated in four small
files (two helper modules, one command, one dispatcher script) plus their
tests. A reviewer reads the pattern once and confirms it's applied
consistently.

**Scope — clean**

Single concern: how tools are located. Nothing changes about what any skill
*does*.

**Safety — clean**

No database migrations, no schema changes, no infrastructure files, no secrets.
The one new destructive operation (deleting old cached versions) is dry-run by
default and can only ever target version-named folders inside the plugin cache.

**Completeness — clean**

Three new test files accompany the new logic, including the exact regression
case that proves the original bug is fixed.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high/medium in the changes. Build Verification
empty. All changed files read end-to-end. All three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — ruff clean on all changed Python; `bash -n` clean on `wpx`)
- **PR Hygiene:** 1 note (PH-02 size, mitigated by repetition); Scope/Safety/Completeness clean
- **In the changes:** 1 finding (1 low — CLI arg-handling untested)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single low finding has no failing characterisation test → Watch List, not a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Leaf modules, acyclic imports, no inversion — nothing surfaced |
| Security | 0 | 0 | `rmtree` is path-traversal-proof (only parsed semver names reach it) — nothing surfaced |
| Quality | 1 | 0 | `sulis-prune-cache` CLI layer has no direct test (low) |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD: `ruff check` on all 6 changed Python/script
files → **All checks passed**. `bash -n plugins/sulis/scripts/wpx` → syntax OK.
No frontend files in the diff (JSX identifier scan N/A). Output:
`tool-outputs/ruff-head.log`. Base run not separately captured — these are new
files (no BASE counterpart), so every HEAD result is PR-introduced and is clean.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {fix}                    → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/sulis) → clean
  severity: low

Size (PH-02):
  lines_added: 877, lines_removed: 166, total: 1043
  files_changed: 24 (code) + 1 journal
  repetition: 18 of 24 files are the identical resolution-block transform
  severity: note (raw band is medium, but the repeated-pattern nature makes
            it far easier to review than the line count implies)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  destructive_ops: 1 (shutil.rmtree in _prune_cache, dry-run by default,
                      scoped to <cache>/sulis-ai-agents/sulis/<parsed-semver>)
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (every new module has a test file)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

#### `plugins/sulis/scripts/sulis-prune-cache` — low (quality)

**What:** The CLI entrypoint (`build_parser` / `main`) has no direct unit test.
**Evidence:** `tests/unit/test_prune_cache.py` tests `_prune_cache.plan_prune`
and `apply_prune` thoroughly (keep-N, dry-run, force, missing-cache,
non-version-dir tolerance) but does not invoke the `sulis-prune-cache` argv
surface. **Why it's low:** the CLI is a thin wrapper (argparse → `plan_prune`
→ `apply_prune` → print); all branching logic lives in the tested core. The
`--keep < 1` guard and dry-run/force toggle were verified manually this session
against a fake cache. **CR-04:** no failing characterisation test constructed →
Watch List, no hardening delta.

### Findings in the Neighbours

None. The neighbour ring (callers of the resolution preambles) is the agent
runtime, not repo code; the changed `.py`/`wpx` files are leaf utilities with
no in-repo callers beyond their own tests.

### Watch List

- `sulis-prune-cache` CLI argv-level test (the low finding above). If the CLI
  grows flags or output contracts, add a subprocess-level test then.

### Lens detail

- **Architecture:** `_version_pick.py` is a pure stdlib leaf (imports only
  `collections.abc.Iterable`). `_prune_cache.py` imports only `_version_pick`
  (single source of truth for version comparison) + stdlib — acyclic, correct
  dependency direction, no singletons, no domain↔infra inversion. `wpx` now
  self-locates via `realpath($0)`, removing its dependence on the cache layout
  entirely. Nothing surfaced.
- **Security:** Checked the one destructive op. `apply_prune` calls
  `shutil.rmtree(plan.sulis_dir / version)` where `version` is sourced from
  `sorted_versions_desc(iterdir-names)`, which drops every name that is not a
  strict `int.int.int` triple. A `..`, absolute path, or arbitrary string can
  never reach `rmtree`; the targets are always direct children of the cache's
  sulis dir. Dry-run is the default. No secrets, no `eval`, no network calls
  (the only `http` token is a documentation URL in `wpx` help text). Nothing
  surfaced.
- **Quality:** Build Verification clean. No JSX (N/A). No dead surface. No
  contract drift. Test coverage: every new logic module has a test, including
  the keystone regression (`["0.98.0","0.122.2","0.126.0","0.45.0"]` →
  `0.126.0`) and the 0.9→0.10 / 0.99→0.100 rollover boundaries. One low
  test-gap finding (CLI argv layer). CR-10 performance: no anti-pattern matches
  (the sort is over a handful of cache dirs; no loops with I/O, no N+1).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` on all 6 changed Python/script files → 0 errors. `bash -n` on `wpx` → OK. No typecheck config for these stdlib scripts beyond ruff. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff is 877 lines / 24 files (above carve-out), but substantively 4 new code files + 18 identical mechanical preamble transforms. Lenses applied by single reviewer with full-file reads of the 4 load-bearing files; the 18 repeated edits verified by pattern-consistency grep. Recorded as a justified deviation: the >5-file count is inflated by mechanical repetition, not independent logic.
- [✓] **CR-03 Full-file reads.** `_version_pick.py` (77 lines), `_prune_cache.py` (79), `sulis-prune-cache` (87), `wpx` (changed region) all read end-to-end. The 18 preamble edits are <50-line block replacements each.
- [✓] **CR-04 Evidence discipline.** The one finding cites file + the absent test surface; no delta drafted (no failing characterisation test).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: import direction, cycles, singletons, inversion). Security: nothing surfaced (checks: rmtree traversal, secrets, eval, network). Quality: 1 finding + build-verification + dead-surface + contract-drift + test-coverage + CR-10 performance all run.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `fix:` concern). PH-02 Size: note (877 lines, but 18/24 files identical transform). PH-03 Safety: low (1 dry-run-default destructive op, traversal-proof). PH-04 Completeness: clean (every new module tested). PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/fix-version-aware-tool-resolution`
- **Neighbour expansion:** N/A — changed files are leaf utilities with no in-repo callers beyond tests.
- **Scanners run:** ruff (lint), bash -n (shell syntax). Gitleaks/Semgrep/Trivy not run — no signals (no secrets pattern, no deps change, no Dockerfile); manual secret/eval/network grep performed instead.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed in this environment; coverage gap noted, mitigated by manual grep given the trivial attack surface (stdlib path ops + version-string parsing).
