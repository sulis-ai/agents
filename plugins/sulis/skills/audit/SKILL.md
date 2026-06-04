---
name: audit
description: "Reviews existing code before you change it and drafts the fixes to close the gaps."
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
    skill: ../codebase-audit/SKILL.md
    notes: the brownfield gap-analysis pass audit routes to (audit report + hardening deltas)
  - relationship: related_to
    skill: ../analyse-codebase/SKILL.md
    notes: the structural baseline audit pairs with the gap analysis
  - relationship: related_to
    skill: ../design/SKILL.md
    notes: design is the greenfield variant of Stage 2 (new work)
  - relationship: related_to
    skill: ../plan-work/SKILL.md
    notes: turns the hardening deltas into a to-do list of tasks
  - relationship: optional_input
    skill: ../../references/founder-facing-conventions.md
    notes: Audience=founder-facing; Rules 1-6 apply (echo-before-act, dual-register)
  - relationship: optional_input
    skill: ../../references/change-primitives.md
    notes: the change's primitive (refactor / harden / fix / replace) flags the brownfield path
---

# /sulis:audit — understand existing code before you change it

## Required Reading (load before auditing)

`audit` is the brownfield twin of `design` — when it produces hardening
deltas / WP candidates, the same per-kind + contract-first discipline
applies. Load:

- `../../references/standards/WP_BACKEND_STANDARD.md` /
  `../../references/standards/WP_FRONTEND_STANDARD.md` — per-kind doctrine
  the proposed fixes must target.
- `../../references/standards/CONTRACT_FIRST_STANDARD.md` — when a finding
  touches a producer/consumer seam, the fix may need a contract artifact
  before the per-kind WPs.
- `../../references/standards/UX_VISUAL_DESIGN_STANDARD.md` — when a
  finding is on a user-facing surface, the fix conforms to the visual
  contract.
- `../../references/standards/WORK_PACKAGE_STANDARD.md` — `kind:` enum +
  WP-08.5 cross-kind decomposition.

## Conclusion (lead with the answer)

`/sulis:audit` is Stage 2 for work against code that already exists (the
brownfield path) — refactors, hardening, fixes, replacements. Before
changing code, it works out how that code is built and where the gaps are,
then drafts the fixes that close them.

| Step | What you get | What it leans on |
|---|---|---|
| **Structural baseline** | A read-only map of how the existing code is put together | `/sulis:analyse-codebase` |
| **Gap audit** | Where the code falls short, and a draft set of fixes | the engineering architect (`/sulis:codebase-audit`) |

This skill is an **orchestrator** — it routes to the engineering architect's
existing brownfield passes and reads their output. It does not re-do the
audit; it runs it, then tells the founder what was found and what the
proposed fixes are in their own words.

`/sulis:audit` is the **brownfield twin of `/sulis:design`**. Use design when
you're building something new; use audit when you're changing code that's
already there and needs understanding first.

Founder-mode is the default: plain English, lead with the outcome. You can
ask for the raw output any time (*"show me the technical version"* /
`--raw`) and get the audit report and the structural analysis as data — same
substance, different shape (Founder-Facing Conventions Rule 6).

## Resolving the change + the tool path (MUST — first action)

This skill runs **inside a change** (a workspace opened by
`/sulis:change start`). It reads the change's identity to know what's being
changed and where the code lives.

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

## Step 0 — confirm this is a brownfield change

`/sulis:audit` is for changes against existing code. The change's primitive
is the signal: `refactor`, `harden`, `fix`, `replace`, `decompose`,
`migrate`, `delete`, `optimise` — anything that operates on code that's
already there (see `../../references/change-primitives.md`).

- **Brownfield primitive** → proceed.
- **Greenfield primitive** (`feat` / `create` / `generate` — building
  something new) → this is the wrong stage. Route to `/sulis:design`:

  > *"This is new work rather than a change to code that's already there, so
  > the design pass fits better than an audit. Run `/sulis:design` and I'll
  > plan how to build it."*

  (If the founder insists the new work still depends on understanding
  existing code, run the structural baseline in Step 1 and hand the rest to
  design — don't force a full gap audit onto a greenfield build.)

## Step 1 — structural baseline (route to analyse-codebase)

Start with a read-only map of how the existing code is put together — what's
there, how big, where the hotspots are. **`/sulis:analyse-codebase` owns
this** — don't re-implement it.

Route to it (recommend `/sulis:analyse-codebase`, or dispatch it) scoped at
the change worktree, focused on the part of the code this change touches. It
produces a navigable report + structured JSON; the gap audit reads it as
its baseline. (Per `analyse-codebase`'s own contract, this structural pass is
required reading before a brownfield audit.)

## Step 2 — gap audit + draft fixes (route to the engineering architect)

The gap analysis — what the existing code is missing against the
architecture pillars, and the draft fixes that close each gap — is the
engineering architect's brownfield pass (`/sulis:codebase-audit`). Do NOT
re-implement it here.

Hand off in plain English (FE-09 — name the outcome, not the machinery):
*"Before we change this, I'll look at how it's built today and where it falls
short — then draft the specific fixes that close those gaps, so we go in with
a plan rather than poking at it."*

Then route to the architect — recommend `/sulis:codebase-audit`, or dispatch
the specialist (Agent tool, `subagent_type: "sulis:engineering-architect"`)
with the change's intent + the structural baseline from Step 1 + the recon
`CONTEXT.md` (`~/.sulis/changes/{change_id}/CONTEXT.md`) as the brief. It
produces an audit report + a draft set of **hardening deltas** (one proposed
fix per gap) in the change's `.architecture/` area.

Read back the result and tell the founder the shape of it in their words —
the few gaps that actually matter for this change, and what closing them
involves. Don't dump the full report verbatim.

### Step 2.5 — Walk the journey (MUST for any user-facing / behavioural change)

The brownfield twin of the design-stage journey-walk (draft-architecture step
8.5): for a change that touches a user round-trip, the gap audit must **walk
each verification `Scenario`'s journey hop-by-hop against the existing code** —
outside-in, the user's first action → every hop → the observable result — and
for **every hop** confirm the handling component **exists** (cite file +
function) or record it as a **GAP → fix**. This is exactly the "the consumption
half of the journey was never built" failure (four green-but-broken login
attempts) caught by walking the *whole* round-trip rather than auditing pieces.

Pull the journey's **complete** scenario set so all are checked even when only
some are in scope (`find_scenarios_for_journey` /
`find_passing_testresults_for_scenario` — `plugins/sulis/scripts/_brain_query.py`):
classify each as **already-green** / **GAP → fix** / **out-of-scope (recorded)**.
A bare GAP (a journey hop with no existing component and no drafted fix) blocks
the audit from being "done" — turn it into a hardening delta or a recorded
out-of-scope decision. (Pure non-user-facing change: exempt — log
`journey-walk: exempt — <reason>`.)

## Step 3 — offer the to-do list (route to plan-work)

The hardening deltas are the proposed fixes; they become the change's to-do
list the same way a greenfield design does. Offer to turn them into
independent tasks via `/sulis:plan-work` (one task per fix, ordered so the
ready ones can ship in parallel). Do NOT re-implement decomposition here.

This is an offer, not automatic — a small audit might surface a single fix
that goes straight to one task; a larger one warrants the full to-do list.
The founder decides.

## Step 4 — report (Rule 1 — lead with the outcome)

> *"Looked at how **{intent}** (`CH-01HQ8X`) is built today. The main thing:
> {one-line of the key gap}. I've drafted {N} fixes that close the gaps —
> want me to turn those into a to-do list and start on the first one?"*

If the audit found the code is in better shape than expected (few or no
gaps), say so plainly — that's a real finding, not a non-result. The next
stage after audit is execution (`/sulis:run-all` ships the fixes).

## When to invoke this skill

- A change is against existing code (a refactor, a fix in unfamiliar code, a
  hardening pass, a replacement) and the founder wants to understand it
  before changing it.
- The founder says "audit this" / "what's wrong with this code?" / "is this
  safe to change?" inside a brownfield change.
- A change with a brownfield primitive reaches Stage 2.

## When NOT to invoke this skill

- The change is new work (building something that isn't there) — that's the
  greenfield variant, `/sulis:design`.
- There is no current change (no `SULIS_CHANGE_ID`) — start one with
  `/sulis:change start`.
- The founder wants the security / health review of finished work — that's
  Stage 4, `/sulis:review`.
- The founder wants the structural map on its own — that's
  `/sulis:analyse-codebase`.
- The founder wants the brownfield gap analysis directly outside the change
  flow — that's `/sulis:codebase-audit` run on its own.

## Gotchas

- **Audit is the brownfield path; design is greenfield.** Check the
  primitive first. Forcing a gap audit onto a `feat`/`create` (new work) wastes
  the founder's time auditing code that doesn't exist yet — route those to
  `/sulis:design`. (MUC-F: wrong-stage dispatch)
- **The structural baseline comes first.** The gap audit reads the structural
  analysis as its input; running the audit without it skips the map the
  findings rest on. Run `analyse-codebase` (Step 1) before `codebase-audit`
  (Step 2).
- **Hardening deltas are draft fixes, not applied changes.** The audit is
  read-only — it *proposes* fixes. Nothing is changed until the tasks run
  (Stage 3). Don't tell the founder the code is fixed when it's only been
  audited.
- **Don't re-implement the architect's passes.** `analyse-codebase` owns the
  structural map; `codebase-audit` owns the gap analysis + hardening deltas;
  `plan-work` owns decomposition. This skill routes to them. Re-doing their
  work here drifts from the one owner.
- **Operator vocabulary must not leak.** "MECE-3 pillars", "hardening
  deltas", "cyclomatic complexity", `worktree_path`, the report filenames —
  none are the founder's words. Lead with the readable name + handle and the
  plain-English finding; keep the artefacts for the `--raw` / technical
  version. (MUC-F1)
- **A clean audit is a real result.** If the existing code holds up, say so —
  don't manufacture gaps to look thorough. Honest uncertainty over false
  findings.

## Vocabulary

- **Audit (brownfield)** — Stage 2 for work against existing code:
  understand how it's built and where it falls short before changing it.
- **Structural baseline** — the read-only map of how the existing code is
  put together (`analyse-codebase`); the input to the gap audit.
- **Gap audit** — where the existing code falls short against the
  architecture pillars (`codebase-audit`).
- **Hardening delta** — one proposed fix that closes one gap; draft only,
  not applied until the tasks run.
- **Brownfield vs greenfield** — changing code that already exists (audit)
  vs building something new (`/sulis:design`).

## See also

- `../../scripts/_wpxlib.py` — `resolve_current_change()` (SULIS_CHANGE_ID →
  manifest).
- `../codebase-audit/SKILL.md` — the brownfield gap-analysis pass (audit
  report + hardening deltas) this skill routes to.
- `../analyse-codebase/SKILL.md` — the structural baseline pass.
- `../design/SKILL.md` — the greenfield variant of Stage 2.
- `../plan-work/SKILL.md` — turns the hardening deltas into a to-do list.
- `../run-all/SKILL.md` — the next stage; runs the fixes audit produces.
- `../../agents/engineering-architect.md` — the specialist this skill routes
  to.
- `../../references/change-primitives.md` — the 22-primitive vocabulary; the
  brownfield primitives that flag this path.
- `../../references/founder-facing-conventions.md` — Rules 1-6.
- `../../docs/change-as-primitive-design.md` — the design this skill realises
  (Stage 2 Design, brownfield variant).
