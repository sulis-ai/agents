# Expected divergence ledger — code-health vs codebase-assess

> **Live document.** Updated per cross-validation run. Records current per-
> primitive divergence + revisit triggers.

## Status legend

- ✅ **PARITY** — both tools produce equivalent verdict
- ⏳ **EXPECTED-DIVERGENT** — divergence is expected at current iteration;
  revisit trigger noted
- ⚠️ **UNEXPECTED-DIVERGENT** — investigate; either fix code-health or
  document as intentional
- 🟢 **NOT_ASSESSED-BOTH** — both tools report not assessed; trivial parity

## Per-primitive ledger (current state: Phase 4 iteration 1 — pre-wrapper)

### Security (SEC-01..07)

| Primitive | code-health | codebase-assess | Status | Revisit trigger |
|-----------|-------------|-----------------|--------|----------------|
| SEC-01 access control | NOT_ASSESSED (semgrep NEW) | full Semgrep coverage | ⏳ EXPECTED-DIVERGENT | trigger \| semgrep.py wrapper integrated |
| SEC-02 authentication | NOT_ASSESSED (semgrep NEW) | full Semgrep coverage | ⏳ EXPECTED-DIVERGENT | trigger \| semgrep.py wrapper integrated |
| SEC-03 injection | regex partial (existing) | Semgrep full | ⏳ EXPECTED-DIVERGENT | trigger \| semgrep.py wrapper replaces regex |
| SEC-04 input validation | NOT_ASSESSED (semgrep NEW) | Semgrep full | ⏳ EXPECTED-DIVERGENT | trigger \| semgrep.py wrapper integrated |
| SEC-05 XSS | regex partial (existing) | Semgrep full | ⏳ EXPECTED-DIVERGENT | trigger \| semgrep.py wrapper replaces regex |
| SEC-06 SSRF | NOT_ASSESSED (semgrep NEW) | Semgrep full | ⏳ EXPECTED-DIVERGENT | trigger \| semgrep.py wrapper integrated |
| SEC-07 secrets in git history | HEAD-only regex (existing) | Gitleaks --unshallow | ⏳ EXPECTED-DIVERGENT | trigger \| gitleaks.py wrapper integrated |

### Data Protection (DAT-01..05)

| Primitive | code-health | codebase-assess | Status | Revisit trigger |
|-----------|-------------|-----------------|--------|----------------|
| DAT-01 encryption at rest | NOT_ASSESSED (hypothesis infra NEW) | hypothesis output | ⏳ EXPECTED-DIVERGENT | trigger \| hypothesis.py integrated |
| DAT-02 TLS (when --url) | NOT_ASSESSED (testssl NEW) | testssl.sh full | ⏳ EXPECTED-DIVERGENT | trigger \| testssl.py wrapper integrated |
| DAT-03 PII / PHI | NOT_ASSESSED (semgrep NEW) | Semgrep + grep full | ⏳ EXPECTED-DIVERGENT | trigger \| semgrep.py wrapper integrated |
| DAT-04 secrets management | HEAD-only regex (existing) | Gitleaks + vault-pattern | ⏳ EXPECTED-DIVERGENT | trigger \| gitleaks.py wrapper integrated |
| DAT-05 audit logging | NOT_ASSESSED (hypothesis infra NEW) | hypothesis output | ⏳ EXPECTED-DIVERGENT | trigger \| hypothesis.py integrated |

### Supply Chain (SC-01..04)

| Primitive | code-health | codebase-assess | Status | Revisit trigger |
|-----------|-------------|-----------------|--------|----------------|
| SC-01 CVE | NOT_ASSESSED (trivy NEW) | Trivy full | ⏳ EXPECTED-DIVERGENT | trigger \| trivy.py wrapper integrated |
| SC-02 dependency freshness | NOT_ASSESSED (trivy NEW) | Trivy full | ⏳ EXPECTED-DIVERGENT | trigger \| trivy.py wrapper integrated |
| SC-03 SBOM + licence | NOT_ASSESSED (trivy NEW) | Trivy SBOM | ⏳ EXPECTED-DIVERGENT | trigger \| trivy.py wrapper integrated |
| SC-04 transitive depth | NOT_ASSESSED (trivy NEW) | Trivy tree depth | ⏳ EXPECTED-DIVERGENT | trigger \| trivy.py wrapper integrated |

### Code Quality (CQ-01..05)

| Primitive | code-health | codebase-assess | Status | Revisit trigger |
|-----------|-------------|-----------------|--------|----------------|
| CQ-01 cyclomatic complexity | NOT_ASSESSED (lizard NEW) | lizard full | ⏳ EXPECTED-DIVERGENT | trigger \| lizard.py wrapper integrated |
| CQ-02 test coverage quality | NOT_ASSESSED (coverage NEW) | coverage tools | ⏳ EXPECTED-DIVERGENT | trigger \| coverage.py wrapper integrated |
| CQ-03 code duplication | NOT_ASSESSED (jscpd NEW) | jscpd full | ⏳ EXPECTED-DIVERGENT | trigger \| jscpd.py wrapper integrated |
| CQ-04 technical debt density | TD-001 + TD-002 regex (existing — canonical) | hypothesis output | ✅ PARITY (with note: check-polish now canonical CQ-04 owner) | — |
| CQ-05 review practices | NOT_ASSESSED (hypothesis infra NEW) | git-log + hypothesis | ⏳ EXPECTED-DIVERGENT | trigger \| hypothesis.py + git-log analysis integrated |

### Infrastructure (INF-01..04)

| Primitive | code-health | codebase-assess | Status | Revisit trigger |
|-----------|-------------|-----------------|--------|----------------|
| INF-01 container security | NOT_ASSESSED (hadolint + trivy NEW) | hadolint + Trivy full | ⏳ EXPECTED-DIVERGENT | trigger \| hadolint.py + trivy.py wrappers integrated |
| INF-02 deploy-config secrets | NOT_ASSESSED (gitleaks NEW) | Gitleaks yaml/k8s/CI | ⏳ EXPECTED-DIVERGENT | trigger \| gitleaks.py wrapper integrated |
| INF-03 HTTP headers (when --url) | NOT_ASSESSED (curl NEW) | curl probe | ⏳ EXPECTED-DIVERGENT | trigger \| curl_probe.py wrapper integrated |
| INF-04 verbose-error / debug mode | NOT_ASSESSED (semgrep NEW) | Semgrep full | ⏳ EXPECTED-DIVERGENT | trigger \| semgrep.py wrapper integrated |

## Summary (current state)

| Bucket | Count |
|--------|-------|
| ✅ PARITY (full) | 1 (CQ-04) |
| ⏳ EXPECTED-DIVERGENT (wrapper pending) | 24 |
| ⚠️ UNEXPECTED-DIVERGENT | 0 |
| 🟢 NOT_ASSESSED-BOTH | 0 |

**Current parity rate: 4%** — expected. The ≥ 95% target is post-wrapper-
integration (Phase 2 iteration 2+).

**Trajectory:**

- After semgrep.py wrapper → +6 primitives (SEC-01/03/04/05/06 + DAT-03 +
  INF-04) — parity ~32%
- After gitleaks.py wrapper → +3 primitives (SEC-07 + DAT-04 + INF-02) —
  parity ~44%
- After trivy.py wrapper → +5 primitives (SC-01..04 + INF-01) — parity
  ~64%
- After lizard.py + jscpd.py wrappers → +2 primitives — parity ~72%
- After coverage.py wrapper → +1 primitive — parity ~76%
- After hadolint.py wrapper → INF-01 fully done — parity ~80%
- After testssl.py + curl_probe.py wrappers + hypothesis.py + git-log
  analysis → +6 primitives — parity ~100%

(Each wrapper integration may reveal real bugs that drop parity; those
become UNEXPECTED-DIVERGENT entries that need iteration to resolve.)
