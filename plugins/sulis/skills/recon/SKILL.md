---
name: recon
description: "Finds out what's already in the repo at the start of a change."
user_invocable: true
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD]
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
  - relationship: depends_on
    skill: ../../scripts/_change_context.py
    notes: write_change_context() writes/refreshes the change's CONTEXT.md
  - relationship: depends_on
    skill: ../../scripts/wpx-arrival-check
    notes: Repository-Contract arrival check (RC-01..RC-12); read-only
  - relationship: related_to
    skill: ../discover-context/SKILL.md
    notes: context cartography — the deeper map of existing docs/decisions
  - relationship: related_to
    skill: ../analyse-codebase/SKILL.md
    notes: structural / app-topology analysis of existing code
  - relationship: related_to
    skill: ../specify/SKILL.md
    notes: recon is Stage 0; specify is the next stage and reads CONTEXT.md
  - relationship: optional_input
    skill: ../../references/founder-facing-conventions.md
    notes: Audience=founder-facing; Rules 1-6 apply (echo-before-act, dual-register)
---

# /sulis:recon — find out what's already here

## Conclusion (lead with the answer)

`/sulis:recon` is the first look around before any work starts. It runs
three quick passes and folds them into one plain-English summary of
**what's already here**, written next to the change so every later stage
reads it first.

| Pass | What it answers | What it leans on |
|---|---|---|
| **Arrival check** | Is the repo set up the way the tools expect? | the Repository-Contract arrival check (read-only) |
| **Context map** | What docs, decisions, and conventions already exist? | the context cartographer (`/sulis:discover-context`) |
| **Code shape** | How is the existing code put together? | structural analysis (`/sulis:analyse-codebase`) |

This skill is an **orchestrator** — it routes to existing tools and
specialists and writes the change's `CONTEXT.md`. It does not re-implement
the map or the structural analysis; it runs them, reads the results, and
tells the founder what matters in their own words.

Recon runs automatically when a change is first opened (`/sulis:change
start`). Running `/sulis:recon` by hand **refreshes** that picture — useful
when the repo has moved on, or when you opened the workspace yourself.

Founder-mode is the default: plain English, lead with the outcome. You can
ask for the raw output any time (*"show me the technical version"* /
`--raw`) and get the arrival-check JSON, the context index, and the
structural report as data — same substance, different shape
(Founder-Facing Conventions Rule 6).

## Resolving the change + the tool path (MUST — first action)

This skill runs **inside a change** (a workspace opened by
`/sulis:change start`). It reads the change's identity to know where to
write `CONTEXT.md`.

1. **Resolve the script directory ONCE** (the sulis tools live in the
   plugin cache when installed downstream, or in the marketplace repo in
   dev):

   ```bash
   SCRIPTS_DIR=$(
     find ~/.claude/plugins/cache \
       -name _change_context.py -type f \
       -path '*/sulis/*/scripts/*' \
       2>/dev/null \
     | sort -r | head -1 | xargs -I{} dirname {} 2>/dev/null
   )
   if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/_change_context.py" ]; then
     SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
   fi
   if [ -z "$SCRIPTS_DIR" ]; then
     echo "ERROR: cannot find the sulis tools. Run: claude plugin install sulis@sulis-ai-agents" >&2
     exit 1
   fi
   echo "SCRIPTS_DIR=$SCRIPTS_DIR"
   ```

   Capture the printed path and substitute the literal at each `$SCRIPTS_DIR`
   below — environment variables do NOT persist between Bash tool calls in
   Claude Code.

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
     `primitive`, `intent`, `branch`, `worktree_path`. You're inside a
     change; proceed.
   - **If this prints `null`** — there is no current change. Do NOT guess.
     Say so plainly and point the way:

     > *"I can't tell which piece of work this is for — `/sulis:recon` runs
     > inside a change. Start one with `/sulis:change start "what you're
     > doing"` (recon runs automatically when you do), and I'll pick it up
     > from there."*

## Step 1 — arrival check (read-only)

Confirm the repo is set up the way the downstream tools expect. This is the
Repository-Contract arrival check — read-only, never changes anything. Run
it inside the change worktree against the repo's GitHub slug:

```bash
"$SCRIPTS_DIR/wpx-arrival-check" --repo {owner}/{name} --repo-root {worktree_path}
```

It emits `{"ok": bool, "errors": [...], "warnings": [...]}` on stdout.

- **`ok: true`** → the repo is set up correctly; carry on quietly. Don't
  narrate a clean pass — it's the expected state.
- **`ok: false`** → there's a setup gap that will bite later stages.
  Translate each error to plain English and surface it (Rule 5 — name what's
  wrong + the next step). Don't drown the founder in RC-codes; lead with the
  consequence (*"the shared `dev` line isn't protected the way the safety
  checks expect — that needs fixing before this work ships"*).
- **Tooling error** (exit 1, e.g. `gh` not authenticated / no network) → say
  the check couldn't run and why; this does not block recon — note it and
  move on.

The arrival check is **defence in depth**: if it's empty (no repo slug
resolvable, e.g. a brand-new local repo with no remote), skip it gracefully
rather than failing recon.

## Step 2 — context map (route to the cartographer)

Map what already exists — architecture docs, prior decisions, conventions,
earlier specs. **The context cartographer owns this** (`/sulis:discover-context`).
Do not re-implement the scan here.

- **First time on this repo** (no `.context/{project}/INDEX.md` yet) →
  recommend the founder run `/sulis:discover-context`, or dispatch the
  cartographer directly (Agent tool, `subagent_type:
  "sulis:context-cartographer"`) with the change's intent as the brief. It
  scans, groups findings by purpose, and asks the founder to classify each
  source. The product is a context index the later stages read first.
- **Index already exists** → don't re-run the full discovery conversation.
  Read the existing `.context/{project}/INDEX.md`, summarise what's
  authoritative in one or two lines, and move on. (`/sulis:refresh-context`
  is the lighter re-validation if the founder wants the index re-checked
  against a moved codebase — recon does not force it.)

Hand off in plain English (FE-09 — name the outcome, not the machinery):
*"Before we touch anything, I'll map what's already here — the docs,
decisions, and conventions this repo already follows — so we build with the
grain, not against it."*

## Step 3 — code shape (route to structural analysis)

Look at how the existing code is put together — what's there, how big, where
the hotspots are, the deployment shape. **`/sulis:analyse-codebase` owns
this** — a deterministic structural pass that produces a navigable report.
Do not re-implement it.

- Recommend `/sulis:analyse-codebase` (or dispatch it) scoped at the change
  worktree. It's read-only and produces an HTML report + structured JSON.
- This is **optional for a small, contained change** — a one-file typo fix
  doesn't need a full structural map. Use judgement from the change's
  primitive + intent: skip the structural pass for trivial mechanical
  changes; run it when the work touches code the founder didn't write or
  doesn't yet understand.

## Step 4 — write / refresh CONTEXT.md (MUST)

Fold the three passes into the change's `CONTEXT.md` via
`write_change_context()`. This is the one artefact recon owns; it's what
later stages read first.

```bash
python3 -c "
import sys; sys.path.insert(0, '$SCRIPTS_DIR')
from _change_context import write_change_context
from pathlib import Path
import json
p = write_change_context(
    change_id='01HQ8XQM8G5KZGZQXPZD8H6PJ7',
    metadata={'handle': 'CH-01HQ8X', 'slug': 'fix-login-bug',
              'primitive': 'fix', 'intent': 'fix the login bug',
              'branch': 'change/fix-login-bug', 'base_branch': 'dev'},
    repo_root=Path('/abs/path/to/worktree'),
)
print(json.dumps({'context_path': str(p) if p else None}))
"
```

It writes `~/.sulis/changes/{change_id}/CONTEXT.md` (change identity + git
state at this point + the suggested next step) and returns the path.

**Then write the recon-done marker (MUST — #27).** `write_change_context()`
is called by BOTH the pre-spawn stub (`sulis-change start`) and this skill,
which produces an identical CONTEXT.md format. The stage-inference rules in
the Sulis agent body distinguish "Stage 0 done" from "spawn stub only" by
checking for a sentinel file the pre-spawn writer never touches:

```bash
# Write the recon-done marker so the spawned Sulis can tell Stage 0 has
# been done (the pre-spawn CONTEXT.md alone doesn't distinguish).
# Path mirrors .SPEC.md naming: .changes/{primitive}-{slug}.RECON.md
# Travels with the change branch (#42 records policy).
RECON_MARKER="{worktree}/.changes/{primitive}-{slug}.RECON.md"
cat > "$RECON_MARKER" <<EOF
# Recon — {primitive}-{slug}

Stage 0 completed at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

This marker file's existence indicates that `/sulis:recon` has been run
for this change. The spawned Sulis's stage-inference uses this file to
distinguish "post-recon" from "pre-spawn stub only" (the change's
`CONTEXT.md` is overwritten by both events with the same shape, so file
content can't distinguish — this sentinel can).

See \`plugins/sulis/agents/sulis.md\` "Change context" section for the
stage-inference rules.
EOF
```

Substitute `{worktree}` (the change worktree path from metadata), `{primitive}`,
and `{slug}` from the change manifest. The file is intentionally minimal —
its existence is the load-bearing signal; the body is documentation for a
future reader who finds it.

**Recon writing is best-effort by design.** If `write_change_context()`
returns `None` (permission denied, read-only filesystem, disk full), the
helper has already logged the reason and recon must NOT crash. Same for the
marker write — log + continue. Tell the founder plainly that the summary
couldn't be saved and why, then carry on — a failed recon-write never blocks
the change (this mirrors the helper's own contract).

## Step 5 — report what's already here (Rule 1 — lead with the outcome)

One short, scannable summary in founder English. Lead with the headline
("here's the lay of the land"), then the few things that actually matter for
this change, then the next step:

> *"Had a look around before we start on **fix the login bug** (`CH-01HQ8X`).
> The repo's set up correctly. There's an existing auth module with its own
> conventions — I've noted them so we follow them. Nothing here blocks us.
> Next up is writing down what this work should do — want me to start that?"*

If recon turned up something that changes the shape of the work (a
convention to follow, a setup gap to fix first, a part of the code that's
fragile), say so — that's the whole point of looking first. Don't bury a
real finding under a clean-bill-of-health summary.

## When to invoke this skill

- A change was just opened and the founder wants the lay of the land before
  specifying.
- The founder opened a workspace by hand and wants recon run.
- The repo has moved on and the founder wants the "what's already here"
  picture refreshed.

## When NOT to invoke this skill

- There is no current change (no `SULIS_CHANGE_ID`) — start one first with
  `/sulis:change start` (recon runs automatically there).
- The founder wants the full, classified context index outside a change
  (onboarding a whole repo, not a single change) — that is
  `/sulis:discover-context` run directly.
- The founder wants the deep structural report on its own — that is
  `/sulis:analyse-codebase`.
- The founder wants to re-validate an existing context index against a
  changed codebase — that is `/sulis:refresh-context`.
- The founder is ready to say what the work should do — that is the next
  stage, `/sulis:specify`.

## Gotchas

- **Recon on an empty or brand-new repo must not fail loudly.** A fresh repo
  has no remote slug (arrival check skips), no context docs (cartography
  finds nothing), and little code (structural pass is thin). That's a valid
  state, not an error. Report "not much here yet — this looks like new
  ground" rather than three failed sub-passes. (MUC-F: empty-repo recon)
- **A clean pass is not news.** Don't narrate the arrival check passing or
  every file the structural pass walked. Founders care about what's
  *different* — a convention to follow, a gap to fix, fragile code. Surface
  findings, not the mechanism (FE-09).
- **Don't re-implement the map or the structural analysis.** The cartographer
  owns context discovery; `analyse-codebase` owns the structural pass. Recon
  routes to them and reads their output. Re-doing their work here drifts from
  the one owner and bloats this skill.
- **Operator vocabulary must not leak.** RC-codes, `worktree_path`,
  `base_sha`, the JSON envelopes — none of these are the founder's words.
  Lead with the readable name + handle; keep the codes for the `--raw` /
  technical version. (MUC-F1)
- **CONTEXT.md write is best-effort — never crash on a failed write.** If
  the home directory isn't writable, log it (the helper does) and continue.
  The change still proceeds; recon just couldn't persist the summary.
- **Skip the heavy passes for trivial changes.** A typo fix doesn't need a
  full structural map. Match recon depth to the change's primitive + intent;
  don't run a five-minute analysis to fix a one-line change.

## Vocabulary

- **Recon** — Stage 0 of a change: the first look around to find out what's
  already here before any work starts.
- **Arrival check** — the read-only Repository-Contract verification
  (`wpx-arrival-check`) that confirms the repo is set up the way the tools
  expect.
- **Context map** — the index of existing docs, decisions, and conventions
  the context cartographer produces.
- **Code shape** — the structural / app-topology picture
  (`analyse-codebase`): what's there, how big, where the hotspots are.
- **CONTEXT.md** — the short "what's already here" summary recon writes; the
  first thing every later stage reads.

## Stamp the workflow stage (on completion)

When the recon work is done and you're inside a change (the `SULIS_CHANGE_ID`
env var is set — every change-bound session has it), record that the change
has reached the **recon** stage so `/sulis:dashboard` reflects it. Use the
`$SCRIPTS_DIR` you resolved earlier:

```bash
"$SCRIPTS_DIR/sulis-change" stage recon
```

Branch-independent, best-effort; it never blocks the stage from completing.
If `SULIS_CHANGE_ID` is unset (work outside a change), skip it — there's
nothing to stamp. Don't narrate this to the founder; the dashboard simply
stays current (FE-09).

## See also

- `../../scripts/_wpxlib.py` — `resolve_current_change()` (SULIS_CHANGE_ID →
  manifest).
- `../../scripts/sulis-change` — `stage` stamps the workflow position read by
  `/sulis:dashboard`.
- `../../scripts/_change_context.py` — `write_change_context()` (writes the
  change's CONTEXT.md; best-effort).
- `../../scripts/wpx-arrival-check` — the read-only Repository-Contract
  arrival check.
- `../discover-context/SKILL.md` — context cartography (the deeper map).
- `../analyse-codebase/SKILL.md` — the structural / app-topology pass.
- `../specify/SKILL.md` — the next stage; reads the CONTEXT.md recon writes.
- `../../agents/context-cartographer.md` — the specialist Step 2 routes to.
- `../../references/founder-facing-conventions.md` — Rules 1-6.
- `../../docs/change-as-primitive-design.md` — the design this skill realises
  (Stage 0 Recon).
