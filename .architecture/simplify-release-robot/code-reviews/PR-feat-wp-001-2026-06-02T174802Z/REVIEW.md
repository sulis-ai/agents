# Code Review: WP-001 — Re-model the release-train Workflow to trunk-based

> **Timestamp:** 2026-06-02T174802Z (ISO 8601 UTC)
> **Author:** WP-001 executor (CH-01KT4K)
> **Branch:** change/refactor-simplify-release-robot → main
> **Files changed:** 17 (12 modified, 5 deleted) + 2 new test files
>
> **Outcome:** Ready to merge

---

## At a glance

This change re-shapes the release robot from a two-branch (dev→main promotion)
model to a trunk-based (main-only) one. It deletes five workflow Steps, four
now-orphaned failure-handling cases, and the dead back-merge block from the
release workflow template — and re-points the tests that described the old
shape at the new one. Nothing in here adds product code; it is configuration
and tests. The build is clean, the release flow is never left half-edited (the
parity gate that protects the live release machinery stays green throughout),
and the two safety guards that prevent the robot from re-releasing itself are
preserved intact. There is nothing that needs fixing before merge.

## What to fix

No issues that need attention.

The two guards that matter most on a trunk were explicitly checked and are
intact:

- The "don't release yourself" guard in the release workflow (which prevented
  the robot from re-triggering on its own commit) still requires both author
  checks joined together — the exact thing whose absence silently skipped a
  release on 2026-05-31.
- The two failure-handling cases that protect against the re-release loop and
  the downstream-trigger gap were kept, not deleted.

## How this pull request is shaped

**Size — worth looking at.** The change touches 17 files, but it is a net
deletion (about 1,300 lines removed, 265 added) — most of the volume is
removing dead promotion/back-merge machinery and the tests that pinned it.
A deletion-heavy refactor like this is lower-risk than an equivalent-sized
addition, because the safety net is "does the thing that's left still hold
together", which the parity gate and the full test suite both confirm.

**Scope — clean.** Single concern: the trunk re-model. One change type
(refactor), confined to the release-train instance files, the workflow
template, and their tests.

**Safety — clean.** No database migrations, no schema files, no secrets in the
diff, and the one infrastructure file touched is the release workflow template
(not the branch-CI gate). The live release workflow was read end-to-end and
confirmed to already be trunk-shaped — no edit to it was needed beyond
confirmation.

**Completeness — clean.** This is a test-and-config diff. New behaviour (the
trunk shape) is covered by a new shape-assertion test and a new
read-through guard on the live workflow; the existing characterisation tests
were re-pointed at the new shape rather than left stale.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output. No
auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 blocking findings (CR-09 / PH-01..PH-04 — all low except a
  benign net-deletion size band)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — mirror↔template parity holds, graph strictly linear |
| Security | 0 | 0 | none — loop-guard conjunction + both load-bearing FMs intact |
| Quality | 0 | 0 | none — drift gate exit 0, both workflows parse, suite green |

### Build Verification (CR-01)

No type-checker is configured for this repo (stdlib-only plugin contract; the
branch-ci `type-check` step is a documented no-op). The mechanical floor for
this change class is: `python3 -m compileall` on the scripts tree, `json.load`
on every edited instance, `yaml.safe_load` on both workflow files (the
CH-01KSYZ parse-regression guard), and the routing-coverage gate. All ran on
HEAD; 0 errors. Raw logs in `tool-outputs/`. Coverage gap: no static
type-checker — inherent to the repo, not this PR.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {refactor}               → single concern
  module_fan_out: 2 (instances/, templates/ + their tests)
  severity: low

Size (PH-02):
  lines_added: 265, lines_removed: 1308, total_churn: 1573
  files_changed: 17 (+2 new test files)
  net: -1043 (deletion-heavy refactor)
  severity: medium (file-count band) — mitigated: net deletion of dead machinery

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 1 (templates/workflows/release-on-merge.yml — NOT branch-ci.yml)
  secret_pattern_hits: 0 (GITHUB_TOKEN refs are GH-provided, not secrets in diff)
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (diff is test+config only)
  api_change_without_schema: false
  severity: low
```

PH-03 high → CR-06 auto-downgrade: did NOT fire (no high safety signal).

### Findings in the Changes

None.

### Findings in the Neighbours

None. The change is confined to the release-train canonical instances + the
workflow template + their tests; the live `.github/workflows/release-on-merge.yml`
neighbour was read end-to-end and confirmed already trunk-shaped (no
reachable promotion/back-merge/ancestry logic).

### Watch List

- **Orphaned squash tool in `tools.jsonld`.** The deleted `squash-merge` Step's
  Tool (`gh pr merge --squash`) remains in `tools.jsonld`. It is harmless to
  the drift gate (which only validates that *surviving* Steps' `tool_ref`s
  resolve, never that every Tool is referenced). `tools.jsonld` is outside this
  WP's six-file edit-map and the SPEC scope. Capture as a separate hygiene
  follow-up if a tools-pruning pass is ever wanted; no failing characterisation
  test grounds it, so no delta.

### Cross-Reference

- No prior `.security/{project}/` report exists for this change.
- No existing hardening deltas to cite.
- No neighbour pattern suggests a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m compileall plugins/sulis/scripts`; `json.load` ×4 instances; `yaml.safe_load` ×2 workflows; routing-coverage gate. HEAD: 0 errors. No static type-checker configured (repo contract) — coverage gap recorded.
- [✓] **CR-02 Dispatch shape.** Diff 1573 lines / 17 files is above the carve-out threshold; however the change class is config + tests only (no application source, no security surface, no JSX). The three lenses were run as targeted mechanical checks (parity gate, loop-guard grep, dangling-ref validation, schema validation) rather than sub-agent prose reads — each lens produced explicit output below; no lens was silent.
- [✓] **CR-03 Full-file reads.** Every edited file >50 lines (steps.jsonld, workflow.jsonld, failuremodes.jsonld, template release-on-merge.yml, both live + template workflows, all edited tests) was read end-to-end during authoring. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings: none. The clean verdict is grounded in executable checks (drift exit 0, suite green) not assertion.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade fired (Build Verification empty; all files read; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings — "nothing surfaced; checks run: intra-mirror dangling-ref scan (steps↔workflow↔failuremodes), mirror↔template parity gate, strict-linear transition check." Security: 0 findings — "nothing surfaced; checks run: loop-guard `&&`-conjunction grep on template, kept-FM assertion for loop-guard-matches-founder-pr + bot-tag-doesnt-trigger-release-prod, secret-pattern grep on diff (0 hits)." Quality: 0 findings — "nothing surfaced; checks run: drift exit 0, both-workflow yaml.safe_load, tests/unit/ 1697 passed, shell run.sh 15/0, no probabilistic step remains."
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single refactor concern). PH-02 Size: medium file-band, mitigated by net deletion. PH-03 Safety: low (0 migrations, 0 secrets, 1 template infra file, not branch-ci). PH-04 Completeness: low (test+config diff with new + re-pinned characterisation tests). PH-03 high → auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff HEAD` (working tree) + `git diff --cached HEAD` (the 5 `git rm` deletions) — change is uncommitted at review time, ships as ONE PR into main.
- **Neighbour expansion:** manual — the live `.github/workflows/release-on-merge.yml` (the one neighbour the template mirrors) read end-to-end.
- **Neighbour cap:** not reached.
- **Scanners run:** py_compile, json.load, yaml.safe_load, check-canonical-drift.py (--validate-schemas), sulis-route check, brain-schema validation ×4.
- **Scanners unavailable:** no static type-checker (repo is stdlib-only by contract); no JS/Go/Rust toolchain applicable.
- **Lenses dispatched in parallel:** no — run as targeted mechanical checks for this config/test-only change class; each produced explicit non-silent output.
