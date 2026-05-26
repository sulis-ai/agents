---
name: change
description: >
  Use when the founder wants to start a new piece of work, see everything
  they have in flight, jump back into one, ship one when it's ready, or
  pull in the latest from the rest of the team, or throw a change away.
  The change-lifecycle command. Subcommands: start / list / focus / ship /
  rebase / nuke.
  Usage: /sulis:change start "fix the login bug", /sulis:change list,
  /sulis:change focus CH-01HQ8X, /sulis:change ship CH-01HQ8X,
  /sulis:change rebase CH-01HQ8X, /sulis:change nuke CH-01HQ8X.
user_invocable: true
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD]
  output: [CRITICAL_THINKING_STANDARD]
register:
  founder_mode: default
  technical_mode:
    shape: json_envelope
    triggers: [intent, --raw, /sulis:jargon]
verification_spiral:
  tier: standard
  template_base: STANDARD_TIER_DEFAULT
related_skills:
  - relationship: related_to
    skill: ../start/SKILL.md
    notes: start re-enters a journey; this skill starts/lists/ships changes
  - relationship: related_to
    skill: ../run-all/SKILL.md
    notes: run-all ships the WPs inside a change; ship lands the whole change to dev
  - relationship: optional_input
    skill: ../../references/founder-facing-conventions.md
    notes: Audience=founder-facing; Rules 1-6 apply (echo-before-act, prompt-before-destroy, dual-register)
  - relationship: optional_input
    skill: ../../references/change-primitives.md
    notes: the 22-primitive vocabulary that picks the change kind on `start`
---

# /sulis:change — your work, start to finish

## Conclusion (lead with the answer)

`/sulis:change` is the one command for the whole life of a piece of work.
You give it a subcommand and it does the right thing:

| You type | What happens |
|---|---|
| `/sulis:change start "fix the login bug"` | Opens a fresh, focused workspace for that work — a new terminal with Sulis already briefed on it. |
| `/sulis:change list` | Shows everything you have in flight, in one scannable list. |
| `/sulis:change focus CH-01HQ8X` | Jumps you back into a piece of work you started earlier. |
| `/sulis:change ship CH-01HQ8X` | Lands the finished work into the shared `dev` line (after the safety checks pass). |
| `/sulis:change rebase CH-01HQ8X` | Pulls in everyone else's latest work so yours stays current. |
| `/sulis:change nuke CH-01HQ8X` | Throws a change away — deletes its branch, workspace, and local state. Asks first; can't be undone. |

This skill is an **orchestrator** — it tells the Sulis session which
existing tool to run for each subcommand. It does not run any new code of
its own; the underlying machinery (`sulis-change`, the terminal launcher,
the back-integration helper) already exists and is wired below.

Founder-mode is the default: plain English, lead with the outcome, the
handle (`CH-XXXXXX`) hangs in parentheses next to the readable name. A
founder can ask for the raw output any time ("show me the technical
version" / `--raw`) and get the JSON the tools emit — same substance,
different shape (Founder-Facing Conventions Rule 6).

## Resolving the `sulis-change` tool path (MUST — first action)

The change tools live inside the sulis plugin. When the plugin is
installed in a downstream project they sit under the plugin cache, not at
a project-relative path. Resolve the tool directory ONCE at the start of
any change subcommand and capture it as `$SCRIPTS_DIR`:

```bash
SCRIPTS_DIR=$(
  find ~/.claude/plugins/cache \
    -name sulis-change -type f \
    -path '*/sulis/*/scripts/*' \
    2>/dev/null \
  | sort -r | head -1 | xargs -I{} dirname {} 2>/dev/null
)
# Dev fallback: marketplace repo cwd
if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/sulis-change" ]; then
  SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
fi
if [ -z "$SCRIPTS_DIR" ]; then
  echo "ERROR: cannot find the change tools. Run: claude plugin install sulis@sulis-ai-agents" >&2
  exit 1
fi
echo "SCRIPTS_DIR=$SCRIPTS_DIR"
```

Capture the printed `SCRIPTS_DIR` into working memory and substitute the
literal path at each `"$SCRIPTS_DIR/sulis-change"` call — environment
variables do NOT persist between Bash tool invocations in Claude Code.

The Python helpers `launch_change_terminal` (in `_terminal_launcher.py`),
`resolve_current_change` + `back_integrate_change_branch` (in `_wpxlib.py`)
are invoked via a `python3 -c` one-liner with `sys.path` pointed at
`$SCRIPTS_DIR` (examples in each subcommand below).

---

## Subcommand contracts

The first positional argument after `change` selects the subcommand. If it
is missing or unrecognised, do NOT guess — show the five-row table from the
Conclusion and ask which one the founder means.

### `start <slug-or-intent> [--primitive P] [--intent "..."]`

Open a new focused workspace for a piece of work.

**1. Work out the kind of change (the primitive).** If `--primitive` is
given, use it. Otherwise read the founder's intent and pick the best fit
from the 22-primitive vocabulary in
`../../references/change-primitives.md` (e.g. "fix the login bug" → `fix`;
"add Stripe checkout" → `feat`/`create`; "split the god-class" →
`decompose`; "remove the dead export" → `delete`). When nothing clearly
fits, default to `feat` — never block on this.

**2. Work out the slug.** A short kebab-case name (2-5 words) the founder
will recognise — derive it from the intent ("fix the login bug" →
`fix-login-bug`) unless the founder gave one explicitly.

**3. Echo the plan before acting (Rule 3).** One sentence, plain English,
before running anything:

> *"I'll start a new piece of work called **fix the login bug**
> (`fix-login-bug`), set up its own workspace, and open a fresh terminal
> with me already focused on it. Here goes."*

**4. Run the tool.** Substitute the resolved path:

```bash
"$SCRIPTS_DIR/sulis-change" start \
  --slug fix-login-bug \
  --primitive fix \
  --intent "fix the login bug" \
  --spawn
```

`--spawn` is what makes a new terminal open: the tool creates the
`change/{primitive}-{slug}` branch + a dedicated worktree, writes the
recon `CONTEXT.md`, and launches a new terminal running
`claude --agent sulis` bound to this change via the `SULIS_CHANGE_ID`
environment variable.

**5. Report (Rule 1 + Rule 2).** Parse the JSON on stdout. Lead with the
outcome; carry the handle in parentheses:

> *"Started **fix the login bug** (`CH-01HQ8X`). A new terminal just
> opened — I'm in there, already briefed on this work and ready to go.
> This window stays free for anything else."*

If `spawn_result.status` is **not** `"spawned"` (`failed` /
`unsupported platform` / no terminal app), the branch + worktree + recon
still succeeded — say so and give the manual fallback in plain English
(Rule 5):

> *"The work is set up (`CH-01HQ8X`), but I couldn't open a new terminal
> automatically ({reason}). To pick it up yourself, open a terminal, run
> `cd {worktree_path}`, then `claude --agent sulis`."*

### `list`

Show everything in flight, file-based — there is **no database**. Read
three sources and merge them:

1. **Repo manifests** — `.changes/*.yaml` (one per change; carries
   `change_id`, `handle`, `slug`, `primitive`, `intent`, `branch`).
   On the current branch these are read directly; for changes on other
   branches the `sulis-change list` tool already enumerates `change/*`
   branches:

   ```bash
   "$SCRIPTS_DIR/sulis-change" list
   ```

2. **Local session state** — `~/.sulis/changes/*/session.json` (carries
   `pid`, `terminal_app_used`, `spawned_at`). A session looks live if its
   `session.json` exists and the recorded `pid` is still running. Read each
   with the Read tool; check liveness with `kill -0 <pid> 2>/dev/null`.

3. **Branches** — `git branch --list 'change/*'` (the ground truth for
   what exists, even without local session state — e.g. a teammate's
   change pulled from `origin`).

Present ONE scannable list, ordered most-recent-first, capped at the most
recent ~10 with a "+N more" line if there are more (Rule 4, MUC-F4
overwhelm guard). Each row in founder English:

> *"**fix the login bug** (`CH-01HQ8X`) — bug fix · branch
> `change/fix-login-bug` · workspace open, last active 4 min ago"*
>
> *"**add Stripe checkout** (`CH-01J2KQ`) — new feature · branch
> `change/feat-add-stripe-checkout` · no live workspace (closed) — use
> `focus` to reopen"*

Translate `primitive` to a plain noun (`fix` → "bug fix", `feat` → "new
feature", `decompose` → "restructuring", etc.). Never print the raw
`change_id` ULID as the headline — the 6-char handle is the founder
reference.

### `focus <CH-handle>`

Reattach to a change the founder started earlier.

**1. Resolve the change.** Match the handle against the manifests
(`sulis-change list` output + `.changes/*.yaml`). If no change matches,
say so plainly and offer `list`:

> *"I don't see a piece of work with the handle `CH-09ZZZZ`. Run
> `/sulis:change list` to see what's in flight."*

**2. Read its session + worktree.** Read
`~/.sulis/changes/{change_id}/session.json` and the manifest's
`worktree_path`.

**3. Branch on liveness.**

- **Session looks live** (`session.json` present, `pid` still running via
  `kill -0`): point the founder at the existing terminal — do NOT spawn a
  second one (MUC-F5: don't act on stale belief, and don't duplicate):

  > *"**fix the login bug** (`CH-01HQ8X`) is already open in another
  > terminal (started 12 min ago). Switch to that window to pick up where
  > you left off."*

- **No live session** (no `session.json`, or the `pid` is dead): re-spawn
  with the same change context. Echo first (Rule 3), then call
  `launch_change_terminal` directly:

  ```bash
  python3 -c "
  import sys; sys.path.insert(0, '$SCRIPTS_DIR')
  from _terminal_launcher import launch_change_terminal
  import json
  r = launch_change_terminal(
      change_id='01HQ8XQM8G5KZGZQXPZD8H6PJ7',
      worktree_path='/abs/path/to/worktree',
      visible=True,
  )
  print(json.dumps(r))
  "
  ```

  Then:

  > *"Reopening **fix the login bug** (`CH-01HQ8X`) — a fresh terminal is
  > coming up, focused on this work."*

  If the spawn returns `status != "spawned"`, give the manual `cd … &&
  claude --agent sulis` fallback (same shape as `start`).

### `ship <CH-handle>` — the solo landing flow

Land a finished change into the shared `dev` line. **Destructive +
external blast radius** — this is the one subcommand that changes shared
state, so echo-before-act AND prompt-before-destroy both apply (Rule 3).

This repo's profile is **solo** (`contribution_model: solo`): no merge
queue, no deploy. Ship = open a PR to `dev`, wait for the branch checks to
pass, squash-merge, sync `dev`. **Ship lands on `dev` ONLY — never
`main`.** Promotion to `main` is a separate, explicit founder act and is
out of scope here.

**1. Resolve the change** (same as `focus`). Get its branch + slug +
primitive. If the handle doesn't match, say so and offer `list`.

**2. Confirm the founder means a real merge, not a casual word**
(MUC-F3). "Ship" is unambiguous as the subcommand, but still echo the
exact branch and the irreversible step BEFORE doing it, and require an
explicit yes:

> *"This will merge **fix the login bug** (`change/fix-login-bug`) into the
> shared `dev` line and delete the change branch afterwards. The merge
> itself can't be casually undone. I'll only do it once the automated
> checks pass. Go ahead? (yes / no)"*

Do not proceed without an affirmative. If the founder's phrasing was
ambiguous ("get rid of this", "clear it"), do NOT treat it as ship — ask
what they mean.

**3. Push the branch and open the PR to `dev`:**

```bash
git push -u origin change/fix-login-bug
gh pr create --base dev --head change/fix-login-bug \
  --title "fix: fix the login bug" \
  --body "Change CH-01HQ8X · primitive: fix"
```

Capture the PR URL from stdout.

**4. Wait for `branch-ci` to pass.** This repo's PR-time check is
`branch-ci` (`.github/workflows/branch-ci.yml`). Poll its conclusion:

```bash
gh pr checks change/fix-login-bug --watch
```

- **Checks pass** → proceed to step 5.
- **Checks fail** → STOP. Do NOT merge. Surface the failure in plain
  English with the next step (Rule 5):

  > *"The automated checks didn't pass on **fix the login bug**, so I
  > haven't merged anything. The failing check is `branch-ci` — open
  > {pr_url} to see what broke, fix it on the change branch, and run
  > `/sulis:change ship CH-01HQ8X` again."*

**5. Squash-merge and clean up** (only after green + confirmation):

```bash
gh pr merge change/fix-login-bug --squash --delete-branch
```

Then sync local `dev`:

```bash
git checkout dev && git pull origin dev
```

**6. Report:**

> *"Shipped **fix the login bug** (`CH-01HQ8X`) into `dev`. The change
> branch is cleaned up. When you're ready to release everything on `dev`
> to production, that's a separate, deliberate step — just ask."*

### `rebase <CH-handle>` — pull in the latest

Bring a change branch current with the rest of the team's work. Uses
**merge, not rebase** (CW-04 — preserves commit SHAs so any in-flight work
inside the change stays valid). Safe action (no prompt needed), but echo
what's happening (Rule 3).

**1. Resolve the change** (same as `focus`); get its branch +
`worktree_path`.

**2. Run `back_integrate_change_branch` from inside the worktree:**

```bash
python3 -c "
import sys; sys.path.insert(0, '$SCRIPTS_DIR')
from _wpxlib import back_integrate_change_branch
from pathlib import Path
import json
r = back_integrate_change_branch(
    repo_root=Path('/abs/path/to/worktree'),
    change_branch='change/fix-login-bug',
    dev_ref='origin/dev',
)
print(json.dumps(r))
"
```

**3. Report by `status` (Rule 5 — explain + next step):**

- `already_current` → *"**fix the login bug** is already up to date with
  the rest of the team — nothing to pull in."*
- `merged_ok` → *"Pulled the latest team work into **fix the login bug**
  ({merged_commits} commit(s) merged in). You're current."* (Then push the
  updated change branch: `git push origin change/fix-login-bug`.)
- `merge_conflict` → *"The latest team work touches the same lines as your
  change, so they can't be combined automatically. The clashing file(s):
  {files}. Want me to walk you through resolving it, or leave it for now
  and keep working on what you have?"* (Per CW-04, do NOT auto-resolve.)
- `fetch_failed` → *"I couldn't reach the shared work to compare against
  ({error}). Check your network/remote and try `/sulis:change rebase
  CH-01HQ8X` again."*
- `internal_error` → surface plainly + suggest re-running; if it persists,
  it's a tooling issue to raise.

### `nuke <CH-handle>` — throw a change away

Delete a change and its full footprint: the git **branch**, the
**workspace** (worktree), the **local state**, and the committed
**manifest**. **Destructive + irreversible** — prompt-before-destroy
applies (Rule 3). Use it for abandoned experiments, dead-ends, and
orphaned changes the founder no longer wants.

**1. Resolve the change** (same as `focus`); get its branch + slug +
worktree. If the handle doesn't match, say so and offer `list`.

**2. Dry-run FIRST — always.** `nuke` without `--force` deletes nothing;
it lists exactly what *would* be removed. Run it and show the founder the
footprint before touching anything:

```bash
"$SCRIPTS_DIR/sulis-change" nuke --handle CH-01HQ8X
```

(Use `--slug <slug>` instead of `--handle` when you resolved the change by
slug — the tool accepts either.)

**3. Echo the footprint + the irreversible step, and require an explicit
yes** (MUC-F3 — never act on vague phrasing like "get rid of this"):

> *"This will permanently delete **fix the login bug** (`CH-01HQ8X`) — its
> branch, its workspace, and its saved state. {If the dry-run reported
> unmerged commits:} It has {N} commit(s) that aren't merged anywhere else,
> so that work would be lost for good. This can't be undone. Go ahead?
> (yes / no)"*

Do not proceed without an affirmative. If the founder is currently *in* the
change's workspace, the tool refuses (you can't nuke the change you're on) —
relay that and tell them to switch away first (`git checkout dev`).

**4. Delete (only after an explicit yes):**

```bash
"$SCRIPTS_DIR/sulis-change" nuke --handle CH-01HQ8X --force
```

`--force` is the confirm switch — it's also what's required to discard a
branch with unmerged commits.

**5. Report (Rule 1):** parse the JSON; lead with the outcome:

> *"Done — **fix the login bug** (`CH-01HQ8X`) is gone: branch, workspace,
> and saved state all removed."*

If the tool reports it couldn't fully resolve the change (e.g. the manifest
lives on a branch you're not on), relay what it *did* and didn't remove in
plain English — never claim a clean delete the tool didn't confirm.

### `stage <name>` — internal: stamp the workflow stage

Not a founder command. The stage skills (recon / specify / design / run-all
/ review) call this on completion so the dashboard reflects where each change
sits in the six-stage workflow. It resolves the change from the
`SULIS_CHANGE_ID` env var and records the stage in the branch-independent
local store:

```bash
"$SCRIPTS_DIR/sulis-change" stage design   # recon|specify|design|implement|review|ship
```

If a founder types it directly, treat it as a no-op-with-explanation: tell
them the dashboard updates on its own as work progresses, and point them at
`/sulis:dashboard` to see it.

---

## When to invoke this skill

- The founder wants to begin a new piece of work.
- The founder asks "what am I working on?" / "what's in flight?".
- The founder wants to get back into something they started earlier.
- The founder says a piece of work is done and wants it merged into the
  shared line.
- The founder wants their in-flight work updated with the latest team work.

## When NOT to invoke this skill

- The founder wants to ship one Work Package inside an active change — that
  is `/sulis:run-wp WP-NNN` / `/sulis:run-all` (the WP executor flow).
- The founder wants to resume a *journey* (the seven-phase coaching arc),
  not start/list/ship a change — that is `/sulis:start`.
- The founder wants to promote `dev` to `main` (release to production) —
  that is a separate, deliberate promotion step, not `ship`.
- The founder wants a read-only status summary of one change's WPs — that
  is `/sulis:status` / `/sulis:wp-status`.

## Gotchas

- **Operator vocabulary must not leak into what the founder reads.** The
  tools emit `branch`, `worktree_path`, `base_sha`, `change_id`,
  `spawn_result.status`. Translate at the seam: lead with the readable name
  + handle, hang the branch/path in parentheses or in a "technical
  version" the founder can opt into. Do NOT print the raw ULID as a
  headline. (MUC-F1)
- **`ship` is the irreversible one — prompt before it, every time.** Even
  though "ship" is an explicit subcommand, echo the exact branch + the
  merge step and require an explicit yes before `gh pr merge`. Never treat
  vague phrasing ("get rid of this", "clear it") as a ship instruction.
  (MUC-F3)
- **Never merge on a red check.** If `branch-ci` fails, STOP — surface the
  failure and the PR URL; do not squash-merge. The whole point of the gate
  is that broken work does not reach `dev`.
- **`ship` lands on `dev`, never `main`.** Promotion to `main` is a
  separate founder act. A `ship` that touches `main` is a bug.
- **`list` is file-based — no SQLite.** Read manifests + `session.json` +
  `git branch`. If you find yourself reaching for a database, you've drifted
  from the contract.
- **A `session.json` is not proof a terminal is live.** The recorded `pid`
  can be dead (terminal closed, machine rebooted). Check `kill -0 <pid>`
  before claiming a workspace is open, and before deciding whether `focus`
  should re-spawn. (MUC-F2 / MUC-F5)
- **`rebase` uses merge, not rebase** (the name is the founder's word for
  "catch up", not the git operation). Merge preserves SHAs so in-flight WP
  worktrees stay valid (CW-04). Do not "fix" this to a real git rebase.
- **`nuke` is irreversible — dry-run, echo, confirm, then `--force`.** Never
  pass `--force` on the first call. Run the dry-run, show the founder the
  exact footprint (and call out any unmerged commits that would be lost),
  require an explicit yes, *then* re-run with `--force`. Never treat vague
  phrasing ("clear it", "get rid of this", "delete that") as a nuke — ask
  what they mean. (MUC-F3)
- **`stage` is machinery, not a founder verb.** It's called by the stage
  skills to keep the dashboard current; don't surface it in founder-facing
  menus or suggest the founder type it.
- **Don't narrate the machinery.** The founder doesn't need to hear about
  `launch_change_terminal`, `back_integrate_change_branch`, or
  `SULIS_CHANGE_ID`. Surface what is now true and what they should do next
  (FE-09 / no mechanism narration).

## Vocabulary

- **Change** — one piece of work in flight: its own branch, worktree, and
  (when spawned) a focused terminal. The founder's mental model of "the
  thing I'm working on".
- **Handle (`CH-XXXXXX`)** — the short, founder-facing reference for a
  change (first 6 characters of its underlying ULID). Used everywhere the
  founder sees a change.
- **Slug** — the short kebab-case name a founder recognises
  (`fix-login-bug`); part of the branch name.
- **Primitive** — the kind of change, from the 22-primitive vocabulary
  (`../../references/change-primitives.md`); translated to a plain noun in
  founder-mode ("bug fix", "new feature", "restructuring").
- **Ship** — land a finished change into the shared `dev` line (PR →
  checks → squash-merge). Solo profile: no merge queue.
- **Rebase** (founder sense) — catch a change up with the latest team work;
  implemented as a merge, not a git rebase (CW-04).
- **Workspace / focused terminal** — the new terminal `start` opens, with
  Sulis already briefed on the change via the recon `CONTEXT.md`.
- **Nuke** — throw a change away: delete its branch, worktree, local state,
  and manifest. Irreversible; dry-runs by default, deletes only with
  `--force` after explicit founder confirmation.
- **Stage** — the change's position in the six-stage workflow (recon →
  specify → design → implement → review → ship), recorded in the branch-
  independent local store. The `stage` subcommand stamps it; `/sulis:dashboard`
  reads it. Internal machinery, not a founder verb.

## See also

- `../../scripts/sulis-change` — the CLI this skill drives
  (`start --spawn --intent`, `list`, `finish --merge`).
- `../../scripts/_terminal_launcher.py` — `launch_change_terminal`
  (spawn + reattach).
- `../../scripts/_wpxlib.py` — `resolve_current_change` (read
  `SULIS_CHANGE_ID` → manifest) + `back_integrate_change_branch` (the
  merge-not-rebase catch-up).
- `../../references/change-primitives.md` — the 22-primitive vocabulary.
- `../../references/founder-facing-conventions.md` — Rules 1-6.
- `../../docs/change-as-primitive-design.md` — the design this skill
  realises (Phase 6 deliverables).
- `/sulis:run-all` — ships the Work Packages inside a change.
- `/sulis:start` — re-enter a coaching journey.
