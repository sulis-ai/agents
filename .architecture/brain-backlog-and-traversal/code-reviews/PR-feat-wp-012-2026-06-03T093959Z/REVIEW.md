# Code Review: PR feat/wp-012 — Wire traverse + opportunity-analyst routing into the Sulis agent

> **Timestamp:** 2026-06-03T093959Z (ISO 8601 UTC)
> **Author:** executor (WP-012)
> **Branch:** feat/wp-012-sulis-agent-traverse-wiring → change/create-brain-backlog-and-traversal
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds two new ways for the assistant to help you, without touching
anything it already does. First, when you ask "what's open?" or "what's on the
roadmap?", it can now answer straight from your captured ideas and requirements
instead of asking you to remember a command. Second, when you want to think
through *why* an idea is worth building, it can hand you to a specialist that
walks you through it.

The change is small, well-contained, and came with a safety test that proves
none of the existing routing was disturbed. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Three files, all additions, no deletions. The kind of small,
single-purpose change that is easy to review thoroughly.

**Scope — clean.** One concern: wiring two new routing capabilities into the
assistant. A safety test was written first to lock down the existing behaviour,
then the additions were made — exactly the discipline this kind of edit calls
for.

**Safety — clean.** No database changes, no configuration changes, no
credentials, no external calls.

**Completeness — clean.** The change is itself test-and-config work, and it
ships with both a snapshot test (proving the old behaviour survives) and three
new tests (proving the new behaviour works).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high findings; Build Verification empty; both
changed source files (the two test files, the agent body) read end-to-end; all
three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `ruff check` clean; full pytest suite 1801 passed / 9 skipped / 0 failed; route+gate+wiring subset 29 passed.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04). Single `refactor:` concern, 289 additive lines, 3 files, no migrations/schemas/secrets/infra, tests included.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — additive routing prose + pure test files |
| Security | 0 | 0 | none — no secrets, external calls, or injection surface |
| Quality | 0 | 0 | none — EP-07 characterisation + 3 wiring tests, no CR-10 perf matches |

### Build Verification (CR-01)

No PR-introduced errors. Mechanical floor: `ruff check` on both changed Python
files → "All checks passed!" (`tool-outputs/ruff-head.log`). No mypy/pyright
config in the scripts package; ruff is the configured linter. The agent body
(`sulis.md`) is Markdown, validated by the methodology agent-shape tests +
the live-tree route gate (`test_route_gate.test_gate_passes_clean_marketplace`),
all green.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {refactor}              → clean (single concern)
  module_fan_out: 2 top-level areas (agents/, scripts/tests/)
  severity: clean

Size (PH-02):
  lines_added: 289, lines_removed: 0, total: 289
  files_changed: 3
  severity: low (single-purpose, all additive)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0  (the change IS test+config; ships its own tests)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

The edit to `plugins/sulis/agents/sulis.md` is purely additive routing prose
(REORGANISE-Refactor, ADR-004 / FR-08): a new `opportunity-analyst` row in
`dispatch_via` (byte-for-pattern identical to the `requirements-analyst` row),
a new `routes_to` slug, and a new body subsection describing the brain-traverse
capability (calling `sulis-brain-query --open|--roadmap|--done`) and the
analyst recommendation. The characterisation test
(`test_route_inventory.test_existing_dispatch_routes_preserved`) proves every
existing `dispatch_via` row and `artifact_owners` mapping is unchanged.

The two test files contain only assertions over small in-memory fixtures and a
read of the real `sulis.md`. No production logic, no I/O in loops, no external
calls.

### Findings in the Neighbours

None. The neighbour ring (`_route_inventory.py`, `_route_frontmatter.py`, the
route gate, `opportunity-analyst.md`) is unchanged and continues to pass its
existing tests; the new `routes_to` slug resolves to the existing
`opportunity-analyst` agent so the no-orphan gate stays green.

### Watch List

None.

### Cross-Reference

- No prior `.security/{project}/viability-report-*.md` for this change relevant to this diff.
- No existing hardening deltas duplicated.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` on both changed Python files (clean); full pytest suite (1801 passed / 9 skipped); route+gate+wiring subset (29 passed). Markdown body validated by methodology + live-tree gate tests. Coverage gap: no mypy/pyright configured (ruff is the project linter) — recorded, not skipped.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size: 3 files (≤5). 289 lines is above the 200-line line-count threshold, but the content is one Markdown agent body + two pure test files with no production logic or control-flow branching; full end-to-end read was tractable for a single reader. Recorded per CR-02.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (sulis.md routing block + new body section; both test files in full).
- [✓] **CR-04 Evidence discipline.** Zero findings; nothing to evidence. Build-verification commands + outputs captured in tool-outputs/.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; no unread >50-line files; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (additive routing prose + pure tests; no domain→infra imports, no singletons, no circular imports). Security: nothing surfaced (no secrets, no external calls, no injection/auth surface; no exec/eval/subprocess introduced — scan logged). Quality: nothing surfaced (CR-10 perf scan — no anti-pattern matches, loops iterate tiny in-memory fixtures; test-coverage observation — EP-07 characterisation + 3 wiring tests present; no dead surface; no contract drift).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single refactor concern). PH-02 Size: low (289 additive lines / 3 files). PH-03 Safety: clean (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: clean (ships its own tests). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff origin/change/create-brain-backlog-and-traversal` (working tree, intent-to-add for the new untracked test file).
- **Neighbour expansion:** git grep over routing-spine modules; the import graph for `_route_inventory` / `_route_frontmatter` is small and fully covered by the existing route test suite.
- **Neighbour cap:** not reached (well under 20 files).
- **Scanners run:** ruff (lint), pytest (full suite). Gitleaks/Semgrep/Trivy not run — no executable production code, dependency, or infra surface in the diff; manual secret/external-call grep on the diff returned clean.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (3 files, no production logic).
