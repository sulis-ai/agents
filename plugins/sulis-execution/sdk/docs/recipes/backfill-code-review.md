# Recipe: backfill code-review for missed-gate WPs

**Applies to:** sulis-execution v0.21.0+

**When to use:** WPs shipped via `wpx-train run` BEFORE `v0.20.1`
may have substituted inline self-attestation for actual
`/sulis:code-review` invocation. The historical record shows
"Step 6.5: 0 findings" in journals but no `.architecture/.../
code-reviews/PR-*/REVIEW.md` bundle on disk.

This recipe walks through `/sulis-execution:backfill-code-review`
to catch up retroactively.

## Background

The Step 6.5 gate (per-WP code-review before push) was MUST
since `v0.16.0`, but enforcement was advisory until `v0.20.1`.
Pre-v0.20.1 executors could declare "0 findings" without invoking
the skill. The slice-2 audit (2026-05-22) found 9 of 12 WPs
took this shortcut.

`v0.20.1` closed the gate forward — executors now write BLOCKER
`trigger=code-review-skipped` if the bundle is missing.
`v0.21.0` ships this skill to retroactively cover the
historical gap.

## Procedure

### Step 1: Identify the gap

Compare shipped WPs (with `merge_sha_on_dev` set in train state
YAMLs) against existing code-review bundles:

```bash
PROJECT=agent-applications

# Shipped WPs
ls .architecture/$PROJECT/train-runs/train-*.yaml | wc -l

# WPs with bundles
ls -d .architecture/$PROJECT/code-reviews/PR-feat-wp-*-*/ 2>/dev/null | wc -l
```

If bundle count < shipped-WP count, you have a gap.

### Step 2: Run iteration 1

In a Claude Code session with `sulis-execution v0.21.0+`:

```
/sulis-execution:backfill-code-review \
  --project <slug> \
  --repo <org/repo> \
  --max-remediation 10
```

The skill:

1. Auto-scans `.architecture/<slug>/train-runs/*.yaml` for WPs
   with `merge_sha_on_dev` set.
2. Cross-references against `.architecture/<slug>/code-reviews/`
   to identify WPs without bundles.
3. For each missing WP:
   - Reads the squash-merge SHA from the train state YAML
   - Computes the parent SHA: `git rev-parse <merge_sha>^`
   - Invokes `/sulis:code-review <parent>..<merge_sha> <slug>`
4. For each finding in each newly-produced bundle:
   - `wpx-findings register` (signature-hash dedup)
   - If new: `wpx-findings auto-draft-wp` + `wpx-index add-wp`
5. Stops at 10 remediation WPs (configurable cap)
6. Writes summary at
   `.architecture/<slug>/backfill-code-review-<TS>/SUMMARY.md`

### Step 3: Founder reviews drafted WPs

```bash
ls .architecture/<slug>/work-packages/WP-AUTO-*.md
```

For each `WP-AUTO-NNN.md`, judge: is the finding real + fixable
in scope? Promote OR cancel:

```bash
# Promote
wpx-index flip-status --wp WP-AUTO-NNN --project <slug> \
  --to pending --expected auto-draft

# Or cancel
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

With `v0.21.1+`, the train's Step 10.5 (bundled-tip code-review)
reviews the composition — catching any cross-WP regressions in
the remediation themselves.

### Step 5: Iterate

```
/sulis-execution:backfill-code-review --project <slug> --repo <org/repo>
```

Signature-hash dedup ensures previously-known findings don't
re-create WPs. Each iteration sees fewer issues.

### Step 6: Terminate

Stop when:
- An iteration produces ZERO new findings AND zero WPs skipped
  by the cap (every shipped WP has a bundle; nothing new to do)
- Remaining findings are explicitly deferred via
  `.architecture/<slug>/deferred-code-review-<SF-ID>.md`

Most slice-sized backfills converge in 2–3 iterations.

## Programmatic surface (SDK)

The skill orchestrates these SDK operations (`sulis-execution
v0.2.3+`):

```python
from sulis_execution import SulisExecution
import subprocess

client = SulisExecution(repo_root=".", project="<slug>")

# For each missing WP:
merge_sha = "..."  # from train state YAML
parent_sha = subprocess.check_output(
    ["git", "rev-parse", f"{merge_sha}^"], text=True
).strip()

# /sulis:code-review is a top-level skill (not an SDK operation);
# invoke via Bash from your orchestrator script:
subprocess.run(
    ["claude", "skill", "/code-review",
     f"{parent_sha}..{merge_sha}", "<slug>"],
    check=True,
)

# Parse signals.json from the produced bundle
import json, glob
bundle = sorted(glob.glob(f".architecture/<slug>/code-reviews/PR-*-*/"))[-1]
signals = json.load(open(f"{bundle}/signals.json"))

# For each finding, register
for finding in signals.get("findings", []):
    result = client.findings.register(
        wp="backfill-WP-NNN",
        severity=finding["severity"],
        summary=finding["summary"],
        file=finding["file"],
        suggested_fix=finding["recommendation"],
        primitive=finding["cr_code"],
        evidence_json=f"@{finding['evidence_path']}",
    )
    if not result.is_duplicate:
        client.findings.draft_remediation(
            source_finding=result.sf_id,
            source_wp="backfill-WP-NNN",
            auto_wp_id=result.auto_wp_id,
            primitive="Refactor",
            severity=finding["severity"],
        )
        client.index.add(wp=result.auto_wp_id, from_wp_file=True)
```

## See also

- `plugins/sulis-execution/skills/backfill-code-review/SKILL.md` —
  the skill body
- `plugins/sulis-execution/skills/backfill-code-review/recipes/post-rollout.md`
  — narrative recipe for the slice-2 9-WP case
- `plugins/sulis-execution/skills/backfill-gates/SKILL.md` — sibling
  skill for security backfill
- `plugins/sulis/skills/code-review/SKILL.md` — the skill this
  orchestrates
- `plugins/sulis-execution/agents/executor.md` — Step 6.5 forward gate
