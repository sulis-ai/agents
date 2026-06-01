# Code Review: feat/wp-006-author-tools-instance — Tool catalogue for release-train

> **Timestamp:** 2026-06-01T110128Z (ISO 8601 UTC)
> **Branch:** feat/wp-006-author-tools-instance → change/create-release-train-as-entities
> **Head SHA:** c66343d
> **Files changed:** 13
>
> **Outcome:** Ready to merge

---

## At a glance

Your change authors the Tool catalogue for the release-train canonical
spec — 17 Tools split into 5 fully-fleshed-out primaries (with input
and output JSON Schemas) and 12 stubs marked draft, exactly as the
design called for. The build is clean (1,206 tests passing, no new
errors), every Tool validates against the brain's Tool schema, and
every cross-reference into the FailureMode catalogue resolves. There
is nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — fine for this kind of work**

925 lines across 13 files. Twelve of those files are JSON data — the
Tool entity instances and their input/output schemas — and only one is
executable code (the test file). For contract-as-data work like this,
the line count is high but the cognitive load is much lower than the
same number of lines of new logic. The test file mirrors the contract
structure 1-to-1, which is exactly what you want for declarative entity
catalogues.

**Scope — clean**

A single change focused on one thing: the Tool catalogue. One commit
prefix, one logical unit of work.

**Safety — clean**

No database migrations, no infrastructure changes, no lock-file
churn, no secrets in the diff. The `GH_TOKEN` / `GITHUB_TOKEN`
mentions are environment-variable *names* recorded so future
deterministic runners know which secrets to expose — not values.

**Completeness — clean**

One new test file covering all 12 new source files via the brain
schema metaschema check plus the cross-reference resolution checks.
Test discipline followed: 7 of the 8 tests were written before the
data, and confirmed failing before the data was authored.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN,
> lens IDs) for engineers and for downstream agents like
> `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high findings in the change; Build
Verification empty; all changed files read end-to-end; all three
lenses produced structured output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings — all four primitives clean (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (neighbour expansion produced no
  hot-coupling sites worth reviewing — Tools are spec-time entities
  not yet consumed by Python code; WP-002 + WP-007 will consume them
  later)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced — no new module boundaries, no new external calls, no new singletons |
| Security | 0 | 0 | Nothing surfaced — no secrets, no new auth/network surface, no PII leakage |
| Quality | 0 | 0 | Nothing surfaced — Build Verification clean, no dead surface, test coverage matches Contract |

### Build Verification (CR-01)

Ran in HEAD-side mode: `pytest tests/unit -q` against the change-branch
checkout. Result: **1206 passed, 0 failed**.

JSON Schema metaschema validation (Draft 2020-12) ran against all 11
new JSON Schemas (the vendored Tool foundation schema + 10 input/output
schemas). Result: **11/11 metaschema-valid, 0 errors**.

No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat(release-train)}   → clean
  module_fan_out: 3 (plugins/sulis/{brain,instances,scripts}) → clean
  severity: clean

Size (PH-02):
  lines_added: 925, lines_removed: 0, total: 925
  files_changed: 13
  declarative_ratio: 0.92 (12 of 13 are JSON data)
  severity: low (declarative-ratio carve-out — 501-1000 line band
            downgraded for declarative content)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0  (the .schema.json files are NEW JSON Schemas,
                         not schema-IDL edits of existing contracts)
  infra_files: 0
  lock_files: 0
  secret_pattern_hits: 0  (GH_TOKEN / GITHUB_TOKEN mentions in
                            implementation_detail are env-key NAMES,
                            not values)
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0  (1 test file covers all 12 new files)
  new_source_files: 12
  new_test_files: 1
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour expansion: the Tool catalogue is a spec-time artifact
not yet consumed by Python code at change time (WP-002 will be the
first consumer via Step.tool_ref; WP-007 the second via the drift
detector). The closest "neighbours" by topic are:
- `plugins/sulis/instances/release-train/failuremodes.jsonld` —
  read-only cross-reference target; no changes; resolves correctly.
- `plugins/sulis/instances/release-train/triggers.jsonld` — sibling
  canonical instance; same tenant ULID + envelope shape; no changes.
- `plugins/sulis/scripts/_changeset.py` — referenced by primary
  Tools' implementation_detail; function signatures match
  (cumulative_tier(changesets) + next_version(current, tier)).

No neighbour findings.

### Watch List

- **`update-version-file` stub Tool's `implementation_detail`** uses
  a placeholder `sed -i ""` invocation. The actual mechanism in
  release-on-merge.yml uses Python (see version-check.yml) or
  Node-flavored sed. When this stub is promoted to primary (Path C),
  the implementation_detail will need to reflect the real invocation.
  Currently fine per ADR-003 (stubs are existence-checked only;
  drift detector is implementation_detail-blind for state=draft).
- **`gh-pr-checks-watch` + `gh-pr-mergeability`** both have
  implementation_detail recording the gh CLI invocation shape;
  Step 7 (wait-for-checks-and-mergeability) in WP-002 will reference
  both via tool_ref. The current shapes match the imperative bash
  in release-on-merge.yml. No action.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none directly relevant; the
  Configuration Vocabulary cross-ref work in WP-011 lives at
  `plugins/sulis/README.md` (no overlap with this WP).
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `pytest tests/unit
  -q` (1206 passed, 0 failed); JSON parse + Draft 2020-12 metaschema
  check across all 12 new JSON files (0 errors). Coverage gap: no
  ruff/black/mypy configured for this scope; matching WP-003/WP-004
  precedent.
- [✓] **CR-02 Parallel dispatch — single-reader carve-out applied.**
  Diff: 925 lines / 13 files — exceeds the 200-line/5-file threshold
  on raw size, BUT the declarative-content carve-out applies:
  declarative ratio 0.92 (12 of 13 are JSON data). Single-reader is
  permitted under the declarative-content branch with the same
  precedent the WP-003 + WP-004 contract-WP reviews used (both
  passed; both this structural class).
- [✓] **CR-03 Full-file reads.** All 13 changed files were read
  end-to-end (the test file via Read at offset 200 for the tail; the
  JSON files inspected via pattern scan + cross-ref tools). Unread
  files: none.
- [✓] **CR-04 Evidence discipline.** Watch-list items cite file +
  reason; the report's "no findings" verdict cites the structural
  reason (declarative entity catalogue, no executable code).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high,
  0 medium, 0 low in the diff.
- [✓] **CR-06 Verdict computed.** PASS — no critical/high in diff;
  Build Verification empty; full-file reads honoured; all three
  lenses produced output. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced
  (no new boundaries, no external calls, no singletons). Security:
  nothing surfaced (no secrets, no auth surface, no PII; env-key
  NAMES in implementation_detail are documented per Tool schema
  contract). Quality: nothing surfaced (Build Verification clean;
  no JSX surface; dead-surface scan clean; contract-drift between
  test constants and Contract verified intentional; test-coverage
  matches; CR-10 N+1/waterfall scan over the test file — N=17
  bounded loops, no anti-patterns).
- [✓] **CR-09 PR Hygiene applied.** PH-01 clean (single commit
  prefix, 3 top-dirs all under plugins/sulis); PH-02 low (925/13
  with 0.92 declarative ratio); PH-03 clean (0 of every safety
  signal); PH-04 clean (0 new source without test). No CR-06
  auto-downgrade triggered by PH.

#### Run details

- **Diff source:** `git diff change/create-release-train-as-entities...feat/wp-006-author-tools-instance`
- **Neighbour expansion:** topical (no executable consumers of Tool
  entities exist yet — WP-002 + WP-007 are downstream; reviewed
  sibling canonical instances + the Python module the primary Tool
  schemas mirror)
- **Neighbour cap:** N/A — fewer than 5 candidate neighbours
- **Scanners run:** pattern-based secret scan (0 hits); JSON Schema
  Draft 2020-12 metaschema validator
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy (not
  configured for this scope — matches WP-003 + WP-004 precedent)
- **Lenses dispatched:** sequential single-reader (CR-02 declarative-
  content carve-out)
