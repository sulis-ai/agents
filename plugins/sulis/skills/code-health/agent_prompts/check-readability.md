# Agent prompt — check-readability (tier 5 Understandable)

You are an independent runner for tier 5 (Understandable) of code-health.
Read `_shared-contract.md` for the output contract.

## Your scope

Tier 5 — Understandable — covers:
- Naming clarity per identifier
- Module cohesion / kitchen-sink-file detection
- Jargon density per module
- CQ-01 cyclomatic complexity (lizard)
- CQ-03 code duplication (jscpd)

## Run the scanner

```bash
cd {repo_root}
python3 plugins/sulis/skills/check-readability/scripts/audit.py \
  --repo-root {repo_root} \
  --project {project} \
  --scope codebase \
  --raw
```

## Apply interpretation lenses

1. **Complexity cluster detection** — if many CCN findings cluster in
   one module (e.g., 10+ findings in `plugins/X/`), surface as a
   single "complexity cluster" finding rather than 10 individual ones.
   Example: "Cluster: 11 functions over CCN 15 in
   `plugins/sea/skills/probe/` — candidate for refactor."

2. **MUC-F4 cap** — ≤ 10 individual findings (after cluster collapsing).
   For complexity, prefer surfacing the worst 5 by CCN value.

3. **Test file exclusion** — naming-clarity findings in test files
   are lower priority; mark as informational unless they conflict
   with production code names.

## Verdict assignment

- PASS — 0 high findings, ≤ 3 concerns
- NEEDS_ATTENTION — 4+ concerns OR 1+ high (CCN ≥ 25)
- FAILED — 1+ critical (rare for this tier; kitchen-sink with
  >25 concerns or naming conflicting across module boundaries)

## Return per the shared contract format
