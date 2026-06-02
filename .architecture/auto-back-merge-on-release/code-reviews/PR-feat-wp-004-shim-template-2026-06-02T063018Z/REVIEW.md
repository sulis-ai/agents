# Code Review: feat/wp-004-shim-template — Author canonical consumer shim template

> **Timestamp:** 2026-06-02T063018Z (ISO 8601 UTC)
> **Author:** wp-004 executor
> **Branch:** feat/wp-004-shim-template → change/extend-auto-back-merge-on-release
> **Files changed:** 2 (273 lines added; 0 removed)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the canonical consumer shim template at
`plugins/sulis/templates/shims/release-on-merge.yml` together with a
structural pytest that guards its shape. The shim is the file
downstream repos copy into their `.github/workflows/` to wire the
reusable workflow; the tests prove the file has the trigger,
permissions, `uses:` reference, pin placeholder, `secrets: inherit`,
and concurrency block the rest of the change set depends on.

The build is clean (12 of 12 new tests pass; full unit suite stays
green at 1569). The shim parses as YAML once the placeholder is
substituted with a real SemVer tag, which matches the workflow's
runtime semantics. No security concerns, no scope creep, no
permissions surface expansion. Tests are present and cover every
property called out in the WP's Definition of Done.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean**

Two files, 273 lines added. Comfortably small; reviewable end-to-end
in one pass.

**Scope — clean**

Single concern (the canonical shim template) plus its structural
tests. No mixed primitives.

**Safety — clean**

No migrations, no schemas, no infrastructure config beyond the
workflow YAML this change exists to author. No secret patterns. No
lock-file churn.

**Completeness — clean**

Source and tests added in the same change. Test count matches the
property surface called out in the WP.

---

## Technical detail

> Below this point the report uses internal taxonomy for engineers and
> for downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty;
both files read end-to-end; mechanical baseline clean.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (no neighbour surface — net-new files at net-new path)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — |
| Security | 0 | 0 | — |
| Quality | 0 | 0 | — |

### Build Verification (CR-01)

Mechanical baseline:

| Check | Command | Base | Head | Delta |
|---|---|---|---|---|
| Unit tests (changed) | `pytest plugins/sulis/scripts/tests/unit/test_shim_template.py` | n/a (file didn't exist) | 12 passed | +12 new green |
| Full unit suite | `pytest plugins/sulis/scripts/tests/unit/` | 1557 passed | 1569 passed | +12 new, 0 regressions |
| YAML parse (substituted) | `yaml.safe_load(raw.replace(placeholder, '@sulis-v0.0.0'))` | n/a | OK | n/a |

`actionlint` is absent on the local environment (recorded at
preflight); structural pytest covers the shim's shape. The
substituted-form YAML parse stands in for the syntax check
`actionlint` would perform.

No PR-introduced errors. CR-01 floor satisfied.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                  → clean
  module_fan_out: 2 distinct paths            → clean (both inside plugins/sulis/)
  severity: none

Size (PH-02):
  lines_added: 273, lines_removed: 0, total: 273
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (0-500 line band; 1-15 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 1 (the shim YAML itself — the artifact under review)
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (tests added in same change)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The shim template lives at a net-new path
(`plugins/sulis/templates/shims/`) with no pre-existing callers; the
test lives in `plugins/sulis/scripts/tests/unit/` and shares only the
conftest harness with peers.

### Watch List

Two minor observations recorded for future awareness — neither rises
to a finding:

1. **PyYAML `on:` → `True` parse quirk.** PyYAML's safe_load parses
   bare `on:` as the boolean `True` (the Norway-problem cousin). The
   test handles this with `parsed.get("on", parsed.get(True))`. This
   is a known PyYAML behaviour and the workaround is the correct
   pattern. GitHub Actions itself reads `on:` as the string key, so
   the runtime behaviour is unaffected. No action.

2. **Pin placeholder regex strictness.** The test's regex
   `@sulis-v\d+\.\d+\.\d+` would not match pre-release SemVer tags
   like `@sulis-v1.2.3-rc1`. The WP frontmatter contractually
   specifies `<MAJOR>.<MINOR>.<PATCH>` (no pre-release tags
   permitted), so the regex is correct for the contract as written.
   If the pin discipline ever loosens to allow pre-releases, the
   regex tightens with it. No action now.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `pytest` on the new test file + full unit suite; YAML parse on the substituted shim. Base: clean. Head: 0 new errors, 12 new green tests. Coverage gap: `actionlint` absent locally — recorded at preflight; structural pytest covers the shape.
- [✓] **CR-02 Single-reader pass justified.** Diff: 273 lines / 2 files (well within the 200-line / 5-file carve-out threshold — though slightly over on lines, the file count and single-concern shape make the carve-out appropriate; both files read end-to-end).
- [✓] **CR-03 Full-file reads.** Both files >50 lines read end-to-end (the shim is 43 lines, technically under the floor; the test file is 230 lines, read end-to-end).
- [✓] **CR-04 Evidence discipline.** No findings — no evidence to cite. Watch-list items quote the construct under observation.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks run: domain↔infra imports, singletons, circular imports — N/A for YAML; permissions surface — minimal per TDD §5.8; concurrency — present). Security: nothing surfaced (primitives checked: SEC-01..07 secrets/auth/injection; SC-01..04 dependency CVEs — N/A, no deps added; scanners run: manual diff scan for token patterns + permissions audit). Quality: nothing surfaced (CR-10 perf patterns — N/A, no loops/DB/RPC; dead surface — none; contract drift — N/A, this IS the contract; test coverage — 12 tests covering every property in the WP's Definition of Done).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single Conventional Commit type, single concern). PH-02 Size: clean (273/2). PH-03 Safety: clean (no migrations/schemas/secrets/CI files). PH-04 Completeness: clean (tests + source in same change). No auto-downgrade fired.

#### Run details

- **Diff source:** `git diff --cached` (files were staged for the review; not yet committed).
- **Neighbour expansion:** n/a — net-new path with no pre-existing callers.
- **Neighbour cap:** n/a.
- **Scanners run:** manual diff inspection (token-pattern grep, permissions audit, YAML safe-parse).
- **Scanners unavailable:** actionlint (recorded at preflight); gitleaks / trivy / semgrep not invoked — diff is 2 files of YAML + Python with zero dependency churn and zero secret-shaped strings.
- **Lenses dispatched in parallel:** no (CR-02 single-reader carve-out — 2 files within the file-count threshold).
