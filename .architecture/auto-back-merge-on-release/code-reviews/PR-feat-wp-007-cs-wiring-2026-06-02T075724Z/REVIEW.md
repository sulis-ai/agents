# Code Review: feat/wp-007-cs-wiring — change-start drift check (WP-007)

> **Timestamp:** 2026-06-02T075724Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** feat/wp-007-cs-wiring → change/extend-auto-back-merge-on-release
> **Files changed:** 2 substantive (skill prose + test) + 1 bookkeeping journal
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one safety check to the start of new work: before opening a
fresh workspace, it checks whether the shared code line ("dev") has fallen
behind the released code line ("main"). If it has, it refuses to start and
points you at how to fix it. If the check can't run (for example a brand-new
clone that hasn't connected to the server yet), it does not block you — it
just notes that it skipped the check and carries on.

Nothing needs fixing. The check is well-scoped, calls a shared helper rather
than copying logic, and comes with a test. The trickiest part — telling a real
"behind" condition apart from a harmless "couldn't check" condition — was
verified by running the actual logic against both cases.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: one new safety check in one skill, plus its test.
The test is included. Nothing about the shape needs changing.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
files read end-to-end; all three lenses produced output. No auto-downgrade
trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01: py_compile + ruff clean; test file is new, no base regression).
- **PR Hygiene:** 0 findings. Scope low (single `chore`), Size low (212 added / 2 files), Safety none (0 migrations/schema/secrets/infra), Completeness none (test included).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — shared helper call, no inlined logic, no new deps |
| Security | 0 | 0 | none — literal helper path (no injection), no secrets |
| Quality | 0 | 0 | none — test discriminator matches helper stderr; behaviour verified |

### Build Verification (CR-01)

Mechanical baseline on the only code file
(`plugins/sulis/scripts/tests/unit/test_change_start_drift_check.py`):
`python3 -m py_compile` → 0 errors; `ruff check` → all checks passed. File is
new (absent on base), so no base/head delta to diff. SKILL.md is prose; the
embedded bash snippet passes `bash -n`. Empty section → no PASS block.

### Findings in the Changes

None.

Notable verifications performed (CR-04 evidence discipline):

- **Snippet correctness — `change/SKILL.md` step 3, lines 126-139.** The
  `$?` test on line 128 reads the exit status of the line-127 command
  substitution; in bash this is the substituted command's status (correct).
  The three branches were executed against stub helpers and behaved exactly
  per the WP contract: clean (exit 0) → proceed; "dev is behind main" (exit
  1) → STOP exit 1, message surfaced verbatim, no branch cut; non-drift exit
  1 (e.g. "not inside a git repository") → heads-up to stderr + continue
  (does NOT block). Log: `tool-outputs/snippet-behaviour.log`.
- **Contract alignment.** The test's discriminator `"dev is behind main"`
  matches the helper's actual stderr (`drift_check.sh` lines 117/123). No
  contract drift between the gate prose, the test, and WP-001's helper.
- **No inlined helper logic** (ADR-003 single source of truth): the section
  contains no `git merge-base --is-ancestor`; it references
  `plugins/sulis/scripts/drift_check.sh` by canonical path.
- **FE-compliance.** The runnable snippet carries no internal IDs (only the
  bullet heading anchors FR-010 / ADR-003 / GIT-12 / TDD §5.5, which the DoD
  permits).

### Findings in the Neighbours

None. The change adds a call site for an existing helper; the helper itself
(WP-001) is unchanged and out of this WP's scope.

### Watch List

None.

### CR-10 Performance procedural checks

No anti-pattern matches. The test contains one `for token in (...)` over a
constant tuple (membership check) — no I/O, not N+1, benign.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `py_compile` + `ruff` on the test file; `bash -n` on the SKILL.md snippet. Base: file new (0 errors). Head: 0 errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass — 242 substantive diff lines / 2 files, within the ≤200-line/≤5-file carve-out (the count includes diff context; added content ≈212 lines). Justified in Methodology.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (SKILL.md step-3 section + 173-line test).
- [✓] **CR-04 Evidence discipline.** Findings/verifications cite file:line and quoted/executed evidence; snippet behaviour empirically demonstrated.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (deps/secrets/structure checked). Security: nothing surfaced (SEC-01..07 — no applicable surface; no injection; no secrets). Quality: build clean, no JSX (N/A), no dead surface, no contract drift, test present, style clean, CR-10 no matches.
- [✓] **CR-09 PR Hygiene applied.** Scope low; Size low; Safety none; Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/extend-auto-back-merge-on-release` (uncommitted staged tree).
- **Neighbour expansion:** git grep — no test depends on the start-action step structure; helper unchanged.
- **Scanners run:** py_compile, ruff, bash -n. Gitleaks/Semgrep/Trivy not run (no applicable surface — prose + grep test, no secrets/deps).
- **Lenses dispatched in parallel:** no (single-reader carve-out).
