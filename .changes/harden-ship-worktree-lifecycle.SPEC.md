---
founder_facing: false
status: BUILT — Part 2 founder-confirmed (record shipped state + recreate on demand); all 5 parts implemented + tested
---
# Spec — harden the ship path for the multi-worktree model

**Change:** harden · ship-worktree-lifecycle
**Closes:** [#56](https://github.com/sulis-ai/agents/issues/56)
**Defers:** [#57](https://github.com/sulis-ai/agents/issues/57) (bare-repo topology — separate)
**Source:** the `/honest:critical-thinking` spiral analysis, 2026-05-28.

## Root cause (from the analysis)

The change tooling assumes a *single-working-tree* git model (`git checkout
{base}`, `git stash`) while operating in a *multi-worktree* model where
per-repo state — the stash stack, which-branch-is-checked-out-where — is
**shared**. Every recurring git-state failure is a symptom. This change
makes the ship path worktree-native.

## What this should do (4 parts)

### 1. Ship is worktree-aware (#56 primary)

`cmd_finish` (and any flow that does `git checkout {base}`) must NEVER
blind-checkout the base in `repo_root`. Instead:
- Detect where `{base}` lives via `git worktree list --porcelain`.
- If `{base}` is checked out in another worktree → perform the squash-merge
  in THAT worktree (or via a ref-update path that needs no checkout).
- If it can't be resolved → `emit_error` with an actionable message naming
  the worktree holding `{base}` (not the opaque git fatal).

git forbids the same branch in two worktrees BY DESIGN (independent indexes
can't reconcile) — so we work *with* that constraint, never against it.

### 2. Remove the worktree on ship; record the shipped state; recreate on demand

On successful ship, `git worktree remove` the change's worktree but KEEP
the branch + the change record — AND pin the shipped state so it's
viewable + reconstructable (founder refinement: "record the state so we
can still view it as it was when shipped; recreate the worktree if
needed").

- **Record `shipped_sha`** — the change branch tip at ship time — in the
  change record (joins `shipped_at` + `base_sha`). This pins "the state
  it was in when we shipped" to a stable ref, viewable even if the branch
  later moves.
- **`git worktree remove` the change's worktree**, gated on
  `session_is_live(change_id)` (#32) — never remove a worktree with a
  bound live session.
- **Keep the branch + record.** Claim-3 validated: the cockpit uses
  `worktree_path` only for `.exists()`; retrace/diff is git-based
  (`base_sha` + branch, #44); the dashboard already models
  `worktree_present`/`branch_present` separately and treats "no worktree,
  branch present" as a valid shipped state. So this preserves the #38
  "keep changes visible/retraceable" intent — the working copy was
  redundant.
- **NEW subcommand `sulis-change recreate <handle>`** — re-materialises
  the worktree from the recorded `shipped_sha` (`git worktree add <path>
  <shipped_sha>`), so "recreate if needed" is one founder-friendly
  command, not a raw git incantation. This is what makes removing the
  worktree on ship palatable: it's always one command away.
- Ends worktree sprawl; shrinks #56's trigger surface.

### 3. Conventional-Commit squash message (#56 secondary)

The squash-merge message derives from the change: `{primitive}: {slug}`
(+ the `{intent}` in the body + correct `Co-Authored-By`), not the
hardcoded `feat({branch}): squash-merge {branch}`. Honours the
Conventional-Commits convention already in the GIT standards.

### 4. Slug-doubling fix

`cmd_start`'s branch/slug derivation must not re-prefix when the slug
already starts with the primitive (`fix` + `fix-login` →
`change/fix-login`, not `change/fix-fix-login`).

### 5. Norm (doc)

A change worktree only ever holds its OWN change branch — never
`git checkout dev` inside one. Add to the change skill's gotchas + the
git-workflow standard. (Part 1 removes the *need* to violate this.)

## How we'll know it's done

- Ship from a repo where `dev` is checked out in a sibling worktree
  succeeds (the exact #56 repro) — merge lands, no `git checkout` fatal.
- After ship: the worktree is gone, the branch + change record remain;
  the dashboard shows the change as shipped (worktree_present=false,
  branch_present=true); `git worktree add` re-materialises it.
- Ship with a live bound session → worktree is NOT removed (session_is_live
  gate).
- Squash commit message is `{primitive}: {slug}` with correct co-author.
- `sulis-change start --primitive fix --slug fix-login` →
  `change/fix-login` (no doubling).
- Unit + integration tests for each; full suite green; review gate PASS.

## What to avoid

- **Do NOT delete the branch or change record on ship** — that's what
  preserves the audit trail (#38 intent). Only the worktree goes.
- **Do NOT remove a worktree with a live bound session** (session_is_live
  gate, #32).
- **Do NOT fight git's same-branch-one-worktree constraint** — it's a
  safety feature; work with it.
- **Do NOT attempt the bare-repo topology here** — that's #57, a deliberate
  separate decision.

## Founder confirm needed before build

Part 2 changes the **mechanism** of the #38 decision (which you explicitly
chose: archive-don't-delete, "keep changes visible"). Claim 3 shows the
worktree was redundant for that intent — the branch + record preserve full
visibility + retrace. So this keeps everything you wanted visible while
dropping the redundant working copy (ending sprawl). **Confirm this
reconciliation before I build Part 2.** Parts 1, 3, 4, 5 are unambiguous.

## References

- `plugins/sulis/scripts/sulis-change` — `cmd_finish` (ship), `cmd_start`
  (slug); `_change_state.session_is_live` (#32 gate)
- `plugins/sulis/skills/change/SKILL.md` — ship flow + gotchas
- `plugins/sulis/references/standards/git-workflow-standard.md` — the norm
- #56 (closes), #57 (defers), #38 (the archive intent), #44 (git-based diff)
