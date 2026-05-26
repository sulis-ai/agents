---
name: design
description: >
  Use when a piece of work is specified and the founder is ready to turn the
  "what" into a "how" — Stage 2 (Design), the greenfield path. Drafts the
  technical blueprint (the design document + the decisions behind it) from
  the change's spec, then breaks it into a to-do list of independent tasks.
  For a small change it offers to skip straight to a single task instead.
  Usage: /sulis:design (run inside a change, after /sulis:specify).
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
    skill: ../../scripts/_wpxlib.py
    notes: resolve_current_change() reads SULIS_CHANGE_ID → change manifest
  - relationship: related_to
    skill: ../draft-architecture/SKILL.md
    notes: the technical-blueprint pass design routes to (TDD + ADRs)
  - relationship: related_to
    skill: ../plan-work/SKILL.md
    notes: decomposes the blueprint into independent Work Packages
  - relationship: related_to
    skill: ../specify/SKILL.md
    notes: design reads the SPEC.md specify produces; design is optional after a lite spec
  - relationship: related_to
    skill: ../audit/SKILL.md
    notes: audit is the brownfield variant of Stage 2 (existing-code changes)
  - relationship: related_to
    skill: ../run-all/SKILL.md
    notes: run-all executes the Work Packages design produces
  - relationship: optional_input
    skill: ../../references/founder-facing-conventions.md
    notes: Audience=founder-facing; Rules 1-6 apply (echo-before-act, dual-register)
---

# /sulis:design — turn the "what" into a "how"

## Conclusion (lead with the answer)

`/sulis:design` is Stage 2 for new work (the greenfield path). It reads the
spec for the piece of work you're in and produces two things:

| Step | What you get | What it leans on |
|---|---|---|
| **Blueprint** | A technical design document + the key decisions behind it | the engineering architect (`/sulis:draft-architecture`) |
| **To-do list** | The work broken into independent tasks that can ship one at a time | `/sulis:plan-work` |

This skill is an **orchestrator** — it routes to the engineering architect's
existing passes and reads back their output. It does not re-do the design
work; it runs it, then tells the founder what was decided and what the to-do
list looks like in their own words.

**Design is optional for a small change.** If the spec is a quick (lite) one,
the work is usually one obvious task — so the skill offers to skip the full
design pass and go straight to drafting that single task. The founder
decides.

Founder-mode is the default: plain English, lead with the outcome. You can
ask for the raw output any time (*"show me the technical version"* /
`--raw`) and get the design document and the Work Package files as data —
same substance, different shape (Founder-Facing Conventions Rule 6).

## Resolving the change + the tool path (MUST — first action)

This skill runs **inside a change** (a workspace opened by
`/sulis:change start`, already specified). It reads the change's identity to
find the spec.

1. **Resolve the script directory ONCE** (cache when installed downstream,
   marketplace repo in dev):

   ```bash
   SCRIPTS_DIR=$(
     find ~/.claude/plugins/cache \
       -name _wpxlib.py -type f \
       -path '*/sulis/*/scripts/*' \
       2>/dev/null \
     | sort -r | head -1 | xargs -I{} dirname {} 2>/dev/null
   )
   if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/_wpxlib.py" ]; then
     SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
   fi
   if [ -z "$SCRIPTS_DIR" ]; then
     echo "ERROR: cannot find the sulis tools. Run: claude plugin install sulis@sulis-ai-agents" >&2
     exit 1
   fi
   echo "SCRIPTS_DIR=$SCRIPTS_DIR"
   ```

   Substitute the literal path at each `$SCRIPTS_DIR` below — environment
   variables do NOT persist between Bash tool calls in Claude Code.

2. **Resolve the current change** via `resolve_current_change()`:

   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '$SCRIPTS_DIR')
   from _wpxlib import resolve_current_change
   import json
   c = resolve_current_change()
   print(json.dumps(c) if c else 'null')
   "
   ```

   - **A change** — capture `change_id`, `handle`, `slug`, `primitive`,
     `intent`, `branch`, `worktree_path`. Proceed.
   - **`null`** — no current change. Say so and route to `/sulis:change
     start`; do not guess.

## Step 1 — read the spec (MUST — design needs a "what")

Design turns a "what" into a "how", so it needs the "what". Read the change's
spec:

```
{worktree_path}/.changes/{primitive}-{slug}.SPEC.md
```

(That's where `/sulis:specify` lands it — alongside the change manifest.)

- **No SPEC.md found** → do NOT invent one and do NOT design against a guess.
  Stop and route to specify (MUC-F: design without a spec):

  > *"There's nothing written down yet about what **{intent}** should do, so
  > there's nothing to design from. Let's capture that first — run
  > `/sulis:specify` and I'll pick up the design once we have it."*

- **SPEC.md found** → read it. Note whether it's a **lite** spec (the
  three-field shape: What this should do / How we'll know / What to avoid) or
  a fuller standard / deep spec. That distinction drives Step 2.

## Step 2 — is this small enough to skip design? (the lite shortcut)

Per the design, decomposition is usually obvious for a small change — it's
one task. Detect a lite spec and offer the shortcut **before** running the
full design pass:

A spec counts as lite if it has the three-field lite shape (no Scope /
Non-goals / Constraints sections), or the change's primitive + intent point
at a single contained change (a typo, a one-file fix, a small mechanical
change).

If lite, offer the founder the choice (surface it — it changes how the next
few minutes go, a real user-facing consequence):

> *"This is small enough that a full design pass would be overkill — I'd go
> straight to a single task and run it. Want me to do that, or would you
> rather a proper design pass first?"*

- **Founder takes the shortcut** → skip to "Lite shortcut" below.
- **Founder wants the full pass, or the spec isn't lite** → Step 3.

The shortcut is an offer, never a silent skip. A lite spec for a change
that's actually load-bearing should still get a design pass if the founder
wants one — the offer is the safety net.

## Step 3 — draft the blueprint (route to the engineering architect)

The technical blueprint — the design document plus one decision record per
non-trivial choice — is the engineering architect's pass
(`/sulis:draft-architecture`). Do NOT re-implement it here.

Hand off in plain English (FE-09 — name the outcome, not the machinery):
*"Now I'll work out how to build this — the shape of it, the key decisions,
and the trade-offs — and write it down so we both know the plan before any
code gets written."*

Then route to the architect — recommend the founder run
`/sulis:draft-architecture` against the change's spec, or dispatch the
specialist (Agent tool, `subagent_type: "sulis:engineering-architect"`) with
the SPEC.md + the recon `CONTEXT.md`
(`~/.sulis/changes/{change_id}/CONTEXT.md`) as the opening brief. It produces
the design document + decision records in the change's `.architecture/` area.

Read back the result and tell the founder the shape of the decision in their
words — not the document verbatim. Lead with the one or two choices that
actually shape the work.

## Step 4 — break it into a to-do list (route to plan-work)

A blueprint isn't yet a thing you can ship one piece at a time. `/sulis:plan-work`
turns the design into independent Work Packages — one task per file, each
with its own context, contract, and definition of done, ordered so the ready
ones can ship in parallel. Do NOT re-implement decomposition here.

Route to it (recommend `/sulis:plan-work`, or dispatch the architect with the
decomposition pass). Then report the to-do list in founder English: how many
tasks, what each one is for in a phrase, and which can start now.

### Lite shortcut — straight to a single task

When the founder takes the shortcut, skip Steps 3–4 and draft a single Work
Package directly from the lite spec (intent → contract; acceptance →
definition of done; what-to-avoid → guardrail), then offer to run it. Keep it
to one task — if the work splits into more than one, that's the signal a
design pass was warranted after all; say so and offer it.

## Step 5 — report (Rule 1 — lead with the outcome)

> *"Worked out how to build **{intent}** (`CH-01HQ8X`). The plan: {one-line
> of the key decision}. I've broken it into {N} tasks that can ship one at a
> time — {first one} is ready to start now. Want me to kick it off?"*

or, after the lite shortcut:

> *"That's small enough for one task — I've drafted it from your spec. Want
> me to run it?"*

The next stage after design is execution (`/sulis:run-all` ships the tasks).

## When to invoke this skill

- A change is specified and the founder is ready to plan how to build it.
- The founder says "how should we build this?" / "design this" inside a
  change with a spec.
- A change's suggested next step (after specify) is the design pass.

## When NOT to invoke this skill

- The change has no spec yet — that's `/sulis:specify` first (design reads
  the spec).
- The change is against existing code that needs auditing before design (a
  refactor, a hardening pass, a fix in unfamiliar code) — that's the
  brownfield variant, `/sulis:audit`.
- There is no current change (no `SULIS_CHANGE_ID`) — start one with
  `/sulis:change start`.
- The founder wants to run the tasks, not plan them — that's `/sulis:run-all`
  / `/sulis:run-wp`.
- The founder wants the technical blueprint directly outside the change
  flow — that's `/sulis:draft-architecture` run on its own.

## Gotchas

- **Design without a spec is a guess.** If there's no SPEC.md, stop and route
  to `/sulis:specify` — never design against an invented "what". The spec is
  the input; design is the transform. (MUC-F: design dispatched without a
  spec — the brief's named case)
- **The lite shortcut is an offer, never a silent skip.** Detect a lite spec
  and *propose* going straight to a single task — but the founder decides. A
  load-bearing one-file change can still warrant a design pass.
- **Don't re-implement the architect's passes.** `draft-architecture` owns
  the blueprint + decision records; `plan-work` owns decomposition. This
  skill routes to them and reads their output. Re-doing their work here
  drifts from the one owner.
- **Greenfield vs brownfield.** Design is the *new-work* path (build
  something that isn't there). If the work is changing code that already
  exists and needs understanding first, that's `/sulis:audit` — don't force a
  greenfield design onto a brownfield change.
- **Operator vocabulary must not leak.** ADR, TDD, WP-NNN, `worktree_path`,
  the design-doc filenames — none are the founder's words. Lead with the
  readable name + handle and the plain-English decision; keep the artefacts
  for the `--raw` / technical version. (MUC-F1)
- **Don't narrate the dispatch.** The founder doesn't need to hear which
  specialist you'll spawn or what `subagent_type` you'll pass. Surface what's
  now decided and what they should do next (FE-09).

## Vocabulary

- **Design (greenfield)** — Stage 2 for new work: turn the spec's "what" into
  a "how" (the blueprint) and a to-do list of tasks.
- **Blueprint** — the technical design document plus the key decisions
  behind it, produced by the engineering architect.
- **To-do list / Work Packages** — the independent tasks the work breaks
  into, one shippable at a time (from `plan-work`).
- **Lite shortcut** — for a small (lite-spec) change, going straight to a
  single task instead of a full design pass.
- **Greenfield vs brownfield** — building something new (design) vs changing
  code that already exists and needs auditing first (`/sulis:audit`).

## See also

- `../../scripts/_wpxlib.py` — `resolve_current_change()` (SULIS_CHANGE_ID →
  manifest).
- `../draft-architecture/SKILL.md` — the technical-blueprint pass (TDD +
  decision records) design routes to.
- `../plan-work/SKILL.md` — the decomposition pass (blueprint → tasks).
- `../specify/SKILL.md` — the prior stage; produces the SPEC.md design reads.
- `../audit/SKILL.md` — the brownfield variant of Stage 2.
- `../run-all/SKILL.md` — the next stage; runs the tasks design produces.
- `../../agents/engineering-architect.md` — the specialist this skill routes
  to.
- `../../references/founder-facing-conventions.md` — Rules 1-6.
- `../../docs/change-as-primitive-design.md` — the design this skill realises
  (Stage 2 Design; § "Design is optional for lite-specify changes").
