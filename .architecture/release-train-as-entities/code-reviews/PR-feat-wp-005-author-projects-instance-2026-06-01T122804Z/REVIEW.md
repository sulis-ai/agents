# Code Review: feat/wp-005-author-projects-instance — Author 4 Project instances

> **Timestamp:** 2026-06-01T12:28:04Z (ISO 8601 UTC)
> **Author:** Senior Engineer (executor)
> **Branch:** feat/wp-005-author-projects-instance → change/create-release-train-as-entities
> **Files changed:** 4
>
> **Outcome:** Ready to merge

---

## At a glance

The pull request adds the four marketplace Project entities (sulis, sulis-brain, plugin-builder, investor-coach) per ADR-004, vendors the brain Project schema, and ships nine deterministic tests that pin parse, cardinality, schema validation, canonical cross-references, source-JSON shape, version-files existence, tenant consistency, and name uniqueness. Everything green: the file passes the foundation schema, every test asserts a specific invariant from the WP Contract, and the full 1240-test suite still passes. Nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

This is a focused, single-concern pull request: four new files under one feature area, no schema migrations, no infrastructure changes, no commit-type spread. The new test file is included alongside the new content it validates, so the test coverage check passes cleanly. Size and scope are well within review-friendly bounds.

---

## Technical detail

> Below this point the report uses internal taxonomy for engineers and downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — |
| Security | 0 | 0 | — |
| Quality | 0 | 0 | — |

### Build Verification (CR-01)

Tools run: `ruff check`, `ruff format --check`, `pytest`.

- `ruff check plugins/sulis/scripts/tests/unit/test_projects_instance_valid.py` → All checks passed.
- `ruff format --check plugins/sulis/scripts/tests/unit/test_projects_instance_valid.py` → 1 file already formatted.
- `pytest plugins/sulis/scripts/tests/unit/test_projects_instance_valid.py` → 9 passed.
- Full unit-test suite (`pytest plugins/sulis/scripts/tests/unit/`) → 1240 passed.
- JSON parse on `projects.jsonld` and `project.schema.json` → OK.

No PR-introduced errors. No coverage gaps in the mechanical floor.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                  → clean
  module_fan_out: 1 (plugins/sulis/)          → clean
  severity: low

Size (PH-02):
  lines_added: 491 (98 jsonld + 132 schema + 259 test + 2 trailing newlines)
  lines_removed: 0
  files_changed: 4
  severity: low (≤200 lines per file boundary; whole-PR ≤500)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 1 (project.schema.json vendored — not changed in-place)
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (the jsonld instance has 9 tests)
  api_change_without_schema: false
  severity: low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Per the WP's parallel-batch scope guard, neighbour files outside the WP's contract (e.g., the drift detector in WP-007, the skill in WP-010) are owned by peer WPs and not in this WP's review ring.

### Watch List

- The 4 Projects all bind to a single release-train Workflow ULID (`dna:workflow:01KT0RTRA1NWFW00000000000A`). This is intentional per the WP-001 + WP-005 design — the Workflow definition is unscoped and Projects bind per-invocation. The drift detector (WP-007) will validate this cross-reference end-to-end once it lands; until then, the test `test_all_release_workflow_refs_resolve_to_wp001` is the local guard.
- Two Projects (`sulis-brain`, `plugin-builder`) declare cross-repo `source.repo` (`sulis-ai/plugins`). Per ADR-004 option (a), their `version_files` are recorded for documentation; existence verification is skipped per WP DoD. Cross-repo resolution is brain v0.7+ work (DR-016) — not a gap, a documented deferral.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this WP
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `pytest`. Base: clean. Head: clean. Coverage gap: none.
- [✓] **CR-02 Carve-out path.** Diff: 491 lines / 4 files. Within carve-out (≤200 lines OR ≤5 files — uses files threshold). Single-reader pass justified.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end. (jsonld 98 lines; schema 132 lines, vendored verbatim; test 259 lines; journal authored via wpx-journal.)
- [✓] **CR-04 Evidence discipline.** No findings → no evidence required.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked dependency-direction, secrets, observability, contract-test). Security: nothing surfaced (checked SEC-01..07, SC-01..04, secrets scan via inline regex review, PII-leak). Quality: nothing surfaced (checked dead-surface, contract-drift, test-coverage observation, style, CR-10 perf patterns — none of the 10 perf anti-patterns matched given the test-only Python file + JSON data files).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: low. PH-03 Safety: low (vendored schema is additive). PH-04 Completeness: low. No auto-downgrade triggers fired.

#### Run details

- **Diff source:** local working tree vs change branch (no commit yet at review time)
- **Neighbour expansion:** declared-scope only per WP-005 contract; peer WPs (007, 010) explicitly out of ring per parallel-batch scope guard
- **Neighbour cap:** not reached
- **Scanners run:** ruff (lint+format), pytest, jsonschema validation (Draft202012Validator), JSON parse
- **Scanners unavailable:** gitleaks, semgrep, trivy (not in repo; project standard for Python-only WPs)
- **Lenses dispatched in parallel:** no — single-reader carve-out path per CR-02
