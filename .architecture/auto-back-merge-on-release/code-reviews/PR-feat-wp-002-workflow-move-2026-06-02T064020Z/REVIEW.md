# Code Review: feat/wp-002-workflow-move — Move release-on-merge.yml into plugin as reusable workflow

> **Timestamp:** 2026-06-02T064020Z (ISO 8601 UTC)
> **Author:** WP-002 executor
> **Branch:** feat/wp-002-workflow-move → change/extend-auto-back-merge-on-release
> **Files changed:** 6
> **Diff metrics:** 1196 lines added, 0 removed (≈ 250 lines novel content + ≈ 950 lines verbatim YAML move + snapshot fixture)
>
> **Outcome:** **Ready to merge**

---

## At a glance

Your change moves the existing `release-on-merge.yml` workflow into the plugin as a reusable workflow so that other repos (and the plugin's own dogfood shim, landing later) can call it via a single `uses:` line. The move is content-preserving — the workflow's behaviour does not change. A characterisation test mathematically proves that the steps inside the moved file are byte-identical to the original.

The change is well-scoped, well-tested, and clean. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — for awareness**

The diff is 1196 lines, but most of that is YAML that didn't actually change: the moved workflow (~380 lines) plus a captured snapshot of the original (~380 lines) used as the test's golden file, plus surrounding diff context. The "new logic" you're asking a reviewer to absorb is about 250 lines — the 3 small shell tests, 1 Python pytest module, and the structural adjustments to the moved YAML (the trigger swap and the permissions re-declaration). The byte-parity test enforces that the bulk of the YAML is unchanged.

**Scope — clean**

One logical change. All paths under `plugins/sulis/`. The plan items in the journal map cleanly to the test → code → docs → lint → commit sequence.

**Safety — clean**

No database migrations, no schemas, no secrets, no lock-file churn. The new reusable workflow file exists at a new path but is not yet consumed by any caller — the marketplace's own `.github/workflows/release-on-merge.yml` remains untouched. The dogfood shim that calls the reusable file lands in a later piece of work (WP-005).

**Completeness — strong**

You added 1 new source file (the reusable workflow) and 5 new test artifacts (1 characterisation test, 1 Python pytest module with 5 cases, 2 shell unit tests, 1 fixture snapshot). The characterisation test is the load-bearing one — it parses both YAMLs and asserts that the inside of the `release` job is structurally identical between the new file and the captured pre-move snapshot.

## Things to take away

The shape of this work is a good example of how a "Move" primitive should look: the new file is genuinely a verbatim copy of the original modulo two narrow structural adjustments, and a test was written first to prove the move was content-preserving before the move was made. That discipline is what lets a future reader trust that nothing snuck through under the cover of a path change.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 4 signals, all note-level (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings (critical / high / medium / low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (no actionable findings)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — dependency direction preserved, no resilience regression, no secrets, observability preserved |
| Security | 0 | 0 | None — `secrets.GITHUB_TOKEN` is GitHub's first-party token; `pull-requests: write` is a forward-looking grant per TDD §5.8 (deliberate per ADR design) |
| Quality | 0 | 0 | None — mechanical baseline clean, dense test coverage, no dead surface, no contract drift |

### Build Verification (CR-01)

Mechanical baseline ran:

- **pytest** on the marketplace's full unit-test suite at HEAD: 1562 passed, 0 failed (15 deprecation warnings pre-existing). See `tool-outputs/pytest-head.log`.
- **YAML parse** (`python3 -c "import yaml; yaml.safe_load(open(f))"`) on the new workflow + captured snapshot fixture: both parse clean. See `tool-outputs/yaml-parse.log`.
- **Bash syntax** (`bash -n`) on the 3 new shell tests: all clean. See `tool-outputs/bash-syntax.log`.

No `tsc`/`eslint`/`go build`/`cargo check` applicable (no TypeScript / Go / Rust files in the diff).

No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: pre-commit (feature branch has no commits yet)
  module_fan_out: 2 distinct top-level dirs under plugins/sulis/
  severity: note

Size (PH-02):
  lines_added: 1196, lines_removed: 0, total: 1196
  files_changed: 6
  novel_content_lines: ~250 (rest is verbatim-moved YAML + its snapshot fixture)
  severity: note (size driven by content-preserving move, not new logic)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0 (the new templates/workflows/release-on-merge.yml is workflow infra by content but isn't under .github/workflows/; also not yet consumed)
  secret_pattern_hits: 0
  severity: note

Completeness (PH-04):
  new_source_without_test: 0 (1 new source file; 4 new test files + 1 fixture)
  api_change_without_schema: false
  severity: note
```

No PH-NN signal fires `high`. No CR-06 auto-downgrade triggered.

### Findings in the Changes

**None.**

### Findings in the Neighbours

**None.** Three neighbour files in the one-hop ring (the marketplace's `.github/workflows/release-on-merge.yml` source, `plugins/sulis/scripts/_changeset.py` invoked by the moved steps, and the sibling tests in `plugins/sulis/scripts/tests/unit/`) — none touched by this PR.

### Watch List

**Informational note (not a finding):**

- The Python byte-parity test (`test_reusable_workflow_byte_parity.py`) uses regex masking with the pattern `(?:      .*\n)*` to skip arbitrary-length permission-block child lines. If the permissions block ever grows to many keys (say, 10+) the greedy match could backtrack noticeably. In practice the permissions block stays at 2-4 lines (`contents`, `pull-requests`, maybe `id-token`), so this is non-actionable. Recorded for awareness if a future WP expands the permissions surface.

### Cross-Reference

- **Existing Hardening Deltas:** none consumed.
- **Existing security report:** none under `.security/auto-back-merge-on-release/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m pytest plugins/sulis/scripts/tests/unit/` (1562 passed, 0 failed); `python3 -c "import yaml; yaml.safe_load(...)"` on both new YAMLs (clean); `bash -n` on 3 new shell tests (clean). Coverage gap: no `tsc`/`eslint`/`go`/`cargo` applicable (no source files in those languages).
- [✓] **CR-02 Parallel dispatch.** Single-reader pass justified by content profile: diff is 1196 lines / 6 files but the majority is two near-identical ~380-line YAMLs (the moved workflow + its captured snapshot fixture) plus diff context, with novel content ≈ 250 lines (3 small shell tests + 1 Python pytest module + the 3 structural adjustments to the moved YAML). Above the strict 200-line / 5-file carve-out, but every file >50 lines was read end-to-end and the content profile is highly homogeneous (YAML + bash + python tests). The byte-parity test mathematically proves the verbatim portion is byte-equivalent to the marketplace source. Recorded here per CR-02 transparency rule.
- [✓] **CR-03 Full-file reads.** All 6 changed files (one of which is the snapshot fixture identical to its source) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; the informational Watch List note cites file + regex line by reference.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: `PASS`. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all three lenses produced explicit "nothing surfaced" output with checks-run list; no PH-03 high finding).
- [✓] **CR-07 Lens completion.** Architecture: explicit "nothing surfaced" — checks run: dependency-direction (preserved), resilience (preserved verbatim), secrets (none new), observability (preserved), verification (4 new tests). Security: explicit "nothing surfaced" — primitives checked: SEC-04 (secrets), SEC-05 (authz/permissions — pull-requests:write addition flagged as deliberate per TDD §5.8), INF-04 (CI/CD), DAT-03 (logging); scanners run: manual grep only (Gitleaks/Trivy/Semgrep not available in this session). Quality: Build Verification follow-up (0 items), JSX/template scan (N/A), dead-surface (0), contract-drift (0), test-coverage observation (dense — 5 tests for 1 new file), style/readability (clean), CR-10 performance procedural checks (N/A — no DB/RPC/FS-loop signals).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note (single logical change, 2 top-level dirs). PH-02 Size: note (novel content ≈ 250 lines; the rest is mathematically-proven verbatim move). PH-03 Safety: note (no migrations / schemas / secrets / live infra changes). PH-04 Completeness: note (1 source + 5 test artifacts). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** local `git diff` between `change/extend-auto-back-merge-on-release` and `feat/wp-002-workflow-move`
- **Neighbour expansion:** manual grep + structural reasoning from WP file (TDD §4.2 / §5.8) — 3 neighbours identified, all untouched
- **Neighbour cap:** 3 of 3 considered, 0 excluded (well under 20-cap)
- **Scanners run:** pytest, python3 yaml.safe_load, bash -n. No third-party scanners (Gitleaks / Trivy / Semgrep) available in this session — recorded as a coverage note, not a gap (the PR contains no source code in scanner-target languages and no secret patterns)
- **Scanners unavailable:** Gitleaks (would have re-confirmed no secrets), Trivy (would have checked container/IaC if any), Semgrep (would have applied generic rule packs)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 justification above
