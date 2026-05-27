---
founder_facing: false
---
# Spec — gate the ship subcommand on /sulis:review

**Change:** CH-01KSNH · extend
**Closes:** [#30](https://github.com/sulis-ai/agents/issues/30)

## What this should do

Insert a new step **4.5** in `plugins/sulis/skills/change/SKILL.md`'s `ship`
subcommand, between the existing **step 4 (wait for `branch-ci`)** and
**step 5 (squash-merge)**, that invokes `/sulis:review` and surfaces its
verdict to the founder.

`/sulis:review` already composes `/sulis:code-health` + a security
assessment + folds them into one PASS / CONCERN / CRITICAL verdict
(verified by reading `plugins/sulis/skills/review/SKILL.md` lines 22-95).
So this change is **skill-prose only** — no amendment to `/sulis:review`
or to `cmd_finish`.

Verdict handling per branch-ci-fail's existing pattern (step 4):
- **PASS** → proceed to step 5 (squash-merge)
- **CONCERN** → echo the findings; require explicit founder yes/no
  before proceeding (mirrors the existing "yes/no" gate at step 2)
- **CRITICAL / FAIL** → STOP. Do NOT merge. Surface findings in plain
  English with the next step

### CW-05 size carve-out (MUST)

Running the 7-tier deep-mode `/sulis:code-health` on a typo or comment
fix is wasteful. Reuse the established CW-05 thresholds from
`change-work-standard.md`: when the change's diff (vs `dev`) is **≤30
lines AND ≤1 file AND no new code added**, skip the review step, log
the skip, proceed directly to step 5.

The agent computes this via `git diff --shortstat dev...HEAD` (returns
e.g. `1 file changed, 5 insertions(+), 0 deletions(-)`), parses the
file count + insertions + deletions, and applies the gate. Inline bash
in the skill prose — no new helper script needed.

## How we'll know it's done

- `change/SKILL.md` ship subcommand has a step 4.5 with PASS / CONCERN /
  CRITICAL handling and the CW-05 carve-out.
- The change is itself shipped through the new step 4.5 (bootstrap
  discipline: the very change that adds the discipline follows it).
- No Python tests touched (no testable code surface).
- Lint clean (`compileall` over scripts is a no-op for this change but
  run anyway).

## What to avoid

- **Do NOT amend `/sulis:review`'s composition** — it already does
  code-health + security. Verified by reading the file. Out of scope.
- **Do NOT add a new Python helper** for the size check — inline `git
  diff --shortstat` is fine. The skill prose is the right surface.
- **Do NOT make CONCERN auto-proceed** — even when findings are
  non-critical, the founder explicitly confirms. The whole point of
  this fix is structural review-before-merge; auto-proceeding on
  CONCERN would undermine that.
- **Do NOT block `mark-shipped`** (#38) or any post-merge step — the
  gate is between branch-ci-green and squash-merge ONLY.

## References

- The change skill: `plugins/sulis/skills/change/SKILL.md` ship
  subcommand (step 4 currently ends with branch-ci green → step 5
  squash-merges).
- The composer: `plugins/sulis/skills/review/SKILL.md` — already wraps
  code-health + security; produces a single verdict.
- CW-05 thresholds: `plugins/sulis/references/change-work-standard.md`
  (~30 lines / 1 file / no new behaviour).
