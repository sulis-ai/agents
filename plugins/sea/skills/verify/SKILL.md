---
name: verify
description: >
  Use after Work Packages have been implemented to verify the architecture
  is complete, hardened, and proven. Runs five verification perspectives
  against the codebase and the architecture artifacts — pillar coverage
  (MECE-3), WP completion, contract test coverage, chaos test coverage, and
  referential integrity between TDD/ADRs/WPs/code. Produces
  COMPLETENESS_REPORT.md with a PASS or GAPS_FOUND verdict.
---

# Verify — Architecture Completeness Check

When invoked, run a five-perspective check across the architecture artifacts
and the codebase. Produce `.architecture/{project}/COMPLETENESS_REPORT.md`
with a PASS or GAPS_FOUND verdict and a remediation list if gaps exist.

If arguments are provided, treat them as the project name. If not, infer
from the most recently modified folder in `.architecture/`.

---

## The Five Perspectives

### P1: Pillar Coverage (MECE-3)

Does the TDD address all three pillars for every component?

- For each component in `TDD §3.1` (Component Inventory):
  - Form covered? (module placement, dependencies, port/adapter clear?)
  - Armor covered? (does the External Dependencies table list this component if it makes external calls?)
  - Proof covered? (does §5 list a contract test for each port?)

A component missing any pillar is a P1 gap.

### P2: WP Completion

Does every WP exist, and is every WP either `done` or scheduled?

- Read `work-packages/INDEX.md`.
- Count WPs by status.
- For each `done` WP, confirm the Acceptance Evidence section is filled
  (commit SHAs present, PR link present, CI run referenced).
- For each `in_progress` WP, confirm it has been in_progress < 14 days
  (otherwise it is staleness).
- For each `blocked` WP, confirm its `dependsOn` is genuinely unmet.

A WP in `done` status without acceptance evidence is a P2 gap.

### P3: Contract Test Coverage

Does every port have a contract test exercised by every adapter?

- Parse the TDD for ports listed in §3.3.
- For each port, locate the contract test file.
- For each adapter implementing that port (production + in-memory), confirm
  it runs the contract test in CI.

A port with no contract test, or an adapter that doesn't share the test, is
a P3 gap.

### P4: Chaos Test Coverage

Does every resilience primitive from `TDD §4.1` have a chaos test from
`TDD §5.3`?

- Cross-reference the External Dependencies table (§4.1) with the chaos
  test list (§5.3).
- For each timeout, retry policy, and circuit breaker, confirm a chaos test
  exists that injects the failure and asserts the primitive's behaviour.

A resilience primitive without a chaos test is a P4 gap (MEA-10 violation).

### P5: Referential Integrity

Is everything consistent across TDD, ADRs, WPs, and code?

- Every WP's `tdd_section` field points to a real TDD section.
- Every WP's `adrs` field points to existing ADR files.
- Every ADR referenced by a WP has `status: accepted` (not `proposed`,
  not `superseded`).
- Every `dependsOn` and `blocks` arc in the WP graph is reciprocal (if
  WP-A `blocks` WP-B, then WP-B `dependsOn` WP-A).
- Every file path referenced in WPs or HDs exists in the codebase (for
  status: done items).
- Every Hardening Delta with `status: implemented` has the commits it
  claims (smoke-check git history).

A broken reference is a P5 gap.

---

## Workflow

1. **Inventory** — list all architecture artifacts under
   `.architecture/{project}/`, all spec artifacts under
   `.specifications/{project}/`, and the codebase top-level structure.
2. **Run P1** — pillar coverage scan. Record gaps.
3. **Run P2** — WP completion scan. Record gaps.
4. **Run P3** — contract test coverage. Use `grep` or AST tooling to locate
   contract test files. Record gaps.
5. **Run P4** — chaos test coverage. Cross-reference §4.1 ↔ §5.3 in the
   TDD. Record gaps.
6. **Run P5** — referential integrity. Walk every cross-reference. Record
   gaps.
7. **Score** — count gaps per perspective.
8. **Emit verdict:**
   - **PASS** — no gaps across all five perspectives.
   - **GAPS_FOUND** — one or more gaps. Verdict includes the gap list and
     suggested remediation (often one or more new WPs or HDs).
9. **Write `COMPLETENESS_REPORT.md`**.

---

## Report Structure

```markdown
# {Project} — Architecture Completeness Report

> **Date:** YYYY-MM-DD
> **Verdict:** PASS | GAPS_FOUND
> **Project:** .architecture/{project}/
> **Spec:** .specifications/{project}/

## Summary

| Perspective | Result | Gaps |
|---|---|---|
| P1 — Pillar Coverage | PASS \| GAPS | N |
| P2 — WP Completion | PASS \| GAPS | N |
| P3 — Contract Test Coverage | PASS \| GAPS | N |
| P4 — Chaos Test Coverage | PASS \| GAPS | N |
| P5 — Referential Integrity | PASS \| GAPS | N |

## P1 — Pillar Coverage

{For each component, table of Form/Armor/Proof coverage.}

| Component | Form | Armor | Proof | Notes |
|---|---|---|---|---|
| Order Application Service | ✓ | ✓ | ✓ | |
| Payment Adapter | ✓ | ✗ | ✓ | No CB configured in §4.1 |

Gaps:
- Payment Adapter is missing Armor (no circuit breaker in TDD §4.1).
  → Remediation: file HD-NNN to add CB, or update TDD §4.1.

## P2 — WP Completion

- Pending: N
- In progress: N (M stale > 14 days)
- Done: N (M missing acceptance evidence)
- Blocked: N (M genuinely vs M overdue)

Gaps:
- WP-007 marked done but no acceptance evidence.
  → Remediation: add commit SHAs to the WP, or revert to in_progress.

## P3 — Contract Test Coverage

| Port | Contract test | Adapters covered |
|---|---|---|
| OrderRepository | tests/contracts/OrderRepositoryContract.ts | Postgres ✓, InMemory ✓ |
| PaymentGateway | (missing) | — |

Gaps:
- PaymentGateway has no contract test.
  → Remediation: file WP-NNN to add contract test.

## P4 — Chaos Test Coverage

| Primitive | Chaos test | Status |
|---|---|---|
| Stripe timeout (2s) | chaos/payments.test.ts::timesOutWithin2s | ✓ |
| Stripe circuit breaker | (missing) | ✗ |

Gaps:
- Stripe circuit breaker is in §4.1 but has no chaos test in §5.3.
  → Remediation: file WP-NNN to add chaos test for CB open/close.

## P5 — Referential Integrity

| Check | Result | Detail |
|---|---|---|
| WP → TDD section | 14/14 | All WPs reference live sections |
| WP → ADR | 11/12 | WP-007 references ADR-005 (missing) |
| ADR status valid | 7/7 | All referenced ADRs are accepted |
| dependsOn/blocks symmetry | 22/22 | All arcs reciprocal |
| File paths exist (done WPs) | 9/10 | WP-003 references `src/legacy/old.ts` (missing) |
| HD commits exist | 6/6 | All implemented HDs verified |

Gaps:
- WP-007 references ADR-005 which does not exist.
  → Remediation: either create ADR-005 or remove the reference.

## Remediation Summary

| Gap | Type | Suggested Action |
|---|---|---|
| Payment Adapter missing CB | P1 | File HD-NNN |
| WP-007 missing evidence | P2 | Backfill or revert status |
| PaymentGateway contract test | P3 | New WP |
| Stripe CB chaos test | P4 | New WP |
| WP-007 references missing ADR | P5 | Create ADR-005 or update WP-007 |

## Next Steps

{Either: "All five perspectives PASS. Architecture is verified."
 Or: "5 gaps found. Remediate, then re-run /sea:verify."}
```

---

## Verdict Rules

- **PASS** — all five perspectives have zero gaps.
- **GAPS_FOUND** — one or more perspectives report a gap. The report lists
  every gap with a suggested remediation.

`/sea:verify` does not block delivery on its own. The user (or an
orchestrator) decides whether GAPS_FOUND is acceptable for this milestone.
SEA's job is honesty, not gatekeeping.

---

## Adapting Depth

- **Quick** ("smoke check") — run P5 only (referential integrity). Catches drift fast. ~5 minutes.
- **Full** (default) — all five perspectives.
- **Pillar-focused** (e.g. `/sea:verify --pillar=armor`) — run P1 and P4 only, scoped to one pillar. Useful for "are we hardened enough to ship?" before release.

**Tier-aware perspective depth.** Read tier from
`.architecture/{project}/SIZING.md` if present, falling back to `TDD.md`'s
Sizing Report appendix. Per `references/right-sizing.md`:

- Tier S: every perspective in compressed form; verification report ~1 page.
- Tier M: every perspective in standard form; ~2-4 page report.
- Tier L: every perspective in full form; per-pillar tables of findings.
- Tier XL: per-bounded-context verification reports + system-level summary.

A tier-S verification report that runs to 20 pages is over-engineered.
A tier-L verification report that runs to 1 page is under-engineered.
Match the tier or surface why you're not matching it.

**Verify also enforces sizing circuit breakers.** If TDD.md was shipped
with a circuit-breaker violation (length > 1.5× target, ADRs > tier max,
section restated authoritative source) and no justification paragraph,
flag it as a perspective finding.

---

## Gotchas

- **Don't auto-remediate.** This skill produces a report. Fixing the gaps is
  a separate decision (which the user makes) and a separate action (file new
  WPs or HDs, run `/sea:harden`, etc.).
- **PASS is not "good architecture".** PASS means "the artifacts are
  internally consistent and the documented hardening exists". An architecture
  with shallow NFRs can still PASS — `/sea:verify` validates against the
  TDD, not against external best practice.
- **Staleness is a real gap.** A WP `in_progress` for 14+ days is a gap not
  because of the calendar but because of merge-conflict risk. Surface it.
- **Don't grade Hardening Deltas alongside WPs.** They are tracked
  separately. The `INDEX.md` for HDs is the source of truth for delta status,
  not the WP INDEX.

---

## See Also

- `references/mece-3-architecture.md` — the pillars P1 checks (plugin root)
- `references/red-green-blue.md` — the cycle WPs must follow (plugin root)
- SRD's `requirements-validation` skill — analogue for the requirements layer
