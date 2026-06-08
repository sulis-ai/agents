# Code Review: feat/wp-016-lifecyclerun-for-project — wire for_project at change-start

> **Branch:** feat/wp-016-lifecyclerun-for-project → change/feat-product-project-opportunity-evolution
> **Files changed:** 3 source + 3 new test files + 1 doc (README)
>
> **Outcome:** Ready to merge

---

## At a glance

This change wires one optional field onto the record Sulis writes when a change starts:
which Project (release-unit / repo) the run operated in. It is small, well-scoped, and
fully tested — happy path, the "no Project found" graceful path, and the rejection of a
bad reference are all covered. No build errors, no security concerns, nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

Well-shaped. A single concern (the `for_project` wiring), 87 lines of source change across
three tightly-related files, and three new test files that cover every new path. No
database migrations, no schema changes, no infrastructure. Tests accompany the new
behaviour.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high findings in the changes; Build Verification empty; all
changed files read end-to-end; three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `compileall` + `ruff check` clean on BASE and HEAD.
- **PR Hygiene:** 0 high findings. Scope/Size/Safety/Completeness all low.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — graceful-degradation reader matches module contract |
| Security | 0 | 0 | none — bounded local-config read, ULID regex-validated |
| Quality | 0 | 0 | none — full test coverage incl. degradation paths |

### Build Verification (CR-01)

No PR-introduced errors. `python3 -m compileall` and `ruff check 0.15.14` both clean on the
three source files and three test files. No type-checker configured for this repo
(stdlib-only plugin contract; branch-ci.yml lint = manifest validity + compileall).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        single concern (for_project wiring)            → low
Size (PH-02):         +87/-2 source, 3 source files, 3 new tests     → low
Safety (PH-03):       migrations 0, schema 0, secrets 0, infra 0     → low
Completeness (PH-04): new_source_without_test 0 (3 test files added) → low
```

### Findings in the Changes

None.

#### Architecture lens

Nothing surfaced. The new `_resolve_project_ulid(repo_root)` reader follows the module's
documented graceful-degradation contract verbatim — it returns `None` on every failure
mode (no `.sulis/projects` dir, OSError on glob, malformed JSON, non-list `projects`,
non-dict entry, non-active status, invalid ref) and never raises, so a brain-emit
side-effect can never break the host `sulis-change start`. `for_project` is correctly a
plain `properties` scope ref (pattern-validated), NOT a `prov_constraints` edge — matching
ADR-007 §2 and the live `Workflow.for_project` precedent. No domain→infra import, no new
singleton, no circular import. Checks run: dependency-direction, resilience (no new
external calls), secrets, observability.

#### Security lens

Nothing surfaced. No secrets, no auth/authz surface, no injection vector. `json.loads` runs
against a fixed local config dir (`<repo_root>/.sulis/projects/*.jsonld`), not untrusted
network input; malformed input is caught and skipped. The resolved Project id is
regex-validated (`^dna:project:[0-9A-HJKMNP-TV-Z]{26}$`) before use. Primitives checked:
SEC-01..07 (none applicable), DAT-03 (no PII/token-shaped strings logged — a missing
Project is a quiet omission, not a log line).

#### Quality lens

1. **Build Verification follow-up:** none (clean baseline).
2. **JSX/template scan:** N/A (Python only).
3. **Dead surface:** none — every new param (`for_project` on compose/emit, `--for-project`
   on CLI) and the new `_resolve_project_ulid` are consumed.
4. **Contract drift:** none — the emitter's `_PROJECT_ID_RE` matches the vendored schema's
   `for_project` pattern, asserted by `test_for_project_shape_matches_workflow`. The
   field is emitted only when truthy, keeping `unevaluatedProperties:false` clean.
5. **Test-coverage:** strong. 22 new tests: compose (emit/omit/reject/shape-match),
   `_resolve_project_ulid` (resolve + 5 degradation branches), change-start emit
   (carries / omits), CLI (threads / absent-omits / bad-ref-rejected), schema (present,
   optional, pattern, no-prov-edge, v2.1-instance-valid). `_lifecyclerun_emission.py` at
   100% line coverage; new resolver >90% (only the glob-OSError branch unhit).
6. **Style:** clean.
7. **Performance (CR-10):** no anti-pattern. The nested loop in `_resolve_project_ulid`
   (`for bag` → `for project`) with a `bag.read_text()` is a bounded scan of a fixed
   config directory (typically 1 file / 1 project), runs once per change-start lifecycle
   event (not a per-request hot path), and returns on the first valid match. Benign.

### Findings in the Neighbours

None. Callers (`sulis-change cmd_start`, the CLI `main`) and callee
(`compose_lifecyclerun`) were inspected; the new optional param is additive and
back-compatible (all existing callers pass nothing → field omitted).

### Watch List

Empty.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `python3 -m compileall` + `ruff check 0.15.14` on BASE and HEAD. Base: 0 errors. Head: 0 new errors. No type-checker configured (stdlib-only plugin contract — recorded as the intended coverage gap, matching branch-ci.yml).
- [✓] **CR-02 Single-reader pass justified.** Source diff is 87 lines across 3 tightly-coupled files (one feature: for_project wiring); the 3 new test files are exercise-only. Cohesive single-concern change reviewed end-to-end by one reader.
- [✓] **CR-03 Full-file reads.** All changed source files read end-to-end via full `git diff`. No sampling.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens outputs cite the specific code paths examined.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (+ checks listed). Security: nothing surfaced (+ primitives listed). Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 low, PH-02 low, PH-03 low, PH-04 low. No auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-product-project-opportunity-evolution`
- **Neighbour expansion:** git grep — callers of `emit_change_started_event` (`sulis-change`), `compose_lifecyclerun`/`emit_lifecyclerun` (CLI + helper).
- **Scanners run:** compileall, ruff. (Gitleaks/Semgrep/Trivy not on PATH — coverage gap noted; diff has no secret patterns, no new deps, no Dockerfile.)
- **Lenses dispatched:** single-reader (CR-02 cohesive-change justification above).
