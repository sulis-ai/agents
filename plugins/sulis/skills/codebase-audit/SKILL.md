---
name: codebase-audit
description: "Audits existing code for gaps and drafts the fixes to close them."
---

# Codebase Audit — Brownfield Gap Analysis

When invoked, scan a codebase against the three MECE-3 pillars and produce:

1. `.architecture/{project}/audit-report.md` — a structured findings document.
2. A set of draft Hardening Deltas under `.architecture/{project}/hardening-deltas/`,
   one per gap, all at `status: proposed`.
3. An `INDEX.md` ordering deltas by severity and dependency.

If arguments are provided, treat them as the project name to write under
`.architecture/`. If not, infer from the working directory's basename or
ask the user.

---

## What You Read

| Source | Look for |
|---|---|
| Source tree | HTTP/RPC/DB clients (timeouts, retries, circuit breakers); module imports (dependency direction); secret patterns; observability calls |
| Test tree | Mocks vs real adapters; chaos test presence; contract test presence per port |
| Build config | Static analysis tools, dependency vulnerabilities, container base image |
| CI config | Test gates, security scans, deployment policies |
| Existing `.specifications/` | Compare to SRD/NFR/**MISUSE_CASES.md** if present — gaps vs spec are extra findings |
| `.specifications/{project}/HANDOFF_TO_SEA.md` (if present) | Direct user intent from SRD's Early Handover — read first when there is no SRD.md |
| `.specifications/{project}/EXPLORATION_JOURNAL.md` `## Deferred to SEA` section (if present) | Architecture content SRD parked mid-session — often points directly at the code regions the user wants audited |

If the project has a prior SRD at `.specifications/{project}/`, the audit
also reconciles **code vs spec drift** (code does things the spec doesn't,
spec requires things the code doesn't do).

If `MISUSE_CASES.md` exists, the audit also reconciles **code vs adversarial
spec drift**: every MUC's System Response is a hardening requirement. Each
unsatisfied MUC system response becomes a Hardening Delta with
`source: srd:misuse-case-MUC-NN` in its frontmatter.

If `HANDOFF_TO_SEA.md` exists and `SRD.md` does not, the audit is operating
in **Early-handoff mode**: read the handoff file first to understand what the
user actually wants you to look at. Their original message often names
specific code regions, integrations, or behaviours — let those drive the audit
scope before running the generic MECE-3 sweep.

---

## Gap Types You Detect

Scan for each of the gap types in `references/hardening-deltas.md` (HD-02
table). The non-exhaustive checklist:

### Form (Structural)
- Domain code that imports from `infrastructure/`, `db/`, `http/`
- Module-level singletons accessed via `getInstance()`
- Circular module dependencies
- Cross-module reach-through into `internal/`

### Armor (Operational)
- HTTP/RPC client calls with no explicit timeout
- Retries with no backoff/jitter; retries on non-idempotent operations without keys
- External calls with no circuit breaker
- Hardcoded credentials, API keys, secrets in source or committed `.env`
- Service-to-service calls over plain HTTP
- Operations missing OpenTelemetry spans
- Logs without `trace_id`
- No RED/USE metrics on handlers/resources
- PII or secrets visible in logs/traces (regex scan for token-like strings)

### Proof (Verification)
- Ports with no contract test
- Adapter tests that don't share a contract test with the in-memory adapter
- Integration tests using mocks instead of real adapters/testcontainers
- Resiliency primitives with no chaos test

---

## Workflow

0. **Read `.context/{project}/INDEX.md` if present.** Use the Authoritative
   Sources to constrain findings — if an authoritative standard already
   mandates a behaviour (e.g. TLS 1.3), do not flag it as a missing
   requirement; flag only missing implementation. The External ADR Registry
   informs delta source-fields (`source: srd:misuse-case-MUC-NN` vs
   `source: external:ADR-NN`).
1. **Discover** — walk the source tree. Identify language, frameworks,
   structure. Produce a 1-paragraph summary so the user knows what you read.
   If `HANDOFF_TO_SEA.md` exists, read it first and let it shape the
   discovery scope. If `## Deferred to SEA` is present in the journal, read
   the parked items and use them to prioritise the audit.
1a. **Compute SIZING.md (MUST).** Per `references/right-sizing.md`'s
   **Brownfield Equivalence** section, derive sFPC + ASR from the codebase
   rather than from SRD artifacts:
   - **ILF** — count distinct database schemas / ORM models / persistent
     collections (look in `migrations/`, `models/`, `entities/`,
     `db/schema.*`, etc.)
   - **EIF** — count outbound HTTP/RPC/queue clients to external systems
     (grep for HTTP client instantiation, queue subscriber setup, etc.)
   - **EI/EO/EQ** — classify endpoints by HTTP verb + body inspection
     (POST/PUT/PATCH/DELETE typically EI; computed GETs are EO; simple GETs
     are EQ; message consumers are EI if they update state)
   - **NFRs as ASRs** — inferred from observed thresholds (rate limits,
     timeout configs, retention policies in code/config); flag as
     "inferred, not documented" in SIZING.md
   - **Integrations** — same as EIF count
   - **MUCs as ASRs** — inferred from auth/audit/replay-protection code
     paths; flag as "inferred"
   - **Cross-cutting policies** — middleware / interceptors / decorators
     with authz, audit, rate-limit, or observability purpose
   
   Apply the tier table from `references/right-sizing.md`. File count is a
   sanity check — if sFPC + ASR suggest tier S but the codebase has 2000+
   source files, surface the mismatch:
   
   > "Computed tier S but codebase has 2247 source files. Likely either
   > substantial generated/boilerplate code, or audit scope needs narrowing.
   > Override tier, narrow scope, or proceed?"
   
   Write `.architecture/{project}/SIZING.md` per the schema in
   `references/right-sizing.md`. The audit report's depth follows the
   resulting tier.
1b. **Misuse-case reconciliation (if MISUSE_CASES.md exists)** — for each MUC,
   determine whether its System Response is implemented in the code. If not,
   draft a Hardening Delta with `source: srd:misuse-case-MUC-NN`. See
   `references/hardening-deltas.md` for the translation pattern.
2. **Scan per gap type** — for each gap type above, search the codebase and
   record findings with file paths and line numbers.
3. **Score severity** — assign `critical | high | medium | low`:
   - `critical` — security flaw exploitable now (hardcoded secret in source, missing authz on data-mutating endpoint)
   - `high` — production incident probable within 90 days (unbounded external call on hot path, no CB on payment provider)
   - `medium` — operational pain or test gap (missing observability on a handler, integration tests with mocks)
   - `low` — structural drift that has not yet caused failure (one-off module-level state, deep import path)
4. **Group into deltas** — one logical change per HD-NNN file. Don't bundle.
5. **Write a failing test for each delta** — every delta references a
   characterisation test that proves the gap exists. If you cannot construct
   such a test, drop the delta (the gap is theoretical, not actual).
6. **Emit the audit report** — see structure below.
7. **Build `hardening-deltas/INDEX.md`** — sorted by severity, then by
   dependency (what blocks what).
8. **Report to the user** — totals per pillar, top 5 by severity, suggested
   acceptance order.

---

## Audit Report Structure

```markdown
# {Project} — Codebase Audit

> **Date:** YYYY-MM-DD
> **Scope:** {paths scanned}
> **Tooling:** {language, frameworks identified}

## Summary

- **Critical findings:** N
- **High findings:** N
- **Medium findings:** N
- **Low findings:** N

| Pillar | Findings | Top concern |
|---|---|---|
| Form | N | Domain imports infrastructure in 3 files |
| Armor | N | 14 unbounded external calls |
| Proof | N | 0 contract tests, 6 mock-based integration tests |

## Findings by Pillar

### Form

| ID | File | Line | Gap | Severity | Delta |
|---|---|---|---|---|---|
| F-01 | `src/domain/order/Order.ts` | 12 | Imports `db` from infrastructure | high | HD-001 |
| F-02 | ... | ... | ... | ... | ... |

### Armor

| ID | File | Line | Gap | Severity | Delta |
|---|---|---|---|---|---|
| A-01 | `src/payments/provider-client.ts` | 42 | Unbounded `fetch()` | high | HD-003 |
| A-02 | `src/config/secrets.ts` | 8 | Hardcoded API key | critical | HD-002 |
| ... | ... | ... | ... | ... | ... |

### Proof

| ID | File | Gap | Severity | Delta |
|---|---|---|---|---|
| P-01 | `tests/payments/integration.test.ts` | Mock used for Stripe; no testcontainer | medium | HD-005 |
| ... | ... | ... | ... | ... |

## Spec Drift (if SRD exists)

| Direction | Item | Action |
|---|---|---|
| Code does X, spec doesn't mention | {behaviour} | Update SRD or remove code |
| Spec requires Y, code doesn't implement | {requirement} | Implement as WP-NNN |

## Adversarial Drift (if MISUSE_CASES.md exists)

| MUC | System Response (Required) | Code Implements? | Delta |
|-----|----------------------------|-------------------|-------|
| MUC-01 | Detect-and-reject replayed payment webhooks | No — webhook handler accepts duplicates | HD-007 |
| MUC-02 | Rate-limit password-reset endpoint to 5/hr/account | No — no rate limit | HD-008 |
| MUC-03 | Audit log on every authorisation grant | Partial — logs grant but not denial | HD-009 |

## Suggested Acceptance Order

1. Critical deltas first: HD-002 (secret leak)
2. High deltas on hot paths: HD-003 (payment timeout), HD-001 (domain leak)
3. Medium hygiene: HD-005, HD-006
4. Low / opportunistic: HD-...

## What Was Not Audited

- {Reason — e.g. "Python service excluded; SEA's auditor is currently TypeScript-only"}
- {Files skipped due to {reason}}
```

---

## Adapting Depth

- **Quick** ("smoke test the security pillar") — scan for hardcoded secrets and missing authz only; produce critical/high findings only. ~10 minutes.
- **Full** (default) — full scan across all three pillars; deltas for every finding above `low`.
- **Audit-mode** ("just tell me where we stand") — produce the audit report only, no deltas. User decides whether to invest in deltas.

---

## Gotchas

- **Don't fabricate a failing test.** If you cannot write a test that proves the gap exists today, drop the delta. Theoretical gaps belong in the audit report's "watch list", not in the delta queue.
- **Severity is operational.** "Critical" means production-impact-now. Don't inflate to drive attention.
- **One file can hold multiple findings.** They become multiple deltas (one per logical change), not one bundled delta. The delta graph cannot express bundled work.
- **Drift cuts both ways.** Code-without-spec is as serious as spec-without-code. Surface both.
- **Static signals can lie.** A function that "looks like" it has a hardcoded secret might be reading from an environment variable that contains the literal. Confirm before flagging critical.

---

## See Also

- `references/hardening-deltas.md` — the HD-NNN format (plugin root)
- `references/mece-3-architecture.md` — the three pillars (plugin root)
