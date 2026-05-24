# Agent prompt — check-maintainability (tier 6 Evolves)

You are an independent runner for tier 6 (Evolves) of code-health.
Read `_shared-contract.md` for the output contract.

## Your scope

Tier 6 — Evolves — covers:
- Dead-code detection (unused functions / classes / imports / constants)
- CQ-05 review practices (git-log analysis + PR template detection)

## Run the scanner

```bash
cd {repo_root}
python3 plugins/sulis/skills/check-maintainability/scripts/scanner.py \
  --repo-root {repo_root} \
  --project {project} \
  --scope codebase \
  --raw
```

## Apply interpretation lenses

1. **CQ-05 hypothesis** — `primitive_status.CQ-05` is always
   HYPOTHESIS. Surface the hypothesis (statement + evidence +
   confidence) in the Hypotheses section. Do NOT include in primary
   findings.

2. **Dead-code is advisory** — all dead-code findings ship at
   advisory severity (FP-philosophy lock per the skill). Do NOT
   escalate severity even if many findings.

3. **Hidden-reference detection** — dead-code findings on files
   that are entry-points (CLI scripts, agent prompt files) are often
   false positives. Note in founder summary: "These may be entry
   points called from outside the Python import graph; verify
   before deleting."

4. **MUC-F4 cap** — ≤ 10 dead-code findings.

## Verdict assignment

- PASS — 0 findings + CQ-05 hypothesis is not CONTRADICTED
- NEEDS_ATTENTION — 1+ dead-code findings (always advisory)
  OR CQ-05 hypothesis shows degraded review practices
- FAILED — rare; only if CQ-05 hypothesis is HIGH-confidence
  contradicted (i.e., team review practices are demonstrably broken)

## Return per the shared contract format
