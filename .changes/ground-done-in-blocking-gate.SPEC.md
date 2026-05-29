---
founder_facing: false
status: SPEC — founder-directed; foundational (false-completion on advisory CI)
---
# Spec — ground "done/shipped" in the gate that actually blocks

**Change:** fix · ground-done-in-blocking-gate
**Closes:** [#79](https://github.com/sulis-ai/agents/issues/79)
**Source:** founder caught a failed deploy that an autonomous run-all had
reported as a *completed* 55-WP journey ("dev is green, nothing blocked").

## Root cause

The completion claim ("shipped" / "complete" / "dev is green") was grounded
in **branch-CI, which is ADVISORY** on the common founder repo (private +
free plan → branch protection unavailable → branch-CI is not a required
check; #52 / platform#36). Broken api tests passed the advisory gate, merged
to dev, and the agent declared the journey complete. The BLOCKING gate
(deploy-to-dev, which runs the same tests as required) then failed. GIT-05's
"ship on branch-CI green, no PR ceremony" silently assumes branch-CI is
*required* — false on most founder repos, and every downstream "done" claim
inherits the false green. We already DETECT the advisory case (wpx-preflight
protection-status / #52) — the gap is that the completion claim ignores it.

## What this change does (core — prose discipline, high-confidence)

1. **Agent body — Definition of Done (MUST).** A completion claim
   ("shipped", "complete", "done", "dev is green", "nothing blocked") MUST be
   grounded in the gate that actually blocks the merge/deploy — never an
   advisory gate. If the blocking gate hasn't been verified green, the only
   honest claim is "merged — not yet verified." Generalises the false-green
   family (#59/#69/#71) into one definition-of-done rule.
2. **`run-all` — batch-completion discipline.** Before any "all WPs shipped /
   journey complete" report, check the gate type (the existing #52
   protection-status). If branch-CI is **advisory**: do NOT say
   shipped/complete/green. Report "merged to dev — CI is advisory on this
   repo, so this is NOT verified-shippable until the blocking gate
   (e.g. deploy-to-dev) is green", and name that gate as the next check.
3. **GIT-05 caveat.** branch-CI-green is a ship gate ONLY when branch
   protection makes branch-CI a *required* status check. When protection is
   unavailable (advisory CI), branch-CI green is informational, not a ship
   gate; completion must be grounded in the blocking gate.

## What this change scopes (follow-on — programmatic, NOT built here)

The durable enforcement: the train/run-all should **poll the post-merge
blocking gate** (the deploy-to-dev workflow conclusion), not just branch-CI,
before declaring a batch shipped — turning "verify the blocking gate" from a
prose instruction into a mechanical check. Heavier + repo-specific (which
workflow is the blocking gate); scope + measure separately. Pairs with the
headless founder-question gate (#71 follow-on) as the structural backstops.

## How we'll know it's done (this change)

- The agent body carries the Definition-of-Done rule (MUST).
- `run-all` downgrades the completion claim on advisory CI + names the
  blocking gate; never claims shipped/complete on advisory-green.
- GIT-05 carries the required-vs-advisory caveat.
- Review gate PASS.

## What to avoid

- Don't weaken the no-PR-ceremony model where branch-CI IS required — this
  only changes behaviour on advisory-CI repos.
- Don't build the programmatic deploy-gate poll here (follow-on); keep this
  to the definition-of-done discipline.

## References

- `plugins/sulis/agents/sulis.md` — Decision Discipline / completion claims
- `plugins/sulis/skills/run-all/SKILL.md` — batch-completion report
- `plugins/sulis/references/git-workflow-standard.md` — GIT-05
- `plugins/sulis/scripts/wpx-preflight` — protection-status (#52 detection)
- #79 (closes), #52 (unprotected-repo detection), #59/#69/#71 (false-green family)
