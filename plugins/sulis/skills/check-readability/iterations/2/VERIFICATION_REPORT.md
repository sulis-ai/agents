# VERIFICATION_REPORT.md — sulis:check-readability (iteration 2)

**Skill:** `sulis/check-readability`
**Iteration:** 2 (tool-wrapper integration)
**Produced:** 2026-05-24

## Spiral Summary

**Tier:** standard / **Template:** STANDARD_TIER_DEFAULT / **Iterations used:** 2 / **Verdict:** PASS

## Primitive coverage (iteration 2)

| Primitive | iter 1 | iter 2 | Source |
|-----------|--------|--------|--------|
| Naming clarity (existing) | PASS | PASS | existing heuristic |
| Kitchen-sink file (existing) | PASS | PASS | existing heuristic |
| Jargon density (existing) | PASS | PASS | existing heuristic |
| CQ-01 cyclomatic complexity | NOT_ASSESSED | **PASS** | lizard (CSV output; threshold CCN ≥ 15) |
| CQ-03 code duplication | NOT_ASSESSED | **PASS** | jscpd (min 5 lines / 50 tokens) |

**Coverage:** 5 of 5 primitives PASS (100%).

## Spiral Verification (iteration 2 re-score)

| Dimension | Threshold | iter 1 | iter 2 |
|-----------|-----------|--------|--------|
| ACCA (min) | >= 4 | 4 | 4 |
| Evidence Grounding | >= 4 | 4 | 5 |
| Structural Coherence | >= 4 | 4 | 4 |
| Honest Uncertainty | >= 3 | 5 | 5 |
| Codebase Referential Integrity | >= 4 | 4 (NEW flagged) | **5** (lizard.py + jscpd.py exist at `_lib/tools/`) |
| Primitive Coverage Completeness (custom) | >= 4 | 3 (DEFERRED) | **5** |

**Verdict:** PASS

## Live test on agents marketplace

Lizard found **20+ findings** across IDC scripts with CCN ≥ 15 — surface examples:

- `plugins/idc/scripts/build_review_html.py:59` — render_markdown CCN=21
- `plugins/idc/scripts/build_finance_html.py:63` — build_html CCN=high
- `plugins/idc/scripts/build_pptx.py:206` — render_slide CCN=high
- `plugins/idc/scripts/build_investor_financials.py:73` — build_html CCN=high

These are real complexity hotspots invisible to the naming/jargon heuristic.

jscpd: scanned; no duplications above threshold detected on this marketplace.

## Gate 5 — Adversarial Review (iteration 2)

All iteration-1 misuse cases (CQ-01/CQ-03 NOT_ASSESSED blur, jscpd npx-fallback variance, lizard pip-fallback variance) — now PREVENTED. The wrappers verify tool version on every invocation; the renderer surfaces NOT_ASSESSED when neither Docker nor native is available.
