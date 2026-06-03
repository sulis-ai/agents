# Code Review: feat/wp-013-dogfood-and-scenario-emission — Dogfood + scenario emission

> **Timestamp:** 2026-06-03T101934Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-013-dogfood-and-scenario-emission → change/create-brain-backlog-and-traversal
> **Files changed:** 7 tracked (+1 new test) + dogfood artifacts (.brain entities, .changes bundle)
>
> **Outcome:** Ready to merge

---

## At a glance

This change closes the loop the whole brain-backlog feature was building toward: it deposits the feature's own ideas into the brain through the new capture path and proves the two verification journeys run end-to-end. The build is clean, the new behaviour is well-tested (both unit and integration), and the source changes are small and tightly scoped. Nothing needs to be fixed before merge.

One housekeeping note: a `.coverage` file was created during testing and has already been removed so it won't be committed.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Around 160 lines of tracked source/test changes plus one new test file (~480 lines) and the feature's own committed brain data. Comfortably reviewable.

**Scope — clean.** One concern: the dogfood. The small source touches (carrying a driver-params field through the journey assembler, and recognising a journey's own internal data hand-offs) are exactly what was needed to make the journeys run, not unrelated drive-by edits.

**Safety — clean.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets.

**Completeness — clean.** New behaviour ships with tests: two new unit tests pin the runner's data-flow rule, and a new integration suite runs both journeys from the brain graph and asserts they pass green.

## Things to take away

Omitted — the change is clean and well-shaped.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean)
- **In the changes:** 0 critical, 0 high, 0 medium, 0 low (2 notes → Watch List)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (no failing characterisation test to ground a delta; CR-04)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 (1 note) | 0 | `test-target` entry-seed literal duplicated across authoring + runner (documented, 2-site) |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 (1 note) | 0 | stray `.coverage` artifact (removed) |

### Build Verification (CR-01)

Mechanical baseline: `ruff` (the configured linter) on every changed Python file. My-authored/edited files: **All checks passed**. `tests/unit/test_scenario_runner.py` reports 2 `E731` (lambda-assignment) errors — both pre-existing on the base branch (lines 59, 114, the file's established `http = lambda` convention), neither introduced by this diff. `compileall` on the three edited modules: OK. **Build Verification section empty** → no `Block` downgrade.

No type-checker configured for this kind (repo-contract `type_check: ""`); recorded as the only coverage note, not a gap (the project deliberately runs stdlib-only tooling).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread: single concern (dogfood) → clean; severity: none
Size (PH-02):        ~160 tracked source/test lines + 1 new test file; 7+1 files; severity: none
Safety (PH-03):      migrations: 0, schema_idl: 0, infra: 0, secret_pattern_hits: 0; severity: none
Completeness (PH-04): new_source_without_test: 0 (new test suite + 2 unit tests added); severity: none
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

None at severity low or above. Two notes recorded in the Watch List.

### Findings in the Neighbours

None. The neighbour ring (`_scenario_dispatch`, `_scenario_graph_load`, `sulis-author-scenario`, `sulis-verify-acceptance`, `sulis-capture`) was read for interaction effects; the data-flow change in `run_scenario` and the `mechanism_detail` carry in the assembler are additive and consumed exactly where expected. The dispatcher's `execute_step` already read `mechanism_detail`; the runtime's `resolve_journey` already preserved unknown fields. No neighbour regressions.

### Watch List

- **`test-target` entry-seed literal duplicated (architecture, note).** The IDEF0 journey entry-seed string `"test-target"` is referenced in both `_scenario_authoring.py:103` (the assembler seeds the first step's `input_artifacts` with it) and `_scenario_runner.py:76` (the runner pre-loads it into the `produced` available-set). They must stay in lockstep. **Not extracted to a shared constant deliberately:** `_scenario_authoring` imports neither `_scenario_runtime` nor `_scenario_runner` today, so a shared constant would introduce a new module-dependency edge purely to dedupe one string — heavier coupling than the duplication it removes. Both sites carry a comment cross-referencing the convention. If a third consumer appears, revisit (3-consumer threshold).
- **Subprocess journey `cmd` runs author-supplied shell (security, note — pre-existing design).** `_scenario_dispatch` runs `subprocess.run(cmd, shell=True)` where `cmd` comes from a Step's `mechanism_detail`. This is author-authored journey content (the same trust level as test code), not user input — the pre-existing v1 design (PR #154). This change forwards `mechanism_detail` through the assembler but introduces no new trust boundary. No action.

### Cross-Reference

- No prior `.security/{project}/viability-report-*.md` for this project.
- No existing accepted hardening deltas to cite.
- No neighbour pattern suggests a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff` on all changed Python; `compileall` on edited modules. Base vs head delta: 0 PR-introduced errors (2 E731 in test_scenario_runner pre-exist on base). No type-checker configured (repo-contract) — recorded, not a silent skip.
- [✓] **CR-02 Single-reader pass justified by diff size:** ~160 tracked source/test lines across 7 files + 1 new test file; well within the ≤200-line / ≤5-source-file spirit for a backend-only, single-concern diff. Read in place end-to-end rather than parallel-dispatched.
- [✓] **CR-03 Full-file reads.** All changed source modules and the new test file read end-to-end. Unread files >50 lines: none.
- [✓] **CR-04 Evidence discipline.** Findings (notes) cite file:line. No delta drafted — neither note has a failing characterisation test to ground a fix (correctly Watch-Listed).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low; 2 notes.
- [✓] **CR-06 Verdict computed.** `PASS`. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + 1 note (entry-seed literal). Security: nothing surfaced (SEC-01..07 N/A — no auth/injection/secrets surface; the subprocess driver is pre-existing author-trust). Quality: 0 findings; test-coverage observation = new behaviour is tested (2 unit + 1 integration suite); CR-10 perf scan = no anti-pattern matches (the `run_scenario` loop is bounded over journey steps, `produced.update` O(1) amortised); 1 note (stray `.coverage`, removed).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single concern). PH-02 Size: none (~160 lines). PH-03 Safety: none (0 migrations/schemas/infra/secrets). PH-04 Completeness: none (tests added). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff origin/change/create-brain-backlog-and-traversal` (working tree, pre-commit)
- **Neighbour expansion:** git grep over `_scenario_*` modules + the four CLIs that consume them
- **Neighbour cap:** not reached (6 neighbours considered)
- **Scanners run:** ruff (lint), compileall (build). Gitleaks/Semgrep/Trivy not run — no secret/dependency surface in the diff (stdlib-only, no new deps, no config/IaC).
- **Scanners unavailable:** n/a
- **Lenses dispatched in parallel:** no — single-reader justified by CR-02 size carve-out.
