# Recipe: backfill security review for a missed-gate batch

**Applies to:** sulis-execution v0.20.2+

**When to use:** you've shipped WPs through `wpx-train run` on a plugin
version BEFORE `v0.20.0` (which added Step 11 to the per-batch flow).
Those WPs landed on dev without any post-deploy security review.

This recipe walks through using the `/sulis-execution:backfill-gates`
skill (v0.20.2+) to catch up retroactively.

## Background

In `sulis-execution` versions `v0.11.0` through `v0.20.0-`, the train's
per-batch flow shipped WPs via:

```
wpx-train run → rebase → bundled-tip CI → sequential merge → deploy → health → smoke
```

That covered Steps 8–10 of the executor lifecycle (CI / merge / deploy
/ verification). **Step 11 — post-deploy security review — was missing**.
The Step 11 dispatch logic lived in the v0.10.7 fallback section of
`run-all/SKILL.md`, explicitly marked "do not invoke in v0.11.0+". A
documentation oversight; no per-batch Step 11 ran.

**Impact:** any WP shipped via train in that window had zero security
review. Findings register has no entries for those WPs.

**Fix:** v0.20.0 wired Step 11 back into per-batch flow. Going forward,
the gate runs after each successful train. To recover the missed
window, v0.20.2 ships `/sulis-execution:backfill-gates`.

## Procedure

### Step 1: Identify the gap window

Find the version of sulis-execution that was active when the missed
WPs shipped:

```bash
# Look at the .yaml record for one of the shipped trains
ls -t .architecture/<project>/train-runs/train-*.yaml | head -1 | xargs cat | head -20

# Compare with .claude/plugins/cache/sulis-ai-agents/sulis-execution/
ls -t ~/.claude/plugins/cache/sulis-ai-agents/sulis-execution/
```

If trains shipped under versions `v0.11.0` through `v0.20.0-` (i.e.,
pre-`0.20.0`), you have a gap.

### Step 2: Invoke the backfill skill (iteration 1)

In a Claude Code session with `sulis-execution v0.20.2+` installed:

```
/sulis-execution:backfill-gates \
  --project <slug> \
  --repo <org/repo> \
  --deployed-url https://<staging-url> \
  --max-remediation 10
```

What happens:

1. The skill invokes `/sulis-security:codebase-assess` over the
   project's current `dev` state.
2. The assessor produces `.security/<slug>/viability-report-<TS>.md`
   with findings categorised by primitive (Security / Data Protection
   / Code Quality / Supply Chain / Infrastructure).
3. The skill parses findings, registers them via `wpx-findings register`,
   and auto-drafts up to 10 remediation WPs (`WP-AUTO-NNN`) via
   `wpx-findings auto-draft-wp`.
4. A summary report lands at `.security/<slug>/backfill-<TS>/SUMMARY.md`.

### Step 3: Founder reviews drafted WPs

The auto-drafted WPs are at status `auto-draft`. Founder judgement
filters which to ship:

```bash
# List drafted
ls .architecture/<slug>/work-packages/WP-AUTO-*.md

# Promote each to pending after review
wpx-index flip-status --wp WP-AUTO-NNN --project <slug> \
  --to pending --expected auto-draft

# Or cancel if not actionable (e.g. assessor false positive)
wpx-index flip-status --wp WP-AUTO-NNN --project <slug> \
  --to cancelled --expected auto-draft
```

### Step 4: Ship promoted remediation WPs

```bash
wpx-train run \
  --project <slug> \
  --repo <org/repo> \
  --deploy-workflow "<workflow>" \
  --staging-url https://<staging-url> \
  --smoke-cmd "<smoke command>" \
  --force  # if fewer than 3 WPs eligible
```

With v0.20.0+'s Step 11 active, each remediation WP is itself reviewed
post-deploy — so any regression introduced by the fix is caught
immediately.

### Step 5: Iterate

After the train ships, re-invoke:

```
/sulis-execution:backfill-gates \
  --project <slug> \
  --repo <org/repo> \
  --deployed-url https://<staging-url>
```

The signature-hash dedup in `wpx-findings register` ensures
previously-known findings don't auto-draft duplicate WPs. Each
iteration's new findings reflect what the latest dev state still has.

### Step 6: Terminate

The loop terminates when:

- An iteration produces ZERO new findings (the codebase is clean
  from the assessor's perspective), OR
- The remaining findings are explicitly deferred (founder-approved
  notes at `.security/<slug>/deferred-critical-<SF-ID>.md`)

Most projects converge in 3–5 iterations.

## Why this is human-in-the-loop

The skill terminates at the end of one iteration. The founder must
review + promote + ship before re-invoking for iteration N+1. This
is deliberate:

- Auto-drafted WPs can be noisy (assessor false positives, scope
  questions). Founder judgement filters.
- Shipping (`wpx-train run`) is itself a deliberate action — auto-
  firing trains without founder approval would violate the change-
  approval contract.
- The convergence is visible to the founder at each iteration —
  they see fewer remediation WPs each cycle, and stop when they
  see zero.

## Programmatic surface (SDK)

The skill orchestrates these SDK operations (available in
`sulis-execution v0.2.3+`):

```python
from sulis_execution import SulisExecution

client = SulisExecution(repo_root=".", project="<slug>")

# Register a finding (returns is_duplicate + sf_id + auto_wp_id)
result = client.findings.register(
    wp="backfill-<TS>",
    severity="CONCERN",
    summary="No rate limiting on /api/auth/login",
    file="apps/api/routes/auth.py",
    suggested_fix="...",
    primitive="SEC-08",
    evidence_json="@/tmp/finding-1.json",
)

if not result.is_duplicate:
    # Auto-draft a remediation WP
    draft = client.findings.draft_remediation(
        source_finding=result.sf_id,
        source_wp="backfill-<TS>",
        auto_wp_id=result.auto_wp_id,
        primitive="Gate",
        severity="CONCERN",
    )
    # Register in INDEX
    client.index.add(wp=result.auto_wp_id, from_wp_file=True)
```

Note: codebase-assess invocation itself is a top-level skill call
(not an SDK operation) — the SDK handles state-changing CLI
operations, not Agent dispatch.

## See also

- `plugins/sulis-execution/skills/backfill-gates/SKILL.md` —
  the skill body (procedure)
- `plugins/sulis-execution/skills/backfill-gates/recipes/post-rollout.md`
  — same recipe, more narrative
- `plugins/sulis-execution/skills/run-all/SKILL.md` — per-batch Step 11
  (forward gate this skill complements)
- `plugins/sulis-security/skills/codebase-assess/SKILL.md` — the
  whole-codebase assessor this skill orchestrates
