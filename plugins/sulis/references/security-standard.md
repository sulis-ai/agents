# Security Standard

<!-- summary -->
Seven security principles (SEC-01 through SEC-07) that govern how software handles
untrusted input, secrets, authorization, output encoding, errors, dependencies, and
logging. All principles are at SHOULD with 90-day calibration notes — see Version History.
Operationalizes EP-01 (Security by Design) and EP-09 (Authorization-First Design) from
the rollout plan.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period

---

## Provenance

These principles encode widely accepted application security practice, drawing on:
OWASP Top 10 (2021), CWE/SANS Top 25 Most Dangerous Software Weaknesses, and
the principle of least privilege (Saltzer & Schroeder, 1975).

This is practitioner knowledge, not peer-reviewed research.

---

## Boundary Definition

This standard contains **universal security principles only**. Content belongs here if
and only if it passes the **ProjectX test**: replacing every project name, file path, and
technology-specific example with a fictional "ProjectX" equivalent requires zero semantic
changes to the principle statement.

Content that fails the ProjectX test belongs in the project's architecture file, not here.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification. |

---

## Principles

### SEC-01: Validate All Inputs at Trust Boundaries

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

Validate all data entering the system at trust boundaries — HTTP requests, message queue
consumers, file uploads, CLI arguments, inter-service calls from untrusted origins.
Prefer allowlist validation over denylist. Parse structured data into typed objects
(parse, don't validate) so that invalid data cannot propagate past the boundary.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Define explicit schemas or types for all external input. Validate at the boundary — controller, handler, or consumer — before passing data to business logic. Use allowlists (permitted characters, ranges, enum values) rather than denylists. Parse input into domain types (e.g., `EmailAddress`, `OrderId`) so the type system enforces validity downstream. Reject unexpected fields rather than silently ignoring them. |
| **Anti-Pattern** | Validating deep inside business logic instead of at the boundary. Using denylists ("block these characters") that miss novel attack vectors. Passing raw strings through the system and validating only at point of use. Trusting input from internal services without verifying the trust boundary. |
| **How to verify** | All controller/handler functions validate or parse input before calling business logic. No raw unvalidated strings from external sources reach domain logic. Validation uses allowlists or typed parsing, not denylists. |

---

### SEC-02: Secrets Never in Code

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Strong candidate for MUST promotion. Promotion requires evidence from
> 3+ executions.

No hardcoded secrets — API keys, passwords, tokens, connection strings with credentials —
in source code, test fixtures, configuration files committed to version control, log
output, or error messages. Secrets are injected at runtime from a secrets manager or
environment, and are never printed, serialised, or included in telemetry.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Store secrets in a secrets manager or inject via environment variables. Reference secrets by name, never by value, in configuration. Use `.gitignore` or equivalent to prevent secret files from being committed. In tests, use obviously fake values (e.g., `test-key-not-real`) or a test-specific secrets provider. Ensure `toString`, logging, and serialisation of objects containing secrets redact sensitive fields. |
| **Anti-Pattern** | Hardcoding API keys or passwords in source files. Committing `.env` files with real credentials. Logging request headers that contain auth tokens. Using production secrets in test fixtures. Relying solely on `.gitignore` without pre-commit hooks or scanning. |
| **How to verify** | No string literals resembling secrets (API keys, passwords, tokens) appear in source or test files. Configuration references secret names, not values. Logging and error output do not include sensitive fields. `.gitignore` excludes secret files. |

---

### SEC-03: Authorization Before Operation

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Strong candidate for MUST promotion. Promotion requires evidence from
> 3+ executions.

Every operation that accesses or mutates a protected resource must verify that the caller
is authorized before executing business logic. Default to deny — if no rule explicitly
grants access, access is refused. Prefer declarative authorization (annotations,
middleware, policy files) over imperative checks scattered through business logic.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Apply authorization checks in middleware, decorators, or a policy layer before the request reaches business logic. Use a default-deny posture: explicitly grant access rather than explicitly denying it. Centralise authorization logic so it can be audited in one place. Ensure authorization is checked on every operation, not just the UI — API endpoints, background jobs, and internal tools all require checks. Test authorization with explicit "forbidden" test cases, not just "happy path." |
| **Anti-Pattern** | Checking permissions inside business logic methods, making it easy to miss a path. Relying on UI-only restrictions (hiding buttons) without server-side enforcement. Default-allow policies where new endpoints are open until someone remembers to lock them down. Skipping authorization on internal or admin endpoints. |
| **How to verify** | All endpoints and operations that access protected resources have authorization checks before business logic executes. No endpoint is accessible without an explicit authorization rule. Forbidden-path test cases exist alongside happy-path tests. Authorization logic is centralised, not scattered. |

---

### SEC-04: Output Encoding and Injection Prevention

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

Never construct SQL, HTML, shell commands, or other interpreted strings by concatenating
user input. Use parameterised queries, prepared statements, auto-escaping template
engines, and safe APIs for shell execution. Treat all data leaving the application for
an interpreter as potentially dangerous.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Use parameterised queries or an ORM for all database access — no string concatenation for SQL. Use template engines with auto-escaping enabled by default for HTML output. Use safe subprocess APIs that accept argument arrays rather than shell strings. When an ORM or parameterised API is not available, use the language's recommended escaping library for the target interpreter. Apply Content-Security-Policy headers to restrict inline scripts. |
| **Anti-Pattern** | Building SQL queries with string concatenation or interpolation. Disabling auto-escaping in templates to "fix" rendering issues. Using `shell=True` or equivalent with unsanitised input. Constructing LDAP, XPath, or other query languages from raw input. Marking user content as "safe" or "raw" in templates without sanitisation. |
| **How to verify** | No SQL string concatenation or interpolation with external input in the codebase. Template rendering uses auto-escaping (no `| safe` or `{!! !!}` without justification). Shell commands use argument arrays, not interpolated strings. Database queries use parameterised statements or ORM methods. |

---

### SEC-05: Safe Error Handling

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

Error responses to external callers must not reveal internal implementation details —
stack traces, database schemas, internal service names, file paths, or library versions.
Return a correlation ID that maps to detailed internal logs, so operators can diagnose
without exposing internals to attackers.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Return generic error messages to external callers (e.g., "An error occurred. Reference: abc-123"). Log full error details (stack trace, context) internally with a correlation ID. Ensure error-handling middleware catches unhandled exceptions before they reach the caller. Differentiate between client errors (4xx — safe to describe) and server errors (5xx — do not describe). Disable debug/development error pages in production. |
| **Anti-Pattern** | Returning stack traces in API responses. Including database error messages (e.g., "column 'users.ssn' not found") in HTTP responses. Leaking internal service names or infrastructure details in error messages. Running with debug mode enabled in production. Catching exceptions silently with no logging. |
| **How to verify** | Error-handling middleware or a global exception handler exists and catches unhandled exceptions. Server error responses (5xx) do not include stack traces, internal paths, or implementation details. Correlation IDs are present in error responses and appear in corresponding log entries. Debug mode is disabled in production configuration. |

---

### SEC-06: Dependency Security

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

Evaluate dependencies before adoption. Audit existing dependencies for known
vulnerabilities. Use lock files to pin exact versions and ensure reproducible builds.
Keep dependencies up to date, especially for security patches.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Before adding a dependency, evaluate: is it actively maintained? Does it have known vulnerabilities? Is the scope appropriate (avoid pulling in a large framework for one utility)? Use lock files (`package-lock.json`, `poetry.lock`, `Cargo.lock`, etc.) and commit them to version control. Run dependency audit tools (`npm audit`, `pip-audit`, `cargo audit`, etc.) in CI. Update dependencies regularly, prioritising security patches. |
| **Anti-Pattern** | Adding dependencies without evaluating maintenance status or vulnerability history. Not committing lock files. Ignoring audit warnings. Pinning to a major version range and never updating. Using deprecated or unmaintained packages because "it still works." |
| **How to verify** | Lock files are committed to version control. Dependency audit passes with no known high/critical vulnerabilities (or documented exceptions). New dependencies have documented justification. CI includes a dependency audit step or equivalent check. |

---

### SEC-07: Secure Logging

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

Log security-relevant events (authentication attempts, authorization failures, input
validation failures, privilege changes) with enough detail to support incident
investigation. Never log sensitive data — passwords, tokens, personal identifiable
information, or secret keys.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Log authentication successes and failures with user identifiers (but not credentials). Log authorization denials with the resource and action attempted. Log input validation failures with the field name and violation type (but not the full input value if it may contain sensitive data). Include timestamps, correlation IDs, and source identifiers in all security log entries. Ensure log output redacts sensitive fields (passwords, tokens, PII). Use structured logging to make security events queryable. |
| **Anti-Pattern** | Logging passwords, API keys, or tokens — even at debug level. Logging full request bodies that may contain sensitive data. Not logging authentication or authorization events at all. Logging security events without enough context to investigate (missing user ID, timestamp, or action). Using unstructured log messages that are difficult to search or alert on. |
| **How to verify** | Authentication and authorization events produce log entries. Log entries do not contain passwords, tokens, or PII. Security log entries include timestamps, correlation IDs, and user/action context. Logging configuration redacts known sensitive fields. |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-03-12 | Initial release. Seven principles (SEC-01 through SEC-07), all at SHOULD with 90-day calibration notes. |
