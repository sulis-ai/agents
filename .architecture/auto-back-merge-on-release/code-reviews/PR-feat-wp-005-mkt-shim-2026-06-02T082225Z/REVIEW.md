# Code Review: feat/wp-005-mkt-shim — Replace the marketplace's release workflow with a shim (n=1 dogfood)

> **Timestamp:** 2026-06-02T082225Z (ISO 8601 UTC)
> **Author:** WP-005 executor
> **Branch:** feat/wp-005-mkt-shim → change/extend-auto-back-merge-on-release
> **Files changed:** 4
>
> **Outcome:** Ready to merge

---

## At a glance

This change does exactly one thing and does it cleanly: it shrinks the marketplace's own release automation from a 280-line file into a short "shim" that hands the work off to the shared, reusable copy of that same automation. Think of it as the marketplace switching from carrying its own private copy of a recipe to pointing at the shared recipe everyone else uses — proving the shared recipe works by eating its own cooking.

There are no build errors, the change is tightly scoped to four related files, and the one genuinely dangerous part — the safeguard that stops the release robot from triggering itself in an endless loop — was checked end to end and is intact. Nothing needs attention before merge.

## What to fix

No issues that need attention.

The one thing worth being aware of: the test files repeat a single short path string (`./plugins/sulis/templates/workflows/release-on-merge.yml`) in two places rather than sharing it from one spot. This was a deliberate call — keeping each test file independent is the normal, expected style for this kind of test, and sharing one short string would add more indirection than it removes. No action needed.

## How this pull request is shaped

**Size — clean.** Four files. The line count looks large only because 280 lines of old automation were deleted wholesale (that logic now lives in the shared copy, so nothing is lost — the project's history keeps the old shape).

**Scope — clean.** A single, focused change: replace one file, update the three tests that described its old shape.

**Safety — clean.** One automation file changed, which is the heart of this work. The release-loop safeguard (the part that would be catastrophic if broken — it prevents the release robot from re-triggering itself forever) was verified to still fire correctly after the change. No database changes, no secrets, no other risky surfaces.

**Completeness — clean.** The change ships with eight new tests plus three updated ones, including a test that specifically locks in the release-loop safeguard so a future edit can't quietly remove it.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all four changed files read end-to-end; all three lenses produced output. No auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — `uv run ruff check` on the 3 changed `.py` files: All checks passed).
- **PR Hygiene:** 0 high, 0 medium findings (PH-01..04 all `low`; net-deletion size signal is an artifact of the wholesale 280-line Replace).
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single `low` is a conscious-skip, not a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Loop-guard survival through `workflow_call` indirection — verified intact |
| Security | 0 | 0 | `secrets: inherit` to same-repo local-path reusable workflow — safe |
| Quality | 1 (low) | 0 | `_LOCAL_USES` constant duplicated across 2 test modules (conscious skip) |

### Build Verification (CR-01)

No PR-introduced errors. `uv run ruff check tests/unit/test_marketplace_shim.py tests/unit/test_release_on_merge_yaml_annotations.py tests/unit/test_reusable_workflow_byte_parity.py` → "All checks passed!". Full unit suite: 1616 passed. The 3 touched test files + new file: 18 passed.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 2 (.github/workflows, plugins/sulis/scripts/tests)
  severity: low

Size (PH-02):
  lines_added: 400, lines_removed: 565, total churn: 965
  files_changed: 4
  severity: low
  note: net deletion of 165 lines; the 565 deletions are almost entirely
        the wholesale removal of the 280-line workflow body (SUBSTITUTE-
        Replace). Mechanically simple despite the churn count.

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 1 (.github/workflows/release-on-merge.yml)
  secret_pattern_hits: 0
  severity: low
  note: the infra file IS the load-bearing change; loop-guard survival
        verified (see Architecture lens).

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: low
  note: the change is itself test + infra; 8 new tests + 3 re-pointed.
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

#### `plugins/sulis/scripts/tests/unit/test_marketplace_shim.py` + `test_reusable_workflow_byte_parity.py` — low (quality)

**What:** The literal `"./plugins/sulis/templates/workflows/release-on-merge.yml"` is defined as `_LOCAL_USES` in both test modules.

**Evidence:**
- `test_marketplace_shim.py`: `_LOCAL_USES = "./plugins/sulis/templates/workflows/release-on-merge.yml"`
- `test_reusable_workflow_byte_parity.py`: `_LOCAL_USES = "./plugins/sulis/templates/workflows/release-on-merge.yml"`

**Why it matters:** Minimal. Two test modules independently assert the same path. If the path changed, both would need updating — but a path change to the reusable workflow is exactly the kind of break the tests exist to catch, so the duplication is self-correcting (both would fail loudly).

**Recommendation:** No change. Conscious skip recorded in the WP journal Blue step (item 9): hoisting one short literal to a shared `conftest` adds indirection and breaks pytest module independence (the established convention) for negligible DRY gain. Listed for awareness only; no Hardening Delta.

### Findings in the Neighbours

None. The neighbour ring (the reusable workflow `plugins/sulis/templates/workflows/release-on-merge.yml`, and `tests/unit/test_branch_ci_has_drift_check.py` / `test_github_workflows_parse.py` which reference the workflow path) was inspected. The reusable workflow is unchanged by this WP; the two referencing tests pass (they assert presence/path-argument, not the replaced body).

### Watch List

- **Pre-existing (out of WP-005 scope):** `tests/methodology/test_release_on_merge_yaml_unchanged_behaviour.sh` fails on the change-branch tip independently of this WP — it diffs the reusable workflow's steps against a WP-002-era snapshot that predates WP-003's back-merge steps. Confirmed pre-existing via a stash test. This is a WP-002/WP-003 characterisation-snapshot reconciliation (belongs to those WPs / WP-009's parity work), not WP-005. Surfaced for awareness; no action in this WP.

### Architecture lens (CR-07)

**Findings: 0.** Checks run:
- **Loop-guard survival (load-bearing).** The pre-shim workflow carried a job-level `if:` skipping the bot's own `release: sulis` commits (matched on `github.event.head_commit.author.username` + `github.actor` against `github-actions[bot]`). After the Replace, the guard lives in the reusable workflow's job-level `if:` (line 103 of `plugins/sulis/templates/workflows/release-on-merge.yml`). GitHub propagates the triggering `push` event's `github.event.*` and `github.actor` context into a `workflow_call`-invoked reusable workflow, so the guard still evaluates and fires through the indirection. `test_loop_guard_preserved` (new) + `test_loop_guard_uses_both_actor_checks` (re-pointed) pin this. No shim-level duplication needed or added.
- **Local-ref-vs-tag decision.** The owning repo uses `uses: ./plugins/...` (local path, tracks current commit). External consumers use the cross-repo `@sulis-vN.M.K` tag form (consumer template, unchanged). Correct per the WP contract — no version-pin lag for the repo that owns the workflow, no tag-must-pre-exist hazard.
- **Boundary / resilience / observability:** N/A — this is a CI workflow caller, not runtime service code. No new imports, no HTTP/DB calls, no timeouts/circuit-breakers in scope.

### Security lens (CR-07)

**Findings: 0.** Primitives checked: SEC (secrets exposure, injection), INF (workflow config), SC (supply chain). Scanners: manual diff secret-pattern scan (no scanner binaries available locally).
- **`secrets: inherit`** forwards `GITHUB_TOKEN` to the reusable workflow referenced by **local path** — same repo, same trust boundary. No cross-repo secret exposure.
- **No hardcoded credentials** in the diff (secret-pattern scan: only matches are the loop-guard comment, a test function name, and a docstring).
- **Supply chain:** the local-path `uses:` is implicitly pinned to the current commit (GitHub resolves local reusable-workflow references at the triggering commit). No third-party action pinning concern introduced by this WP.
- The reusable workflow's own injection defences (GitHub expressions crossing the shell boundary via `env:` ports) are unchanged.

### Quality lens (CR-07)

1. **Build Verification follow-up:** none (CR-01 clean).
2. **JSX/template scan:** N/A (no TSX/JSX/Vue/Svelte files).
3. **Dead-surface:** none. All new test functions are collected + run; the `_executable_lines` helper is used by `test_shim_is_thin`.
4. **Contract-drift:** none. The shim's parsed shape matches every assertion.
5. **Test-coverage observation:** strong. 8 new tests cover the shim shape (thin, local-uses, trigger, secrets-inherit, loop-guard, resolvable reference, parse); 3 sibling characterisation tests re-pointed to the reusable workflow where the relocated invariants now live.
6. **Style/readability:** clean. ruff passes; comments are accurate and load-bearing.
7. **Performance (CR-10):** no anti-pattern matches. The only loop constructs in the diff are bounded in-memory comprehensions over a single-job `jobs` mapping in tests — no N+1, no DB/RPC/filesystem in a loop.

One `low` finding (the `_LOCAL_USES` duplication) — see Findings in the Changes.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `uv run ruff check` on the 3 changed `.py` files: All checks passed. No type checker is configured for these stdlib+pyyaml test files (coverage gap noted; PyYAML parse + shape assertions cover the YAML). Build Verification empty.
- [✓] **CR-02 Dispatch shape.** Diff is 4 files; raw churn 965 lines but dominated by the wholesale 280-line Replace deletion. Single-reader pass applied and justified: the substantive surface is one 12-line infra shim + test re-points, all read end-to-end by the author during RGB. Recorded here per CR-02.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end (authored/edited in this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file + quoted constant.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + loop-guard/local-ref checks. Security: 0 findings + secrets/injection/supply-chain checks. Quality: 1 low + all 7 outputs (build follow-up, jsx N/A, dead-surface, contract-drift, test-coverage, style, CR-10 perf).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `feat`). PH-02 Size: low (net deletion; Replace artifact). PH-03 Safety: low (1 infra file, loop-guard verified, 0 secrets/migrations). PH-04 Completeness: low (test+infra change, well-covered). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff origin/change/extend-auto-back-merge-on-release` (working tree vs base; pre-commit).
- **Neighbour expansion:** git grep for references to `.github/workflows/release-on-merge.yml` (5 test files + the reusable workflow). All inspected; reusable workflow unchanged.
- **Neighbour cap:** not reached (≪ 20 files).
- **Scanners run:** ruff (lint). Gitleaks/Semgrep/Trivy: unavailable locally — manual secret-pattern scan applied as fallback.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (small infra diff).
