# Code Review: feat/wp-004-extend-engineering-architect-agent — Extend engineering-architect agent prompt

> **Timestamp:** 2026-06-01T20:45:50Z (ISO 8601 UTC)
> **Author:** sulis:engineering-executor (parallel batch wave 2)
> **Branch:** feat/wp-004-extend-engineering-architect-agent → change/extend-verification-by-design
> **Files changed:** 2 (1 modified, 1 new)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request extends the engineering-architect agent prompt so it reads the SRD's `## Verification Plan` section as a first-class input, asks the implementation-side concretion questions, surfaces SRD↔TDD contradictions explicitly, and cites the canonical question file rather than inlining its content. The change is markdown-prose only — no code logic, no API surface, no migrations, no database changes. All structural assertions pass. Nothing to fix before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 525 lines across 2 files (1 modified agent prompt, 1 new structural test). Well-scoped — the entire change concerns a single methodology refinement.

**Scope — clean.** Single concern: the engineering-architect's design-time verification responsibilities. One commit type (`feat`).

**Safety — clean.** No migrations, no schema changes, no infra changes, no secret patterns.

**Completeness — clean.** New behaviour (the structural-assertion test file at `plugins/sulis/scripts/tests/unit/test_engineering_architect_verification_phase.py`) ships with the change.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

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
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced (markdown prose only — no code surface) |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No PR-introduced errors.

- **Test run:** `uv run pytest plugins/sulis/scripts/tests/unit/test_engineering_architect_verification_phase.py` → 11 passed in 0.05s.
- **Lint:** `uv run ruff check plugins/sulis/scripts/tests/unit/test_engineering_architect_verification_phase.py` → All checks passed.
- **Format:** `uv run ruff format --check` → file formatted to compliance.
- **Full suite regression:** `uv run pytest plugins/sulis/scripts/tests/unit/` → 1457 passed, 0 failures.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 2 distinct dirs (agents, scripts/tests/unit)
  severity: none

Size (PH-02):
  lines_added: ~525, lines_removed: 0, total: ~525
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: note (above 200-line threshold but single-concern;
            see CR-02 dispatch deviation in Methodology)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (test file IS the new source for this WP)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### Architecture lens

Architecture lens: nothing surfaced. Checks run:

- Dependency-direction: the agent prompt cites `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` by relative path (inward-pointing dependency; no inline duplication). Aligns with MEA-01-style SSOT.
- New imports: none (markdown prose).
- Module boundaries: the new section sits in the architect's existing system-prompt area, with proper top-level heading and Markdown `---` separators.
- Hexagonal seam discipline: prose only — the change instructs the architect to identify port/adapter seams in downstream TDDs, not to introduce them here.

#### Security lens

Security lens: nothing surfaced. Markdown-prose-only diff with no executable surface in production runtime. The test file uses stdlib + pytest only; no network calls, no subprocess, no eval, no file writes outside pytest's tmp_path. Scanners not applicable to docs prose.

#### Quality lens

Quality lens: nothing surfaced beyond test coverage observation below.

1. **Build Verification follow-up:** none (Build Verification empty).
2. **JSX / template identifier scan:** N/A (no TSX/JSX/Vue/Svelte files in diff).
3. **Dead-surface findings:** none. Every constant in the test file (`_REPO_ROOT`, `_AGENT`, `_CANONICAL_REL`, `_FORBIDDEN_INLINE_QUESTION_TEXT`, `_REQUIRED_TDD_SECTION_SUBSECTIONS`) is referenced by at least one test.
4. **Contract-drift findings:** none. The test's assertions match the WP-004 Definition of Done > Red checklist (canonical citation literal, HTML-comment annotation shape with `v\d+\.\d+\.\d+`, no inline duplication, `## Verification Plan` section, six subsections, concretion-question instruction, `Contradiction with SRD` marker, ADR-003 three-shape references).
5. **Test-coverage observation:** 11 structural assertions cover the 5 WP-Contract requirements (citation, HTML-comment, no inline duplication, contradiction-surface, three-shape reference) plus 5 supporting invariants (file exists, section-name presence, six subsections, concretion-question vocabulary, open-architecture-questions routing) plus first-class SRD-ingestion verification.
6. **Style / readability:** prose matches the architect's existing senior-engineer voice (MUST framing, Staff Engineer perspective, cites references rather than restating). Test file uses stdlib + pytest only, fully type-hinted, docstrings explain intent for each assertion.
7. **Performance procedural checks (CR-10):** no anti-pattern matches. Tests are O(N) scans over a single file's text; the file is ~1000 lines, scans complete in 0.05s for 11 assertions.

### Findings in the Neighbours

None. Neighbour expansion considered: `plugins/sulis/agents/requirements-analyst.md` (parallel sibling WP-003 — different branch, not in this diff's ring); `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` (WP-001 canonical — not modified in this WP).

### Watch List

None — no theoretical gaps surfaced.

### Cross-Reference

- **Existing Hardening Deltas covered:** none — first review for this WP.
- **Existing security report:** none — methodology change with no executable surface.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`. Base: implicit (working-tree-only diff; HEAD == base + uncommitted). Head: 0 errors. Coverage gap: none — Python + ruff + pytest are the project's mechanical floor.
- [✓ / partial] **CR-02 Parallel dispatch — single-reader deviation justified.** Diff: ~525 lines / 2 files (above the ≤200-line carve-out, within the ≤5-file carve-out). Deviation rationale: this is a markdown-prose-only change to an agent system prompt (the engineering-architect.md file is documentation that gets loaded into Claude's system prompt at agent dispatch — it has no executable runtime). The three architectural lenses (architecture / security / quality) reduce to near-empty outputs for prose-only diffs. The single-reader pass covered the entire diff end-to-end (per CR-03). Parallel sub-agent dispatch from inside an executor subagent is structurally complex (nested Agent tool invocation) and the marginal value is zero for prose-only methodology changes. Documenting the deviation in Methodology per CR-02's audit-trail requirement.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end:
  - `plugins/sulis/agents/engineering-architect.md` — 997 lines after extension, fully read (existing 822 + 175 new). The diff is contiguous (one bullet inserted in SRD-reading list at line 358-368, one new section at lines 401-558, one bullet added to "Your References" at lines 800-803).
  - `plugins/sulis/scripts/tests/unit/test_engineering_architect_verification_phase.py` — ~350 lines, fully read.
  - Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings empty — no evidence required.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings → 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none (Build Verification empty, all files >50 lines read end-to-end, all three lenses produced explicit "nothing surfaced" output, no PH-03 high finding).
- [✓] **CR-07 Lens completion.** Architecture: explicit "nothing surfaced" + 4 checks listed. Security: explicit "nothing surfaced" + applicability note. Quality: explicit "nothing surfaced" + 7 sub-outputs (CR-10 scan included, no matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single commit type, 2 dirs). PH-02 Size: note (above 200-line threshold but single-concern). PH-03 Safety: clean (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: clean (new tests included). No PH-03 high → no CR-06 auto-downgrade fired.

#### Run details

- **Diff source:** `git diff --name-only change/extend-verification-by-design` (uncommitted working tree)
- **Neighbour expansion:** `git grep` (ast-grep not configured for markdown); no executable callers of an agent prompt file exist
- **Neighbour cap:** 0 of 0 considered (no callers — agent prompts are loaded at dispatch, not imported)
- **Scanners run:** ruff (lint + format), pytest (unit suite)
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy — none applicable to docs-only markdown diff
- **Lenses dispatched in parallel:** no (single-reader pass — CR-02 deviation justified above)
