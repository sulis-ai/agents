# Primitive Catalogue

The 25 primitives the `codebase-assess` skill evaluates. Each has an ID,
a check description, a pass condition, and the tool (or heuristic) that
covers it. Primitives marked **manual** require hypothesis formation rather
than tool output.

---

## Security (SEC)

| ID | Primitive | What to Check | Pass Condition | Tool |
|---|---|---|---|---|
| SEC-01 | Broken access control | Missing authorisation checks, IDOR (insecure direct object reference), privilege escalation paths | No high/critical access-control findings | Semgrep, code review |
| SEC-02 | Authentication failures | Weak password handling, missing MFA, insecure session management | No hardcoded credentials, session tokens properly managed | Semgrep, code review |
| SEC-03 | Injection attacks | SQL injection, command injection, OS injection via unsanitised input | No unsanitised user input in queries or system calls | Semgrep |
| SEC-04 | Input validation | Missing or insufficient validation of user-supplied data | All user input validated before processing | Semgrep |
| SEC-05 | XSS prevention | Missing output encoding, no CSP, unsanitised HTML rendering | No unescaped user content in HTML output | Semgrep |
| SEC-06 | SSRF prevention | Unvalidated internal resource requests, cloud metadata access | Server-side requests validated and restricted | Semgrep |
| SEC-07 | Sensitive data exposure | Hardcoded secrets, API keys, tokens in code or git history | No secrets in code or git history | Gitleaks |

---

## Data Protection (DAT)

| ID | Primitive | What to Check | Pass Condition | Tool |
|---|---|---|---|---|
| DAT-01 | Encryption at rest *(manual)* | Database encryption config, file storage encryption | Evidence of encryption for stored sensitive data | Code review (ORM/DB config) → hypothesis if not conclusive |
| DAT-02 | Encryption in transit | TLS version, cipher strength, certificate validity | TLS 1.2+, strong ciphers, valid certificate | testssl.sh (if URL provided) |
| DAT-03 | PII/PHI handling | Personal data in logs, unencrypted PII storage, data flow | PII identified and handled per GDPR/HIPAA | Grep + Semgrep rules |
| DAT-04 | Secrets management | Hardcoded vs vault-based secrets, env-var handling | No hardcoded secrets; vault or env-based management | Gitleaks, code review |
| DAT-05 | Audit logging *(manual)* | Logging of auth events, data access, admin actions | Sensitive operations logged with sufficient detail | Code review (logging framework usage) → hypothesis |

---

## Code Quality (CQ)

| ID | Primitive | What to Check | Pass Condition | Tool |
|---|---|---|---|---|
| CQ-01 | Cyclomatic complexity | Functions with high branching complexity | No functions with complexity > 15, median < 5 | lizard, or heuristic (function length / nesting depth) |
| CQ-02 | Test coverage | Presence and quality of test suites | Test files exist and cover critical paths | File analysis (test dir structure, count, framework signals) |
| CQ-03 | Code duplication | Repeated code blocks across the codebase | No large duplicated blocks (>20 lines) | jscpd, or heuristic |
| CQ-04 | Technical debt signals *(manual)* | TODO/FIXME/HACK comments, disabled tests, commented-out code | Low density of debt markers | Grep for debt markers → hypothesis |
| CQ-05 | Code review practices *(manual)* | PR/MR patterns, review coverage, direct-to-main commits | Evidence of peer review process | Git log analysis → hypothesis |

---

## Supply Chain (SC)

| ID | Primitive | What to Check | Pass Condition | Tool |
|---|---|---|---|---|
| SC-01 | Known vulnerabilities (CVE) | Dependencies with known CVEs | No critical/high CVEs in direct dependencies | Trivy, npm audit, pip-audit |
| SC-02 | Dependency freshness | Outdated dependencies, EOL versions | No dependencies > 2 major versions behind | Trivy |
| SC-03 | SBOM & licence compliance | Software bill of materials, licence compatibility | No GPL-incompatible licences in proprietary code | Trivy SBOM mode |
| SC-04 | Transitive dependency depth | Dependency tree depth and breadth | Awareness of transitive risk; no deeply nested vulnerable deps | Trivy |

---

## Infrastructure (INF)

| ID | Primitive | What to Check | Pass Condition | Tool |
|---|---|---|---|---|
| INF-01 | Container security | Dockerfile best practices, base-image vulns | No critical vulns in base image, non-root user | Trivy + hadolint (if Dockerfiles present) |
| INF-02 | Secrets in deployment config | Secrets in docker-compose, k8s manifests, CI config | No plaintext secrets in deployment files | Gitleaks + Grep |
| INF-03 | HTTP security headers | CSP, HSTS, X-Frame-Options, Referrer-Policy, X-Content-Type-Options | All recommended headers present and correctly configured | curl + header check (if URL provided) |
| INF-04 | Error handling | Verbose error messages, stack traces in responses, debug mode in production | No information disclosure via error responses | Semgrep + code review |

---

## Status Convention

Every primitive ends up in one of six states:

| Status | Meaning | Score |
|---|---|---|
| **PASS** | No findings, or low-severity only | 100 |
| **ADVISORY** | Medium-severity findings; no immediate risk | 70 |
| **CONCERN** | High-severity findings requiring attention | 40 |
| **CRITICAL** | Critical findings requiring immediate action | 10 |
| **HYPOTHESIS** | Manual primitive — agent formed an evidence-backed hypothesis | N/A |
| **NOT ASSESSED** | Primitive not applicable, or tool unavailable | N/A |

Score formulas:

- **Category score:** mean of assessed primitive scores within that category (excluding HYPOTHESIS and NOT ASSESSED).
- **Overall score:** mean of category scores (categories with no assessed primitives are excluded).

---

## Per-Primitive Pointers

### SEC-01: Broken access control
Look for routes/handlers that don't check authorisation before performing
state changes. Semgrep rules: `python.flask.security.unsafe-objects`,
`javascript.express.security.express-no-authn`. Also grep for endpoints that
use the request user only for filtering (not for authorisation) — classic
IDOR pattern.

### SEC-02: Authentication failures
Hardcoded passwords (Gitleaks). Sessions in URLs (`req.params.session`).
Missing CSRF tokens on state-changing requests. Crypto-weak hash for
passwords (`MD5`, `SHA1`).

### SEC-03/04: Injection / Validation
Semgrep handles most. Pay extra attention to dynamic SQL builders, shell
exec with user input, and untyped query parameters.

### SEC-05: XSS
Look for `dangerouslySetInnerHTML` (React), `v-html` (Vue), `innerHTML =`
(vanilla JS). CSP header presence on the deployed URL.

### SEC-06: SSRF
Code that fetches URLs from user input without an allowlist. Cloud metadata
endpoints (`169.254.169.254`) accessible from app code.

### SEC-07: Sensitive data exposure
Gitleaks across git history (not just HEAD). Run with `git fetch --unshallow`
if the initial clone was shallow.

### DAT-01: Encryption at rest *(manual)*
Look for: cloud-provider DB config (RDS encryption, GCP CMEK), ORM-level
encryption (`pgcrypto`, application-layer encryption libraries), file
storage encryption. Often inconclusive from code alone — form a hypothesis.

### DAT-02: Encryption in transit
testssl.sh on the deployed URL. TLS version, cipher strength, HSTS,
certificate chain.

### DAT-03: PII/PHI
Grep for SSN patterns (`\d{3}-\d{2}-\d{4}`), credit card patterns (Luhn-able
sequences), email patterns in logging calls. Verify with code review —
high false-positive rate from test fixtures.

### DAT-04: Secrets management
Gitleaks for source. Grep deployment configs for credential-shaped strings.
Confirm env-var-based or vault-based management at runtime.

### DAT-05: Audit logging *(manual)*
Search for logging framework calls around auth events (login, logout,
password reset), data access (especially admin/PII), and admin actions.
Often inconclusive — form a hypothesis.

### CQ-01: Complexity
`lizard` (Python) handles most languages. Heuristic fallback: function
length and nesting depth via Grep.

### CQ-02: Test coverage
Existence check: are there test files? What ratio of test files to source
files? What testing framework? Coverage tools require running the test
suite — out of scope for code-only assessment; flag as `HYPOTHESIS` if
test ratio is low.

### CQ-03: Duplication
`jscpd` for multi-language. Or use grep heuristics for likely duplication
markers.

### CQ-04: Technical debt *(manual)*
Grep `TODO|FIXME|HACK|XXX|TEMPORARY|WORKAROUND` density. Disabled tests
(`it.skip`, `@pytest.mark.skip`). Commented-out code blocks. Compare
to LOC for density.

### CQ-05: Review practices *(manual)*
Git log analysis: direct-to-main commits, average reviewers per merge,
PR template presence. Branch protection rules (need GitHub API or repo
metadata).

### SC-01..SC-04: Supply chain
Trivy is the workhorse. SBOM mode for SC-03. For SC-04, render the
dependency tree depth.

### INF-01: Container security
hadolint on Dockerfiles, Trivy on base images. Look for non-root user,
minimal base image, `HEALTHCHECK` instruction, no `latest` tags.

### INF-02: Deploy-config secrets
Gitleaks + targeted grep on `docker-compose.yml`, `k8s/*.yaml`, `.github/workflows/*.yml`, `.gitlab-ci.yml`. False positives from interpolated env-var references — verify.

### INF-03: HTTP headers
curl-based check against deployed URL. Cross-reference with code-level
header config (Helmet, ASP.NET, Spring Security).

### INF-04: Error handling
Semgrep rules for verbose error responses. Grep for `console.log(err)`,
`print(traceback)`, `e.printStackTrace()` in HTTP response paths. Check
for `NODE_ENV=development` references or debug routes.

---

## Adding New Primitives

This catalogue is intentionally fixed at 25 for the v0.1.0 calibration
period. Proposals for new primitives go through the standard reference-
standard process — see the plugin's `references/viability-framework.md`
Version History.

Until calibration is complete, additional findings outside these 25 are
captured in the report's "Observations" section but do not affect the
score.
