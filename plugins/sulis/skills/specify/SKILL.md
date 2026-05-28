---
name: specify
description: "Writes down what a piece of work should do, at the right depth."
user_invocable: true
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
  output: [CRITICAL_THINKING_STANDARD, COACHING_STANDARD, TONE_STANDARD]
register:
  founder_mode: default
  technical_mode:
    shape: json_envelope
    triggers: [intent, --raw, /sulis:jargon]
verification_spiral:
  tier: standard
  template_base: STANDARD_TIER_DEFAULT
related_skills:
  - relationship: depends_on
    skill: ../../scripts/_specify_classifier.py
    notes: deterministic depth classifier (file count + primitive + founder-facing → lite/standard/deep)
  - relationship: depends_on
    skill: ../../scripts/_wpxlib.py
    notes: resolve_current_change() reads SULIS_CHANGE_ID → change manifest (primitive, intent, branch, worktree)
  - relationship: related_to
    skill: ../change/SKILL.md
    notes: change start opens the workspace; specify is the first stage inside it
  - relationship: related_to
    skill: ../draft-architecture/SKILL.md
    notes: design reads the SPEC.md this skill produces; design is optional after a lite spec
  - relationship: related_to
    skill: ../index-specifications/SKILL.md
    notes: a deep spec lands a .specifications/{name}/ folder this skill can index
  - relationship: optional_input
    skill: ../../references/founder-facing-conventions.md
    notes: Audience=founder-facing; Rules 1-6 apply (echo-before-act, dual-register)
  - relationship: optional_input
    skill: ../../references/change-primitives.md
    notes: the change's primitive is one of the classifier's signals
---

# /sulis:specify — write down what the work should do

## Conclusion (lead with the answer)

`/sulis:specify` captures what a piece of work should do, at a depth that
matches the work. It looks at the change you're in, **picks** one of three
depths (a deterministic call the agent owns), announces it in plain English,
and runs it — writing a `SPEC.md` next to the change. You can redirect the
depth any time ("keep it light" / "go deeper"); you're never asked to ratify
it up front.

| Depth | What you do | What you get | Good for |
|---|---|---|---|
| **Lite** | Answer three short prompts (~30 seconds) | A ten-line `SPEC.md` | A typo, a one-file fix, a small mechanical change |
| **Standard** (default) | A few questions, back and forth (~3 minutes) | A `SPEC.md` with the goal, what's in and out, how you'll know it's done, and what to avoid | Most work |
| **Deep** | A full guided requirements session | A `SPEC.md` plus flow diagrams (the requirements specialist runs this) | A new feature, a new system, anything your users will see |

The skill **decides** the depth and announces it (e.g. *"This is a small,
contained change, so I'll write a quick lite spec — shout if you'd rather a
fuller one."*), then runs. The depth is the agent's call, not a question put
to you — a non-technical founder has no basis to ratify "lite vs standard",
and asking would be permission-theatre. Only a *deep* spec (a ~20-min guided
session) gets a one-line heads-up before it starts, since that's real time of
yours — and even then it starts, it doesn't block.

Founder-mode is the default: plain English, no jargon. You can ask for the
raw output any time (*"show me the technical version"* / `--raw`) and get the
underlying signals and the decision as data — same substance, different shape
(Founder-Facing Conventions Rule 6).

## Resolving the change + the tool path (MUST — first action)

This skill runs **inside a change** (a workspace opened by
`/sulis:change start`). It reads the change's identity to know the primitive,
the intent, and where to write the spec.

1. **Resolve the script directory ONCE** (the sulis tools live in the plugin
   cache when installed downstream, or in the marketplace repo in dev):

   ```bash
   SCRIPTS_DIR=$(
     find ~/.claude/plugins/cache \
       -name _specify_classifier.py -type f \
       -path '*/sulis/*/scripts/*' \
       2>/dev/null \
     | sort -r | head -1 | xargs -I{} dirname {} 2>/dev/null
   )
   if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/_specify_classifier.py" ]; then
     SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
   fi
   if [ -z "$SCRIPTS_DIR" ]; then
     echo "ERROR: cannot find the sulis tools. Run: claude plugin install sulis@sulis-ai-agents" >&2
     exit 1
   fi
   echo "SCRIPTS_DIR=$SCRIPTS_DIR"
   ```

   Capture the printed path and substitute the literal at each
   `$SCRIPTS_DIR` below — environment variables do NOT persist between Bash
   tool calls in Claude Code.

2. **Resolve the current change** via `resolve_current_change()` (reads the
   `SULIS_CHANGE_ID` env var → the change manifest):

   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '$SCRIPTS_DIR')
   from _wpxlib import resolve_current_change
   import json
   c = resolve_current_change()
   print(json.dumps(c) if c else 'null')
   "
   ```

   - **If this prints a change** — capture `change_id`, `handle`, `slug`,
     `primitive`, `intent`, `branch`, `worktree_path`. You're inside a change;
     proceed.
   - **If this prints `null`** — there is no current change. Do NOT guess.
     Say so plainly and point the way:

     > *"I can't tell which piece of work this is for — `/sulis:specify` runs
     > inside a change. Start one with `/sulis:change start "what you're
     > doing"`, and I'll pick it up from there."*

## Step 1 — gather the three signals (deterministic)

The depth proposal comes from three signals. Gather them; never invent them.

1. **The primitive** — from the change manifest (`primitive` field). This is
   the kind of change (`fix`, `create`, `refactor`, …). One of the 22 in
   `../../references/change-primitives.md`, or a Conventional-Commits fallback
   (`feat` / `fix` / `chore`).

2. **The file count** — how many files the change touches so far.
   Best-effort: at specify time there may be no commits yet, in which case
   this is unknown (`None`). Compute it from the change branch against its
   base, run **inside the worktree**:

   ```bash
   git -C {worktree_path} diff --name-only {base_branch}...HEAD 2>/dev/null | wc -l
   ```

   If the change has no commits yet, also count staged + unstaged work:
   `git -C {worktree_path} status --porcelain | wc -l`. If both are zero, pass
   `None` (unknown) — do NOT pass `0` as if the change were empty by design.

3. **The founder-facing flag** — does the change touch a user-visible
   surface? Feed the touched paths (from the same `git diff --name-only`) to
   the classifier's `paths_touch_founder_surface()` helper. If there are no
   files yet, fall back to the primitive + intent: a `create` / `feat` /
   `generate` whose intent mentions a screen, page, flow, email, or anything
   the user sees → founder-facing.

## Step 2 — classify the depth (deterministic helper)

Call the classifier with the three signals:

```bash
python3 -c "
import sys; sys.path.insert(0, '$SCRIPTS_DIR')
from _specify_classifier import classify_depth, paths_touch_founder_surface, proposal_sentence
paths = ['src/components/Login.tsx']  # the touched paths from Step 1, or []
d = classify_depth(
    primitive='fix',          # from the manifest
    file_count=1,             # int, or None if unknown
    founder_facing=paths_touch_founder_surface(paths),
)
print(d.depth)
print(proposal_sentence(d))
"
```

The classifier is **deterministic** and **defaults to standard on
uncertainty** (unknown primitive, mid-size work, ambiguous signals). It only
proposes — it never runs a mode.

## Step 3 — decide the depth, announce it, proceed (Rule 3 + AAF; decide-and-report)

The depth is an **engineering-internal decision the agent owns** — the
classifier already computed it deterministically, and a founder has no basis
to ratify "lite vs standard". Do **not** ask them to confirm or override it;
that's the permission-theatre AAF-08 forbids (a process decision dressed as a
founder choice). Take the classified depth, announce it in one plain sentence,
and run it. The founder can always redirect *after* ("make it lighter" / "go
deeper") — the override never needs pre-asking.

> *"This is a small, contained change, so I'll write a quick three-line spec —
> shout if you'd rather a fuller one."*

- **lite / standard** → just run it (announce + proceed). No question.
- **deep** is the one case with a genuine founder-facing consequence — a full
  guided requirements session is ~20–30 min of *your* time. Still don't block:
  start it with a one-line heads-up + a cheap opt-out
  (*"This looks big enough for a full spec — that's ~20 min of questions; say
  'keep it light' if you'd rather a quick version."*), then proceed.
- The classifier defaults to standard on uncertainty; that default is the
  agent's to apply, not the founder's to confirm.

Never *interrogate* the founder to ratify the computed depth. (Genuine scope
questions discovered *while writing* the spec — what a feature should do, who
it's for — are different: those are founder-owned, ask them per AAF-01.)

## Step 4 — run the chosen mode

### Lite mode

Three short prompts, conversational, ~30 seconds total:

1. **What do you want this to do?** (the intent — one or two sentences)
2. **How will you know it's done?** (acceptance — what's observably true after)
3. **What should this NOT touch / what to avoid?** (the guardrail)

Write a ~10-line `SPEC.md` (see Output below) with exactly those three
fields. Do not pad it with empty sections — lite is lite on purpose.

**After a lite spec, design is optional.** Decomposition is usually obvious
for a small change (one Work Package). Offer the shortcut:

> *"That's small enough to go straight to a single task — want me to draft it
> and run it, or would you rather do a design pass first?"*

### Standard mode (default)

A 5–10 question facilitated conversation, **one question at a time**, ~3
minutes. Cover, in roughly this order, adapting to what the founder says:

- **Goal** — what this change is for, in the founder's words.
- **Scope** — what's in. The concrete things it will do.
- **Non-goals** — what's explicitly out (prevents scope creep later).
- **Acceptance** — how you'll both know it's done; observable behaviour.
- **Constraints** — anything it must respect (an existing convention, a data
  shape, a deadline, a thing it must not break).

Apply COACHING_STANDARD (questions over statements; hypotheses over
conclusions) and TONE_STANDARD (plain English, no banned vocabulary) through
the conversation. Then write a `SPEC.md` with sections: Intent, Scope,
Non-goals, Acceptance, Constraints.

### Deep mode — dispatch the requirements specialist (do NOT reimplement)

Deep mode is a full Software Requirements Document with use cases and
sequence / state / process diagrams in Mermaid. **The requirements specialist
owns this** — do not re-implement SRD facilitation here.

1. **Hand off in plain English** (FE-09 — name the outcome, not the
   machinery): *"This is a new piece of the product, so it's worth specifying
   properly. I'll bring in the requirements specialist — they'll walk you
   through it one question at a time and draw out the flows. Ready?"*

2. **Dispatch the agent.** Recommend the founder run the specialist directly:

   ```
   claude --agent requirements-analyst
   ```

   Pass the change's intent + the recon `CONTEXT.md`
   (`~/.sulis/changes/{change_id}/CONTEXT.md`) as the opening brief so the
   specialist starts grounded. If invoking via the Agent tool instead, use
   `subagent_type: "sulis:requirements-analyst"`.

3. **Land the output as the change's SPEC.md.** The requirements-analyst
   writes a `.specifications/{name}/` folder (SRD.md + diagrams/ + NFR.md +
   …). For a change, the founder-facing spec of record is the change's
   `SPEC.md`: write a `SPEC.md` in the change's spec area (Output below) whose
   body is — or links to — the SRD the specialist produced. Don't duplicate
   the whole SRD into SPEC.md; point to the `.specifications/{name}/` folder
   and summarise the intent + acceptance at the top so the change has one
   readable entry point.

## Output — where SPEC.md lands

Write the change's spec next to its manifest, in the change worktree, using
the established change-storage convention:

```
{worktree_path}/.changes/{primitive}-{slug}.SPEC.md
```

This sits alongside the change manifest at
`{worktree_path}/.changes/{primitive}-{slug}.yaml` (written by
`sulis-change start`) and the recon `CONTEXT.md` lives at
`~/.sulis/changes/{change_id}/CONTEXT.md`. Keeping the spec with the manifest
means it travels with the change branch — teammates who pull the branch see
it; it's reviewable in the one PR per change (per the design's hybrid-storage
model: manifest + spec committed in the repo).

For **deep** specs, the requirements-analyst's full `.specifications/{name}/`
folder is also committed (its native home); the change's `SPEC.md` is the
short readable front door that links to it.

**Record the founder-facing flag (MUST).** Every SPEC.md opens with a tiny
frontmatter block carrying the `founder_facing` value already computed in
Step 1 (the `paths_touch_founder_surface()` result), so `design` inherits the
signal instead of re-deriving it — and so the #45 visual-contract gate knows a
user-facing surface is in scope:

```yaml
---
founder_facing: true   # or false — from the Step 1 classifier
---
```

### SPEC.md shapes

**Lite** (~10 lines):

```markdown
# Spec — {intent}

**Change:** {handle} · {primitive}

## What this should do
{intent, one or two sentences}

## How we'll know it's done
{acceptance}

## What to avoid
{guardrail}
```

**Standard:**

```markdown
# Spec — {intent}

**Change:** {handle} · {primitive}

## Intent
{what this is for}

## Scope
- {in-scope item}

## Non-goals
- {explicitly out}

## Acceptance
- {observable, testable}

## Constraints
- {must respect / must not break}
```

**Deep:** a short front-door SPEC.md (Intent + Acceptance summary) that links
to the `.specifications/{name}/` folder the requirements-analyst produced.

After writing, report in plain English (Rule 1 — lead with the outcome):

> *"Wrote the spec for **{intent}** ({handle}). {one-line of what's in it}.
> Next up is the design pass — want me to start it?"* (for standard / deep)

or, after lite:

> *"Wrote a quick spec for **{intent}** ({handle}). It's small enough to go
> straight to a single task — want me to draft and run it, or do a design
> pass first?"*

## When to invoke this skill

- The founder has started a change and is ready to say what it should do.
- The founder says "let's spec this out" / "write down what we want" inside a
  change.
- A change's suggested next step (from recon) is `/sulis:specify`.

## When NOT to invoke this skill

- There is no current change (no `SULIS_CHANGE_ID`) — start one first with
  `/sulis:change start`.
- The founder wants the technical blueprint (components, trade-offs, ADRs) —
  that is `/sulis:draft-architecture` (design), which reads the SPEC this
  skill produces.
- The founder wants to break a finished design into a to-do list — that is
  `/sulis:plan-work`.
- The founder wants a full standalone requirements document outside a change
  (learning systems analysis, a system not yet a change) — dispatch
  `requirements-analyst` directly; this skill is the change-scoped front door.
- The founder wants to rebuild the index of existing specs — that is
  `/sulis:index-specifications`.

## Gotchas

- **The classifier decides; the agent announces; the founder can redirect.**
  It picks a depth from three signals and will sometimes pick wrong (a
  one-file change that's actually load-bearing; a `create` that's really a
  tiny stub). Announce the chosen depth and run it — do NOT wait for the
  founder to ratify it (they have no basis to judge "lite vs standard", and
  asking is permission-theatre, AAF-08). The safety net is that the founder
  can redirect *after* ("go deeper" / "keep it light") and the cost of a
  wrong default is one cheap correction, not a blocking question every time.
- **Operator vocabulary must not leak.** The signals are `primitive`,
  `file_count`, `founder_facing`; the manifest carries `change_id`, `branch`,
  `worktree_path`. None of these appear in what the founder reads. Lead with
  the readable name + handle; keep the rest for the `--raw` / technical
  version. (MUC-F1)
- **Don't pass `file_count=0` for an empty change.** At specify time a change
  often has no commits yet. Unknown is `None`, not `0` — `0` would read as
  "deliberately touches nothing" and skew the proposal toward lite. Pass
  `None` when you genuinely can't tell.
- **Deep mode is a dispatch, not a re-implementation.** The
  requirements-analyst owns SRD facilitation, diagrams, and the
  `.specifications/{name}/` folder. This skill hands off and then lands a
  short front-door SPEC.md — it does not interview the founder about use
  cases itself. Re-implementing that here would drift from the one owner.
- **Default to standard when unsure — out loud.** If the signals are
  ambiguous or the primitive is unknown, the classifier returns standard and
  says "defaulting to standard when it's not clear-cut." Surface that
  reasoning; don't present a guess as a confident call (no-hyperbole / honest
  uncertainty).
- **Lite means lite.** Don't pad a lite SPEC.md with empty Scope / Non-goals
  sections to look thorough. Three fields is the contract; a fuller spec means
  the founder should have picked standard.
- **`SULIS_CHANGE_ID` must resolve to a real change.** If
  `resolve_current_change()` returns `null`, stop and route to
  `/sulis:change start`. Do not write a SPEC.md into the current directory as
  a fallback — a spec with no change has no home. (MUC-F5)

## Vocabulary

- **Depth mode** — one of three Specify levels: lite / standard / deep. The
  amount of specifying the work warrants.
- **Lite spec** — a three-field SPEC.md (intent / acceptance / what-to-avoid)
  for small mechanical changes.
- **Standard spec** — a SPEC.md from a short facilitated conversation
  (intent / scope / non-goals / acceptance / constraints); the default.
- **Deep spec** — a full SRD (use cases + Mermaid diagrams) produced by the
  requirements-analyst, fronted by a short change SPEC.md.
- **Depth classifier** — the deterministic helper
  (`_specify_classifier.py`) that proposes a depth from file count +
  primitive + founder-facing flag; defaults to standard on uncertainty.
- **Founder-facing flag** — a signal: does the change touch a user-visible
  surface (UI, page, route, template, email)?
- **Primitive** — the change's kind (one of the 22 in
  `../../references/change-primitives.md`); a classifier signal.

## Stamp the workflow stage (on completion)

When the spec is done and you're inside a change (the `SULIS_CHANGE_ID` env
var is set), record that the change has reached the **specify** stage so
`/sulis:dashboard` reflects it. Use the `$SCRIPTS_DIR` you resolved earlier:

```bash
"$SCRIPTS_DIR/sulis-change" stage specify
```

Branch-independent, best-effort; it never blocks the stage from completing.
If `SULIS_CHANGE_ID` is unset (work outside a change), skip it. Don't narrate
this to the founder; the dashboard simply stays current (FE-09).

## See also

- `../../scripts/_specify_classifier.py` — the depth classifier
  (`classify_depth`, `paths_touch_founder_surface`, `proposal_sentence`).
- `../../scripts/sulis-change` — `stage` stamps the workflow position read by
  `/sulis:dashboard`.
- `../../scripts/_wpxlib.py` — `resolve_current_change()` (SULIS_CHANGE_ID →
  manifest).
- `../change/SKILL.md` — `/sulis:change start` opens the workspace this skill
  runs inside.
- `../draft-architecture/SKILL.md` — the design stage that reads this SPEC.
- `../index-specifications/SKILL.md` — indexes deep specs'
  `.specifications/{name}/` folders.
- `../../agents/requirements-analyst.md` — the specialist deep mode dispatches.
- `../../references/founder-facing-conventions.md` — Rules 1-6.
- `../../references/change-primitives.md` — the 22-primitive vocabulary.
- `../../docs/change-as-primitive-design.md` — the design this skill realises
  (Phase 6b; § "Depth modes for Specify").
