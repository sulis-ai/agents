# Code Review: WP-006 — Adopt detect-secrets for the outbound secret-scrub

> **Timestamp:** 2026-06-13T105111Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-006)
> **Branch:** feat/wp-006-outbound-scrub-adopt-detect-secrets → change/harden-agent-execution-boundary
> **Files changed:** 6 (3 modified, 3 added)
>
> **Outcome:** Ready to merge

---

## At a glance

This change strengthens the safety net that stops the agent from accidentally
sending a secret (an API key, password, or token) out to the open web. It keeps
the existing in-house checks and adds an established, widely-used secret
detector on top, so it now catches common provider key formats it used to miss.
Nothing serious surfaced. One small efficiency improvement was found and fixed
during review (the detector was rebuilding its rule set on every check; it now
builds once). The change leaves the unrelated feedback-anonymiser untouched,
which is exactly the intent.

## What to fix

No issues that need attention. One efficiency finding was fixed inline during
this review (see below), so nothing is outstanding.

### Fixed during review — `plugins/sulis/scripts/_secret_patterns.py`

**What was happening:** The new detector rebuilt its full rule set every single
time it checked a piece of an outbound request. Since each web request gets
checked in several pieces (the address, each header, the body), that rebuild
happened many times per request.

**Why it mattered:** It was wasted work on the path that runs just before every
outbound fetch. Not a correctness problem and not slow enough to notice in
practice, but easy to avoid.

**What was done:** The rule set is now built once and reused. Measured result:
each check dropped from about 0.42 to 0.08 milliseconds — roughly five times
faster — with no behaviour change (all tests still pass).

## How this change is shaped

**Size — clean.** Small and single-purpose: ~140 lines of real logic in one
module, plus a generated lock file, a new test file, and two short decision
documents. Comfortably reviewable in one pass.

**Scope — clean.** One concern: widen the outbound secret-scrub. The feedback
anonymiser is deliberately left byte-for-byte unchanged, and the tests prove it.

**Safety — clean.** One new dependency (detect-secrets), pinned in the lock
file. No database migrations, no infrastructure changes, no secrets in the
diff.

**Completeness — clean.** Eleven new tests cover the new provider formats, the
benign cases that must keep working, and the multi-line body path.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, lens IDs) for engineers and
> downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the
one changed source file >50 lines was read end-to-end; all three lenses
produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01: `ruff check` clean; full regression suite 143 passed)
- **PR Hygiene:** 0 high, 0 medium (PH-01..04 all clean)
- **In the changes:** 1 finding (1 low — CR-10 repeated-invariant; fixed inline)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single finding was fixed inline, not deferred to a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 (fixed) | 0 | CR-10 #7 repeated invariant computation (plugin registry rebuilt per call) — fixed inline via module-level cache |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` on `_secret_patterns.py` +
`test_secret_patterns_outbound.py`: "All checks passed!". Full regression suite
(`test_secret_patterns_outbound`, `test_secret_patterns`, `test_safe_fetch_proxy`,
`test_anonymiser`, `test_anonymiser_characterisation`): 143 passed.

Note: there is no typechecker configured for this scripts package (no
mypy/pyright config); `ruff check` is the configured mechanical floor and it is
the gate CI runs. `ruff format` is NOT enforced repo-wide (existing committed
files do not satisfy it), so it was deliberately not run — applying it would
reshape pre-existing untouched catalogue code, out of WP scope (EP-07).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 source module + docs        → clean
  severity: low

Size (PH-02):
  lines_added: ~295 (146 of which are generated uv.lock), lines_removed: 35
  files_changed: 6 (1 source, 1 lock, 1 test, 2 docs, 1 WP)
  generated_ratio: ~0.5 (uv.lock)
  severity: low

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0 (fixtures are synthetic AWS-docs EXAMPLE literals + fake high-entropy strings)
  new_dependency: detect-secrets>=1.5 (pinned in uv.lock)
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (test_secret_patterns_outbound.py added)
  api_change_without_schema: false (find_secrets signature unchanged)
  severity: low
```

### Findings in the Changes

#### `plugins/sulis/scripts/_secret_patterns.py` — low (quality) — FIXED INLINE

**CR-10 pattern #7 — repeated invariant computation in a hot-ish path.**

**Original code:** `_find_detect_secrets` entered `with default_settings():` and
called `get_plugins()` on every invocation. The L1 proxy calls `find_secrets`
once per request part (method + url + each header + body), so the plugin
registry was rebuilt several times per fetch.

**Context (CR-03):** read the proxy's `_refuse_if_secret` — it iterates parts
and calls `find_secrets(part)` per part. Measured cost: 0.45ms/rebuild,
~0.42ms per `find_secrets` call. The scrub runs before DNS (network-bound), so
the absolute impact is negligible — hence `low`, not `medium`.

**Resolution:** added a module-level lazily-initialised cache
(`_detect_secrets_plugins()`) that builds the stateless plugin instances once
under `default_settings()` and reuses them. Re-measured: 0.08ms per call (~5x).
All 143 tests remain green; behaviour unchanged.

### Findings in the Neighbours

None. The proxy (`_safe_fetch/proxy.py`) is an unchanged caller of
`find_secrets` — signature and `SecretHit` return are identical, so no neighbour
adaptation is required. The anonymiser (`_anonymiser.py`) imports the raw
catalogue patterns (not `find_secrets`) and is byte-unchanged (not in the diff).

### Watch List

- **Detection is not exhaustive (by design, documented).** detect-secrets ∪
  catalogue widens the net materially but a novel secret shape neither
  recognises can still pass. ADR-006 records this; the Rule-of-Two credential
  exclusion (ADR-001) is the primary wall, this scrub is defence-in-depth. No
  action — recorded honest limit.
- **Fail-closed entropy false-positives.** A quoted/assigned high-entropy
  benign value in an outbound body (e.g. a quoted commit SHA) will now be
  refused. This is the accepted fail-closed cost per ADR-006; prose mentions
  stay clean. No action.

### Cross-Reference

- **ADR-006** (this change) records the decision and supersedes ADR-002 for the
  outbound-scrub policy only.
- No prior security viability report for this project; nothing to cite.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` (the configured + CI floor) on changed source: clean. Full regression suite: 143 passed. No typechecker configured (coverage gap noted in Build Verification); `ruff format` deliberately not run (not enforced; out of scope).
- [✓] **CR-02 Single-reader pass justified by diff size:** ~140 lines of real logic in 1 source module (the rest is generated uv.lock + docs + tests), well under the 200-line / 5-source-file carve-out.
- [✓] **CR-03 Full-file reads.** `_secret_patterns.py` (the one changed source file >50 lines) read end-to-end. Test file read in full. uv.lock is generated (not read line-by-line — generated artifact).
- [✓] **CR-04 Evidence discipline.** The single finding cites file + quoted mechanism + measured numbers.
- [✓] **CR-05 Severity rubric.** Applied. 1 low (fixed inline). No critical/high/medium.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; no unread >50-line file; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no domain→infra import, pure functions, no singletons beyond the intentional plugin cache). Security: nothing surfaced (in-process, no shell-out, no network, no secret-value logging, fail-closed widens detection). Quality: 1 finding (CR-10 #7, fixed) + test-coverage observation (11 new tests present) + no dead surface + no contract drift (find_secrets signature stable).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `feat` concern). PH-02 Size: low. PH-03 Safety: low (1 pinned dep, no migrations/secrets). PH-04 Completeness: low (tests present). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** working-tree diff vs `change/harden-agent-execution-boundary` (review run pre-commit, per Step 6.5 of the executor lifecycle; the same tree is committed at Step 7).
- **Neighbour expansion:** git grep for `find_secrets` consumers — only `_safe_fetch/proxy.py` (unchanged caller); `_anonymiser.py` uses raw patterns, not the function.
- **Neighbour cap:** not reached (2 candidate neighbours).
- **Scanners run:** ruff (lint); pytest (143 regression tests). Gitleaks/Semgrep/Trivy not available in env — fixtures manually verified as synthetic AWS-docs EXAMPLE literals + fake high-entropy strings (push-safe).
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02) justified by diff size.
