# Recipe: backfill the slice-2 12-WP gate gap

**Use when:** you've shipped a batch (or several) via `wpx-train run`
on a plugin version BEFORE `v0.20.0` (the version that wired Step 11
into the per-batch flow). Your findings register is missing entries
for those WPs. You want to catch up retroactively.

**The specific case this recipe was written for:** slice-2 shipped
12 WPs in May 2026 with `wpx-train v0.11.0+` but `run-all/SKILL.md`
that didn't dispatch Step 11. Zero security findings registered for
those WPs. The slice-1 register stops at SF-023.

## Step-by-step

### 1. Confirm the gap

```bash
# Count slice-2 WPs that were merged (look for completed entries)
"$WPX_DIR/wpx-index" list-ready --project agent-applications \
  --status done --since 2026-05-15

# Compare to the findings register's last entry
ls -t .security/agent-applications/findings/SF-*.md 2>/dev/null | head -3
# Or check directly:
tail -5 .security/agent-applications/findings/register.md
```

If the most recent SF predates your most recent done WPs, you have
the gap.

### 2. Run iteration 1

```bash
/sulis:backfill-gates \
  --project agent-applications \
  --repo sulis-ai/platform \
  --deployed-url https://dev.example.com \
  --max-remediation 10
```

This will:

1. Invoke `/sulis-security:codebase-assess`
2. Parse findings from the produced viability report
3. Register findings; auto-draft remediation WPs for novel ones
4. Stop after 10 remediation WPs (or sooner if fewer exist)
5. Print a summary

Expected output: 5–10 remediation WPs drafted on iteration 1 (based
on slice-1 finding density of ~20 across 14 WPs).

### 3. Review the drafted WPs

```bash
ls .architecture/agent-applications/work-packages/WP-AUTO-*.md | head -10
```

For each WP-AUTO-NNN.md:

- Read the SF reference + the suggested fix
- Judge whether the finding is real + scope-bounded
- If yes, promote: `wpx-index flip-status --wp WP-AUTO-NNN --to pending --expected auto-draft`
- If no (assessor false positive, out of scope), close with note:
  `wpx-index flip-status --wp WP-AUTO-NNN --to cancelled --expected auto-draft`
  and add a brief note to `.security/agent-applications/deferred-critical-<SF-ID>.md`
  if it was CRITICAL

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

The train ships them. Crucially, with `v0.20.0+`, the per-batch Step 11
in `run-all` reviews each of the remediation WPs as they ship — closing
the local loop for any new issues the remediation might introduce.

### 5. Run iteration 2

After the train completes:

```bash
/sulis:backfill-gates \
  --project agent-applications \
  --repo sulis-ai/platform \
  --deployed-url https://dev.example.com
```

Expected: fewer remediation WPs than iteration 1 — the shipped fixes
should have addressed the high-frequency findings; the assessor sees
fewer issues. Signature-hash dedup ensures any RESIDUAL findings (the
fix changed surface area but not the root cause) get registered once,
not multiple times.

### 6. Iterate

Repeat steps 3–5 until an iteration produces ZERO new findings. At
that point the codebase is clean from codebase-assess's 25-primitive
perspective.

## Expected total cycle count

Based on slice-1 density: 3–5 iterations to converge. Each iteration
ships 3–10 remediation WPs, so the total remediation cost is roughly
15–30 follow-up WPs over a slice-2-sized codebase. Quote this
upfront when planning the schedule — backfill is not a one-shot.

## What can go wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| codebase-assess produces no report | Auth issue with the repo clone | Set `GITHUB_APP_ID` / `GITHUB_APP_PRIVATE_KEY` / `GITHUB_APP_INSTALLATION_ID` env vars or use a personal token |
| Every finding is "duplicate" | Same scan ran recently; nothing changed | Confirm the dev branch has actually been deployed since the prior assessment; if so, dedup is working as intended |
| Auto-drafted WPs accumulate to 100+ | Backfill cap not respected | Check `--max-remediation` was passed; the cap is per-iteration, not session-total |
| Founder spent more time triaging WPs than fixing | Too many low-quality auto-drafts | Tighten the assessment scope: pass `--deployed-url` so DAST findings are actionable; consider scoping the next iteration to one category (e.g., security only) |
| Step 11 (post-train) flagged regressions on the remediation WPs themselves | A remediation introduced a new issue | Normal; the gate caught it. The remediation WP gets a follow-up WP-AUTO; next iteration sees it |

## Why this is iterative, not one-shot

Codebase-assess scores against 25 primitives. Even if iteration 1
fixes everything codebase-assess sees, the act of fixing changes the
codebase — which iteration 2's assess may evaluate differently
(new code paths, new dependencies). The loop converges because:

- `wpx-findings register` dedups on signature hash (severity + summary
  + file). Identical findings register once.
- Each iteration's remediation either resolves the underlying issue
  (no longer present in next scan) OR moves it (same finding,
  different file — different signature, re-registers as new but
  rare in practice).
- After 3–5 iterations, most projects reach equilibrium: the assess
  produces 0–1 new findings per run, which is the "clean" steady
  state.

## Termination

Stop iterating when:

- An iteration produces ZERO new findings (loop complete), OR
- The remaining findings have been explicitly deferred via documented
  `.security/<project>/deferred-critical-<SF-ID>.md` notes with
  founder approval, OR
- The marginal cost of another iteration exceeds the marginal benefit
  (after 5+ iterations with diminishing returns)

The first criterion is the strict mathematical one; the other two
are pragmatic stops. Record which one applied at the end of the
backfill in `.security/<project>/backfill-complete-<TIMESTAMP>.md`.
