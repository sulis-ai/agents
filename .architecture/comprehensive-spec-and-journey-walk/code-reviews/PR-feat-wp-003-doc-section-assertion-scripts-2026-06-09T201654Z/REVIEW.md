# Code Review: PR feat/wp-003-doc-section-assertion-scripts — Document-section assertion scripts

> **Timestamp:** 2026-06-09T201654Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-003)
> **Branch:** feat/wp-003-doc-section-assertion-scripts → change/harden-comprehensive-spec-and-journey-walk
> **Files changed:** 7 (6 new source modules + 1 new test file)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds five small, single-purpose checking scripts plus one shared
helper that read a design document and confirm it is complete — every required
section present, the same sections across short and long versions, unfinished
sections clearly marked rather than silently dropped, performance targets
stated as real numbers, and no place where the document quietly skips a section
just because a change is "small". The code is clean: no build errors, no
security concerns, and a thorough test file covering both the pass and fail
path of every script. No issues that need attention.

## What to fix

No issues that need attention.

One thing worth being aware of (not a problem): the script that checks
performance targets are "measurable" uses a set of recognised patterns
(a number with a unit, a comparison like "under 5 ms", a percentage). It is
deliberately tolerant — it is meant to catch the obvious "fast and responsive"
adjective-only case, not to grade every possible phrasing. That is the right
trade-off for a guardrail, and the behaviour is documented in the script.

## How this pull request is shaped

**Size — clean.** 878 lines across 7 files, all new, all in one directory
(`plugins/sulis/scripts/`). Single concern: the document-completeness check
scripts.

**Scope — clean.** One purpose, one commit type (a new feature).

**Safety — clean.** No database migrations, no schema changes, no
infrastructure files, no secrets.

**Completeness — clean.** Six new source files, one new test file with 21 tests
covering every script's pass and fail path; 99% line coverage on the new code.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty;
every file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 1 note (no critical/high/medium/low)
- **In the neighbours:** 0 (leaf modules — no neighbour ring)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 (+1 note) | 0 | heuristic NFR regex (documented, by-design) |

### Build Verification (CR-01)

Mechanical baseline: `python3 -m py_compile` (the repo's CI lint floor) +
`ruff check` on all 7 new files. Base: clean. Head: clean — 0 PR-introduced
errors. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):      commit_type_spread {feat}; module_fan_out 1 dir   → none
Size (PH-02):       +878 lines / 7 files; generated 0; locks 0        → low
Safety (PH-03):     migrations 0; schema 0; infra 0; secrets 0        → none
Completeness (PH-04): new_source 6; new_tests 1; api_change false     → none
```

### Findings in the Changes

**Watch list (note, no delta):** `_assert_measurable_nfr.py` — the
`_MEASURABLE_RE` token recogniser is a heuristic (comparator+number, number+unit,
percent, multiplier). Probed against tricky inputs (bare year "2025", "section 4
of the spec") — does not false-positive; "fast and responsive" correctly fails.
By-design tolerance for a guardrail; documented in the module docstring. No
failing characterisation test to ground a delta (CR-04) → Watch List, not delta.

### Findings in the Neighbours

None. The six new modules are leaf inspectors: only the new test file imports
them (verified by `grep`). No production-code dependency (per the WP Context —
"pure document inspectors").

### Architecture lens

Nothing surfaced. Checks run: domain→infra import (none — stdlib only); module
singletons / getInstance (none); circular imports (none — leaf modules);
resilience primitives (N/A — no network/DB/RPC); errors-as-values (yes — exit
codes + human-readable stderr per BC-04). The shared parser `_doc_section_parse`
is the single source of header detection consumed by 4 of the 5 inspectors
(BC-05 one-way-to-do-each-thing satisfied).

### Security lens

Nothing surfaced. Primitives checked: SEC (injection, secrets, path) — the
scripts only `Path(...).read_text()` a caller-supplied doc path (read-only, no
write, no eval, no subprocess-with-input, no network). No secret patterns in the
diff. INF / DAT / SC: N/A (no Dockerfile, no logging of sensitive data, no new
dependencies — stdlib only).

### Quality lens

1. **Build Verification follow-up:** none (baseline clean).
2. **JSX/template identifier scan:** N/A (no TSX/JSX/Vue/Svelte files).
3. **Dead-surface:** none — every public function is exercised by the test
   suite; no unused imports (ruff clean).
4. **Contract-drift:** none — each script's exit-code contract (0/1/2) matches
   the WP Contract verbatim; verified by CLI smoke test.
5. **Test-coverage:** 21 tests cover the happy + fail path of all five scripts
   and the CLI error paths (exit 2); 99% line coverage on new files (every new
   file ≥97%, all clear the 90% bar).
6. **Style/readability:** clean; module docstrings cite the SC-/FR-/NFR- IDs
   each script verifies.
7. **Performance (CR-10):** no anti-pattern matches. The only loops iterate
   document lines / category lists in-memory; the gate scanner's look-ahead is
   bounded by `_BODY_WINDOW=3`. No I/O in loops, no N+1, no unbounded
   materialisation.

### Watch List

`_assert_measurable_nfr._MEASURABLE_RE` heuristic — see Findings in the Changes.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `py_compile` + `ruff check` on all 7 files. Base clean / Head clean. Coverage gap: none (no type-checker configured — stdlib-only plugin contract, matches repo CI).
- [✓] **CR-02 Dispatch shape.** Single-reader pass. 878 lines / 7 files is above the 200-line line, but all 7 are new leaf modules with no neighbour ring to dispatch lenses against; each file read end-to-end and probed with targeted property checks. Recorded as a justified deviation: no symbol callers/callees exist (verified by grep) so parallel sub-agent dispatch would read the same isolated files.
- [✓] **CR-03 Full-file reads.** All 7 files read end-to-end (authored this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file + quoted behaviour; the one note is grounded in an executed probe.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low, 1 note.
- [✓] **CR-06 Verdict computed.** `PASS`. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (+checks). Security: nothing surfaced (+primitives). Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 none / PH-02 low / PH-03 none / PH-04 none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** working tree vs change/harden-comprehensive-spec-and-journey-walk (untracked new files)
- **Neighbour expansion:** git grep — 0 importers beyond the test file
- **Neighbour cap:** not reached (0 neighbours)
- **Scanners run:** py_compile, ruff, grep secret-scan
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed — manual secret grep substituted (stdlib-only diff, low risk)
