---
name: change
description: "Starts, lists, resumes, ships, or discards a piece of work."
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
| `/sulis:change recreate CH-01HQ8X` | Re-opens the workspace for a shipped change, exactly as it was when it shipped. |
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

**3. Preflight — don't start work on a stale `dev` (FR-010, ADR-003, GIT-12).**
This is the first thing that runs and it runs BEFORE any branch is cut.
A new change branch taken off a `dev` that's behind `main` re-introduces
stale content into the next release — so refuse to start until `dev` has
caught up. Run the shared drift helper, which prints its own recovery
instructions when it finds drift:

```bash
DRIFT_ERR="$(bash plugins/sulis/scripts/drift_check.sh 2>&1)"
if [ $? -ne 0 ]; then
  if printf '%s' "$DRIFT_ERR" | grep -q "dev is behind main"; then
    # Definitive drift. STOP — cut no branch, write no change record.
    printf '%s\n' "$DRIFT_ERR" >&2
    exit 1
  fi
  # Tooling / fresh-repo error (no git, not a repo yet, no origin/main,
  # or a failed fetch). Surface it as a heads-up but DO NOT block — a
  # fresh clone with no upstream yet is not drift.
  printf 'Heads-up: skipped the stale-dev check (%s). Continuing.\n' "$DRIFT_ERR" >&2
fi
```

Only a definitive "`dev` is behind `main`" stops the skill — then no
branch is cut and no change record is created, and the helper's message
names the next step (wait for the open back-integrate PR to merge, or run
the GIT-12 manual recovery). Any other non-zero result is a tooling or
fresh-repo condition (the helper can't reach `origin/main`); that does not
block — surface it and carry on. The helper owns the recovery wording; do
not restate it here. This is the developer-side half of the same gate
`/sulis:release-train` runs (single helper, two call sites). Per TDD §5.5
L3: this is the developer entry-point's defence-in-depth layer — the
release-train gate is L2, the workflow itself is L1.

**4. Echo the plan before acting (Rule 3).** One sentence, plain English,
before running anything:

> *"I'll start a new piece of work called **fix the login bug**
> (`fix-login-bug`), set up its own workspace, and open a fresh terminal
> with me already focused on it. Here goes."*

**5. Run the tool.** Substitute the resolved path:

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

**6. Report (Rule 1 + Rule 2).** Parse the JSON on stdout. Lead with the
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
   `pid`, `pid_kind`, `tty`, `terminal_app_used`, `spawned_at`).
   A session is live iff `session_is_live(change_id)` from
   `_change_state.py` returns True — the helper dispatches on
   `pid_kind` (macOS sessions check the tty; Linux/headless check
   the pid via `os.kill(pid, 0)`). A bare `kill -0 <pid>` would
   false-negative on macOS (the launcher pid exits within ~1s; the
   tty is the real handle).

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

- **Session looks live** (`session_is_live(change_id)` returns True
  — the helper checks the right handle for the platform): point the
  founder at the existing terminal — do NOT spawn a second one
  (MUC-F5: don't act on stale belief, and don't duplicate):

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
> shared `dev` line. The merge itself can't be casually undone. Afterwards
> I'll tidy away the workspace (you don't need it once it's shipped), but
> the branch + the full history stay as an audit trail you can retrace in
> the cockpit — and I can re-open the exact workspace any time with
> `recreate`. I'll only merge once the automated checks pass. Go ahead?
> (yes / no)"*

Do not proceed without an affirmative. If the founder's phrasing was
ambiguous ("get rid of this", "clear it"), do NOT treat it as ship — ask
what they mean.

**3. Push the branch and open the PR to `dev`:**

```bash
git push -u origin change/fix-login-bug
gh pr create --base dev --head change/fix-login-bug \
  --title "fix: fix the login bug" \
  --body "Change CH-01HQ8X · primitive: fix · Closes #42"
```

Capture the PR URL from stdout.

**PR-body close-trailer rules (MUST when the change addresses GitHub
issues, #34).** Scan the change's intent for `#NN` tokens. For every
issue the change addresses, the PR body MUST include a `Closes`-form
keyword PER issue — GitHub's auto-close-on-merge only acts on the issue
adjacent to the keyword. Accepted forms:

| Form | Example | Result |
|---|---|---|
| Comma-separated, keyword repeated | `Closes #27, closes #28` | Both auto-close ✅ |
| One sentence per issue | `Closes #27. Closes #28.` | Both auto-close ✅ |
| One trailer per line | `Closes #27`<br>`Closes #28` | Both auto-close ✅ |

**Forbidden** — only the first issue auto-closes:

| Form | Example | Result |
|---|---|---|
| Chained with "and" | `Closes #27 and #28` | Only #27 closes ✗ |
| Comma-separated, keyword once | `Closes #27, #28` | Only #27 closes ✗ |

Bit PR #33 (the #27 + #28 bundle); captured as #34. The rule applies
to richer PR-body templates too — when composing a longer Summary /
Test plan / Notes body, place a `Closes #N` trailer per addressed
issue near the bottom, separated per rule above.

**4. Wait for `branch-ci` to pass.** This repo's PR-time check is
`branch-ci` (`.github/workflows/branch-ci.yml`). Poll its conclusion:

```bash
gh pr checks change/fix-login-bug --watch
```

`gh pr checks --watch` is the correct gate — it exits non-zero on
failure. Read the CI *conclusion*, never a shell exit code: NEVER
substitute a chained `gh run watch <id>; echo $?` (the echo's exit is
always 0, not gh's) or a `gh run watch` without `--exit-status` (it
exits 0 on completion regardless of pass/fail) — see
`git-workflow-standard.md` GIT-04 *"Confirm CI by reading the
conclusion, not a shell exit code"*.

Alongside the wait — ONCE per ship — probe branch protection on the
landing line (`dev`). This is purely informational: it NEVER gates the
ship, no matter what it returns. The PR, the branch-ci wait, and the
review gate are all unchanged.

```bash
PROTECTION=$("$SCRIPTS_DIR/wpx-preflight" protection-status \
  --repo <org/repo> --branch dev)
```

Read `data.protection` from the JSON it emits:

- `protected` → say nothing. Protection is in force; the automated
  checks gate the merge. (Public / properly-protected repos behave
  exactly as before — no notice.)
- `unconfigured` → say nothing here. The repo CAN enforce gating but
  hasn't set it up; that is a one-time repo-setup matter the arrival
  check already surfaces, not a per-ship notice.
- `unavailable-free-plan` → emit the one-time warning below (founder-
  English — no rule codes, no HTTP status, no script or command
  names), THEN PROCEED with the ship regardless. Show it at most once
  per ship:

  > *"Heads-up before this lands: branch protection isn't available on
  > your plan, so the automated checks can't block a manual merge —
  > only merges I route through Sulis are checked before landing. This
  > ship goes through the checks as normal; I'm just flagging that a
  > merge by hand or a direct push to the shared line wouldn't be
  > stopped if it were broken. To close that gap you can make the repo
  > public or move to a paid plan. Carrying on with the ship now."*

  The notice never blocks: the ship continues to the checks + review
  gate exactly as it would on a protected repo.

- **Checks pass** → proceed to step 4.5.
- **Checks fail** → STOP. Do NOT merge. Surface the failure in plain
  English with the next step (Rule 5):

  > *"The automated checks didn't pass on **fix the login bug**, so I
  > haven't merged anything. The failing check is `branch-ci` — open
  > {pr_url} to see what broke, fix it on the change branch, and run
  > `/sulis:change ship CH-01HQ8X` again."*

**4.5. Review gate — run `/sulis:review` and respect its verdict
(MUST, #30).** `branch-ci` proves the tests + lint pass; it does NOT
audit the seven tiers (security, reliability, maintainability, …) or
the architectural / hygiene lenses a code-review applies. `/sulis:review`
composes `/sulis:code-health` + a security assessment + folds the result
into a single verdict. Run it **before** the squash-merge so any
critical findings block the merge rather than land on `dev`.

*CW-05 size carve-out — skip review when the change is genuinely
trivial:* before invoking the review, parse the diff size against
`origin/dev`:

```bash
git fetch origin dev -q
SHORTSTAT=$(git diff --shortstat origin/dev...HEAD)
# e.g. " 1 file changed, 5 insertions(+), 0 deletions(-)"
FILES=$(echo "$SHORTSTAT" | grep -oE '[0-9]+ files? changed' | grep -oE '[0-9]+')
INS=$(echo "$SHORTSTAT" | grep -oE '[0-9]+ insertions?\(\+\)' | grep -oE '[0-9]+')
DEL=$(echo "$SHORTSTAT" | grep -oE '[0-9]+ deletions?\(-\)' | grep -oE '[0-9]+')
TOTAL=$(( ${INS:-0} + ${DEL:-0} ))
```

If `FILES ≤ 1 AND TOTAL ≤ 30 AND no new files added (the diff has no
`new file mode` lines)` → log the skip in founder English ("The change
is small enough to skip the full review — 5 lines changed in 1 file.")
and proceed to step 5. **Otherwise**, dispatch `/sulis:review` (or
invoke the skill via the Skill tool) scoped to the PR diff:

> *"Running the review gate now — code-health across seven tiers + a
> security check. I'll come back with a verdict."*

The skill returns one of **PASS** / **CONCERN** / **CRITICAL**:

- **PASS** → log it ("Review verdict: clear. Proceeding to merge.")
  and continue to step 5.
- **CONCERN** → surface the findings to the founder in plain English
  and require explicit yes/no before continuing (mirrors the step 2
  confirm pattern). Don't auto-proceed — the founder owns the
  acceptable-risk call.

  > *"Review verdict: needs your eye. Three medium findings: {list}.
  > None block shipping, but worth seeing before the merge lands.
  > Proceed with the merge anyway? (yes / no)"*

- **CRITICAL** → STOP. Do NOT merge. Surface findings + the next step
  (mirrors the branch-ci-fail path):

  > *"Review found a critical issue I won't ship over: {finding +
  > file:line}. I haven't merged. Fix on the change branch, then run
  > `/sulis:change ship CH-01HQ8X` again."*

**4.6. Capture lessons (REQUIRED — before the merge, never a post-ship
question).** Any lessons surfaced while doing this change — gaps or bugs
in Sulis's own tooling, recurring friction, design observations worth
keeping — get captured as durable issues **now, automatically, before the
merge**. This is a mandatory gate, not a *"want me to capture these? before
or after you ship?"* question. Asking would be the permission-theatre
AAF-08 forbids: capturing lessons is a process step the agent owns, like
the review gate itself. (A lost lesson is the expensive failure; an empty
capture run costs nothing.)

Assemble the change's findings into an items file (each with a
`disposition`: `sea`/`task` = actionable → durable issue; `fix-now` /
`fixed` / `note` = recorded without an issue) and run the capture — or
invoke `/sulis:capture-lessons`, which assembles + files them:

```bash
"$SCRIPTS_DIR/sulis-issues" capture --descriptor lesson \
  --items-file /tmp/lessons-{slug}.json --repo <owner/repo>
```

It is a **no-op when there are no actionable findings**, so running it on
every ship is safe. If there are findings, surface what was captured in the
ship report (step 7) — "Captured 4 lessons as issues #60-63" — never as a
question. By the time the merge runs, the lessons are already filed.

**4.7. Write the changeset (REQUIRED — before the merge, never a post-ship
question).** Every change that touches what people install records a one-line
**release note** of its own, automatically, before it lands. That note is what
lets the project assemble the next release — its version and its changelog —
in one batched, deterministic step instead of leaving it to whoever ships to
remember. Like the review gate and the lesson capture, this is a step the agent
owns, not a *"want me to record a release note?"* question (AAF-08).

The note records *what changed and how big a release it is* — never a version
number. The size (`patch` / `minor` / `major`) is read straight off the kind of
change the founder already chose at `start` (its primitive), so there is no
second judgment call to get wrong. Admin-only or docs-only changes that don't
touch what people install record **no** note — that's expected, not a miss.

Resolve `$SCRIPTS_DIR` exactly as the block at the top of this skill already
does (don't re-derive it), then:

```bash
# Does this change touch what people install? (the sulis plugin tree)
git fetch origin dev -q
TOUCHES_PLUGIN=$( [ -n "$(git diff --name-only origin/dev...HEAD -- plugins/sulis/)" ] \
  && echo True || echo False )

# Record the release note. The size is read from the change's primitive;
# admin/docs-only changes (size = none) record nothing — and that's fine.
python3 -c "
import sys; sys.path.insert(0, '$SCRIPTS_DIR')
import _changeset, datetime, json
primitive = '<the change primitive, e.g. fix / feat / extend>'
tier = _changeset.tier_for_primitive(primitive)
if tier is None:
    print(json.dumps({'wrote': False, 'reason': 'admin/docs-only — no release note'}))
else:
    p = _changeset.write_changeset(
        '.changesets',
        change_id='<this change ULID>',
        primitive=primitive,
        tier=tier,
        touches_plugin=$TOUCHES_PLUGIN,
        summary='''<the change intent, in plain English — this becomes the changelog line>''',
        slug='<the change slug, e.g. release-train>',
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    print(json.dumps({'wrote': True, 'path': str(p), 'tier': tier}))
"
git add .changesets/   # the note is part of the change, so it lands on dev with the squash
```

The note is written **before** the squash-merge so it travels in with the
merged change and lands on `dev`. **This step records the note and explicitly
does NOT bump any version** — the version is computed and applied once, for the
whole batch, when `dev` is released to production. Read the `wrote` field of the
JSON to know what to say in the ship report (step 7).

**4.8. DoD verification gate — run `sulis-verify-requirements` (MUST when
an SRD is touched).** The change's tests claim what they verify via
`@pytest.mark.verifies("FR-NN")` markers; the pytest brain-emit plugin
turns those claims into TestResult entities in `.brain/instances/`; this
gate asks the brain whether every Requirement the change touched has at
least one passing TestResult verifying it. If yes → ship. If not → the
founder owns the call.

Detect: does this change touch any SRD?

```bash
git fetch origin dev -q
SRDS_TOUCHED=$(git diff --name-only origin/dev...HEAD \
  | grep -E '^\.specifications/.+/SRD\.md$' || true)
```

If `SRDS_TOUCHED` is empty → skip the gate silently (lite/standard
specs and trivial changes don't carry FR-NN blocks; there's nothing
to verify against). If any SRDs are touched, run the gate against
EACH and aggregate:

```bash
WORST=pass
for srd in $SRDS_TOUCHED; do
  rc=0
  OUT=$("$SCRIPTS_DIR/sulis-verify-requirements" --srd "$srd") || rc=$?
  case $rc in
    0) ;;  # this SRD passes — keep aggregating
    1) [ "$WORST" = "pass" ] && WORST=partial ;;
    2) WORST=fail ;;
    3) WORST=error ;;  # gate broke — advisory only
  esac
  echo "$OUT"  # surface the per-SRD verdict for the report
done
```

Verdict policy:

- **WORST=pass** → log it ("DoD gate: every Requirement verified by a
  passing test.") and continue to step 5.
- **WORST=partial** → some Requirements have NO passing verifier. The
  founder owns the call (mirrors the review-gate CONCERN pattern):

  > *"DoD gate: {N} of {M} Requirements aren't yet verified by a
  > passing test: {fr_ids + titles, plain English, no IDs}. None of
  > this is broken — these Requirements just don't have a test claim
  > yet. Proceed with the merge anyway? (yes / no)"*

- **WORST=fail** → STOP. Zero Requirements have a passing verifier,
  which means either no tests claim them OR every claim is currently
  failing. Don't merge:

  > *"DoD gate: no Requirements have a passing test verifying them.
  > That usually means tests aren't tagged with `@pytest.mark.verifies`
  > yet, or the tests that DO claim Requirements are failing. I
  > haven't merged. Either add `@verifies` to the tests that prove
  > the Requirements, or run `sulis-verify-requirements --srd <path>`
  > locally to see which ones are uncovered. Then
  > `/sulis:change ship CH-XXXXXX` again."*

- **WORST=error** → log the gate failure but PROCEED with the merge
  (don't break ship on tooling issues; the gate is advisory when it
  itself can't run):

  > *"DoD gate couldn't run — proceeding without it. (Tooling issue,
  > not a coverage issue. See `{error}` for detail.)"*

The gate is best-effort in the same way the review gate's CONCERN is:
the founder always owns the proceed-anyway decision. Block-by-default
applies only to verdict=fail (zero coverage), which is genuinely
broken state.

**4.9. Testable-state acceptance gate — run `sulis-verify-acceptance`
(MUST for a user-facing / behavioural change).** A change that authored
verification `Scenario`s at design (draft-architecture step 3.5 clause d)
is not *done* until those Scenarios pass against a **standing app** — the
real "done" is *the app is testable*, not *merged* (the failure this
catches: agent-journey shipped, but you couldn't log in). Run each
in-scope Scenario:

```bash
"$SCRIPTS_DIR/sulis-verify-acceptance" \
  --bundle <scenario-bundle> --target local --repo-root . --json
```

(`local` now; the `deployed` leg once that target is reachable — both per
the repo-contract `targets:` + `commands.standup`.) Read the gate verdict:

- **pass** → every Scenario passed, or is deferred-with-need. Done is
  honest. Log it.
- **blocked** → a step failed, or a manual check is unconfirmed. **STOP** —
  surface the founder-English gap (which Scenario, what's broken). Do not
  call the change done.
- **deferred-with-need** → a recorded gap (a credential / infra absent);
  non-blocking, but surface the needs so they're visible.

Advisory when it can't run (no Scenarios authored — pure docs/infra change;
or no target URL yet): like 4.8, the founder owns proceed-anyway, and
block-by-default applies only to a real `blocked`.

**5. Squash-merge** (only after green + confirmation):

```bash
gh pr merge change/fix-login-bug --squash --delete-branch
```

`--delete-branch` deletes only the **remote** branch (the merge artefact gh
no longer needs). The **local** branch stays — it's the audit trail. (The
local worktree is tidied away in step 6.)

Then sync local `dev` — **in whichever worktree holds it** (never `git
checkout dev` inside a change worktree; in the multi-worktree model `dev`
may be checked out elsewhere and git forbids the same branch in two
worktrees):

```bash
git -C "$(git worktree list --porcelain | awk '/^worktree /{p=$2} /^branch refs\/heads\/dev$/{print p}')" pull origin dev 2>/dev/null \
  || { git checkout dev && git pull origin dev; }
```

**6. Mark the change as shipped, and tidy the workspace (#38/#56).** Flips
`stage='shipped'`, pins `shipped_sha` (the branch tip — "the state it was in
when we shipped"), and **removes the now-redundant worktree** (kept if a live
session is bound or if there's uncommitted work). The branch + record stay;
`recreate` brings the worktree back on demand:

```bash
"$SCRIPTS_DIR/sulis-change" mark-shipped --handle CH-01HQ8X \
  --repo-root <main-repo-root>
```

**7. Report** (include the lessons captured at step 4.6 and the release note
recorded at step 4.7, if any):

> *"Shipped **fix the login bug** (`CH-01HQ8X`) into `dev`. Recorded this as a
> `minor` release note, and captured 2 lessons along the way (issues #60-61).
> I've tidied away the workspace, but the full history is preserved as an audit
> trail you can retrace in the cockpit (under 'Shipped') — and I can re-open the
> exact workspace any time with `recreate`. When you're ready to release
> everything on `dev` to production, that's a separate, deliberate step — just
> ask."*

State the release note as a fact, never as a question. When step 4.7 wrote one,
name its size (*"Recorded this as a `minor` release note."*); when it wrote none
(an admin/docs-only change), say so plainly (*"No release note needed — this
doesn't change what people install."*). Drop the lessons sentence when step 4.6
captured none.

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

### `recreate <CH-handle>` — re-open a shipped change's workspace

After a change ships, its workspace (worktree) is tidied away to avoid
sprawl — but the branch + full history are kept and the shipped state is
pinned (`shipped_sha`). `recreate` brings the workspace back, exactly as it
was. Safe action (no prompt needed), but echo what's happening (Rule 3).

**1. Resolve the change** (same as `focus`); get its handle.

**2. Run the tool:**

```bash
"$SCRIPTS_DIR/sulis-change" recreate --handle CH-01HQ8X \
  --repo-root <main-repo-root>
```

It re-materialises the worktree on the kept branch (so the founder can pick
work back up), or — if the branch has since been deleted — detached at the
pinned `shipped_sha` (a read-only view of exactly what shipped).

**3. Report by the JSON (Rule 1):**

- `recreated: true`, `detached: false` → *"Re-opened the workspace for
  **fix the login bug** (`CH-01HQ8X`) on its branch — pick up right where it
  shipped."*
- `recreated: true`, `detached: true` → *"Re-opened **fix the login bug**
  (`CH-01HQ8X`) as a read-only snapshot of exactly what shipped (its branch
  was removed, so it's a view, not a place to keep working)."*
- `recreated: false` (`already exists`) → *"The workspace for **fix the
  login bug** (`CH-01HQ8X`) is already open at `{worktree}`."*

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
  that is a separate, deliberate step (`/sulis:release-train` opens the
  reviewed promotion PR; the release Action applies the version bump from
  the accumulated release notes), not `ship`.
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
  can be dead (terminal closed, machine rebooted). On macOS the launcher
  pid exits within ~1s — `pid` is `null` and the real handle is the
  recorded `tty`. Always use `session_is_live(change_id)` from
  `_change_state.py`; it dispatches on `pid_kind` to the right check.
  Never inline `kill -0 <pid>` — that false-negatives on macOS.
  (MUC-F2 / MUC-F5)
- **`rebase` uses merge, not rebase** (the name is the founder's word for
  "catch up", not the git operation). Merge preserves SHAs so in-flight WP
  worktrees stay valid (CW-04). Do not "fix" this to a real git rebase.
- **Never `git stash` in a change worktree (issue #53).** The stash stack
  is shared per-repo across every worktree, so a positional `git stash pop`
  can grab an *unrelated* sibling worktree's stash and dump its files in as
  cruft (the DC-04 incident). `adopt` moves uncommitted work with explicit
  file movement (`transfer_worktree_changes`), never the shared stash stack.
  If you ever need to park transient state, make a throwaway WIP commit —
  don't reach for `git stash`.
- **Never `git checkout dev` inside a change worktree (issue #56).** A change
  worktree only ever holds its OWN `change/*` branch. In the multi-worktree
  model `dev` is checked out elsewhere and git forbids the same branch in two
  worktrees — `git checkout dev` returns *"fatal: 'dev' is already checked
  out"*. To sync `dev`, operate in whatever worktree holds it (`git worktree
  list --porcelain`). `sulis-change finish --merge` already does this for you.
- **Ship removes the worktree but keeps the branch — that's intended (issue
  #56).** After ship, the worktree is tidied away (it's redundant; the branch
  + record + cockpit preserve full retrace) and `shipped_sha` pins the exact
  shipped state. It is KEPT when a live session is bound or there's
  uncommitted work. If the founder wants it back, that's `recreate` — never
  tell them their work is gone.
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
- **The release note is written before the merge, and it never bumps a
  version.** Step 4.7 writes the changeset on the change branch so it travels
  in with the squash and lands on `dev` — write it after the squash and it
  never reaches the shared line. The step records *intent and size only*; the
  version bump happens once, for the whole batch, when `dev` is released to
  production (a separate, automated step). A ship step that bumps a version is
  a bug. Admin-only / docs-only changes (ones that don't touch what people
  install) write no note — that's expected, not a missed step.

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
