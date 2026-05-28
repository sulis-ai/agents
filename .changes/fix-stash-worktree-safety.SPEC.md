# SPEC — fix: worktree-safe adopt (stop using the shared per-repo git stash stack)

> Change: `change/fix-stash-worktree-safety` (CH-01KSQ4)
> Primitive: `fix`
> Resolves: GitHub issue #53 (lesson: `git stash` is unsafe in the
> multi-worktree change model — the stash stack is shared per-repo and
> leaks across worktrees)

## Context — the hazard

`git stash` operates on **one stack per repository**, shared across ALL
of that repo's worktrees. The change-as-primitive model creates many
sibling worktrees per repo (this marketplace alone has ~15 live change
branches right now). Any positional `git stash pop` in a change worktree
can grab an **unrelated** sibling worktree's stash — silent
cross-contamination. The `--include-untracked` (`-u`) variant is still
shared.

This already happened once (DC-04 worktree): a `git stash pop` in a
change worktree grabbed an unrelated hardening stash pushed from a
different worktree, dumping its files in as untracked cruft. Caught
immediately, no work lost — but the failure mode is real and silent.

## The two damage sites (both in the `adopt` path of `sulis-change`)

The `sulis-change start` path is **already safe** — it uses
`git_worktree_add` off `dev` with no stash. The hazard lives only in the
**adopt** path (retrofitting pre-existing uncommitted/local work into a
new change worktree):

1. **`plugins/sulis/scripts/sulis-change`**, `cmd_adopt` — the
   local-commits branch (~lines 338–360): `git stash push -u` in the
   main repo, then a **positional** `git stash pop` in the worktree
   (`_run(["git", "stash", "pop"], cwd=worktree_dest, ...)`).
2. **`plugins/sulis/scripts/_wpxlib.py`**,
   `adopt_uncommitted_into_change` (~lines 3773–3791): `git stash push
   -u` in the main repo, then `git stash pop` in the worktree (and a
   `git stash pop` in the main repo on the rollback path).

Both rely on `git stash pop` taking **the top of the shared stack**,
which is the exact cross-worktree hazard.

## The required property (what "fixed" means)

The adopt transfer MUST move **only this change's own working-tree work**
from the source repo tree into the destination worktree, and MUST be
immune to concurrent stashes pushed by sibling worktrees. Concretely:
**no positional `git stash pop` (top-of-stack) anywhere in the adopt
path.** A sibling worktree's stash sitting on the shared stack MUST NOT
be consumed, applied, or dropped by an adopt run.

## The fix (recommended approach — executor may choose an equivalent that
satisfies the property)

Replace the shared-stack push/positional-pop with **explicit
worktree-local file movement** (the lesson's suggested fix — "explicit
file moves … never the shared stash stack"):

For the uncommitted-work transfer (`adopt_uncommitted_into_change`, and
the uncommitted-on-top-of-local-commits tail of `cmd_adopt`):

1. Capture the tracked working-tree delta as a patch from the source
   tree: `git diff HEAD --binary` → a temp patch file. (`git diff HEAD`
   covers both staged and unstaged changes relative to HEAD.)
2. Enumerate untracked files: `git ls-files --others --exclude-standard`.
3. Create the change worktree off base (clean — this already works via
   `git_worktree_add`).
4. In the destination worktree: `git apply <patch>` for the tracked
   delta, and copy each untracked file to the same relative path.
5. Clean the source tree of the moved work: restore tracked files
   (`git restore .` / `git checkout -- .`) and remove the moved untracked
   files. This matches today's stash-push semantics (push clears the
   source tree) — it is the adopt contract, not new destructive
   behaviour.

If the executor prefers a transient-WIP-commit variant instead, that is
acceptable **only if** it satisfies the required property (no positional
pop; sibling stashes untouched). A bare `git stash create` + apply-by-SHA
is NOT sufficient on its own because `create` does not capture untracked
files (`-u` semantics) — whatever is chosen MUST preserve untracked-file
transfer.

## Definition of Done (Red → Green → Blue)

**RED — write these tests first, watch them fail against current code.**
The adopt functions are exercised by the integration lifecycle test
(`plugins/sulis/scripts/tests/integration/test_sulis_change_lifecycle.py`)
because real git operations are required. Add:

1. **Cross-worktree-safety regression (the load-bearing test).** Set up a
   repo with an unrelated stash already on the shared stack (simulating a
   sibling worktree's parked work). Run an adopt with its own uncommitted
   work. Assert: after adopt, the unrelated stash is **still present and
   unchanged** on the stack (`git stash list` still shows it; its content
   is intact). Against current code this FAILS (the positional pop grabs
   the unrelated stash).
2. **Tracked + untracked uncommitted work lands in the new worktree.**
   Adopt a repo state with both a tracked modification and an untracked
   file; assert both appear in the destination worktree with correct
   content.
3. **Source tree is clean after adopt.** Assert the source repo working
   tree has no leftover modifications or moved untracked files after a
   successful adopt.
4. **Combined local-commits + uncommitted case** (`cmd_adopt` local-commits
   branch): assert the local commits are cherry-picked onto the change
   branch AND the trailing uncommitted work lands in the worktree, with
   no shared-stack pop.

**GREEN — implement the fix** at both call sites so the tests pass.
Extract the working-tree-delta transfer into a single shared helper in
`_wpxlib.py` (per EP-03: two call sites doing the same thing → extract the
primitive) and call it from both `adopt_uncommitted_into_change` and
`cmd_adopt`. Do not leave duplicated transfer logic.

**BLUE — refactor + docs.**
- Ensure the new helper has a clear name + docstring and the two call
  sites read cleanly.
- Add a one-line caution to
  `plugins/sulis/references/git-workflow-standard.md`: *never `git stash`
  in a change worktree — the stash stack is shared per-repo and a
  positional pop can grab another worktree's stash.*
- Add the same caution to the change skill's gotchas
  (`plugins/sulis/skills/change/SKILL.md`).

## Acceptance criteria

- [ ] No positional `git stash pop` (top-of-stack) remains anywhere in
      the adopt path (`sulis-change` `cmd_adopt` + `_wpxlib.py`
      `adopt_uncommitted_into_change`).
- [ ] The cross-worktree-safety regression test passes (a sibling
      worktree's stash is never consumed by an adopt).
- [ ] Tracked + untracked uncommitted work transfers correctly into the
      new worktree; source tree left clean.
- [ ] Combined local-commits + uncommitted adopt works.
- [ ] Shared transfer helper extracted (no duplicated logic across the
      two call sites).
- [ ] Caution added to the git-workflow standard and the change skill
      gotchas.
- [ ] Full test suite green; no lint/type errors.

## Out of scope

- Issue #52 (branch-ci whole-tree drift) — deferred, separate change.
- Any change to `sulis-change start` (already safe — no stash).
