# Code Review: WP-005 — Executor exports autonomous `SULIS_ORIGIN` at commit time

> **Timestamp:** 2026-06-07T195635Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** feat/wp-005-executor-autonomous-origin → change/feat-live-origin-stamping
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small helper that the executor uses to label each commit
with where it came from (an autonomous run), then wires the executor's commit
step to use it. The helper reuses the existing labelling code rather than
writing its own, and it is careful to never block a commit if the run label
is missing. There are no build errors, the new behaviour is covered by tests
including the "what if the label is missing" case, and nothing risky was
introduced. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: one new helper function, its tests, and a
documentation update to the executor's commit step. New source and new tests
arrive together. Nothing about the shape raises a concern.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings
- **In the changes:** 0 findings
- **In the neighbours:** 1 note (downgraded; pre-existing, dropped from blocking)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (reuses existing constructors; no new infra import, no new port) |
| Security | 0 | 0 | — (no secrets; inherits #216 control-char boundary) |
| Quality | 0 | 1 (note) | Pre-existing E741 in `append_trailer_to_message` (untouched) |

### Build Verification (CR-01)

Project gate is `python3 -m compileall -q plugins/sulis/scripts` (no
ruff/typecheck configured in `branch-ci.yml`; the lint step is manifest JSON
validity + `py_compile`). HEAD: `compileall OK`. Base: `compileall OK`.

Supplementary `ruff check` on the changed Python surfaces one E741
(`Ambiguous variable name: l`) at `_origin_stamp.py:218` — present on **both**
base (`/tmp baseline` line 188) and HEAD. It is **pre-existing**, not
PR-introduced; it lives in `append_trailer_to_message`, which this change does
not touch. Build Verification is therefore empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top dir (plugins/sulis)    → clean
  severity: none
Size (PH-02):
  lines_added: 213 (72 to existing + 141 new test file), lines_removed: 0
  files_changed: 3
  severity: none (well within bands)
Safety (PH-03):
  migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0
  severity: none
Completeness (PH-04):
  new_source: 0 (helper added to existing module); new_tests: 1
  api_change_without_schema: false
  severity: none (new behaviour fully tested)
```

### Findings in the Changes

None.

### Findings in the Neighbours

#### `_origin_stamp.py:218` — low → dropped (CR-05 neighbour-drop)

`append_trailer_to_message` uses `l` as a comprehension variable (E741). This
predates the change and is untouched by it. Per CR-05, a `low` neighbour
finding is dropped. Reformatting the whole file to satisfy ruff is out of
scope (the project's CI lint gate is `py_compile`, not ruff; the baseline
ships unformatted-by-ruff-standards).

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none
- **Consumes #216 unchanged:** `autonomous_origin`, `format_trailer`,
  `parse_origin_env`, the `prepare-commit-msg` hook — no re-implementation
  (verified: the bare-body grammar test asserts equality with `format_trailer`'s
  output, not a hand-rolled string).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Project gate `compileall` green on HEAD and base. Supplementary `ruff check` delta: 0 PR-introduced (the lone E741 is pre-existing on both). Coverage gap: no typechecker configured for this repo (stdlib-only plugin contract; recorded, not skipped silently).
- [✓] **CR-02 Single-reader pass justified by diff size: 213 lines, 3 files.** 141 of the 213 lines are a new test file; substantive logic is 31 lines (one pure helper). Tightly-coupled, single-concern; below the 5-file threshold. Full diff + new test file read end-to-end.
- [✓] **CR-03 Full-file reads.** `_origin_stamp.py` diff hunk + the full new test file (141 lines) + the executor.md doc hunk read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single neighbour note cites file:line and quoted code.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low in changes; 1 dropped neighbour note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: new-infra-import, module singleton, circular import, new external call/timeout/CB, new port without contract test. Security: nothing surfaced — primitives checked SEC-01..07 (no auth/injection/validation surface — pure string builder), SC-01..04 (no new deps), DAT-03 (no new log lines carrying PII); manual grep for secrets/shell=True/eval/exec — none. Quality: build-verification follow-up (empty), no JSX (no frontend files), no dead surface, no contract drift, test-coverage observation (8 new tests incl. non-fatal degradation + hook round-trip), CR-10 performance — no anti-pattern matches (`autonomous_env` has no loops/queries/IO).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none ({feat}, 1 module). PH-02 Size: none (213 lines / 3 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (new behaviour fully tested). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff 3b25346...` (working tree; pre-commit review per Step 6.5)
- **Neighbour expansion:** git grep over `_origin_stamp` symbol callers; the helper's only production consumer is the executor commit step (documented in `agents/executor.md`)
- **Neighbour cap:** 1 of 1 considered (small module)
- **Scanners run:** compileall, ruff (manual grep for secret/shell/eval patterns)
- **Scanners unavailable:** gitleaks/semgrep/trivy not installed in worktree; manual pattern grep used as floor (no new deps, no secrets, no network — low residual risk)
- **Lenses dispatched in parallel:** no (single-reader pass per CR-02 carve-out)
