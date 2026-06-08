# Code Review: WP-015 — minter canonical save + human mirror

> **Timestamp:** 2026-06-03T192337Z
> **Author:** executor (WP-015)
> **Branch:** feat/wp-015-minter-canonical-plus-mirror → change/feat-product-project-opportunity-evolution
> **Files changed:** 5 (4 modified + 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change reconciles where a Project's record lives: the brain store becomes the single source of truth, and the file in `.sulis/projects/` is kept as a human-readable copy. The build is clean, the change is well-scoped to one concern, and it ships with a thorough new test file. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 5 files, ~288 added lines — and most of that is the new test file plus expanded documentation comments. One logical concern (the Project home reconciliation).

**Scope — clean.** A single refactor: the Project-write function now saves to the canonical store first, then writes the human-readable copy. The three small test edits are consequences of the same change (the canonical store now validates the Project, which surfaced three test inputs that were never schema-valid).

**Safety — clean.** No database migrations, no schema/IDL files, no infrastructure changes, no secrets.

**Completeness — clean.** New behaviour ships with a new test file (10 tests) and the existing safety-pinning test still passes unchanged.

---

## Technical detail

> Internal taxonomy (CR-NN, PH-NN) below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all files read end-to-end (executor-authored); all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01: ruff check + pytest; no type-checker configured per plugin contract)
- **PR Hygiene:** 0 high findings (PH-01 scope low, PH-02 size low, PH-03 safety none, PH-04 completeness none)
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — canonical write routed through the EntityRepository port (correct dependency direction); reuses central_tenant_home + LocalFileEntityAdapter (ADR-005 reuse, not new persistence) |
| Security | 0 | 0 | none — no secrets/injection; degradation log interpolates only target_path; x-sensitive `source` carried opaque, not logged |
| Quality | 0 | 0 | none — branch_policy 'trunk-based' was *pre-existing* contract drift; this WP fixes it |

### Build Verification (CR-01)

Mechanical baseline: `ruff check` (exit 0) on all 4 changed Python files; full `pytest` suite green (2055 passed, 9 skipped). No type-checker is configured for this repo (branch-ci.yml: "none configured; stdlib-only tooling per plugin contract"). Coverage gap: type-checking — repo has no type-checker by design.

### Findings in the Changes

None.

### Findings in the Neighbours

None. Direct callers/callees inspected: `_discovery/__init__.py:run_discovery_headless` (the production call site, updated in this diff), `_entity_evolve.evolve_entity` (WP-009, reused unchanged), `_brain_emit_helper.central_tenant_home` (WP-013, reused unchanged), `_entity_adapter_local.LocalFileEntityAdapter` (reused unchanged). No gaps exposed.

### Watch List

- `_save_canonical` iterates `_canonical_projects(entity)` calling `evolve_entity` per Project. In the discover-project flow the composed bag holds exactly one Project per mint, so the loop is N=1 — not an N+1 query pattern (CR-10 pattern 1 checked, benign on context). If a future caller passes a many-Project bag, each iteration is still a distinct entity's persistence, not a query-in-loop over children.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` (exit 0) + `pytest` (2055 passed). Base + head both clean for the changed files. Coverage gap: no type-checker configured (by repo design).
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Carve-out justified: the diff is one logical concern authored by the executor in this session; 288 added lines are dominated by the new test file (~280 lines) + docstring expansion. Substantive logic delta in `minter.py` is ~60 lines, fully read end-to-end.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (executor authored every line this session).
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens scan logs in tool-outputs/.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency direction, reuse, graceful degradation, no untimed external call — local FS). Security: nothing surfaced (secrets, injection, eval/shell, sensitive logging all checked). Quality: nothing surfaced (CR-10 perf no anti-pattern matches; test coverage comprehensive; no dead surface; contract-drift on branch_policy is FIXED by this WP).
- [✓] **CR-09 PR Hygiene applied.** PH-01 scope: low (single refactor). PH-02 size: low (5 files / 288 add). PH-03 safety: none (0 migrations/schemas/secrets/infra). PH-04 completeness: none (new tests shipped). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** working tree vs change/feat-product-project-opportunity-evolution
- **Neighbour expansion:** git grep on touched symbols (write_project_entity, evolve_entity, central_tenant_home, LocalFileEntityAdapter)
- **Scanners run:** ruff (lint), grep-based secret/injection/perf signatures
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed — grep signatures used as floor; no secret patterns in diff
- **Lenses dispatched in parallel:** no (single-reader carve-out)
