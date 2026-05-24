# VERIFICATION_REPORT.md — sulis:check-maintainability

**Skill:** `sulis/check-maintainability`
**Iteration:** 1 (first upsurge against v0.7.0 methodology)
**Produced:** 2026-05-24
**Methodology:** `sulis:add-skill` v0.7.0 (standards-grounded) in deepening mode

## Spiral Summary

**Tier:** standard / **Template:** STANDARD_TIER_DEFAULT / **Iterations:** 1 of 3 / **Verdict:** APPROVED-WITH-RISK

## Gate 1 — Find + Primitive Discovery

**Primitives identified (level: skill-scope):**

| Primitive | Provenance | Status |
|-----------|------------|--------|
| Dead-code detection (existing; extensionless-script-aware) | extracted | PASS |
| CQ-05 review practices (git-log analysis) | extracted from codebase-assess primitives.md | NOT_ASSESSED — git-log analysis function not yet built; HYPOTHESIS infrastructure not yet present |

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Verification tier | STANDARD |
| Tool stack | git (native; always available) for log analysis. No external tool wrapper needed; CQ-05 is implemented in-skill as a git-log analysis function (heuristic + hypothesis output). |
| Audience | both |

## Gate 4 — Spiral Verification

| Dimension | Threshold | Score |
|-----------|-----------|-------|
| ACCA (min) | >= 4 | 4 |
| Evidence Grounding | >= 4 | 4 |
| Structural Coherence | >= 4 | 4 |
| Honest Uncertainty | >= 3 | 5 |
| Codebase Referential Integrity | >= 4 | 4 (git is native; HYPOTHESIS infrastructure flagged NEW) |
| Primitive Coverage Completeness (custom) | >= 4 | 3 (DEFERRED) |

**Verdict:** PASS for required dimensions; Primitive Coverage Completeness DEFERRED with revisit_by: trigger | git-log CQ-05 analysis function + HYPOTHESIS infrastructure integrated.

## Gate 5 — Adversarial Review

### Misuse case 1: CQ-05 hypothesis read as fact

- **Status:** OPEN_RISK; revisit_by: trigger | `_lib/hypothesis.py` Hypothesis dataclass with confidence field + verification_question; code-health renders under "## Things to verify with the team" section.

### Misuse case 2: git-log analysis fails on shallow clones

- **Status:** OPEN_RISK; revisit_by: trigger | check-maintainability iteration 2 invokes `git fetch --unshallow` similar to check-security gitleaks pattern.

### Misuse case 3: Dead-code false-positives on extensionless scripts (existing — fixed in v0.12.0)

- **Status:** PREVENTED — already fixed via shebang-detection in walker.

## Open risks

### Risk 1: CQ-05 NOT_ASSESSED until iteration 2

- **revisit_by:** trigger | git-log analysis function + `_lib/hypothesis.py` integrated.
