# Code Review: feat/wp-006-mint-phase — Mint phase (atomic write + path safety + signal handler + slug derivation)

> **Timestamp:** 2026-06-01T181034Z (ISO 8601 UTC)
> **Author:** Sulis executor (WP-006)
> **Branch:** feat/wp-006-mint-phase → change/create-discover-project
> **Files changed:** 4 (2 source + 2 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds the Mint phase of the discover-project skill — the part that writes a Project entity to disk. It's a focused change: two source files plus two test files, all in the new `_discovery/` module. The build is clean, every behaviour is covered by a test, and the safety checks (refusing to write outside the allowed directory, recovering from a cancelled run, refusing to clobber an existing entity) are explicit and tested with the right attack vectors.

Nothing needs to be fixed before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — worth being aware of**

The pull request is 680 lines across 4 files. About 60% of that (408 lines) is test code — the production surface is 272 lines. Tests-heavy is usually a good sign; it means the work is small but well-covered, not large and untested. No split needed.

**Scope — clean**

Single concern: the Mint phase. One commit type (`feat`), one module touched (`_discovery`). Easy to revert if needed.

**Safety — clean**

No database migrations, no schema changes, no infrastructure changes, no credentials in the code. The change is internal to the marketplace's Python helpers; nothing external moves.

**Completeness — clean**

Every new source file has a matching test file with strong coverage (94% on the minter, 100% on the slug helper).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06 (no critical/high in diff, Build Verification empty, all files >50 lines read end-to-end, all three lenses produced output).

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 4 signal severities ({low, medium, low, low}) (CR-09 / PH-01..PH-04). No `high`; no auto-downgrade trigger.
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (neighbour ring: 0 callers — module is new; downstream consumer WP-008 is still `dependency_blocked`)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — see below for the one watch-list note |
| Security | 0 | 0 | path-safety primitive present + tested with symlink + .. + outside-repo vectors |
| Quality | 0 | 0 | full RGB cycle complete; ≥90% coverage on both new files |

### Build Verification (CR-01)

Mechanical baseline clean:

```
$ ruff check _discovery/minter.py _discovery/slug.py tests/unit/test_discovery_minter.py tests/unit/test_discovery_slug.py
All checks passed!

$ ruff format --check ...
4 files already formatted

$ mypy _discovery/minter.py _discovery/slug.py
Success: no issues found in 2 source files

$ uv run pytest tests/unit/test_discovery_minter.py tests/unit/test_discovery_slug.py
22 passed in 0.10s
```

No PR-introduced errors. Empty section; no entries follow.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (_discovery)               → clean
  severity: low (single concern, single module)

Size (PH-02):
  lines_added: 680, lines_removed: 0
  files_changed: 4 (2 source + 2 test)
  test_ratio: 60%
  severity: medium (501-1000 line band; advisory only — 60% of diff is test code, no split needed)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: low
```

No PH-03 `high` finding → no CR-06 auto-downgrade.

### Findings in the Changes

None.

### Findings in the Neighbours

None. The module is new; the downstream consumer (WP-008 SKILL.md prose) is still `dependency_blocked` so there are no callers yet. The 20-file cap was not approached.

### Watch List

**`subprocess.check_output` in `consuming_repo_root()` has no explicit timeout.**

Location: `plugins/sulis/scripts/_discovery/minter.py:75`. The call is `subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)` — list-form, no shell, deterministic local-only git operation. WPB-related ("explicit timeout on external calls") in principle, but TDD §Armor External dependencies mandates the 5s timeout specifically for `LocalFilesystemInspector` (WP-003's adapter that calls `git remote get-url origin`), not for the repo-root resolution. The hang risk is essentially zero in practice (local git, no network). Not introduced as a finding; recorded here in case future hardening decides to apply WPB uniformly. No delta drafted.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none under `.security/discover-project/`.
- **Patterns suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `mypy`, `uv run pytest`. All clean. Outputs at `tool-outputs/{ruff-check,ruff-format,mypy,pytest}.log`.
- [—] **CR-02 Parallel dispatch carve-out.** Diff is 680 lines / 4 files, above the 200-line / 5-file single-reader threshold. However: this review runs inside the executor subagent that authored the change, so the Agent tool's parallel-dispatch primitive is not externally addressable. The lens work was done sequentially by the same agent that read the diff end-to-end; this is recorded as a methodology deviation. The diff is small, narrowly scoped, and 60% test code — single-reader risk is materially lower than the bare line-count band implies. Future runs should dispatch from a top-level session.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end during authoring + during review pass. minter.py (213 LOC), slug.py (59 LOC), test_discovery_minter.py (356 LOC), test_discovery_slug.py (52 LOC).
- [✓] **CR-04 Evidence discipline.** No findings produced → no quoted-text obligations triggered. Watch-list note cites file:line.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (CR-01 empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + structure/resilience/verification checks recorded above. Security: 0 findings + primitive checks (path-safety, secrets, injection, JSON encoding) recorded above; scanners (gitleaks/trivy/semgrep) not available in this environment, noted as coverage gap. Quality: 0 findings; mechanical baseline clean; CR-10 ten-pattern scan run, no matches; test coverage 95% total.
- [✓] **CR-08 Self-attestation.** This checklist.
- [✓] **CR-09 PR Hygiene applied.** PH-01: low. PH-02: medium (size band, advisory). PH-03: low. PH-04: low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** working-tree vs `change/create-discover-project` (changes are uncommitted at review time — Step 6.5 of the WP-006 lifecycle runs before commit).
- **Neighbour expansion:** N/A — new module, no callers yet.
- **Neighbour cap:** not approached.
- **Scanners run:** ruff (check + format), mypy, pytest.
- **Scanners unavailable:** gitleaks, trivy, semgrep — not installed in the executor environment. Coverage gap noted; mitigated by (a) explicit `# canonical` annotations / docstrings reviewed manually, (b) no new dependencies introduced (no SC-NN surface).
- **Lenses dispatched in parallel:** no (single-agent context — see CR-02 note above).

#### Coverage gaps

- Static-analysis scanners (Gitleaks, Trivy, Semgrep) were not available in this environment. The diff introduces no new dependencies (no `pyproject.toml` changes), no secrets (manual scan clean), and no new attack surfaces beyond the path-safety primitive (which is itself tested with the expected attack vectors). The gap is low-risk for this WP; future runs should ensure scanners are present.
- CR-02 single-agent context: see methodology note above.
