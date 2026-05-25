# Recipe: backfill the slice-2 9-WP code-review gap

**Use when:** WPs shipped via train BEFORE `v0.20.1` (which added
the Step 6.5 bundle-path verification). Those WPs may have shown
"Step 6.5 inline review: 0 findings" in journals without actually
invoking `/sea:code-review` — no bundle on disk; no audit trail.

**The specific case:** the 2026-05-22 slice-2 audit found 9 of 12
WPs had no bundle. Inline self-attestation pattern. This recipe
catches them up retroactively.

## Step-by-step

### 1. Identify the gap

```bash
# All slice-2 train state YAMLs
ls -t .architecture/agent-applications/train-runs/train-2026-05-*.yaml

# For each train, list WPs + check for bundles
python3 <<'PYEOF'
import yaml, os, glob

PROJECT = "agent-applications"
TRAINS = glob.glob(f".architecture/{PROJECT}/train-runs/train-2026-05-*.yaml")
BUNDLE_DIR = f".architecture/{PROJECT}/code-reviews"
bundles = {os.path.basename(d).split('-PR-feat-wp-')[1].split('-')[0]
           for d in glob.glob(f"{BUNDLE_DIR}/PR-feat-wp-*-*/")
           if 'PR-feat-wp-' in d}

missing = []
for t in TRAINS:
    state = yaml.safe_load(open(t))
    for entry in state.get('bundle', []):
        if entry.get('merge_sha_on_dev'):
            wp = entry['wp']
            branch = entry.get('branch', '')
            wp_key = branch.replace('feat/wp-', '').split('-')[0] if branch else wp
            if wp_key.lower() not in {b.lower() for b in bundles}:
                missing.append((wp, entry['merge_sha_on_dev'][:8], branch))

print(f"Missing bundles for {len(missing)} WP(s):")
for wp, sha, branch in missing:
    print(f"  {wp:30s} {sha} ({branch})")
PYEOF
```

Expected output: 9 WPs (the slice-2 self-attestation cohort).

### 2. Run iteration 1

```
/sulis:backfill-code-review \
  --project agent-applications \
  --repo sulis-ai/platform \
  --max-remediation 10
```

This will:

1. Auto-scan train-runs YAMLs for shipped WPs without bundles
2. For each (default: all 9): invoke `/sea:code-review <parent>..<merge_sha> agent-applications`
3. Parse the resulting `signals.json` per bundle
4. Register findings (signature-hash dedup)
5. For NEW findings: auto-draft remediation WPs (up to 10 total)
6. Write summary report

Expected output: 9 bundles produced, ~10–20 findings registered,
~5–10 remediation WPs auto-drafted (based on slice-1's finding
density of ~20 findings across 14 WPs).

### 3. Review the drafted WPs

```bash
# Find newly-drafted code-review remediation WPs
ls -lt .architecture/agent-applications/work-packages/WP-AUTO-*.md \
  | head -20

# For each, read the SF reference + suggested fix
cat .architecture/agent-applications/work-packages/WP-AUTO-NNN-*.md
```

For each `WP-AUTO-NNN.md`:

- Read the SF reference and the suggested fix paragraph
- Judge: is the finding real? Is the fix scope-appropriate?
- Promote if yes:
  ```bash
  wpx-index flip-status \
    --wp WP-AUTO-NNN --project agent-applications \
    --to pending --expected auto-draft
  ```
- Cancel if no (assessor false positive, out of scope for now):
  ```bash
  wpx-index flip-status \
    --wp WP-AUTO-NNN --project agent-applications \
    --to cancelled --expected auto-draft
  ```

### 4. Ship the promoted WPs

```bash
wpx-train run \
  --project agent-applications \
  --repo sulis-ai/platform \
  --base-branch dev \
  --deploy-workflow "Deploy to Dev" \
  --staging-url https://dev.example.com \
  --smoke-cmd "curl -sf https://dev.example.com/health" \
  --force  # if fewer than 3 promoted WPs (size trigger not met)
```

With `v0.21.1+`, the train's Step 10.5 (bundled-tip code-review)
runs against the composition of the remediation WPs — so any
regression they introduce together is caught immediately.

### 5. Run iteration 2

After the train completes:

```
/sulis:backfill-code-review \
  --project agent-applications \
  --repo sulis-ai/platform
```

Expected: at most a handful of new findings on the shipped
remediation WPs themselves (the fixes were small, focused). Signature-
hash dedup ensures previously-registered findings don't re-create WPs.

### 6. Iterate

Repeat steps 3–5 until an iteration produces ZERO new findings
AND no WPs were skipped by the cap. The original 9-WP gap is closed
when every shipped WP from slice-2 has a corresponding code-review
bundle on disk.

## Expected total cycle count

Based on slice-1 density: 2–3 iterations to converge. Iteration 1
processes all 9 missing WPs and drafts the high-density findings;
iteration 2 handles the residue. Quote 2–3 cycles when planning
the schedule.

## What can go wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `/code-review` errors out on the commit range | Range syntax not supported, OR parent SHA doesn't resolve (force-pushed branch) | Check the train state YAML — if `pre_train_sha` is set, the parent might be `<pre_train_sha>` instead of `<merge_sha>^` |
| Bundle has fewer findings than expected | The WP's diff was small; not all CR-NN rules fire | Normal; small WPs legitimately have few findings |
| Every WP's bundle has the same finding | A repo-wide pattern issue (e.g., everywhere uses raw SQL; CR-10 fires on every WP that touches data layer) | Promote one WP-AUTO that drafts a centralised fix; cancel the rest as duplicates (signature-hash should auto-dedup) |
| Backfill cap reached after only 3 WPs processed | Many findings per WP this iteration; cap is doing its job | Iterate again — shipped fixes will reduce next iteration's count |

## Termination

Stop iterating when:

- An iteration produces ZERO new findings AND zero skipped-by-cap WPs
  (every shipped WP has a bundle; nothing new to do), OR
- Remaining issues are explicitly deferred (founder approval in
  `.architecture/<project>/deferred-code-review-<SF-ID>.md`)

Record the termination in `.architecture/<project>/backfill-code-review-complete-<TIMESTAMP>.md`
with the count of WPs caught up + remediation WPs created.
