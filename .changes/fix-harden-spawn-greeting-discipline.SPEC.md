---
founder_facing: false
---
# Spec — harden the spawn-greeting discipline

**Change:** CH-01KSNP · fix
**Closes:** [#27](https://github.com/sulis-ai/agents/issues/27), [#28](https://github.com/sulis-ai/agents/issues/28)

## What this should do

Fix three concrete contradictions in `plugins/sulis/agents/sulis.md`'s
"Change context" section (line 1473+) where the agent body's own
Decision Discipline / Forbidden-Output-Shapes rules are not being
honoured at change-context-greeting time:

### Fix 1 — `Step 3 "Greet in change-context mode"` (line 1497-1503)

Current example explicitly tells the agent to hand the floor back with
a menu ("Or tell me what you've already tried — I can route from
there."). This is the **#28 violation**, written into the example the
agent learns from. Replace with an example that follows
action-then-report shape: announce the stage + the skill being run +
report on the next turn.

### Fix 2 — Stage-inference rules (line 1554) + recon marker

Current rule:
> 1. No `CONTEXT.md` written yet → Stage 0 (Recon).

`CONTEXT.md` is **always** written by `sulis-change start --spawn` as
the pre-spawn stub. So this rule never fires → Stage 0 is invisible
100% of the time. This is **#27**.

**Reviewer (PR #33, pre-merge step 4.5) caught a flaw in the first cut
of this fix:** `/sulis:recon` doesn't write its own distinct artifact —
it calls the SAME `write_change_context()` helper that the pre-spawn
stub uses, producing identical CONTEXT.md output. So checking for
"RECON.md or similar in the worktree" would have found nothing
existing today; the rule would have always concluded "Stage 0 not
done" and re-routed to `/sulis:recon` on every greeting forever. Two
wrongs.

**In-PR scope widen (acknowledged):** the spec originally scoped out
edits to `/sulis:recon`; the reviewer's catch made that scope-out
untenable. So this PR now also amends `plugins/sulis/skills/recon/SKILL.md`
Step 4 to write a sentinel file at
`{worktree}/.changes/{primitive}-{slug}.RECON.md` after the
`write_change_context()` call. The pre-spawn writer doesn't touch this
file; its existence is the load-bearing "Stage 0 done" signal. Path
mirrors the `.SPEC.md` naming pattern; travels with the change branch
per the #42 records policy.

Reword rule 1 in `sulis.md` to key off this real sentinel.

### Fix 3 — `How you route` example (line 1573-1574)

Current example: *"You're in change CH-01KSG1 — 'fix the auth bug' —
at the Specify stage. Ready to run `/sulis:specify` to write down
what the fix should do?"*

The "Ready to run …?" phrasing is exactly the permission-theatre
closure the agent body's Forbidden Output Shapes already forbid
(*"Want me to X?" / "Should I X?"*). This is the second
**#28 violation**. Replace with action-then-report:
*"You're in change CH-01KSG1 at the Specify stage — running
`/sulis:specify` now to write down what the fix should do."* — and the
next turn IS the skill running.

### Fix 4 — Add the positive rule (new block)

After the existing routing prose, add an explicit "MUST" block:

> **MUST: after greeting, immediately run the inferred next-stage
> skill — do not surface a menu of options unless the stage is
> genuinely ambiguous (per the ambiguous-stage exception below).** The
> agent owns the "which skill does that work" decision; the founder
> owns "is this the work I want next?" — and a confirmed change with
> a clear next stage IS confirmation that this is the work. Stop
> asking permission to execute the call you already made.

This is a direct re-statement of Decision Discipline tailored to the
spawn-greeting case, so the agent can't pattern-match on the existing
broken examples.

## How we'll know it's done

- The agent body's "Change context" section is consistent with the
  rest of the file's Decision Discipline / Forbidden Output Shapes
  rules (no contradictory examples).
- The greeting example demonstrates action-then-report, not menu-shape.
- The stage-inference rules treat the pre-spawn CONTEXT.md stub as
  identity + recon-input, not as Stage 0 completion.
- A new MUST rule explicitly forbids the menu-of-options shape at
  greeting time.
- Lint clean (compileall + JSON parse — no Python touched).
- Review gate passes via the new step 4.5 added in #30.

## What to avoid

- **Do NOT change `sulis-change start`'s pre-spawn CONTEXT.md writer**
  — that's a separate file (`_change_context.py`), out of scope.
- **`/sulis:recon` skill IS in scope (revised after the #33 review
  catch)** — Step 4 now writes a sentinel marker file so the agent's
  stage-inference has a real signal to key off. The rest of the recon
  skill stays untouched.
- **Do NOT delete the "ambiguous stage" exception** at line 1586-1591
  — that's the one legitimate case for surfacing two options (when
  the stage genuinely can't be inferred). Keep it; mark it as the
  *only* legitimate menu case.
- **Do NOT add a `stage:` field to the change manifest** — that'd be
  a bigger change touching `_change_state.py` and `sulis-change`.
  Filesystem-marker inference (presence of `RECON.md` etc.) is
  sufficient and keeps this change small.

## References

- The seam: `plugins/sulis/agents/sulis.md` lines 1473-1592.
- The contradicting rules already in the file: Forbidden Output Shapes
  (line 791-819), Decision Discipline (line 1203-1296), Phase
  Auto-Progression (referenced at line 1567).
- The two issues this closes: #27 (Stage-0 invisible), #28 (menu).
- Prior art for the action-then-report shape: lines 1576-1584 already
  have the correct example for stage advancement — the change just
  brings the first-time-greeting case into line with that pattern.
