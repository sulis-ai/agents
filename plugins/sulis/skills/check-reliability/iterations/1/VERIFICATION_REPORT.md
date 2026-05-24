# VERIFICATION_REPORT.md — sulis:check-reliability

**Skill:** `sulis/check-reliability`
**Iteration:** 1 (first upsurge against v0.7.0 methodology)
**Produced:** 2026-05-24
**Methodology:** `sulis:add-skill` v0.7.0 (standards-grounded) in deepening mode

## Spiral Summary

**Tier:** standard / **Template:** STANDARD_TIER_DEFAULT / **Iterations:** 1 of 3 / **Verdict:** APPROVED-WITH-RISK

## Gate 1 — Find + Primitive Discovery

**Primitives identified (level: skill-scope):**

| Primitive | Provenance | Status |
|-----------|------------|--------|
| Missing timeout on external calls (existing) | extracted | PASS |
| Silent-except / broad-except (existing) | extracted | PASS |
| Missing observability (existing) | extracted | PASS |
| Data-loss patterns (existing) | extracted | PASS |
| INF-04 verbose-error / debug-mode-in-prod | extracted from codebase-assess primitives.md | NOT_ASSESSED — semgrep wrapper NEW |
| DAT-05 audit-logging (manual hypothesis) | extracted | NOT_ASSESSED — HYPOTHESIS output infrastructure not yet built |

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Verification tier | STANDARD |
| Tool stack | Semgrep (INF-04 rule pack) + grep + heuristic (DAT-05). Foundation present; semgrep.py wrapper NEW (also flagged by check-security). |
| Audience | both |

## Gate 4 — Spiral Verification

| Dimension | Threshold | Score |
|-----------|-----------|-------|
| ACCA (min) | >= 4 | 4 |
| Evidence Grounding | >= 4 | 4 |
| Structural Coherence | >= 4 | 4 |
| Honest Uncertainty | >= 3 | 5 |
| Codebase Referential Integrity | >= 4 | 4 (semgrep flagged NEW) |
| Primitive Coverage Completeness (custom) | >= 4 | 3 (DEFERRED) |

**Verdict:** PASS for required dimensions; Primitive Coverage Completeness DEFERRED with revisit_by: trigger | semgrep.py + hypothesis infrastructure integrated.

## Gate 5 — Adversarial Review

### Misuse case 1: INF-04 NOT_ASSESSED rendered as ✅

- **Status:** PREVENTED in iteration 2+ via SPIRAL_TEMPLATES rendering policy.

### Misuse case 2: DAT-05 hypothesis output mistaken for finding

- **Status:** OPEN_RISK; revisit_by: trigger | `_lib/hypothesis.py` infrastructure + code-health renderer surfaces hypotheses under "## Things to verify with the team" section.

### Misuse case 3: Silent regex fallback when Semgrep unavailable

- **Status:** PREVENTED by `_lib/tools/_runner.py` NOT_ASSESSED degradation policy.

## Open risks

### Risk 1: INF-04 + DAT-05 NOT_ASSESSED until iteration 2

- **revisit_by:** trigger | semgrep.py + hypothesis infrastructure integrated.
