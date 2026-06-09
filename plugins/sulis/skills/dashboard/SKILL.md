---
name: dashboard
description: "Shows every piece of work you have in flight and how far along each is."
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
    skill: ../inbox/SKILL.md
    notes: dashboard is the by-CHANGE map; inbox is the by-ITEM attention list. Dashboard flags attention, inbox shows the detail.
  - relationship: related_to
    skill: ../change/SKILL.md
    notes: change start/focus/ship/nuke act on one change; dashboard surveys them all
  - relationship: optional_input
    skill: ../../references/founder-facing-conventions.md
    notes: Audience=founder-facing; Rules 1-6 apply (no operator-jargon leak, MUC-F4 overwhelm cap)
---

# /sulis:dashboard — the map of everything you're working on

## Conclusion (lead with the answer)

`/sulis:dashboard` is the one screen that shows **every piece of work you
have in flight and where each one sits**. For each change it shows:

- the readable name + handle (`CH-XXXXXX`),
- the kind of work (bug fix / new feature / restructuring …),
- the **stage** it has reached — recon → specify → design → implement →
  review → ship,
- whether its **workspace is open** (a live terminal) or closed,
- and a flag if it **needs your attention**.

The dashboard is the *by-change* view ("what are all my things, and how far
along is each?"). For the *by-item* detail of what's actually waiting on you
— paused work, things to review, blockers, decisions — it points you to
`/sulis:inbox`. Dashboard highlights; inbox drills in.

It is **read-only**. It surveys; it never starts, ships, or deletes a
change. To act on one, the dashboard tells you the exact `/sulis:change …`
command to run.

This skill is an **orchestrator** — it reads the branch-independent local
store via existing tooling and renders it. It introduces no new state of its
own.

## Resolving the tool path (MUST — first action)

The change tools live inside the sulis plugin. Resolve the directory ONCE
and capture it as `$SCRIPTS_DIR` (same resolver the `change` skill uses):

```bash
# Resolve from the ACTIVE plugin version (its bin/ is on PATH) — avoids the
# lexical-sort cache pick that mis-ranks 0.98.0 above 0.126.0 (#49).
SCRIPTS_DIR=""
_sulis_bin=$(printf '%s\n' "$PATH" | tr ':' '\n' | grep -E 'sulis-ai-agents/sulis/[^/]+/bin$' | head -1)
if [ -n "$_sulis_bin" ] && [ -d "$(dirname "$_sulis_bin")/scripts" ]; then
  SCRIPTS_DIR="$(dirname "$_sulis_bin")/scripts"
fi
# Dev fallback: marketplace repo cwd.
if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/sulis-change" ]; then
  SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
fi
# Last-resort fallback ONLY if PATH anchor + dev both miss: a PORTABLE
# version-aware cache pick (numeric, NOT lexical, NOT `sort -V`).
if [ -z "$SCRIPTS_DIR" ]; then
  SCRIPTS_DIR=$(find ~/.claude/plugins/cache -name sulis-change -type f -path '*/sulis/*/scripts/*' 2>/dev/null \
    | sed -E 's#(.*/sulis/)([^/]+)(/scripts/.*)#\2 &#' \
    | sort -t. -k1,1n -k2,2n -k3,3n \
    | tail -1 | cut -d' ' -f2- | xargs -I{} dirname {} 2>/dev/null)
fi
if [ -z "$SCRIPTS_DIR" ]; then
  echo "ERROR: cannot find the change tools. Run: claude plugin install sulis@sulis-ai-agents" >&2
  exit 1
fi
echo "SCRIPTS_DIR=$SCRIPTS_DIR"
```

## When invoked

**1. Read the global change store.** This is branch-independent — it lives
outside git, so it sees every change regardless of which branch you're on.
`list_all_changes()` returns the full records (most-recent-first), with each
change's *live* stage already overlaid:

```bash
python3 -c "
import sys, json; sys.path.insert(0, '$SCRIPTS_DIR')
from _change_state import list_all_changes, change_dir
rows = list_all_changes()
print(json.dumps(rows, indent=2))
"
```

If the list is empty, say so plainly and point at the next step:

> *"You have no changes in flight right now. To start one, run
> `/sulis:change start \"<what you want to do>\"`."*

**2. Enrich each change with ground-truth liveness + git state.** The store
record is the index; cross-check it against reality so the dashboard never
lies:

- **Workspace open?** Call `session_is_live(change_id)` from
  `_change_state.py`. The helper dispatches on `pid_kind`: macOS
  sessions (`pid_kind="session"`) check the recorded `tty` device
  file + active processes on it; Linux/headless sessions
  (`pid_kind="launcher"`) check `os.kill(pid, 0)`. A bare
  `kill -0 <pid>` would false-negative on the macOS path (the
  launcher pid exits within ~1s; the tty is the real liveness
  handle). Invoke via:

  ```bash
  python3 -c "
  import sys; sys.path.insert(0, '$SCRIPTS_DIR')
  from _change_state import session_is_live
  print('1' if session_is_live('<change_id>') else '0')
  "
  ```

  Output `1` → "workspace open"; `0` → "no live workspace".
- **Branch still there?** `git branch --list <branch>` — a change whose
  branch is gone has almost certainly shipped or been nuked.
- **Worktree still there?** `Path(worktree_path).exists()`.

A change with **no branch and no worktree** has been shipped or removed —
show it under a separate "Recently closed" line, not as active work (or omit
if the store record is stale; never present a shipped change as in-flight).

**3. Translate to founder English.** Per `founder-facing-conventions.md`:

- **primitive → plain noun**: `fix`→"bug fix", `feat`/`create`→"new
  feature", `decompose`→"restructuring", `replace`→"replacement",
  `delete`→"removal", etc.
- **stage → plain position**: show it as a position in the six-stage
  journey, e.g. *"design stage (3 of 6)"*. The six, in order: recon,
  specify, design, implement, review, ship.
- **handle, not ULID**: lead with the readable name; the `CH-XXXXXX` handle
  hangs in parentheses. Never show the raw 26-char `change_id` as the
  headline.

**4. Flag attention.** A change wants attention when it is **at the review
stage** (something is waiting to be reviewed) or has **work in progress with
no live workspace** (it stalled). Don't try to enumerate the items here —
that is inbox's job. Just flag the change and point on.

**5. Render the dashboard** (MUC-F4 overwhelm cap: show the most-recent ~10
active; if more, add a "+N more" line):

```
🗂  Your changes — {N} in flight

  ▸ {readable name} ({CH-XXXXXX}) — {plain noun}
      {stage} stage ({k} of 6) · {workspace open, last active 4 min ago | no live workspace}
      {⚠ needs attention — {one-line why}   ← only when flagged}

  ▸ add Stripe checkout (CH-01J2KQ) — new feature
      review stage (5 of 6) · no live workspace
      ⚠ needs attention — waiting on a review

  ▸ fix the login bug (CH-01HQ8X) — bug fix
      implement stage (4 of 6) · workspace open, last active 4 min ago

  (Recently closed: 2 changes shipped — run `/sulis:change list` to see them.)

{If anything is flagged:}
  {M} of your changes need attention. To see exactly what's waiting on you
  — things to review, blockers, decisions — run `/sulis:inbox`.

What you can do:
  • Jump back into one        → /sulis:change focus CH-XXXXXX
  • Land a finished one       → /sulis:change ship  CH-XXXXXX
  • Throw one away            → /sulis:change nuke  CH-XXXXXX
  • See the item-level detail → /sulis:inbox
```

Omit the "needs attention" summary line entirely when nothing is flagged —
don't manufacture urgency.

**6. Technical mode (`--raw` / "show me the raw version").** Emit the
enriched JSON array — one object per change with `change_id`, `handle`,
`slug`, `primitive`, `branch`, `stage`, `workspace_live` (bool),
`branch_present` (bool), `worktree_present` (bool), `needs_attention`
(bool). Same substance, machine shape.

## Gotchas

- **The store record is the index, not the ground truth for liveness or git
  state.** A `session.json` can record a dead `pid` (terminal closed); a
  branch can be gone (shipped). Always cross-check `kill -0`, `git branch
  --list`, and `worktree_path.exists()` before claiming a workspace is open
  or a change is active. Presenting a shipped change as in-flight is the
  MUC-F5 stale-belief failure.
  *Source: the same liveness discipline the `change focus`/`list`
  subcommands enforce.*

- **Operator vocabulary must not leak.** The store emits `change_id`,
  `branch`, `worktree_path`, `stage` (raw enum). Translate every one at the
  seam: readable name + handle, plain-noun primitive, stage-as-position.
  Never print the 26-char ULID or a raw branch ref as a headline. (MUC-F1)
  *Source: founder-english anchor cases 3 and 4.*

- **Don't double-do the inbox's job.** The dashboard flags *that* a change
  needs attention; it does not enumerate the paused trains, findings, and
  decisions — that is `/sulis:inbox`. Listing every item here re-implements
  inbox and overwhelms the by-change view. Flag, then route. (MUC-F4)

- **Compute on read; never cache.** Re-read the store and re-check liveness
  on every invocation. A cached dashboard shows state from N minutes ago and
  the founder acts on a workspace that has since closed or a change that has
  since shipped.
  *Source: the same compute-on-read rule inbox follows.*

- **Empty store is a valid, common state — not an error.** A founder who has
  shipped everything (or not started) sees zero changes. Say so plainly and
  give the `start` command; do not surface a scary "nothing found".

- **The store is branch-independent by design.** It lives at
  `{state_base}/changes/` (outside git) precisely so the dashboard works
  from any branch. Don't "fix" this by reading `.changes/*.yaml` off the
  current branch — that only sees the change you're on. (The committed
  manifest is per-branch; the local store is the global view.)

## Vocabulary

- **dashboard** — this skill; the by-change map of all work in flight and
  the stage each has reached.
- **change** — one piece of work: its branch, worktree, and (when open) a
  focused terminal. Referenced by its handle `CH-XXXXXX`.
- **stage** — where a change sits in the six-stage workflow: recon → specify
  → design → implement → review → ship. Stored as branch-independent local
  state and stamped by each stage skill as the work progresses.
- **global change store** — the branch-independent local index at
  `{state_base}/changes/{change_id}/` (`change.json` + `state.json`). The
  source the dashboard reads. Distinct from the committed per-branch
  `.changes/*.yaml` manifest.
- **needs attention** — a dashboard flag (at-review, or stalled-with-no-live-
  workspace). The *detail* of what's waiting lives in `/sulis:inbox`.
- **workspace open / closed** — whether a change has a live terminal,
  determined by `kill -0` on the recorded session `pid`, not by the mere
  presence of a `session.json`.

## When to invoke this skill

- Founder asks "what am I working on?", "show me my changes", "what's in
  flight?", "where's everything at?"
- After a break / new session — founder wants the lay of the land across all
  their work before deciding what to pick up.
- Sulis wants to ground a "what next?" recommendation in the actual set of
  changes and their stages.

## When NOT to invoke this skill

- Founder asks "what's *waiting on me*?" / "what needs my attention?" —
  that's `/sulis:inbox` (the item-level detail this skill points to).
- Founder wants to act on one specific change (start / focus / ship / nuke /
  rebase) — that's `/sulis:change <subcommand>`.
- Founder asks "what phase am I in?" for a single project's journey — that's
  `/sulis:status` / `/sulis:start`.
- Operator wants the raw branch list — `sulis-change list` (or
  `/sulis:dashboard --raw`).

## See also

- `../../scripts/_change_state.py` — `list_all_changes()` (the branch-
  independent read seam), `change_dir()`, `WORKFLOW_STAGES`.
- `../change/SKILL.md` — start / list / focus / ship / rebase / nuke.
- `../inbox/SKILL.md` — the by-item attention list this skill routes to.
- `../../references/founder-facing-conventions.md` — Rules 1-6.
- `../../docs/change-as-primitive-design.md` — the hybrid-storage design
  (committed per-branch vs local global store) this skill reads.
