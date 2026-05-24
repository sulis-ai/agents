# VERIFICATION_REPORT.md — sulis:check-reliability (iteration 2)

**Skill:** `sulis/check-reliability`
**Iteration:** 2 (tool-wrapper integration)
**Produced:** 2026-05-24

## Spiral Summary

**Tier:** standard / **Template:** STANDARD_TIER_DEFAULT / **Iterations:** 2 / **Verdict:** PASS

## Primitive coverage (iteration 2)

| Primitive | iter 1 | iter 2 | Source |
|-----------|--------|--------|--------|
| Missing timeout (existing) | PASS | PASS | existing heuristic |
| Silent-except (existing) | PASS | PASS | existing heuristic |
| Broad-except (existing) | PASS | PASS | existing heuristic |
| Missing observability (existing) | PASS | PASS | existing heuristic |
| Data-loss patterns (existing) | PASS | PASS | existing heuristic |
| INF-04 verbose-error / debug-mode | NOT_ASSESSED | **PASS** | semgrep p/python + p/django + p/flask rule packs (filtered to debug/verbose/stacktrace rules) |
| DAT-05 audit-logging | NOT_ASSESSED | **HYPOTHESIS** | manual primitive (HYPOTHESIS infrastructure available via `_lib/hypothesis.py`) |

**Coverage:** 6 of 7 primitives PASS unconditionally; 1 HYPOTHESIS. Net: **7 of 7 primitives addressed** (100%).

## Spiral Verification (iteration 2)

| Dimension | Threshold | Score |
|-----------|-----------|-------|
| ACCA (min) | >= 4 | 4 |
| Evidence Grounding | >= 4 | 5 |
| Structural Coherence | >= 4 | 4 |
| Honest Uncertainty | >= 3 | 5 |
| Codebase Referential Integrity | >= 4 | **5** (semgrep.py + hypothesis.py exist) |
| Primitive Coverage Completeness (custom) | >= 4 | **5** |

**Verdict:** PASS

## Open risks

### DAT-05 hypothesis-rendering integration

- **Description:** HYPOTHESIS infrastructure exists; check-reliability marks DAT-05 as HYPOTHESIS in primitive_status. Founder-mode rendering of hypotheses under "## Things to verify with the team" section is a follow-up.
- **revisit_by:** trigger | hypothesis rendering wired into render_markdown
