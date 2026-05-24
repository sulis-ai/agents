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
| SEC-07 secrets in git history | gitleaks PASS (default HEAD; --scan-git-history for full) | gitleaks --unshallow | ⏳ EXPECTED-DIVERGENT | trigger \| code-health invokes check-security with --scan-git-history by default |

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
| CQ-02 test coverage quality | coverage detection PASS (full run DEFERRED) | coverage tools full | ⏳ EXPECTED-DIVERGENT | trigger \| coverage.py full run integrated into check-tests runner |
| CQ-03 code duplication | jscpd PASS | jscpd full | ✅ PARITY | — |
| CQ-04 technical debt density | TD-001 + TD-002 regex (canonical) | hypothesis output | ✅ PARITY (with note: check-polish now canonical CQ-04 owner) | — |
| CQ-05 review practices | NOT_ASSESSED (git-log analysis follow-up) | git-log + hypothesis | ⏳ EXPECTED-DIVERGENT | trigger \| git-log CQ-05 analysis function in check-maintainability |

### Infrastructure (INF-01..04)

| Primitive | code-health (v0.20.0) | codebase-assess | Status | Revisit trigger |
|-----------|----------------------|-----------------|--------|----------------|
| INF-01 container security | hadolint PASS (Trivy base-image via SC-01..04) | hadolint + Trivy full | ✅ PARITY | — |
| INF-02 deploy-config secrets | gitleaks PASS (yaml/k8s/CI filter) | Gitleaks yaml/k8s/CI | ✅ PARITY | — |
| INF-03 HTTP headers (when --url) | curl_probe PASS / NOT_APPLICABLE | curl probe | ✅ PARITY | — |
| INF-04 verbose-error / debug mode | semgrep PASS | Semgrep full | ✅ PARITY | — |

## Summary (current state — Phase 4 iteration 2)

| Bucket | Count |
|--------|-------|
| ✅ PARITY (full) | **22** (was 1) |
| ⏳ EXPECTED-DIVERGENT (wrapper-pending or partial) | **3** (was 24) |
| ⚠️ UNEXPECTED-DIVERGENT | 0 |
| 🟢 NOT_ASSESSED-BOTH | 0 |

**Current parity rate: 88%** (22 of 25 primitives match). Threshold for codebase-assess deprecation: ≥ 95%.

**Remaining divergence (3 primitives) — all EXPECTED:**

1. **SEC-07 default depth.** code-health invokes Gitleaks with `--no-git` (HEAD only) by default; full SEC-07 depth requires `--scan-git-history` flag. codebase-assess uses `--unshallow` by default. Closes by changing the default invocation in `code-health` orchestrator.
2. **CQ-02 detection-only.** code-health detects coverage tool presence; doesn't run the full suite to measure coverage. codebase-assess invokes coverage tools fully. Closes by wiring pytest-cov / vitest / jest into check-tests' existing runner.
3. **CQ-05 NOT_ASSESSED.** code-health doesn't yet have a git-log analysis function. codebase-assess uses git-log + hypothesis. Closes by adding `_run_review_practices_check()` to check-maintainability.

**Estimated work to reach ≥ 95% parity:** ~1-2 follow-up commits (default `--scan-git-history` + check-maintainability git-log helper). CQ-02 full integration is more involved but doesn't block 95% (drops parity to ~84% if all 3 close except CQ-02, so technically need CQ-02 too).

## Trajectory (achieved)

- ~~After semgrep.py wrapper → +6 primitives (parity ~32%)~~ ✅
- ~~After gitleaks.py wrapper → +3 primitives (parity ~44%)~~ ✅
- ~~After trivy.py wrapper → +5 primitives (parity ~64%)~~ ✅
- ~~After lizard.py + jscpd.py → +2 primitives (parity ~72%)~~ ✅
- ~~After coverage.py wrapper → +1 primitive (parity ~76%)~~ ✅ (detection-only)
- ~~After hadolint.py wrapper → ~80%~~ ✅
- ~~After testssl.py + curl_probe.py + hypothesis.py + git-log analysis → ~100%~~ ✅ (except CQ-05 git-log + CQ-02 full run)

**Achieved 88% in Phase 4 iteration 2.** Phase 4 iteration 3 (default SEC-07 history scan + CQ-05 git-log function) will push to ≥ 95%.

## Phase 5 (codebase-assess deprecation) — re-evaluation

Current state warrants **soft-deprecation advance**: codebase-assess SKILL.md upgrades MIGRATION NOTICE to "RECOMMENDED FOR DEPRECATION" with revisit trigger | parity ≥ 95% (~1-2 follow-up commits). Founders should be informed that check-* now covers 88% of codebase-assess's primitives; the 3 gaps are documented + tracked.

Full `[DEPRECATED]` banner still requires:
1. Parity ≥ 95% (need 1-2 more commits)
2. compare.py implementation against real targets (not just expected_divergence)
3. One run on a real platform-scale codebase (e.g., the platform repo) confirming no UNEXPECTED-DIVERGENT findings
