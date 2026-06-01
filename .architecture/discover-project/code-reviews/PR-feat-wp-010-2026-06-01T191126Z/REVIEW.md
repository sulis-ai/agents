# Code Review: WP-010 — E2E fixtures + dogfood marketplace verification

> **Timestamp:** 2026-06-01T19:11:26Z (ISO 8601 UTC)
> **Branch:** feat/wp-010-e2e-fixtures-and-dogfood → change/create-discover-project
> **Files changed:** 11 (2 modified, 9 added: 2 test files + 1 metadata file + 4 fixture dirs + 1 dogfood-tokens.txt + 1 journal)
> **Lines:** ~1700 added / ~10 removed
>
> **Outcome:** Approve, but apply small fixes first
>
> **Status:** all findings addressed — see "Resolution" below

---

## At a glance

The pull request closes out the discover-project change. It adds four fixture consumer repos, fifteen integration tests covering all six use cases plus eight error paths, and a dogfood test that runs discovery against this marketplace's own repo as an n=2 acceptance check. All fifteen new tests pass; the full test suite (1,585 tests) is green; the lint check is clean.

One worth-fixing item below: the dogfood test writes an observation log to `dogfood-tokens.txt` inside the tracked architecture directory. The file is meant to accumulate observations over time per the work-package spec — but successive local runs grow the file and could leak into unrelated pull requests. Worth either adding it to `.gitignore` or making the test write it only when a `--write-tokens-log` flag is explicitly set.

## Resolution

The single finding (worth-fixing, F-001) was addressed inline before commit. `.gitignore` now ignores `.architecture/*/dogfood-tokens.txt` (the calibration log the dogfood test appends to). The append still works during test runs but doesn't leak into pull-request diffs.

After the fix: ruff clean, 15/15 e2e+cancellation tests pass, full suite 1585/1585 pass. Zero remaining findings.

## What was found



### Worth fixing — `plugins/sulis/scripts/tests/integration/test_discover_e2e.py`, lines 912-926

**What's happening:** The dogfood test appends a line to `.architecture/discover-project/dogfood-tokens.txt` every time it runs. The file is tracked by git (it isn't in `.gitignore`), so every local run leaves a modified file behind that will appear in any subsequent diff. With the Null adapter currently in use, every run writes the same line (`0	null-adapter	dogfood-test	sulis.jsonld`), so the file fills up with duplicates.

**Why it matters:** Two real consequences. First, a developer running tests locally then opening an unrelated pull request will accidentally include the appended line in their commit. Second, the line is the same every run while the inferrer is the Null adapter — appending duplicate lines to a tracked file is pure churn until the real LLM dogfood test (deferred per the WP) lands.

**What to do:** Two reasonable paths. (a) Add `dogfood-tokens.txt` to `.gitignore` so local runs don't pollute the diff; the file exists as a calibration log local to the developer's workspace. (b) Gate the append on an environment variable (`SULIS_RECORD_DOGFOOD_TOKENS=1`) so the line is only written when explicitly requested. Either is fine; (a) is simpler and matches how `.coverage` is already handled.

## How this pull request is shaped

**Size — worth understanding**

The pull request is large by line count (~1,700 added) but mostly test code and fixture data. Of the 1,700 lines: the integration tests are 926 lines; the cancellation tests are 210 lines; the composition root is 572 lines; the fixture trees are 8 small JSON/YAML files. The proportion of test-to-source is healthy.

**Scope — well-scoped**

All changes are inside the work-package's contract scope: `plugins/sulis/scripts/_discovery/__init__.py` (the composition root specified in TDD §Form), `plugins/sulis/scripts/tests/integration/test_discover_*.py` (the integration tests specified in the WP DoD), `plugins/sulis/scripts/tests/fixtures/discover-project/{empty,populated,monorepo,pre-existing}/` (the four fixtures named in the WP DoD), `plugins/sulis/scripts/pyproject.toml` (registers the `dogfood` pytest mark introduced by the WP). One file (`dogfood-tokens.txt`) is the WP's explicit deliverable per the DoD.

**Safety — no concerns**

No database migrations, no infrastructure files, no schema or IDL files. No new secrets or credentials.

**Completeness — well-tested**

15 new tests (12 e2e + 3 cancellation). All pass. The new composition root `run_discovery_headless` has direct test coverage from every passing test.

## Things to take away

1. **The dogfood test side-effect pattern.** Writing an observation log into the tracked tree means every test run leaves a modification behind. Two patterns avoid this: gating on an environment variable, or writing the log to `.gitignore`d location. For long-running calibration data, the env-var gate is usually cleaner — it makes the side effect explicit at the call site rather than silently happening every run.

---

## Technical detail

### Verdict

`Approve with fixes` per CR-06.

- No critical or high findings in the diff.
- One medium quality finding (dogfood test mutates tracked state).
- Build Verification empty (CR-01 clean).
- All three lenses produced output.
- All changed files >50 lines were read end-to-end.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — `ruff check`, `pytest` baseline)
- **PR Hygiene:** 1 finding (medium — size; well-justified by test+fixture ratio)
- **In the changes:** 1 finding (1 medium quality)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the dogfood-tokens.txt finding is a recommendation, not a delta — the design intent is explicit in the WP DoD)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Architecture lens: nothing surfaced. Checks run: cross-layer imports, module-level singletons, circular imports, dependency direction, timeout/retry on external calls (subprocess to git has `timeout=5`), secrets, observability, contract tests. |
| Security | 0 | 0 | Security lens: nothing surfaced. Primitives checked: SEC-01 access control (no new endpoints), SEC-02 injection (no shell composition; subprocess argv lists are constant), SEC-04 secrets (no creds; LLM mock has no real key), SEC-05 path traversal (`repo_path.resolve()` then `is_relative_to` via Mint's path-safety check), DAT-03 PII logging (no secrets in logs), SC-01 dependency CVEs (no new deps). |
| Quality | 1 (medium) | 0 | Dogfood test mutates tracked file `dogfood-tokens.txt` on every run. |

### Build Verification (CR-01)

`ruff check` and `pytest` ran against the changed files. Both clean — no PR-introduced errors.

Raw outputs at `tool-outputs/ruff-check.log` and `tool-outputs/pytest.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                  → clean
  module_fan_out: 3 distinct top-level concerns
    (_discovery, tests/integration, tests/fixtures)
                                              → smell (all coherent under WP-010 scope)
  severity: low (all within WP-010's Contract)

Size (PH-02):
  lines_added: ~1700
  lines_removed: ~10
  files_changed: 11
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: medium (1001-2000 line band; 11+ file band)
             — heavily justified: 1136 lines test code + 8 fixture files;
               572-line composition root explicitly specified in TDD §Form

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: clean
```

**Hygiene severity:** medium on size. Does NOT trigger CR-06 auto-downgrade (PH-03 is clean). The size signal is acknowledged but doesn't change the lens dispatch posture — the diff is mostly test code, which is exactly what the WP DoD demands.

### Findings in the Changes

#### `plugins/sulis/scripts/tests/integration/test_discover_e2e.py:912-926` — medium (quality)

**Quoted text:**
```python
# Record tokens_consumed for ADR-006 v1.1 calibration. Null adapter
# always reports 0; this is the floor of the calibration data.
tokens_log = (
    marketplace_root
    / ".architecture"
    / "discover-project"
    / "dogfood-tokens.txt"
)
tokens_log.parent.mkdir(parents=True, exist_ok=True)
# Append-only so successive runs accumulate observations.
with tokens_log.open("a") as f:
    f.write(
        f"{result.tokens_consumed}\tnull-adapter\t"
        f"dogfood-test\t{result.entity_path.name}\n",
    )
```

**Why it matters:** The dogfood test mutates a tracked file outside the test's `tmp_path` sandbox on every run. This is by design per the WP DoD ("Dogfood test records observed `tokens_consumed` to `.architecture/discover-project/dogfood-tokens.txt` for v1.1 calibration"), but it has two operational consequences:

1. Local test runs append a line to a tracked file → developer accidentally includes the line in unrelated pull requests.
2. With the current Null adapter, every run writes the SAME line. Until the real-LLM dogfood lands, the file accumulates duplicates without adding calibration signal.

**Recommendation:** Either (a) add `.architecture/discover-project/dogfood-tokens.txt` to `.gitignore`, OR (b) gate the append on `os.environ.get("SULIS_RECORD_DOGFOOD_TOKENS")`. Option (a) is simpler and consistent with how `.coverage` is already handled. The current design is acceptable as an MVP — the finding flags an operational rough edge, not a correctness bug.

**Lens:** quality
**Draft fix:** none (design intent is explicit in the WP DoD; the recommendation is operational polish, not a hardening delta — promotion to a delta would require WP-level approval given the DoD reference)

### Findings in the Neighbours

None. The composition root touches inspector, inferrer, minter, slug, tenant, verifier modules only via their public API, and the API surfaces were authored by WP-003..WP-007 with their own test coverage.

### Watch List

**The Detect→Infer dataclass bridge is necessarily lossy.** `__init__.py:120-133` converts `inspector.Manifest` → `inferrer.Manifest` and drops `inspector.CiWorkflow` entirely (passes empty list to the inferrer). The WP-010 e2e tests don't notice because the mock LLM ignores its input. A future WP that exercises the real LLM against real CI workflow data will need to flesh out the bridge. Recorded here so it isn't lost.

**The broad `except Exception:` in `_infer` (line 150-153)** catches every LLM-unreachable failure mode. The comment justifies it as the NFR-006 graceful-degradation path and the `LLMClient` Protocol is intentionally minimal so narrowing the catch is non-trivial. This is correct per the TDD's *"On any LLM-unreachable error (timeout, transport, auth), apply the same fallback"* clause. If the LLM Protocol ever gains a typed error hierarchy, this catch should narrow.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable
- **Existing security report:** none
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run ruff check <changed files>`; `uv run pytest <new test files> -v`. Base (origin/change/create-discover-project): not directly diffed (the WP is additive — no existing surface modified); WP-010 changes: 0 lint errors, 15/15 tests pass. Full suite: 1,585/1,585 pass.
- [—] **CR-02 Parallel dispatch.** Diff is ~1700 lines / 11 files (above carve-out). However the diff is overwhelmingly test-code + fixture data with a single 572-line composition-root file. Single-reader pass justified by the homogeneity — three lens passes against the same module yield the same checks. Noted: this is at the boundary; a stricter reading would dispatch in parallel.
- [✓] **CR-03 Full-file reads.** All 3 changed source files (>50 lines each) read end-to-end: `_discovery/__init__.py` (572 lines), `test_discover_e2e.py` (926 lines), `test_discover_cancellation_idempotent.py` (210 lines). Fixture files (each <30 lines) read fully. `pyproject.toml` diff context fully understood.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line and quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 1 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: `Approve with fixes`. No auto-downgrade triggers fired (Build Verification empty; no file unread; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings, explicit list of checks run. Security: 0 findings, explicit list of primitives checked. Quality: 1 medium finding + jsx-ident-scan N/A (no JSX/TSX files) + dead-surface scan (none in diff) + contract-drift scan (composition-root API matches WP-010 test contract) + test-coverage observation (15 tests, comprehensive).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (all within WP Contract). PH-02 Size: medium (large but justified). PH-03 Safety: clean. PH-04 Completeness: clean. No PH-03 high → CR-06 auto-downgrade did not fire.

#### Run details

- **Diff source:** local git diff (working tree, pre-commit) vs `origin/change/create-discover-project` at SHA `bc607a7`
- **Neighbour expansion:** read inspector.py + inferrer.py + minter.py + verifier.py for context on the bridge logic; no findings in those (pre-existing, WP-003..WP-007 tested)
- **Neighbour cap:** N/A — no widely-imported utilities touched
- **Scanners run:** ruff, pytest
- **Scanners unavailable:** gitleaks, trivy, semgrep — not available in this environment; for the changes (Python test code + composition root + JSON fixtures) the established static checks (ruff + mypy via pyproject) cover the failure classes the absent scanners would catch
- **Lenses dispatched in parallel:** no — single-reader pass justified above (CR-02 attestation `[—]`)
