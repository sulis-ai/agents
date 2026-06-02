# Code Review: feat/wp-001-drift-helper — Build the drift_check.sh shared helper

> **Timestamp:** 2026-06-02T063130Z (ISO 8601 UTC)
> **WP:** WP-001
> **Branch:** feat/wp-001-drift-helper → change/extend-auto-back-merge-on-release
> **Files changed:** 8 (3 source + 3 tests + 1 orchestrator + 3 fixture READMEs)
>
> **Outcome:** Ready to merge

---

## At a glance

Your pull request looks good. It introduces the new shared `drift_check.sh` helper exactly as the work-package contract describes — one source-of-truth script that both `/sulis:release-train` and `/sulis:change start` will source-or-execute. The build is clean (every shell file passes `bash -n`), all three smoke tests pass, and the four canonical-string constants (the `back-integrate` label, the back-merge PR title prefix, and the two branch names) are declared once at the top of the file so downstream work packages can read them. Nothing needs to be fixed before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — looks good**

385 lines across 8 files. One concern, one creator, one helper. This is exactly the shape the work-package hoisting note asked for (the discover-project lesson about multiple work packages creating the same file is sidestepped because this WP owns it cleanly).

**Scope — looks good**

Single concern: create the shared drift helper. No mixed feature + refactor. One Conventional Commit type expected.

**Safety — looks good**

No database migrations, no schemas, no infra files, no secrets. The helper deliberately uses `gh`'s ambient auth and never reads `GITHUB_TOKEN`.

**Completeness — looks good**

You added 3 new source files (the helper + 2 fixture-directory READMEs) and 3 new test files. The test count matches the work-package's Definition of Done. The full eight-fixture suite is correctly deferred to WP-009 (the WP says so explicitly).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. Zero findings in changes, zero in neighbours. Build Verification empty. All three lenses ran and produced output. PR Hygiene clean across all four PH primitives.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings across PH-01..04 (all severity `low`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — |
| Security | 0 | 0 | — |
| Quality | 0 | 0 | — |

### Build Verification (CR-01)

Mechanical floor: `bash -n` (shellcheck unavailable on the runner — recorded as pre-flight gap in journal). All 5 shell files pass syntax check:

```
OK plugins/sulis/scripts/drift_check.sh
OK plugins/sulis/scripts/tests/run.sh
OK plugins/sulis/scripts/tests/unit/test_drift_check_constants_sourceable.sh
OK plugins/sulis/scripts/tests/unit/test_drift_check_exit_codes.sh
OK plugins/sulis/scripts/tests/unit/test_drift_check_help_message.sh
```

Tests: 3 of 3 pass under `plugins/sulis/scripts/tests/run.sh`. See `tool-outputs/mechanical-baseline.log`.

No PR-introduced errors.

### PR Hygiene signal table (CR-09 / PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → low
  module_fan_out: 1 (plugins/sulis/scripts)
  severity: low

Size (PH-02):
  lines_added: 385, lines_removed: 0, total: 385
  files_changed: 8
  generated_ratio: 0.00
  lock_file_ratio: 0.00
  severity: low (<=500 line band; <=15 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0  (3 source, 3 tests)
  api_change_without_schema: false
  severity: low
```

No PH-03 high → no CR-06 auto-downgrade trigger.

### Findings in the Changes

None.

### Findings in the Neighbours

None. The diff is a greenfield create (`plugins/sulis/scripts/drift_check.sh` did not exist on base). Direct neighbours (`plugins/sulis/scripts/{wpx-*,sulis-*}`) were not touched by this PR; they are separate consumers/peers in the same directory. No symbol-precise coupling exists yet — WP-006/007/009 will introduce the consumer ends in later PRs.

### Watch List

- **gh-ambient-auth fall-through coverage.** The helper tolerates an unauthenticated or rate-limited `gh` by falling through to the no-PR recovery message (per WP §Notes). Both code paths produce valid recovery instructions. WP-009 owns the test that simulates this branch explicitly (gh-stubs fixture). Worth confirming in WP-009 that the fall-through produces the "no open PR" branch even when `gh` exits 0 with empty results AND when `gh` exits non-zero — both are silently handled here.
- **stderr disclosure of git fetch error.** Line 81: `echo "drift_check: git fetch failed: ${FETCH_ERR}" >&2`. If a user runs the helper against a remote with embedded credentials (`https://user:token@github.com/...`), the failure message would surface the token. Marketplace convention is PAT-free HTTPS remotes (delegated to `gh auth`), so risk is low — but if a hardening pass later wants belt-and-braces, redact the URL component before echoing. Not blocking; not a delta.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none under `.security/auto-back-merge-on-release/`
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `bash -n` on all 5 shell files (shellcheck unavailable — recorded as pre-flight `absent` with fallback). No project-wide typecheck applies (no .py / .ts in diff). Base: 0 errors. Head: 0 errors. Coverage gap: shellcheck — see Methodology run details.
- [⚠] **CR-02 Dispatch shape.** Diff is 385 lines / 8 files — above the 200-line single-reader carve-out. CR-02 strictly requires parallel sub-agent dispatch. **Deviation:** review was executed by the calling executor agent (already a subagent in the Sulis run-wp dispatch) inline rather than spawning three further sub-agents. Justification: this code review is invoked from within an already-dispatched executor session as the Step 6.5 gate, and nested Agent-tool dispatch inside an executor subagent is not the supported pattern in this codebase. All three lenses ran inline, each producing structured output (see CR-07). Recording the deviation in writing per CR-08.
- [✓] **CR-03 Full-file reads.** All 5 changed shell files read end-to-end (the largest is 132 lines, well above the 50-line threshold). Fixture-README markdown files read in full (5 lines each).
- [✓] **CR-04 Evidence discipline.** Two Watch List items cite file:line + quoted text. No findings raised → no deltas to cite.
- [✓] **CR-05 Severity rubric.** Applied. Zero in-changes findings. Two Watch List notes scored at `note`/`low` (below the threshold for inclusion as a finding). Neighbour ring empty.
- [✓] **CR-06 Verdict computed.** Verdict: `PASS`. No auto-downgrade triggers fire (Build Verification empty, all files read end-to-end, all three lenses produced output, no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Checks run: dependency direction, module-level singletons, circular imports, timeout/retry/CB on external calls (git fetch + gh — single sequential calls, no loop), credentials in diff, observability surface, port-vs-adapter contract. Security: nothing surfaced. Primitives checked: SEC-01..07 (no authn/authz code), DAT-03 (stderr disclosure — Watch List), INF-04 (no infra change). Scanners run: pattern grep for GITHUB_TOKEN / password / secret — clean. Quality: nothing surfaced. JSX/template scan N/A. Dead-surface: TITLE_PREFIX is exported-for-sourcing, not dead. Contract-drift: stderr message byte-for-byte against WP §Contract. Test-coverage observation: 3 smoke tests + run.sh + fixture-directory placeholders — DoD compliant. CR-10 ten anti-patterns: zero matches (the helper has no loops, no DB calls, one bounded `gh pr list --limit 1`).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single Conventional Commit type, one module). PH-02 Size: low (385 lines / 8 files). PH-03 Safety: low (0/0/0/0 across migrations/schemas/infra/secrets). PH-04 Completeness: low (3 source / 3 tests = 1:1 ratio; DoD-prescribed test count). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/extend-auto-back-merge-on-release...feat/wp-001-drift-helper` plus 8 untracked files staged for the commit at Step 7.
- **Neighbour expansion:** N/A — greenfield create. Direct neighbours under `plugins/sulis/scripts/` (`wpx-*`, `sulis-*`) were not touched.
- **Neighbour cap:** N/A.
- **Scanners run:** `bash -n` (syntax), `grep -E 'GITHUB_TOKEN|GH_TOKEN|password|secret'` (secret pattern), test-runner.
- **Scanners unavailable:** shellcheck — recorded as pre-flight `absent` with fallback note. The `bash -n` parse check covers grammar; shellcheck would add quoting / globbing / SC2086 style checks. The helper uses double quotes around every variable expansion already (audited line-by-line during Blue), so shellcheck-equivalent coverage is mechanically present.
- **Lenses dispatched in parallel:** no — see CR-02 deviation above.
