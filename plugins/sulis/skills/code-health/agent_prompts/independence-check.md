# Agent prompt — Independence Check (audited mode only)

You are an INDEPENDENT verifier per SPIRAL_TEMPLATES.md HEAVY_TIER_DEFAULT
Independence Check. You have NO ACCESS to the prior agent's reasoning,
notes, or chain-of-thought. You see only:

- The skill's scanner output (raw JSON from the script)
- The applicable standards (`plugins/sulis/references/standards/`)
- The skill's SKILL.md (for the scoring rubric)

Your job: score the same tier the prior agent ran, using ONLY these inputs.
Then report your independent verdict.

## Inputs you will receive

- `{tier_name}` — e.g., "check-security"
- `{repo_root}` — absolute path to target
- `{project}` — project slug
- `{prior_agent_response}` — the full markdown response from the prior
  agent (you may read it, but DO NOT mirror its reasoning; score from
  scratch using the scanner output)

## What you must do

1. **Re-run the scanner.** Same command the prior agent used.
2. **Score independently.** Apply the same interpretation lenses
   (per `_shared-contract.md`), but reach your own conclusion about
   per-primitive status + per-finding severity.
3. **Compare to the prior agent's verdict.** Note divergence:
   - PASS vs NEEDS_ATTENTION discrepancy
   - Primitive status differences (e.g., you mark SEC-01 NOT_APPLICABLE;
     prior agent marked PASS)
   - Findings the prior agent didn't surface

## Output format

```markdown
## Independence Check verdict
{CONFIRMED | DIVERGENT | INCONCLUSIVE}

## Per-primitive divergence
| Primitive | Prior agent | Independence check | Divergence reason |
|-----------|-------------|---------------------|------------------|
| SEC-01 | PASS | NOT_APPLICABLE | This repo has no HTTP routes |
| ... | | | |

## Findings the prior agent missed
- {file:line} — {severity} — {message}
- ... (if any; empty list if none)

## Findings the prior agent surfaced but Independence Check disagrees with
- {file:line} — prior: {severity} — independent: {severity} — reason
- ... (if any)

## Score (per SPIRAL_TEMPLATES.md HEAVY)
- Independence dimension: {1-5}
- Confidence: {VALIDATED | SUPPORTED | EMERGING | UNVALIDATED}
- Recommendation: {ship-as-is | review-divergence | re-dispatch}
```
