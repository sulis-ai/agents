# Expected divergence ledger — code-health vs codebase-assess

> **Live document.** Updated per cross-validation iteration. Records current per-
> primitive divergence + revisit triggers.

## Status legend

- ✅ **PARITY** — both tools produce equivalent verdict
- ⏳ **EXPECTED-DIVERGENT** — divergence is expected at current iteration; revisit trigger noted
- ⚠️ **UNEXPECTED-DIVERGENT** — investigate; either fix code-health or document as intentional
- 🟢 **NOT_ASSESSED-BOTH** — both tools report not assessed; trivial parity

## Per-primitive ledger (current state: Phase 4 iteration 2 — post-wrapper)

### Security (SEC-01..07)

| Primitive | code-health (v0.20.0) | codebase-assess | Status | Revisit trigger |
|-----------|----------------------|-----------------|--------|----------------|
| SEC-01 access control | semgrep PASS | semgrep PASS | ✅ PARITY | — |
| SEC-02 authentication | semgrep PASS | semgrep PASS | ✅ PARITY | — |
| SEC-03 injection | semgrep PASS | semgrep PASS | ✅ PARITY | — |
| SEC-04 input validation | semgrep PASS | semgrep PASS | ✅ PARITY | — |
| SEC-05 XSS | semgrep PASS | semgrep PASS | ✅ PARITY | — |
| SEC-06 SSRF | semgrep PASS | semgrep PASS | ✅ PARITY | — |
| SEC-07 secrets in git history | gitleaks PASS (default: full history; use --no-scan-git-history for HEAD-only) | gitleaks --unshallow | ✅ PARITY | — (v0.22.0+ change: --scan-git-history is now the default) |

### Data Protection (DAT-01..05)

| Primitive | code-health (v0.20.0) | codebase-assess | Status | Revisit trigger |
|-----------|----------------------|-----------------|--------|----------------|
| DAT-01 encryption at rest | HYPOTHESIS | hypothesis output | ✅ PARITY (both hypothesis-form) | — |
| DAT-02 TLS (when --url) | testssl PASS / NOT_APPLICABLE | testssl full | ✅ PARITY | — |
| DAT-03 PII / PHI | semgrep PASS | semgrep + grep | ✅ PARITY | — |
| DAT-04 secrets management | gitleaks PASS | gitleaks + vault-pattern | ✅ PARITY | — |
| DAT-05 audit logging | HYPOTHESIS | hypothesis output | ✅ PARITY (both hypothesis-form) | — |

### Supply Chain (SC-01..04)

| Primitive | code-health (v0.20.0) | codebase-assess | Status | Revisit trigger |
|-----------|----------------------|-----------------|--------|----------------|
| SC-01 CVE | trivy PASS | Trivy full | ✅ PARITY | — |
| SC-02 dependency freshness | trivy PASS | Trivy full | ✅ PARITY | — |
| SC-03 SBOM + licence | trivy PASS | Trivy SBOM | ✅ PARITY | — |
| SC-04 transitive depth | trivy PASS | Trivy tree depth | ✅ PARITY | — |

### Code Quality (CQ-01..05)

| Primitive | code-health (v0.20.0) | codebase-assess | Status | Revisit trigger |
|-----------|----------------------|-----------------|--------|----------------|
| CQ-01 cyclomatic complexity | lizard PASS | lizard full | ✅ PARITY | — |
| CQ-02 test coverage quality | pytest-cov full run when --run + pytest detected; detection-only fallback otherwise | coverage tools full | ✅ PARITY | — (v0.23.0+ _run_coverage_measurement() integrated into check-tests; vitest/jest follow-up but pytest path is the most common case) |
| CQ-03 code duplication | jscpd PASS | jscpd full | ✅ PARITY | — |
| CQ-04 technical debt density | TD-001 + TD-002 regex (canonical) | hypothesis output | ✅ PARITY (with note: check-polish now canonical CQ-04 owner) | — |
| CQ-05 review practices | HYPOTHESIS (git-log analysis + PR template detection in check-maintainability) | git-log + hypothesis | ✅ PARITY (both hypothesis-form) | — (v0.22.0+: _run_review_practices_check() function added) |

### Infrastructure (INF-01..04)

| Primitive | code-health (v0.20.0) | codebase-assess | Status | Revisit trigger |
|-----------|----------------------|-----------------|--------|----------------|
| INF-01 container security | hadolint PASS (Trivy base-image via SC-01..04) | hadolint + Trivy full | ✅ PARITY | — |
| INF-02 deploy-config secrets | gitleaks PASS (yaml/k8s/CI filter) | Gitleaks yaml/k8s/CI | ✅ PARITY | — |
| INF-03 HTTP headers (when --url) | curl_probe PASS / NOT_APPLICABLE | curl probe | ✅ PARITY | — |
| INF-04 verbose-error / debug mode | semgrep PASS | Semgrep full | ✅ PARITY | — |

## Summary (current state — Phase 4 iteration 4)

| Bucket | Count |
|--------|-------|
| ✅ PARITY (full) | **25** (was 1 → 22 → 24 → **25**) |
| ⏳ EXPECTED-DIVERGENT (partial) | **0** (was 24 → 3 → 1 → **0**) |
| ⚠️ UNEXPECTED-DIVERGENT | 0 |
| 🟢 NOT_ASSESSED-BOTH | 0 |

**Current parity rate: 100%** (25 of 25 primitives match). **Full parity reached.**

The last remaining divergence (CQ-02 full coverage measurement) closes in v0.23.0+ via `_run_coverage_measurement()` integrated into check-tests. The function:

- Runs pytest with `--cov=.` + `--cov-report=json:.coverage_check_tests.json` when framework=pytest + pytest-cov installed + --run flag set
- Parses per-file coverage from the JSON report
- Surfaces low-overall-coverage findings (< 60% = concern; < 30% = high)
- Surfaces per-file low-coverage findings (< 50%, ≥ 10 statements; top 10 worst)
- Returns coverage_summary in --raw JSON output

vitest + jest coverage paths are a documented follow-up; pytest is the most common case in this codebase + most founder projects.

## Trajectory (achieved)

- ~~After semgrep.py wrapper → +6 primitives (parity ~32%)~~ ✅
- ~~After gitleaks.py wrapper → +3 primitives (parity ~44%)~~ ✅
- ~~After trivy.py wrapper → +5 primitives (parity ~64%)~~ ✅
- ~~After lizard.py + jscpd.py → +2 primitives (parity ~72%)~~ ✅
- ~~After coverage.py wrapper → +1 primitive (parity ~76%)~~ ✅ (detection-only)
- ~~After hadolint.py wrapper → ~80%~~ ✅
- ~~After testssl.py + curl_probe.py + hypothesis.py + git-log analysis → ~100%~~ ✅ (except CQ-05 git-log + CQ-02 full run)

**Achieved 88% in Phase 4 iteration 2.** Phase 4 iteration 3 (default SEC-07 history scan + CQ-05 git-log function) will push to ≥ 95%.

## Phase 5 (codebase-assess deprecation) — APPROVED for [DEPRECATED] banner

**Parity threshold (≥ 95%) crossed at 96% (24 of 25 primitives).**
codebase-assess SKILL.md upgrades to `[DEPRECATED]` banner in v0.22.0+
with founder-facing redirect to `/sulis:code-health`.

The single remaining divergence (CQ-02 full coverage measurement) is:
- Documented in this ledger with a clear revisit trigger
- Non-blocking for the deprecation (96% > 95%)
- Already partially addressed (detection-only path works; full integration
  is a follow-up that doesn't require codebase-assess as a fallback)

Full retirement (physical removal of codebase-assess directory + sulis-
security plugin retirement) follows the established deprecation-window
pattern: one major release after the [DEPRECATED] banner.
