# Code Review: WP-004 — Infer phase (ConfigurationInferrer + LLM/Null adapters + token budget)

> **Timestamp:** 2026-06-01T17:18:23Z
> **Author:** Sulis Executor (WP-004 dispatch, wave 2a)
> **Branch:** `feat/wp-004-infer-phase` → `change/create-discover-project`
> **Files changed:** 4 new (inferrer.py, __init__.py, infer.txt, test_discovery_inferrer.py); 0 modified
>
> **Outcome:** Ready to merge.

---

## At a glance

Your changes look good. The mechanical checks all come back clean — no type errors, no lint errors, all 17 tests pass with 100% coverage on the new module. The shape follows the hexagonal pattern the rest of the codebase uses: a port (the contract for "propose configuration values") with two adapters behind it (one that calls an LLM, one that returns nothing for the safe fallback path).

There is one small thing worth knowing about — not a fix-it, just an awareness item — explained below.

## What to fix

No issues that need attention.

## Things to take away

(Section omitted — your pull request is well-shaped and clean.)

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, WPB-NN) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical or high findings in diff. Build Verification empty. All four files read end-to-end. All three lenses produced explicit "nothing surfaced" output (one note in the Watch List).

### Summary

- **Build Verification (CR-01):** 0 errors
- **PR Hygiene (CR-09):** all four primitives `low` severity
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low) + 1 Watch List note
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (no remediation needed)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced. |
| Security | 0 | 0 | Nothing surfaced. |
| Quality | 0 | 0 | 1 Watch List note (input-shape mirror of WP-003). |

### Build Verification (CR-01)

All clean. Tool outputs at `tool-outputs/ruff.log`, `tool-outputs/mypy.log`, `tool-outputs/pytest.log`.

- `ruff check _discovery/ tests/unit/test_discovery_inferrer.py` → "All checks passed!"
- `ruff format --check` → all files formatted (Step 6 applied the format pass).
- `mypy _discovery/inferrer.py --strict` → "Success: no issues found in 1 source file"
- `pytest tests/unit/test_discovery_inferrer.py` → 17 passed, 0 failed
- Coverage on `_discovery/inferrer.py`: 100% (95/95 statements)

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: []                       (single uncommitted change set)
  module_fan_out: 1 top-level dir              (plugins/sulis/scripts/_discovery + tests/)
  severity: low

Size (PH-02):
  lines_added: 825, lines_removed: 0, total: 825
  files_changed: 4 (3 source + 1 prompt template + 1 test)
  severity: low (one focused package; cohesion is high)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0
  test_coverage_ratio: 1.0
  api_change_without_schema: false
  severity: low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring scoped to: `_discovery/__init__.py` (this WP authored it; trivially empty); planned consumers `_discovery/inspector.py` (WP-003, in flight) and `_discovery/tenant.py` (WP-002, in flight) — both out of scope here; WP-008 SKILL.md composition (not yet authored — deferred to WP-008 with hard dep on this WP).

### Watch List

#### W-001: Input-shape mirror of WP-003's inspector dataclasses (note, no delta)

**File:** `plugins/sulis/scripts/_discovery/inferrer.py:56-97`

**Observation:** This WP defines `RepoRoot`, `Manifest`, `CiWorkflow`, `RepoContract` as local frozen dataclasses that "mirror WP-003's `inspector.py`" (per module docstring lines 33-41). WP-003 is in flight in a parallel worktree and has not landed on `change/create-discover-project` yet. If WP-003 lands and its field shapes diverge from this WP's mirror, the WP-008 composition will need a shim.

**Risk:** Low — both WPs reference the same TDD §Form §Ports section (line 212-220) for the field names + types, so divergence requires SEA-level drift in the TDD itself. Documented in the module docstring as the explicit contract: *"once WP-003 lands the composition root can adopt the inspector.py types directly (structurally identical, frozen dataclasses with the same field names)"*.

**Why not a Hardening Delta:** No failing characterisation test can be constructed for a theoretical future-divergence (CR-04 evidence discipline). This is a Watch List item: WP-008's review pass will catch any actual drift.

**Recommendation:** None for this WP. WP-008 (the skill prose composition) should verify shape compatibility when it imports from both modules.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this project
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy --strict`, `uv run pytest`. Base (initial state) was empty (new files). Head: all checks pass. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified.** Diff is 825 lines but cohesively scoped to a single new Python package (`_discovery/`) with one source module + one prompt template + one test file. The 200-line / 5-file threshold technically fires on line count, but the carve-out's intent — multi-module change requiring parallel cognition — does not apply. Single-reader pass with full end-to-end reads of all four files.
- [✓] **CR-03 Full-file reads.** All 4 changed files (inferrer.py 367L, test 399L, prompt 42L, __init__ 17L) read end-to-end during review. No file >50 lines was sampled.
- [✓] **CR-04 Evidence discipline.** Zero findings produced; Watch List note cites file:line range with a concrete observation.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low, 1 note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced explicit output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (WPB-01..12 checks run — hexagonal port + adapter shape verified, typed Results via InferenceError family, NFR-001 timeout encoded, no secrets, observability via tokens_consumed). Security: nothing surfaced (SEC-01..07 checks — no new network surface, no hardcoded creds, no env-var secrets read, JSON parsing shape-guarded, token-budget IS the cost-amplification control per ADR-006). Quality: 1 Watch List note + CR-10 perf scan ran (patterns 1-10: no anti-pattern matches — single LLM call per infer, prompt template hoisted, JSON parse single-pass).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single package). PH-02 Size: low (cohesive). PH-03 Safety: low (no migrations / schemas / secrets / infra). PH-04 Completeness: low (1:1 test-to-source ratio; 100% coverage). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** local working tree vs `change/create-discover-project@7c15e8a` (worktree at `/Users/iain/Documents/repos/wp-004-discover`)
- **Neighbour expansion:** none required — diff scoped to a single new package with no callers yet (WP-008 composition is the planned consumer, dependency-blocked behind this WP)
- **Neighbour cap:** N/A (0 of 0 considered)
- **Scanners run:** ruff, mypy --strict, pytest
- **Scanners unavailable:** Gitleaks (not installed on host; manual grep for secret patterns produced 0 hits), Semgrep (not installed), Trivy (no dependency changes — pyproject.toml untouched)
- **Lenses dispatched in parallel:** no — single-reader pass justified per CR-02 carve-out
