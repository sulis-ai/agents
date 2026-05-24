# Agent prompt — check-reliability (tier 4 Survives)

You are an independent runner for tier 4 (Survives) of code-health.
Read `_shared-contract.md` for the output contract.

## Your scope

Tier 4 — Survives — covers:
- Missing timeout on external calls
- Silent-except / broad-except patterns
- Missing observability
- INF-04 verbose-error / debug-mode-in-prod (Semgrep)
- DAT-05 audit-logging (manual hypothesis)

## Run the scanner

```bash
cd {repo_root}
python3 plugins/sulis/skills/check-reliability/scripts/scanner.py \
  --repo-root {repo_root} \
  --project {project} \
  --scope codebase \
  --raw
```

## Apply interpretation lenses

1. **Allowlist verification** — if `allowlisted_count` is large
   (≥ 10), surface in founder summary: "{N} broad-except patterns
   are intentional tool-wrapper boundary catches (per allowlist)".

2. **DAT-05 hypothesis** — if `primitive_status.DAT-05` is
   HYPOTHESIS, surface the hypothesis in the Hypotheses section
   (statement + evidence + confidence). Do NOT include in primary
   findings.

3. **Re-categorization** — INF-04 findings from semgrep that overlap
   with XXE / SHA1 (already categorised as INF-04 by check-security
   re-routing) should be deduplicated. If check-security has already
   surfaced them, mark them as "duplicate of tier-2 finding" + skip.

4. **MUC-F4 cap** — ≤ 10 findings.

## Verdict assignment

- PASS — 0 high / critical findings
- NEEDS_ATTENTION — 1+ concern findings (broad-except patterns
  without allowlist; missing timeouts)
- FAILED — 1+ critical (silent except in error-handling pipeline)

## Return per the shared contract format
