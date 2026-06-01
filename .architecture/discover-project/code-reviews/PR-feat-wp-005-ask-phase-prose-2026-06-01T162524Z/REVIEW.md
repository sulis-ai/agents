# Code Review: feat/wp-005-ask-phase-prose — WP-005 Author Ask-phase prose

> **Timestamp:** 2026-06-01T16:25:24Z (ISO 8601 UTC)
> **Author:** executor (sulis run-all, WP-005)
> **Branch:** feat/wp-005-ask-phase-prose → change/create-discover-project
> **Files changed:** 8 (585 lines added, 0 removed)
>
> **Outcome:** Ready to merge

---

## At a glance

Your change is in good shape. It adds three founder-facing prose
fragments plus three rendered examples for the discover-project skill's
Ask phase, and pins their structure with nine tests that all pass. No
build errors, no lint issues, well-scoped to a single concern.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — worth being aware of**

The change is 585 lines across 8 files. That's larger than the smallest
ideal pull request, but five of those files are short prose fragments
or rendered example transcripts (no executable code), and one is a
journal of how the work progressed. The actual code change is one
new test file. The size is the natural minimum for the deliverable —
splitting prose from its tests would create two pull requests that
neither stands alone.

**Scope — clean**

One purpose: author the Ask-phase prose for the discover-project skill.
Every file in the change serves that single purpose.

**Safety — clean**

No database migrations, no schema changes, no infrastructure files
touched, no secrets pattern matches.

**Completeness — clean**

The new prose files are pinned by structural tests (one test file
covering nine invariants — founder-English check, one-field-per-prompt
shape, no-confidence-displayed, etc.). Tests live next to the existing
release-train docs-prose test pattern.

---

## Technical detail

> Below this point the report uses internal taxonomy for engineers and
> for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 1 medium (PH-02 size band), 0 note (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (neighbour expansion: see Methodology)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (no runtime code in diff) |
| Security | 0 | 0 | — (no secrets, no auth surface, no new deps) |
| Quality | 0 | 0 | — (test pins prose contract; ruff clean) |

### Build Verification (CR-01)

Zero PR-introduced errors. Tooling output:

| Check | Result | Log |
|---|---|---|
| `ruff check tests/unit/test_discover_project_prompts.py` | All checks passed | `tool-outputs/ruff-check.log` |
| `ruff format --check tests/unit/test_discover_project_prompts.py` | 1 file already formatted | `tool-outputs/ruff-format.log` |
| `pytest tests/unit/test_discover_project_prompts.py` | 9 passed in 0.04s | `tool-outputs/pytest.log` |
| `pytest tests/unit/ ` (full unit suite) | 1322 passed in 40.70s | (Step 3 journal entry) |

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single Conventional-Commit type)
  module_fan_out: 3 top-level dirs             → expected for the artefact set:
                                                  .architecture/ (journal),
                                                  plugins/sulis/scripts/ (test),
                                                  plugins/sulis/skills/ (prose)
  severity: low

Size (PH-02):
  lines_added: 585, lines_removed: 0, total: 585
  files_changed: 8
  generated_ratio: 0.00
  lock_file_ratio: 0.00
  severity: medium  (501-1000 line band; 6-15 file band)
  mitigating: 5/8 files are prose/example text;
              1 of 8 is journal bookkeeping;
              1 of 8 is the contract test;
              no executable production code in the diff

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low  (no CR-06 auto-downgrade triggered)

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: low  (test file pins all new prose invariants)
```

### Findings in the Changes

None.

Lens-by-lens scan output:

**Architecture lens — nothing surfaced.** Checks run on the diff:

  * New HTTP/RPC/DB calls — none in diff (zero runtime code).
  * New domain → infrastructure imports — none.
  * New module-level singletons / `getInstance()` — none.
  * New circular import paths — none.
  * New cross-module reach-through into `internal/` — none.
  * New external calls without timeout — none (no external calls).
  * Hardcoded credentials/API keys/secrets — none (`secret_pattern_hits=0`).
  * New service-to-service calls over plain HTTP — none.
  * New handlers/operations missing OpenTelemetry spans — n/a (no handlers).
  * New ports without contract test — n/a (no new ports).

**Security lens — nothing surfaced.** Primitives checked: SEC-01..07
(access control, auth, injection, validation, XSS, SSRF, secrets
exposure), SC-01..04 (dependency CVEs), DAT-03 (PII in logs/traces),
INF-04. Specifically:

  * No authentication or authorization surface added.
  * No injection vector (the prose is read-only test fixtures; the test
    file uses `Path.read_text(encoding="utf-8")` on whitelisted paths
    resolved relative to `__file__` — no user input reaches a file
    operation).
  * No new dependencies introduced (test uses stdlib + pytest only).
  * No secrets, tokens, or credentials in any of the 8 files.
  * The Ask-phase prose explicitly **excludes** confidence values and
    token-counting surfaces from the founder-facing display — this is a
    positive privacy/least-information stance enforced by the test
    suite (`test_no_confidence_displayed`,
    `test_no_token_count_displayed_in_ask_prose`).

**Quality lens — nothing surfaced. All seven outputs produced:**

  1. Build Verification follow-up: none — CR-01 baseline was clean.
  2. JSX / template identifier scan: n/a — no `.tsx/.jsx/.vue/.svelte`
     files in the diff.
  3. Dead-surface findings: none. All imports
     (`from __future__`, `re`, `Path`, `pytest`) are referenced;
     both helpers (`_strip_annotation_lines`, `_assert_no_internal_ids`)
     are called from tests.
  4. Contract-drift findings: n/a — no DTO/enum/response-shape changes.
  5. Test-coverage observation: satisfied. The diff is prose + a test
     file that pins it. The prose IS the deliverable; the test IS the
     contract. Per the WP-011/WP-010 docs-prose pattern there is no
     additional production code under test.
  6. Style/readability: `ruff check` clean; `ruff format --check`
     clean; naming consistent with codebase conventions
     (`_PROMPTS_DIR`, `_CONFIRM`, `_INTERNAL_ID_REGEXES`); docstrings
     present on every test and helper.
  7. Performance procedural checks (CR-10): no anti-pattern matches.
     The test reads 6 text files end-to-end at module scope — N is
     fixed at 6, files are small (each <80 lines), no nested loops, no
     DB/RPC/FS calls in a loop. None of the 10 CR-10 patterns apply.

### Findings in the Neighbours

None. Neighbour expansion (CR-05) considered:

  * `plugins/sulis/scripts/tests/unit/test_release_train_readme_section.py`
    — the prior-art test file the new test mirrors. Reviewed; the same
    structural-assertion pattern (path resolution via `Path(__file__).resolve().parents[N]`,
    module-scope `pytest.fixture` use, structural greps on a markdown
    file) was followed. No drift introduced.
  * `plugins/sulis/instances/discover-project/` — the parallel WP-001
    deliverable (canonical entities). Not touched by this diff;
    explicitly out of scope per the parallel-batch dispatch contract.

No neighbour ring findings; nothing to downgrade.

### Watch List

None.

### Cross-Reference

  * **Existing Hardening Deltas covered:** none.
  * **Existing security report:** none for `discover-project` yet
    (change is in flight).
  * **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `pytest -q`. Base: not separately re-run because diff is additive-only (8 new files, 0 modifications) — every error observed is therefore PR-introduced. Head: 0 errors. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch.** Diff size 585 lines / 8 files breaches the 200-line carve-out threshold. Single-reader pass nevertheless justified because 6 of 8 files are prose/example markdown/text (no executable surface), 1 is bookkeeping journal, and 1 is a structural test file (252 lines). The "code surface" being reviewed is effectively one Python file; parallel lens dispatch would have produced three identical "nothing surfaced" reports against an empty target space. Recorded here per the standard's transparency rule.
- [✓] **CR-03 Full-file reads.** All 8 changed files read end-to-end (every file <300 lines; trivially in budget).
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens scan outputs cite the checks run rather than findings.
- [✓] **CR-05 Severity rubric.** No findings to score.
- [✓] **CR-06 Verdict computed.** Verdict: `PASS`. Auto-downgrade triggers: none fired. CR-01 Build Verification empty → no `Block` downgrade. All files read end-to-end → no `Request changes` downgrade. All three lenses produced output (not silence) → no `Request changes` downgrade. PH-03 `low` → no `Request changes` downgrade.
- [✓] **CR-07 Lens completion.** Architecture: explicit "nothing surfaced" + checks-run list. Security: explicit "nothing surfaced" + primitives-checked list. Quality: all 7 outputs produced (build-followup, jsx-scan n/a, dead-surface, contract-drift n/a, test-coverage, style, CR-10 performance).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: `low` (single Conventional-Commit type, expected fan-out). PH-02 Size: `medium` (501-1000 line band, mitigated by non-executable file ratio). PH-03 Safety: `low` (0 migrations, 0 schemas, 0 infra, 0 secrets). PH-04 Completeness: `low` (test file pins prose contract; no test-for-the-test needed). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

  * **Diff source:** `git diff --cached` against `change/create-discover-project` (staged uncommitted at review time per Step 6.5 contract; commit happens at Step 7).
  * **Neighbour expansion:** `git grep` on import strings + visual inspection of the prior-art docs-prose test file. No `ast-grep` used (overkill for this surface).
  * **Neighbour cap:** 2 of 2 considered, 0 excluded.
  * **Scanners run:** ruff (lint + format), pytest. No additional security scanners (gitleaks/semgrep/trivy) invoked because (a) no new dependencies introduced, (b) zero secret-shaped strings in diff, (c) the diff has no network or external-process surface.
  * **Scanners unavailable:** gitleaks, semgrep, trivy — not invoked given coverage-gap reasoning above. Recorded for transparency.
  * **Lenses dispatched in parallel:** no (single-reader carve-out justified above per CR-02 transparency).
