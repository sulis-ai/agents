# Viability Assessment Framework

<!-- summary -->
The Viability Framework defines how `sulis-security` evaluates an arbitrary
codebase. It comprises **25 primitives across 5 categories**, an **OODA-spiral
methodology** for adaptive assessment, and a **scoring rubric** that produces
per-primitive, per-category, and overall scores. The framework is opinionated
about evidence: every finding cites a file path, line number, or tool output.
Manual primitives that cannot be fully automated become **hypotheses** —
evidence-backed statements a human can confirm or reject.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period

---

## Provenance

Synthesised from:
- **OWASP Top 10** (2021) — application-security primitives
- **CWE/SANS Top 25** — dangerous software weaknesses
- **CIS Benchmarks** — infrastructure hardening
- **NIST SSDF** (Secure Software Development Framework, SP 800-218) — supply chain
- **Boyd's OODA loop** (Observe-Orient-Decide-Act) — adaptive assessment cycle

This is practitioner knowledge, not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block assessment validity. |
| **SHOULD** | Default. Deviation needs justification in the report's Methodology section. |

---

## The 25 Primitives

The full catalogue lives in [`skills/codebase-assess/references/primitives.md`](../skills/codebase-assess/references/primitives.md).
This standard summarises the categories and the structure.

| Category | Prefix | Count | What it covers |
|---|---|---|---|
| **Security** | SEC | 7 | Access control, auth, injection, validation, XSS, SSRF, sensitive data exposure |
| **Data Protection** | DAT | 5 | Encryption at rest/transit, PII/PHI, secrets management, audit logging |
| **Code Quality** | CQ | 5 | Complexity, test coverage, duplication, technical debt, review practices |
| **Supply Chain** | SC | 4 | CVEs, dependency freshness, SBOM/licence, transitive depth |
| **Infrastructure** | INF | 4 | Container security, deploy secrets, HTTP headers, error handling |
| **Total** | — | **25** | |

Each primitive has:
- An **ID** (e.g. `SEC-03`)
- A **what to check** specification
- A **pass condition**
- A **tool** (or a heuristic if no tool applies)
- A **status** assigned by the assessment

---

## OODA Spiral Methodology

The assessment is not a flat checklist run. It is a spiral — each cycle deepens
understanding and adapts based on what was found in the previous cycle. Typical
runs complete in 3-5 cycles for code-only, 5-7 cycles with a deployed URL.

### Cycle 1: Reconnaissance

**Observe:** scan the cloned repo. Languages, frameworks, database, deployment,
test structure, size.

**Orient:** map the target to the primitive framework. Mark which primitives
apply (no Dockerfile → skip INF-01; no deployed URL → skip DAT-02, INF-03).

**Decide:** plan tool execution order — broad-spectrum first (Gitleaks, Trivy,
Semgrep), targeted later.

**Act:** execute the first round of tools.

### Cycle 2: Triage and Depth

**Observe:** read tool outputs. What's critical? What's noise?

**Orient:** prioritise critical/high findings; spot patterns (e.g. five
injection findings in one module → that module needs focused review); spot
surprises (e.g. zero test files → CQ-02 is critical).

**Decide:** plan targeted follow-up — does a finding chain into another
primitive? Are vulnerable code paths actually reachable?

**Act:** execute targeted checks. Update findings.

### Cycle 3: Cross-Primitive Chaining

**Observe:** look for findings that connect across primitives.

**Orient:** "Does finding A in primitive X make primitive Y worse?" Examples:

- Secret in git (SEC-07) + API endpoint in code (SEC-01) → can the secret authenticate the API?
- No input validation (SEC-04) + SQL queries in the same module (SEC-03) → injection chain
- Debug mode enabled (INF-04) + PII in logs (DAT-03) → data exposure chain
- No tests (CQ-02) + high complexity (CQ-01) → high regression risk

**Decide:** document the chains — these are the most compelling findings.

**Act:** write the chains with evidence.

### Cycle 4: Deployed Surface (if URL provided)

**Observe:** non-invasive checks against the deployed URL — TLS, security
headers, common file exposure (`/.env`, `/.git/config`).

**Orient:** compare deployed state to code findings. Does the code say TLS 1.2
but the server accepts 1.0? Does CORS look strict in code but the deployed
server emits `Access-Control-Allow-Origin: *`?

**Decide:** focus on discrepancies — these are the highest-value findings.

**Act:** document, distinguishing code issues from deployment configuration
issues.

### Cycle 5: Hypothesis Formation

**Observe:** review all 25 primitives. Which haven't been assessed?

**Orient:** for primitives that cannot be fully automated (DAT-01 encryption at
rest, DAT-05 audit logging, CQ-04/CQ-05 process signals), form hypotheses
from available evidence.

Example: "Found PostgreSQL config with no `pgcrypto` extension, no encryption
helpers in the ORM configuration. **Hypothesis: encryption at rest is not
implemented.** Confidence: medium. To verify: ask the team."

**Decide:** write hypotheses as specific, evidence-backed statements someone
can confirm or reject.

**Act:** complete the primitive assessment table.

### Termination

Stop cycling when:
- All applicable primitives have a result (automated or hypothesis)
- No productive lines of inquiry remain
- Diminishing returns on each new cycle

---

## Scoring Rubric

Each primitive receives a **status** and a **score**:

| Status | Meaning | Score |
|---|---|---|
| **PASS** | No findings, or low-severity only | 100 |
| **ADVISORY** | Medium-severity findings; no immediate risk | 70 |
| **CONCERN** | High-severity findings requiring attention | 40 |
| **CRITICAL** | Critical findings requiring immediate action | 10 |
| **HYPOTHESIS** | Manual primitive — agent formed a hypothesis | N/A (excluded from average) |
| **NOT ASSESSED** | Primitive not applicable, or tool not available | N/A (excluded from average) |

**Category score:** mean of assessed primitive scores within that category.
**Overall score:** mean of category scores (categories without any assessed
primitives are excluded).

Scoring is a heuristic, not a benchmark. A score of 70 across the board is not
the same as a score of 70 driven by one critical finding masked by passing
peers — the report's Critical Findings and Attack Chains sections matter more
than the headline number.

---

## Evidence Discipline

Every finding **MUST** cite specific evidence:

- A file path and line number (e.g. `src/api/users.js:42`)
- A tool output snippet (gitleaks SARIF entry, trivy CVE record)
- A git log range (for review-practice findings)
- A URL response header (for deployed-surface findings)

Findings without evidence are flagged as `UNSUPPORTED` and excluded from
scoring. A hypothesis is permitted without conclusive evidence — but it must
state the evidence base and confidence level.

---

## Composition with Other Plugins

`sulis-security` is one lens among several. It composes with:

- **SEA** (Senior Engineering Architect) — sulis-security findings often
  correspond to SEA Hardening Deltas. The report's "Recommendations →
  Immediate" section maps directly to `.architecture/{project}/hardening-deltas/`.
- **SRD** (Requirements Analyst) — if `.specifications/{project}/SRD.md`
  exists, the assessment cross-references findings against documented NFRs
  (e.g. "SEC-07 critical finding contradicts NFR-12 secret-management
  requirement").

The viability assessment runs without either plugin — it scans codebases
that have no prior specification or architecture.

---

## Tool Degradation Policy

The framework assumes Docker is the preferred execution environment for
tools (Gitleaks, Trivy, Semgrep). If Docker is not available:

1. Attempt the native binary if installed (`gitleaks`, `trivy`, `semgrep`).
2. If neither is available, fall back to heuristic checks using Bash, Grep,
   and Read. Document the degradation in the report's Methodology section.

A primitive with no available tool defaults to `NOT ASSESSED` — not a failure.
The report makes coverage gaps explicit so the reader can decide whether to
trust the verdict.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-12 | Initial framework. 25 primitives, OODA spiral, scoring rubric, evidence discipline. |
