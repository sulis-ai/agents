---
name: review
description: >
  Use when the work on a change is built and the founder wants to know if
  it's safe and sound before shipping — Stage 4 (Review) of a change. Runs
  the full code-health check across all seven tiers and folds in a security
  assessment, then gives one plain-English verdict — good to ship, or here's
  what needs attention first. Read-only; never changes code. Usage:
  /sulis:review (run inside a change, after the work is built).
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
    skill: ../code-health/SKILL.md
    notes: the 7-tier health check review folds in (dispatches its own tier agents)
  - relationship: related_to
    skill: ../check-security/SKILL.md
    notes: the security / data-protection / supply-chain assessment
  - relationship: related_to
    skill: ../codebase-assess/SKILL.md
    notes: the evidence-based viability assessment (alternative security depth)
  - relationship: related_to
    skill: ../run-all/SKILL.md
    notes: review runs after the work (the Work Packages) is built
  - relationship: related_to
    skill: ../change/SKILL.md
    notes: a clean review verdict is the green light for /sulis:change ship
  - relationship: optional_input
    skill: ../../references/founder-facing-conventions.md
    notes: Audience=founder-facing; Rules 1-6 apply (echo-before-act, dual-register)
---

# /sulis:review — is it safe and sound before shipping?

## Required Reading (load as the rubric)

The review scores the diff against the per-kind + contract-first + visual
standards — they're not background context, they're the **rubric**:

- `../../references/standards/WP_BACKEND_STANDARD.md` — score backend diff
  against WPB-01..12.
- `../../references/standards/WP_FRONTEND_STANDARD.md` — score frontend
  diff against WPF-01..13 (a11y is a gate, not a nice-to-have).
- `../../references/standards/CONTRACT_FIRST_STANDARD.md` — for cross-kind
  changes, verify the contract conformance check passed (CF-07).
- `../../references/standards/UX_VISUAL_DESIGN_STANDARD.md` — for
  user-facing changes, verify the visual contract was honoured (semantic
  tokens not hex; design-time WCAG AA; agentic-UX principles for AI
  surfaces).

## Conclusion (lead with the answer)

`/sulis:review` is Stage 4: the check on built work before it ships. It folds
two read-only passes into **one verdict** — good to ship, or here's what
needs attention first.

| Pass | What it answers | What it leans on |
|---|---|---|
| **Health check** | Does it build, work, hold up, and read cleanly? (all 7 tiers) | `/sulis:code-health` |
| **Security check** | Could anything here harm users or the business? | `/sulis:check-security` (deeper: `/sulis:codebase-assess`), via the security reviewer |

This skill is an **orchestrator** — it runs the existing health check and
security assessment, then interprets and presents their results as one
founder-facing verdict. It does NOT re-implement the seven tiers or the
security tool stack; `/sulis:code-health` already dispatches its own per-tier
agents, and the security reviewer owns the security pass. Review calls them,
reads the results, and folds them together.

Both passes are **read-only** — review never changes code. Any rename or
refactor suggestions are advice, not edits.

The verdict is one of:

- **Good to ship** — no blocking findings; the work is safe and sound.
  Green light for `/sulis:change ship`.
- **Needs attention first** — there are findings that should be addressed
  before shipping. Review surfaces the few that matter most and points at
  how to act on them.

Founder-mode is the default: plain English, lead with the verdict. You can
ask for the raw output any time (*"show me the technical version"* /
`--raw`) and get the full health report and the security findings as data —
same substance, different shape (Founder-Facing Conventions Rule 6).

## Resolving the change + the tool path (MUST — first action)

This skill runs **inside a change** (a workspace opened by
`/sulis:change start`, with the work built). It reads the change's identity
to scope the review.

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

## Step 1 — the health check (route to code-health; do NOT re-implement)

Run the seven-tier health check scoped at the change worktree.
`/sulis:code-health` is the one comprehensive check — it walks all seven
tiers (does it build / could anyone be harmed / do the tests pass / does it
handle failure / can a new person read it / can we change it safely /
documentation + tech-debt + hygiene) and **dispatches its own seven per-tier
agents in parallel**. Review does NOT duplicate that tier logic — it calls
code-health, then interprets the single CHECKUP it produces.

Run it in its default (deep) mode for a founder-interactive review:

```
/sulis:code-health
```

(Deep mode dispatches the seven tier agents and aggregates one CHECKUP.md.
For a fast, token-free pass — e.g. a quick re-check after a fix — `--mode
fast` is available; review defaults to deep so the founder gets the
interpreted findings, not raw scanner output.)

Read the CHECKUP. Note which tiers are clean and which have findings, and at
what severity.

## Step 2 — the security check (route to the security reviewer)

Tier 2 of the health check (Safe) already runs the core security scan. For a
change that touches anything sensitive — auth, payments, user data, external
inputs, a deployed surface — go deeper with the dedicated security
assessment rather than relying on the tier-2 pass alone.

**The security reviewer owns this** — don't re-implement the tool stack.

- **Standard depth** → `/sulis:check-security` (the deep multi-tool
  security + data-protection + supply-chain assessment, SEC / DAT / SC
  primitives). Add `--url` if the change is deployed somewhere reviewable.
- **Production-readiness depth** → `/sulis:codebase-assess` (the
  evidence-based viability assessment with attack chains) when the founder is
  about to ship something high-stakes.

Route to it (recommend the command, or dispatch the specialist via the Agent
tool with `subagent_type: "sulis:security-reviewer"`) scoped at the change
worktree. Read back the findings.

Use judgement on depth: a typo fix or a docs change doesn't need a full
security assessment — the tier-2 pass inside code-health is enough. Reserve
the deeper pass for changes that touch a security-relevant surface. Don't run
a heavy security assessment on a trivial change.

## Step 3 — fold into one verdict (Rule 1 — lead with the verdict)

Combine the health check and the security check into **one** founder-facing
verdict. Don't hand the founder two separate reports to reconcile — that's
the whole point of this stage.

- **No blocking findings across either pass** → **Good to ship.** State it
  plainly and name the green light:

  > *"Reviewed **{intent}** (`CH-01HQ8X`). It builds, the tests pass, nothing
  > here puts users or the business at risk, and it reads cleanly. Good to
  > ship — when you're ready, `/sulis:change ship CH-01HQ8X` lands it."*

- **Findings that should be addressed first** → **Needs attention first.**
  Lead with the verdict, then the few findings that matter most — **not a
  wall of every finding**. Cap what you surface to the handful that actually
  block or matter (the overwhelm guard, MUC-F4); group the rest as a count
  the founder can drill into via the technical version. Each surfaced finding
  in plain English: what it is, why it matters, what to do:

  > *"Reviewed **{intent}** (`CH-01HQ8X`). Mostly solid, but two things to
  > sort before shipping: {finding 1 in plain English — what + why + next
  > step}; {finding 2}. There are {N} smaller notes beyond those — say the
  > word for the full list. Want me to turn the blockers into a to-do list?"*

When findings warrant follow-up work, `/sulis:address-findings` turns them
into a queue of tasks — offer it rather than leaving the founder with a list
and no path forward (Rule 5 — always name the next step).

Coaching applies here (COACHING_STANDARD): deliver findings structurally
("this code has X" / "this pattern leaves Y open"), not personally ("you
forgot X"). The founder built this; the review's job is to make it safe to
ship without triggering defensiveness.

## When to invoke this skill

- The work on a change is built and the founder wants to know if it's safe to
  ship.
- The founder says "is this good to go?" / "review this" / "check this
  before I ship it" inside a change.
- A change reaches Stage 4 (after execution, before ship).

## When NOT to invoke this skill

- There is no current change (no `SULIS_CHANGE_ID`) — start one with
  `/sulis:change start`.
- The work isn't built yet — review checks built work; run the tasks first
  (`/sulis:run-all`).
- The founder wants the health check on its own (a standalone codebase
  checkup, not a pre-ship review) — that's `/sulis:code-health` directly.
- The founder wants only the security assessment — that's
  `/sulis:check-security` / `/sulis:codebase-assess` directly.
- The founder wants to turn review findings into a work queue — that's
  `/sulis:address-findings` (review offers it; it doesn't do it).
- The founder wants to ship — that's `/sulis:change ship` (review is the
  green light before it, not the ship itself).

## Gotchas

- **One verdict, not two reports.** The point of this stage is to fold the
  health check and the security check into a single plain-English answer.
  Handing the founder two separate documents to reconcile defeats it. Lead
  with "good to ship" / "needs attention first", then the few findings that
  matter.
- **Don't overwhelm with findings.** A real review can surface dozens of
  notes. Surface the handful that block or matter most; group the rest as a
  count the founder can drill into. A 40-line wall of findings is a worse
  outcome than three clear ones plus a path forward. (MUC-F4 — the brief's
  named overwhelm case)
- **Don't re-implement the tiers or the security stack.** `code-health`
  dispatches its own seven tier agents; the security reviewer owns the
  security pass. Review calls them and interprets — re-doing their work here
  drifts from the one owner and double-runs the scanners.
- **Match depth to the change.** A typo fix doesn't need a full security
  assessment; the tier-2 pass inside code-health covers it. Reserve the deep
  security pass for changes touching a security-relevant surface.
- **Review never changes code.** Both passes are read-only; findings are
  advice, not edits. Don't "fix it while you're in there" — that's separate
  work (`/sulis:address-findings` → tasks). Saying the code is fixed when
  it's only been reviewed is a false claim.
- **Deliver findings structurally, not personally.** The founder built this.
  "This pattern leaves the login open to X" lands; "you forgot to validate
  X" triggers defensiveness. (COACHING_STANDARD)
- **Operator vocabulary must not leak.** Tier numbers, SEC/DAT/SC primitive
  codes, Semgrep / Trivy / Gitleaks tool names, `worktree_path` — none are
  the founder's words. Lead with the consequence; keep the codes for the
  `--raw` / technical version. (MUC-F1)

## Vocabulary

- **Review** — Stage 4 of a change: the read-only check on built work before
  it ships, folding the health check and the security check into one verdict.
- **Health check** — the seven-tier code-health pass (build / safe / works /
  survives / understandable / evolves / polished).
- **Security check** — the security / data-protection / supply-chain
  assessment (`check-security`, or the deeper `codebase-assess`), owned by
  the security reviewer.
- **Verdict** — the one founder-facing answer: good to ship, or needs
  attention first.
- **Blocking finding** — something that should be addressed before shipping;
  the few of these are what review leads with.

## Stamp the workflow stage (on completion)

When the review is done and you're inside a change (the `SULIS_CHANGE_ID` env
var is set), record that the change has reached the **review** stage so
`/sulis:dashboard` reflects it. Use the `$SCRIPTS_DIR` you resolved earlier:

```bash
"$SCRIPTS_DIR/sulis-change" stage review
```

Branch-independent, best-effort; it never blocks the stage from completing.
If `SULIS_CHANGE_ID` is unset (work outside a change), skip it. Don't narrate
this to the founder; the dashboard simply stays current (FE-09).

## See also

- `../../scripts/_wpxlib.py` — `resolve_current_change()` (SULIS_CHANGE_ID →
  manifest).
- `../../scripts/sulis-change` — `stage` stamps the workflow position read by
  `/sulis:dashboard`.
- `../code-health/SKILL.md` — the seven-tier health check (dispatches its own
  tier agents) this skill folds in.
- `../check-security/SKILL.md` — the security / data-protection /
  supply-chain assessment.
- `../codebase-assess/SKILL.md` — the deeper evidence-based viability
  assessment.
- `../run-all/SKILL.md` — the prior stage; builds the work review checks.
- `../change/SKILL.md` — `/sulis:change ship`; a clean verdict is its green
  light.
- `../address-findings/SKILL.md` — turns review findings into a work queue.
- `../../agents/security-reviewer.md` — the specialist this skill routes to.
- `../../references/founder-facing-conventions.md` — Rules 1-6.
- `../../docs/change-as-primitive-design.md` — the design this skill realises
  (Stage 4 Review).
