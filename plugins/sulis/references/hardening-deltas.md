# Hardening Delta Format Standard

<!-- summary -->
A Hardening Delta (HD) is the artifact `/sulis:harden-codebase` produces when auditing
brownfield code. Each delta describes one concrete change to existing code
that closes a gap against the [[mece-3-architecture]] pillars. The format is
adapted from the OpenSpec delta convention (ADDED / MODIFIED / REMOVED) and
extended with a Verification section that names the failing test that proves
the gap exists. A delta is not done until the failing test is written, the
implementation lands, and the test turns green.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period

---

## Provenance

The delta format adapts the OpenSpec change-proposal convention (Fission AI,
2026) for SEA's hardening domain. The Verification section follows the
characterisation-test discipline from Working Effectively With Legacy Code
(Feathers, 2004) — the failing test characterises current (broken) behaviour
before the change.

This is practitioner knowledge, not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block the delta from being accepted. |
| **SHOULD** | Default. Deviation documented in the delta's Rationale. |

---

## File Layout

Hardening Deltas live under the per-project architecture folder in **one
of two locations**:

**1. Canonical flat location** — for deltas from audit, security, MUC,
NFR, and other non-review sources:

```
.architecture/{project}/hardening-deltas/
  INDEX.md
  HD-001-add-payment-timeout.md
  HD-002-redact-pii-from-logs.md
  ...
```

**2. Per-review bundle** — for deltas drafted by `/code-review` runs:

```
.architecture/{project}/code-reviews/PR-{number}-{TIMESTAMP}/hardening-deltas/
  INDEX.md
  HD-018-add-timeout-stripe.md
  HD-019-declare-hasMore.md
```

Both locations are valid. `/sulis:harden-codebase` discovers deltas recursively
under `.architecture/{project}/` (matches `HD-*.md` anywhere in the
tree). The `status:` field in each delta's frontmatter still gates
whether harden implements it — only `accepted` runs; `proposed`,
`rejected`, `implemented` are skipped.

Files are numbered sequentially **per ID-space** (HD-001..HD-NNN
globally, not per-location — keep IDs unique across the whole project
to avoid ambiguity in delta cross-references and `dependsOn` graphs).

A delta is one logical change — not "harden everything in service X". If
service X has five gaps, that is five deltas.

---

## Required Sections

### HD-01: Header

**Severity:** MUST

```yaml
---
id: HD-003
title: Wrap payment provider call in circuit breaker
pillar: armor                 # form | armor | proof
gap_type: resiliency          # see HD-02
severity: high                # critical | high | medium | low
status: proposed              # proposed | accepted | implemented | verified | rejected
source_file: src/payments/provider-client.ts
source: srd:misuse-case-MUC-04   # optional — provenance of this delta
created: 2026-05-12
---
```

The optional **`source`** field records where the delta came from. Recognised forms:

| Source value | Meaning |
|--------------|---------|
| (omitted) | Delta originated from a `/sulis:codebase-audit` finding with no upstream spec |
| `srd:misuse-case-MUC-NN` | Delta implements the System Response required by an SRD misuse case (SRD v1.11.0+) |
| `srd:negative-requirement-NR-NN` | Delta implements a per-use-case negative requirement from SRD.md |
| `sulis-security:viability-report-{timestamp}#SEC-NN` | Delta closes a finding from a sulis-security viability report. `timestamp` is the ISO 8601 UTC stamp embedded in the report filename (e.g., `2026-05-21T143052Z`). |
| `nfr:NFR-NN` | Delta implements a non-functional requirement from NFR.md |
| `code-review:PR-NN` | Delta closes a finding from a `/code-review` run against a pull request, branch, or commit range (SEA v0.12.0+). The delta also carries a `lens:` field (`architecture` / `security` / `quality`) identifying which reviewer produced it. |

The source field is for traceability — when SRD or sulis-security re-run, the upstream
artifact's status can be reconciled against the delta's status without manual matching.

### HD-02: Gap Type

**Severity:** MUST

The gap closes one specific category. Use one of:

| Gap Type | Pillar | Examples |
|---|---|---|
| `dependency-direction` | Form | Domain imports infrastructure |
| `module-coupling` | Form | Cross-module reach-through into internals |
| `timeout` | Armor | Unbounded HTTP/DB call |
| `retry` | Armor | Missing retry, or retry without backoff/jitter |
| `circuit-breaker` | Armor | No circuit breaker on external dependency |
| `bulkhead` | Armor | Shared thread/connection pool for unrelated workloads |
| `secrets` | Armor | Hardcoded credentials or secrets in env files |
| `encryption` | Armor | Plain HTTP, unencrypted storage, missing mTLS |
| `authz` | Armor | Missing authorization check; insufficient claim validation |
| `redaction` | Armor | PII/secrets leaking to logs, traces, error messages |
| `observability-trace` | Armor | Operation has no OpenTelemetry span |
| `observability-log` | Armor | Operation has no structured log with trace_id |
| `observability-metric` | Armor | Operation has no RED/USE metric |
| `contract-test` | Proof | Port has no contract test |
| `integration-test` | Proof | Boundary tested only with mocks |
| `chaos-test` | Proof | Resiliency primitive has no fault-injection test |

### HD-03: Context

**Severity:** MUST

A short prose section (2-5 sentences) explaining what currently happens, why
it is a gap, and what failure mode it enables. Reference specific file paths
and line numbers where the gap exists.

Example:

> The payment provider client at `src/payments/provider-client.ts:42` calls
> `fetch(url)` with no explicit timeout. The provider has been observed to
> hang for >30s during regional incidents. With no timeout, request threads
> accumulate, exhaust the connection pool, and cascade failure to unrelated
> endpoints. This violates MEA-04.

### HD-04: Change (ADDED / MODIFIED / REMOVED)

**Severity:** MUST

The delta uses three subsections borrowed from OpenSpec format. Include only
the subsections that apply. Each entry is a concrete code-level change.

```markdown
## Change

### ADDED
- `src/payments/resilience-policy.ts` — new file exporting `paymentCircuit`
  with timeout=2s, retry=2x with exponential backoff (200ms, 400ms), circuit
  breaker (5 failures in 30s opens, half-open after 60s).

### MODIFIED
- `src/payments/provider-client.ts:42` — `fetch(url)` → `paymentCircuit.execute(() => fetch(url, { signal }))`.
- `src/payments/provider-client.ts:1-5` — import resilience policy.

### REMOVED
- `src/payments/legacy-retry.ts` — old ad-hoc retry helper, replaced by policy.
```

### HD-05: Verification (Characterisation Test)

**Severity:** MUST

Every delta states the **failing test** that proves the gap exists today and
will prove the gap is closed once the delta lands. This is the Proof pillar
applied to the delta itself.

```markdown
## Verification

### Failing test (proves gap exists today)
- File: `tests/payments/resilience.test.ts`
- Name: `times_out_after_2s_when_provider_hangs`
- Setup: Use toxiproxy to inject 5s latency into the payment provider downstream.
- Expectation: The call rejects with `TimeoutError` within 2.1s.
- Current behaviour: hangs for full toxiproxy timeout (~30s) — test fails.

### Additional tests added by this delta
- `opens_circuit_after_5_consecutive_provider_500s` — chaos test for CB open
- `closes_circuit_after_recovery_window` — chaos test for CB half-open → closed
- `retries_with_backoff_on_transient_502` — retry behaviour test
```

### HD-06: Rationale

**Severity:** SHOULD

Why this specific approach, what alternatives were considered, and why they
were rejected. Keep to 3-5 sentences. Use this section to document trade-offs
the next reader will care about (latency budget, dependency added, etc.).

### HD-07: Sequence

**Severity:** SHOULD

If the delta depends on another delta, name it: `dependsOn: [HD-001]`. If
the delta blocks others, name them: `blocks: [HD-007, HD-009]`. This drives
the `hardening-deltas/INDEX.md` graph.

---

## Worked Example

`.architecture/payments-service/hardening-deltas/HD-003-add-payment-timeout.md`:

```markdown
---
id: HD-003
title: Wrap payment provider call in circuit breaker
pillar: armor
gap_type: circuit-breaker
severity: high
status: proposed
source_file: src/payments/provider-client.ts
created: 2026-05-12
dependsOn: []
blocks: [HD-004]
---

## Context

The payment provider client at `src/payments/provider-client.ts:42` calls
`fetch(url)` with no explicit timeout, no retry, and no circuit breaker.
The provider has been observed to hang for >30s during regional incidents
(see INC-2026-04-12). Request threads accumulate, exhaust the connection
pool, and cascade failure to unrelated endpoints. This violates MEA-04
(every external call has a timeout, retry, and circuit breaker).

## Change

### ADDED
- `src/payments/resilience-policy.ts` — `paymentCircuit` with timeout=2s,
  retry=2x exponential backoff (200ms, 400ms), circuit breaker (5 failures
  in 30s opens, half-open probe after 60s).

### MODIFIED
- `src/payments/provider-client.ts:42` — `fetch(url, opts)` →
  `paymentCircuit.execute(signal => fetch(url, { ...opts, signal }))`.

### REMOVED
- (none)

## Verification

### Failing test (proves gap exists today)
- File: `tests/payments/resilience.test.ts`
- Name: `times_out_after_2s_when_provider_hangs`
- Setup: toxiproxy injects 5s latency on payment provider downstream.
- Expectation: rejects with `TimeoutError` within 2.1s.
- Current behaviour: hangs ~30s — test fails.

### Additional tests added
- `opens_circuit_after_5_consecutive_provider_500s`
- `half_opens_after_60s_recovery_window`
- `retries_with_backoff_on_transient_502`

## Rationale

Considered: simple timeout only, full bulkhead with dedicated pool. Rejected
simple timeout (still cascades pool exhaustion on slow provider). Rejected
full bulkhead (over-engineered for single downstream; revisit when we add a
second provider — HD-008). Circuit breaker is the minimum sufficient
intervention.

## Sequence

- dependsOn: (none — provider client is self-contained)
- blocks: HD-004 (payment fallback delta needs the circuit breaker's
  `isOpen()` to decide when to invoke the fallback path).
```

---

## How `/sulis:harden-codebase` Uses This Format

1. Scans the source tree for gaps in each MEA pillar.
2. Groups gaps by file and gap-type.
3. Emits one HD-NNN file per logical change.
4. Builds `hardening-deltas/INDEX.md` ordered by `severity` then `dependsOn` graph.
5. Each delta starts at `status: proposed`. The user accepts deltas one or in
   batches. Accepted deltas become Work Packages on the implementation queue.

---

## Misuse-Case-to-Delta Translation (SRD v1.11.0+)

When `.specifications/{project}/MISUSE_CASES.md` exists, each misuse case is a
candidate for one or more Hardening Deltas. The MUC's **System Response (REQUIRED)**
is the contract; the delta is its implementation.

### Translation pattern

| MUC field | Becomes delta field |
|-----------|---------------------|
| `MUC-NN` | `source: srd:misuse-case-MUC-NN` (in HD frontmatter) |
| Abusive Actor + Misuse Flow | HD-03 Context section — explain why the gap is exploitable |
| System Response (REQUIRED) | HD-04 Change section — the ADDED/MODIFIED to satisfy the requirement |
| Misuse Flow's "System (no response)" column | HD-05 Verification — the failing test reproduces this column |
| Misuse Flow's "System (with required response)" column | HD-05 Verification — the test that passes after the change |
| MUC-linked NFR (rate ceiling, retention period, integrity threshold) | Test assertion thresholds; if values change, NFR is the source of truth |

### Worked example — MUC-04 (replay payment webhook) → HD-007

**MUC-04 (in MISUSE_CASES.md):**
- Abusive Actor: any party who captured a Stripe webhook payload
- Targets: UC-03 (payment confirmation)
- System Response (REQUIRED): MUST detect-and-reject webhook deliveries whose
  Stripe signature timestamp is older than 5 minutes OR whose payload-hash
  matches a delivery in the last 24 hours

**HD-007 derived from MUC-04:**

```yaml
---
id: HD-007
title: Reject replayed Stripe webhooks (signature freshness + dedup)
pillar: armor
gap_type: idempotency
severity: high
status: proposed
source_file: src/payments/webhook-handler.ts
source: srd:misuse-case-MUC-04
created: 2026-05-13
---

## Context

UC-03 (payment confirmation) processes Stripe webhooks. MUC-04 in
`.specifications/{project}/MISUSE_CASES.md` requires detect-and-reject for
replayed deliveries. Today the handler accepts any payload with a valid signature
regardless of timestamp or payload-hash history. This is the gap MUC-04 names.

## Change

### ADDED
- `src/payments/webhook-replay-guard.ts` — verifies Stripe `t=` timestamp is within
  5 minutes, looks up payload-hash in 24-hour Redis dedup window, rejects if either
  check fails.

### MODIFIED
- `src/payments/webhook-handler.ts` — calls `webhook-replay-guard` before payload
  processing; returns 409 on rejection per Stripe's recommended replay-handling
  convention.

## Verification

### Failing test (proves gap exists today)
- `tests/payments/webhook-replay.test.ts::rejects_replayed_signature` — replays
  a captured webhook payload 6 minutes later; currently passes the handler
  (returns 200); after change, must return 409.

### Additional tests added by this delta
- `rejects_payload_hash_within_dedup_window` — same payload twice within 24h.
- `accepts_payload_hash_after_dedup_window` — same payload 25h later.

## Rationale

MUC-04 requires detect-and-reject — see `.specifications/{project}/MISUSE_CASES.md`.
NFR-09 sets the dedup window at 24 hours. Stripe's signature freshness window of
5 minutes is the industry default and matches Stripe's own guidance.

## Sequence

`dependsOn: []` — independent change.
`blocks: HD-012` (payment audit log, which assumes only-non-replayed webhooks reach it).
```

### What `/sulis:codebase-audit` does with MUCs

When auditing a brownfield codebase that has a `MISUSE_CASES.md`:

1. For each MUC, look up the implementation status of its System Response in the code.
2. If absent or partial, draft a Hardening Delta with `source: srd:misuse-case-MUC-NN`.
3. Record adversarial drift in the audit report's "Adversarial Drift" table.
4. Cross-reference: every MUC should appear either as an implemented system response
   in the code OR as a draft delta. MUCs that appear in neither are a process gap —
   surface them to the user.

### What `/sulis:draft-architecture` does with MUCs

For greenfield work, MUCs are baked directly into the TDD's Armor section rather
than emerging as deltas (deltas are a brownfield concept). The MUC-to-primitive
translation is the same — replay guard, rate limiter, audit logger, integrity
verifier, etc. — but it appears in the TDD's Armor inventory, not as HD-NNN files.

---

## Gotchas

- **One gap, one delta.** Do not bundle "harden all of service X" into one
  delta. The delta graph cannot express bundled work and the failing-test
  discipline gets diluted.
- **Failing test first.** A delta without a failing characterisation test is
  not accepted. If you cannot write a test that proves the gap exists today,
  reconsider whether it is actually a gap.
- **Status transitions are linear.** `proposed → accepted → implemented → verified`.
  Skipping `implemented` because "the test passes locally" is not allowed.
- **Severity is operational, not aesthetic.** "high" means "production
  incident probable within the next 90 days". Don't inflate severity for
  unrelated cleanup.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-12 | Initial format spec. Adapts OpenSpec delta convention for SEA's hardening output. |
| 0.2.0 | 2026-05-13 | Added optional `source` frontmatter field for upstream provenance (SRD misuse cases, SRD negative requirements, sulis-security findings, NFRs). Added "Misuse-Case-to-Delta Translation" section with the MUC → HD mapping pattern, the MUC-04 → HD-007 worked example, and the audit/blueprint usage notes. |
