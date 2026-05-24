# VERIFICATION_REPORT.md — sulis:check-tests

**Skill:** `sulis/check-tests`
**Iteration:** 1 (first upsurge against v0.7.0 methodology)
**Produced:** 2026-05-24
**Methodology:** `sulis:add-skill` v0.7.0 (standards-grounded) in deepening mode

## Spiral Summary

**Tier:** standard / **Template:** STANDARD_TIER_DEFAULT / **Iterations:** 1 of 3 / **Verdict:** APPROVED-WITH-RISK

## Gate 1 — Find + Primitive Discovery

**Primitives identified (level: skill-scope):**

| Primitive | Provenance | Status |
|-----------|------------|--------|
| Test regression detection (existing) | extracted | PASS |
| CQ-02 test coverage quality | extracted from codebase-assess primitives.md | NOT_ASSESSED — coverage.py wrapper NEW |

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Verification tier | STANDARD |
| Tool stack | pytest-cov / vitest coverage / jest coverage (per-framework integration). Foundation present; coverage.py wrapper NEW. |
| Audience | both |

## Gate 4 — Spiral Verification

| Dimension | Threshold | Score |
|-----------|-----------|-------|
| ACCA (min) | >= 4 | 4 |
| Evidence Grounding | >= 4 | 4 |
| Structural Coherence | >= 4 | 4 |
| Honest Uncertainty | >= 3 | 5 |
| Codebase Referential Integrity | >= 4 | 4 |
| Primitive Coverage Completeness (custom) | >= 4 | 3 (DEFERRED) |

**Verdict:** PASS for required dimensions; Primitive Coverage Completeness DEFERRED with revisit_by: trigger | coverage.py wrapper integrated.

## Gate 5 — Adversarial Review

### Misuse case 1: CQ-02 NOT_ASSESSED rendered as ✅

- **Status:** PREVENTED in iteration 2+ via SPIRAL_TEMPLATES policy (NOT_ASSESSED renders explicitly distinct from PASS).

### Misuse case 2: pytest-cov absent on founder's machine

- **Status:** PREVENTED by `_lib/tools/_runner.py` degradation policy.

### Misuse case 3: Per-framework coverage tool detection drift

- **Status:** OPEN_RISK; revisit_by: trigger | coverage.py wrapper introduces auto-detection registry.

## Open risks

### Risk 1: CQ-02 NOT_ASSESSED until coverage.py wrapper built

- **revisit_by:** trigger | coverage.py wrapper integrated.
