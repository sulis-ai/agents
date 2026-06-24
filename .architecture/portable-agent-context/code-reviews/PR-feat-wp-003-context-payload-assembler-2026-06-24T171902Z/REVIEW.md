# Code Review: WP-003 — ContextPayloadAssembler (tiered, vendor-neutral, budget-enforcing)

> **Timestamp:** 2026-06-24T171902Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/create-portable-agent-context/wp-003-context-payload-assembler → change/create-portable-agent-context
> **Files changed:** 2 (both new)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new building block — the piece that assembles the rich,
provider-neutral context we hand a fresh agent on resume — plus a thorough
test for it. The build is clean (no type or lint errors), it is well-scoped
(one module + its test, nothing else touched), and every behaviour the task
asked for is covered by a test that genuinely exercises it.

One efficiency issue was found while reviewing and fixed on the spot: the
routine that trims a thread's history to fit a size budget was doing more
work than necessary on very large threads. It now does the same job in a
single pass, and the fix was checked to produce identical results.

## What to fix

No issues that need attention. The one efficiency finding was resolved during
the review.

## How this pull request is shaped

**Size — clean.** 603 new lines across 2 files (one source module, one test
file). Single concern.

**Scope — clean.** One feature (`feat`), one module. No refactor mixed in, no
migrations, no infrastructure changes.

**Safety — clean.** No database migrations, no schema/IDL changes, no
infrastructure files, no secrets.

**Completeness — clean.** New source file ships with its test file; 100% line
coverage on the new module.

## Things to take away

Nothing specific — the change is well-shaped and well-tested.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high/medium/low findings remain in the diff;
Build Verification empty; both files read end-to-end; all three lenses produced
output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01).
- **PR Hygiene:** 0 findings (PH-01..04 all clean).
- **In the changes:** 1 finding surfaced (quality / CR-10), **resolved inline**;
  0 remaining.
- **In the neighbours:** 0 findings (no production neighbours; the module is
  consumed later by WP-004 / WP-005 / WP-007 via the contract).
- **Draft fixes:** 0 (the single finding was fixed inline, not deferred).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — inward-only deps, no IO, separable summary fn |
| Security | 0 | 0 | none — no secrets/network/sinks |
| Quality | 1 (resolved) | 0 | O(N²) trim loop → fixed to O(N) |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD:
- `ruff check _session_manager/context_payload.py tests/unit/test_context_payload_assembler.py` → All checks passed.
- `ruff format --check` → both files already formatted.
- `mypy --follow-imports=silent _session_manager/context_payload.py` → Success: no issues.
- `python3 -m py_compile` (CI's lint gate) → OK.

Scope note: `mypy` is run with `--follow-imports=silent` scoped to the changed
module because the package's pre-existing `_session_manager/manager.py` carries
12 unrelated mypy errors (untouched by this WP — out of scope). The project's
CI lint gate is `py_compile` + `pytest`, both green.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):      commit_type_spread: {feat}; module_fan_out: 1 dir   → severity: none
Size (PH-02):       lines: +603 / -0; files: 2; generated_ratio: 0      → severity: low
Safety (PH-03):     migrations: 0; schemas: 0; infra: 0; secrets: 0     → severity: none
Completeness (PH-04): new_source: 1; new_tests: 1; without_test: 0      → severity: none
```

### Findings in the Changes

#### `_session_manager/context_payload.py` (summarise_memory trim loops) — medium (quality), RESOLVED INLINE

- **Lens:** quality (CR-10 pattern #4 — O(N²) over the same collection).
- **What:** the original trim used `while messages and _message_tokens(messages) > budget: messages.pop(0)`, re-joining and re-measuring the whole list on every drop — O(N²) for a pathologically large thread (the over-budget degrade path). Same shape on the journal trim loop.
- **Evidence:** lines ~150-159 (pre-fix).
- **Fix applied:** replaced both loops with `_keep_fitting_suffix`, a single backward pass maintaining a running character total (mirrors `estimate_tokens` exactly: summed body lengths + one separator space per adjacent body, floor-divided by 4). O(N).
- **Equivalence proof:** property test over 2000 random `(bodies, budget)` inputs confirms the running-total suffix start index equals the join-based reference. All 12 unit tests remain green; coverage 100%.

### Findings in the Neighbours

None. The only string match for the module name is `tests/unit/test_thread_store_contract.py` (a false match — it tests the WP-001 contract, not this module). No production code imports the assembler yet; it is consumed downstream by WP-004 (checkpoint regen reuses `summarise_memory`), WP-005 (the `thread_context` MCP tool shares the discovery pointer), and WP-007 (the resume drive).

### Watch List

None.

### Cross-Reference

- No prior `.security/portable-agent-context/` viability report to cite.
- No existing hardening deltas to dedupe against.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff + ruff-format + mypy (scoped) + py_compile on both changed files. Base: n/a (both files new). Head: 0 errors. Coverage gap: mypy package-wide blocked by pre-existing `manager.py` errors → scoped to the changed file with `--follow-imports=silent` (noted).
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Deviation note: diff is 603 lines (>200 threshold) but is exactly 2 tightly-coupled new files (one module + its test) forming a single logical concern with **no neighbour ring** (nothing imports the module yet). The carve-out's intent — bound reviewer load so nothing is skimmed — is met: both files were read end-to-end. Recorded here per CR-02.
- [✓] **CR-03 Full-file reads.** Both files (296 + 307 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file + line range + quoted shape + an equivalence proof.
- [✓] **CR-05 Severity rubric.** Applied. 1 medium (quality), resolved inline. 0 remaining.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks run: dependency direction, singletons, infra-into-domain imports, contract-test presence — the WP-001 contract test already covers the port; the assembler is a pure consumer). Security: nothing surfaced (primitives checked: SEC-01..07 access/injection/validation/secrets, SC-01..04 deps, DAT-03 logging — no secrets, no network, no exec sink, injected text is data; vendor-neutral key-leak guard is tested). Quality: 1 finding (CR-10 #4) + jsx-ident-scan n/a (no JSX) + dead-surface none + contract-drift none (builds on contract types verbatim) + test-coverage 100% on new module.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: low (603/2). PH-03 Safety: none. PH-04 Completeness: none. PH-03 high → auto-downgrade: did not fire.

#### Run details

- **Diff source:** local working-tree diff vs `change/create-portable-agent-context`.
- **Neighbour expansion:** `grep -rln` for `context_payload` / `ContextPayloadAssembler` across the scripts tree → no production neighbours.
- **Neighbour cap:** not reached (0 neighbours).
- **Scanners run:** ruff, mypy (scoped), py_compile, pytest+coverage. Equivalence property test for the perf fix.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not run (no network/secret/dependency surface in a pure stdlib value-assembler diff; manually reviewed for SEC/SC signals — none present).
- **Lenses dispatched in parallel:** no (single-reader per CR-02 deviation note above).
