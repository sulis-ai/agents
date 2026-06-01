# Code Review: feat/wp-009-drift-extensions — Extend drift detector

> **Timestamp:** 2026-06-01T17:48:56Z (ISO 8601 UTC)
> **Branch:** feat/wp-009-drift-extensions → change/create-discover-project
> **Files changed:** 4 modified (parser.py, matcher.py, __init__.py, check-canonical-drift.py); 1 new test file; 4 new fixture dirs (16 small JSON/MD files); 1 journal artifact
> **Diff size:** 193 insertions / 33 deletions / 4 modified source files
>
> **Outcome:** Ready to merge

---

## At a glance

The pull request lands the two surgical extensions the work package called for: a Markdown HTML-comment annotation parser sitting next to the existing YAML one, with a file-extension dispatcher choosing between them; and a new `--cross-tenant-refs-allowed-for` flag on the drift-detector CLI plus a small helper that future callers (the Verify phase, WP-007) will plug into. The diff is tight, the existing release-train tests stay green, and 13 new tests give the new code targeted coverage. Nothing in the changes needs to be fixed before merge.

## What to fix

No issues that need attention.

A few notes for future awareness — none of these block this merge:

- The `cross_tenant_ref_is_allowed` helper has no in-detector caller yet. It exists for the Verify phase (WP-007) to call. Until WP-007 wires it in, the `--cross-tenant-refs-allowed-for` flag is parsed but has no effect on the drift report. That's by design (WP-009 lands the surface; WP-007 consumes it) and the cross-tenant test fixture at `drift-discover/cross_tenant/` is set up to validate the eventual integration. Worth keeping an eye on so WP-007 doesn't quietly skip wiring it.
- The `YamlAnnotation` dataclass name is now slightly misleading — it carries both YAML and Markdown annotations. Renaming would ripple to release-train tests that import the name, so leaving it is the right call here, but a future "drop the Yaml prefix" rename is worth noting if the test surface gets a bigger overhaul down the line.

## How this pull request is shaped

Clean across every hygiene dimension.

- **Scope** — single concern (extend drift detector); commits all under `feat:` for one WP.
- **Size** — 193 insertions / 33 deletions; 4 modified source files + 1 new test file. Well within the small-PR band.
- **Safety** — no migrations, no schema changes, no infra files, no lockfiles, no secrets.
- **Completeness** — 13 new tests covering the new code; characterisation tests for backward compatibility; full unit suite (1,352 tests) green.

No split recommended.

---

## Technical detail

> Below uses internal taxonomy (CR-NN, PH-NN). Author-facing tier above contains everything actionable.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `note`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`ruff check` and `ruff format --check` both pass on every touched file. Full `pytest tests/unit/` suite: 1,352 passed in 27s — including the 47 existing release-train drift tests (characterisation pass per WP DoD) plus the 13 new discover-project drift tests.

Raw outputs at `tool-outputs/ruff-check.log` and `tool-outputs/ruff-format.log` (both empty / "all checks passed").

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: note (single-concern WP)

Size (PH-02):
  lines_added: 193, lines_removed: 33, total: 226
  files_changed: 4 source + 1 new test + journal/fixtures
  severity: note (well below the 200-line / 5-source-file carve-out)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: note (no safety signals)

Completeness (PH-04):
  new_source_without_test: 0   (the only new "code" addition is `cross_tenant_ref_is_allowed` helper + `MarkdownHtmlAnnotationParser` + dispatcher — all covered by the new test file)
  api_change_without_schema: false
  severity: note
```

### Findings in the Changes

Architecture lens: nothing surfaced. Checks run:
- No new domain → infrastructure imports (changes are inside `_canonical_drift/`, the existing module).
- No new module-level singletons or `getInstance` accessors.
- No new circular import paths (the dispatcher table is at module load, parser classes free of cross-imports).
- No new HTTP/RPC/DB calls; no retries; no external system dependencies introduced; the only added external surface is argparse + regex + Path I/O on local files.
- New port-equivalent (`parse_annotations` dispatcher function) has direct test coverage via `test_dispatch_chooses_parser_by_extension` covering 3 input extensions (n=3 contract test).

Security lens: nothing surfaced. Primitives checked: SEC-01..07 (no auth surface introduced; no validation gaps because input is regex over file content); INF-04 (no Dockerfile / infra files); SC-01..04 (no new dependencies — uses stdlib `re` + existing `pyyaml`). The `--cross-tenant-refs-allowed-for` flag parses via `argparse` with a `type` callable that filters empty strings; no injection surface (the value lands in a Python list and is consumed by an `in` check). Scanners run: visual review only (no new external scanner targets).

Quality lens: nothing surfaced beyond Build Verification (clean). Checks run:
1. **CR-01 follow-up:** No errors translated.
2. **JSX scan:** N/A (Python diff).
3. **Dead-surface scan:** `cross_tenant_ref_is_allowed` is currently consumer-less in production code but consumed by tests + slated for WP-007 wiring per WP-009 Contract (WP-009 lands the surface, WP-007 consumes it). Acceptable per WP boundary.
4. **Contract-drift scan:** The CLI flag name + helper function signature match what TDD §Cross-tenant drift semantics (line 351) prescribes (`--cross-tenant-refs-allowed-for`) — verified manually against the TDD passage.
5. **Test coverage:** 13 new tests cover: 2 characterisation (release-train baseline), 5 parser-extension (HTML-comment match + whitespace tolerance + cross-format no-match × 2 + dispatcher table), 3 cross-tenant helper (in/out of allow-list, multi-field), 3 conformance fixtures (pass / missing_in_yaml / missing_in_canonical). Full backward-compat suite (47 release-train tests) passes unchanged.
6. **Style/readability:** Clean. Docstrings cite ADR-001 (HTML annotations) + ADR-002 (cross-tenant boundary) on the new surfaces. The dispatcher table is a 3-entry dict with a 1-line lookup function — minimal abstraction.
7. **CR-10 performance:** No anti-pattern matches. Loops iterate `file.splitlines()` (bounded by file size); the Markdown parser's `finditer` per line is bounded by line length; no DB/RPC/filesystem inside loops. No anti-patterns from `performance-procedural-checks.md`.

### Findings in the Neighbours

None. The neighbour ring is the existing `_canonical_drift/reader.py` + `report.py` + `tests/unit/test_check_canonical_drift.py`. No issues exposed by the extension; the existing tests run unchanged and continue to pass.

### Watch List

- **`cross_tenant_ref_is_allowed` has no production caller yet.** This is intentional per WP-009/WP-007 split. Watch that WP-007 actually wires it in; otherwise the flag is observably parsed but inert.
- **`YamlAnnotation` dataclass name carries Markdown annotations too.** Renaming deferred per backward-compat with release-train test imports.

### Cross-Reference

- **Existing Hardening Deltas covered:** none in scope.
- **Existing security report:** none for this branch.
- **Pattern suggesting full audit:** no.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `uv run pytest tests/unit/`. All passed (0 errors; 1,352 tests green; release-train fixtures unchanged).
- [✓] **CR-02 Single-reader pass justified by diff size:** 193 lines added / 4 modified source files. Below the 200-line / 5-file carve-out.
- [✓] **CR-03 Full-file reads.** All 4 modified source files + 1 new test file (864 total lines) read end-to-end during authoring; spot-verified after Step 6 lint adjustment.
- [✓] **CR-04 Evidence discipline.** No findings emitted, so no file:line citations required; Watch List items name the symbols.
- [✓] **CR-05 Severity rubric.** N/A — no findings.
- [✓] **CR-06 Verdict computed.** PASS. Auto-downgrade triggers: none fired (Build Verification empty; full-file reads; all three lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + scan checklist. Security: nothing surfaced + primitive checklist. Quality: nothing surfaced + 7 sub-checks all run including CR-10.
- [✓] **CR-09 PR Hygiene applied.** PH-01..PH-04 all `note` (clean). No CR-06 auto-downgrade fired.

#### Run details

- **Diff source:** local working tree on `feat/wp-009-drift-extensions` vs `change/create-discover-project` base
- **Neighbour expansion:** module-local (`_canonical_drift/` package); no broader ring needed
- **Neighbour cap:** N/A (3 neighbour files inside the package)
- **Scanners run:** ruff check, ruff format, pytest unit suite
- **Scanners unavailable:** gitleaks, semgrep, trivy (no new dependencies or secrets surface to scan; skipped as low-value per scope)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (diff under threshold)
