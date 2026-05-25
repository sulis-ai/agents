# Founder-Facing Conventions

The contract for any skill, agent, or surface in this marketplace that talks
to a non-technical founder. Conditional on the Gate 2 `Audience` lock in
`sulis:add-skill` — if a skill is locked as `founder-facing` or `both`, it
MUST follow these conventions.

Wraps the existing Founder English standard (FE-01..FE-11) at
`plugins/srd/references/founder-english.md`. This document is the
applied-conventions layer: what FE looks like specifically for skill
chrome, error messages, trigger conditions, and shortcuts.

## The six rules

### Rule 1 — Apply FE-06 to every founder-visible string

The Founder English five-point check (strip internal IDs, translate
filenames, expand acronyms, strip internal taxonomy, read-aloud test)
applies to:

- Every chat message
- Every chunk of chrome the founder sees (status updates, progress bars,
  prompts)
- Every Agent-tool `description` parameter visible in the UI
- Every error message the founder might see
- Every shortcut label

If a string would fail the read-aloud test (would a non-technical person
understand this spoken aloud at coffee?), it fails the conventions.

### Rule 2 — Lead with the founder-readable name; the operator ID is parenthetical

Operator IDs (`WP-AUTO-018`, `SF-024`, train IDs) are load-bearing in the
machine layer; they're noise in the founder layer. Convention:

- **Bad:** `"WP-AUTO-018 is blocked"`
- **Good:** `"Observability adapter (WP-AUTO-018) — blocked"`

The slug-from-filename becomes the headline; the ID hangs in parens for
operator reference. If no founder-readable slug exists, use a category
noun ("Build run", "Security finding", "Task") plus a short identifier.

### Rule 3 — Echo before acting; prompt before destroying

Two layered safety mechanisms:

**Echo before acting** — every action triggered by a shortcut or
recommendation, even safe ones, MUST echo the action AND the affected
item BEFORE performing it. This prevents "wait, what did I just do?"
moments.

- **Bad:** _(silently resumes train)_
- **Good:** `"Resuming the paused build run a3f2c1d8 — picking up from
  where it stopped."`

**Prompt before destroying** — destructive actions (force-push, branch
delete, abort train, drop data, modify shared state) MUST prompt for
explicit confirmation, even if the founder asked for them.

- **Bad:** _"You said abort, so I aborted."_
- **Good:** `"This will discard the partial work on branch xyz and the
  changes won't be recoverable from the train state. Are you sure?"`

Allow-list of safe actions (proceed without prompt):
- read / view / open / show
- resume / continue
- mark-done / mark-accepted (if updating non-destructive state)
- dismiss-from-view

Anything else: prompt.

### Rule 4 — Translate operator vocabulary at output time, not at write time

Internal data sources are operator-vocab — `BLOCKER`, `WP-NNN`, `train
state paused`, `S-NNN finding pending triage`. Translation belongs at the
SKILL.md layer (when constructing the founder-visible string), not at the
storage layer.

Why: the same data is read by operators (who want the precise term) and
by founders (who want plain English). Storing the founder term means
operators lose precision; storing the operator term and translating at
the seam means both audiences get what they need.

Translation tables live with the skill (in SKILL.md or a `references/`
file), not in the source-of-truth storage.

### Rule 5 — Error messages explain in founder terms what happened AND what to do

Operator error messages are diagnostic ("rebase failed: merge conflict in
src/foo.py"). Founder error messages must explain the situation AND
propose the next step.

- **Bad:** `"rebase conflict on WP-AUTO-018"`
- **Good:** `"The code couldn't be merged together cleanly because two
  changes touched the same lines. To resolve, ask the AI engineer to
  reconcile the conflict and try again."`

Even better: provide a shortcut to the resolution path where possible.

### Rule 6 — Dual register: default founder, on-request technical

Every founder-facing agent and skill is **dual-register** — defaults to
founder-mode (full tone stack applied: AAF + FE + COACHING + TONE +
Rules 1-5 above), switches to technical-mode on request.

Founder-mode is a **translation, not a filter**. Same substance,
different shape. No information hidden in founder-mode that surfaces
only in technical — that would erode trust. If a file path or
identifier is signal the founder needs to act on, surface it in
founder-mode too (using Rule 2 — readable name with ID in parens).

#### The three trigger mechanisms

| Trigger | Scope | Example |
|---|---|---|
| **Natural language intent** | This response only | "show me the technical version" / "what's the raw output?" / "give it to me straight" → agent detects intent and switches |
| **`--raw` flag on command** | This invocation only | `/sulis:wp-status WP-101 --raw` returns JSON envelope, no translation |
| **Session toggle** | Until toggled back | `/sulis:jargon on` switches the session to technical-mode; `/sulis:jargon off` reverts to founder-mode default |

Intent detection is the primary mechanism — it requires no command
memorisation. Flags and toggles are explicit overrides for power users
(or for when intent detection misfires).

#### Mode declaration requirement

Every founder-facing or both-audience skill / agent MUST declare its
technical-mode output shape in its SKILL.md or agent.md frontmatter:

```yaml
register:
  founder_mode: default
  technical_mode:
    shape: json_envelope | markdown_with_paths | diff | raw_tool_output
    triggers: [intent, --raw, /sulis:jargon]
```

Operator-facing skills declare `register: { technical_mode: default }`
and skip the founder-mode shape entirely.

#### What the agent does on register switch

1. **Intent-triggered switch:** Agent confirms the switch in one
   sentence ("Switching to technical-mode for this response."), then
   produces the technical-mode output. Returns to founder-mode default
   on the next interaction unless the founder explicitly persists it
   ("keep it technical").
2. **`--raw` flag:** No confirmation needed; the flag is the explicit
   request. Emit the declared technical-mode shape directly.
3. **`/sulis:jargon on` toggle:** Confirms ("Switched to technical-mode
   for the rest of this session — `/sulis:jargon off` reverts."), then
   all subsequent responses are technical-mode until toggled back or
   the session ends.

#### What technical-mode does NOT do

- It does NOT skip safety checks (Rule 3's prompt-before-destroy
  still applies — though the prompt is operator-direct: "Force-push
  to dev. Confirm? (y/N)")
- It does NOT skip the standards stack — CRITICAL_THINKING, SPIRAL
  verification, REFERENTIAL_INTEGRITY all still apply
- It does NOT enable destructive shortcuts that founder-mode would
  prompt on — the prompt is just shorter

#### Examples

**Founder-mode (default):**
> *"WP-102 (handler) failed at Step 6 (test). The assertion on `auth.py:42` expected a `dict` but got a `list`. Worktree preserved at `~/repo-wp-102-handler/`. Want me to look at it or do you want first crack?"*

**Technical-mode (same situation, `--raw` or after `/sulis:jargon on`):**
```json
{
  "wp_id": "WP-102",
  "stage": "step-6-test",
  "status": "failed",
  "error": {
    "file": "auth.py",
    "line": 42,
    "type": "AssertionError",
    "message": "expected dict, got list"
  },
  "worktree": "~/repo-wp-102-handler/",
  "next_actions": ["resume", "abandon", "retry-with-fix"]
}
```

Same substance. Different shape. Founder-mode does the translation
work; technical-mode trusts the operator with the structured raw.

## What this means for skill authoring

When the Gate 2 `Audience` lock = `founder-facing`:

- **Trigger condition** uses ONLY user-facing vocabulary (no operator
  jargon, even if accurate). Test: hand Claude the description alone in
  a fresh session; would it know when to invoke?
- **Display strings** in SKILL.md follow Rules 1-2.
- **Shortcuts and actions** in SKILL.md follow Rule 3.
- **Vocabulary section** documents which translations the skill performs
  (operator → founder) and which terms it leaves alone (terms that are
  already plain English).
- **Error message specifications** in SKILL.md follow Rule 5.
- **Gotchas section** must include at least one gotcha about
  operator-vocab leakage and one about destructive-action confirmation.

When the Gate 2 `Audience` lock = `operator-facing`:

These conventions do NOT apply. Operator skills can use technical
vocabulary directly; that's the audience's preference.

When the Gate 2 `Audience` lock = `both`:

The skill must declare a mode-selection strategy: how does the skill
know which audience it's currently serving? Common patterns:
- Outermost invocation (founder via `sulis` plugin → founder mode;
  direct operator invocation → operator mode)
- Explicit flag (`--audience operator`)
- Context-derived (read concierge JOURNEY.md to infer)

Both modes must satisfy their respective conventions.

## How to verify (Gate 4 perspective)

The `Audience: founder-facing` lock implies an extra Gate 4 sub-check:

**Founder-readability perspective.**

1. Take every founder-visible string from SKILL.md (trigger condition,
   templates, error specs, shortcut labels, gotchas).
2. For each, apply the FE-06 read-aloud test.
3. Record verdicts (PASS / FAIL with the failing string + reason).

Threshold: 100% of founder-visible strings pass. Any FAIL blocks publish.

DEFERRED is not appropriate for this check — every string is readable or
not.

## Adversarial sweep additions (Gate 5)

For founder-facing skills, the Gate 5 misuse-case catalogue extends to:

- **MUC-F1: Operator jargon leak in error string.** The skill body
  produces clean strings but a wrapped script's error bubbles up
  untranslated. Mitigation: SKILL.md catches script errors and
  re-translates before showing.
- **MUC-F2: Shortcut acts on stale state without echoing.** Founder
  presses [1]; state changed; action is wrong. Mitigation: echo-first +
  re-read state before action.
- **MUC-F3: Destructive action triggered by ambiguous phrasing.**
  Founder said "clear" — meaning "clear this from view" — but Claude
  interpreted as "delete the underlying data". Mitigation: prompt-before-
  destroy is universal; allow-list governs.
- **MUC-F4: Number-of-items overwhelm.** Real-state surfaces 20+
  attention-items; founder bounces. Mitigation: presentation cap +
  ordering by severity.
- **MUC-F5: Inbox false-positive.** Source state not updated after
  out-of-band resolution. Mitigation: dismissal write-back AND/OR
  source-of-truth doctor checks.

For agents and skills declaring a dual-register pattern (Rule 6), the
catalogue extends to register-specific misuse cases:

- **MUC-R1: Technical-mode leaks into founder-mode default.** Agent
  emits a JSON envelope or IDs-only string when the founder expected
  plain English. Mitigation: register flag checked at emission time;
  default-register-check in Gate 4 verification.
- **MUC-R2: Founder-mode jargon-stripping drops information the
  founder needed.** File path stripped from an error message, but the
  founder asked "what file?" — the file path was signal, not jargon.
  Mitigation: surface load-bearing identifiers in founder-mode too
  (per Rule 2: readable name with ID in parens).
- **MUC-R3: Register-switch ambiguity.** Founder says "more detail"
  — does that mean more depth in founder-mode or switch to
  technical-mode? Mitigation: default is "more depth in founder-mode";
  ask explicitly if the founder seems to want the technical version
  ("Want the technical version, or more detail in plain English?").

Each founder-facing skill MUST address at least 3 of MUC-F1..F5 in its
COMPLETENESS_REPORT.md adversarial-review section. Skills declaring
dual-register MUST additionally address at least 2 of MUC-R1..R3.

## Concrete examples

### Trigger condition

- **Founder-facing, good:** `"Use when the founder asks 'what's waiting
  for me?' or wants a one-screen view of all attention-needed items."`
- **Founder-facing, bad:** `"Aggregator over paused trains, gate
  findings, auto-drafted WPs, and BLOCKERs."` — leaks four operator
  terms into the trigger condition.

### Status message

- **Founder-facing, good:** `"I'm checking on your project's status —
  this'll take a few seconds."`
- **Founder-facing, bad:** `"Invoking /sulis-execution:status against
  .architecture/{project}/work-packages/INDEX.md..."`

### Confirmation prompt

- **Founder-facing, good:** `"This will throw away the partial work and
  start the build over. The changes won't be recoverable. Continue? (yes
  / no)"`
- **Founder-facing, bad:** `"abort train abc1234? [y/N]"`

## Source

- Founder English standard: `plugins/srd/references/founder-english.md`
  (FE-01..FE-11). This document is the marketplace-wide canonical
  reference.
- Anchor cases informing Rules 1, 2, 4: anchor cases 3 + 4 in
  `founder-english.md`.
- Anchor case informing Rule 3: Claude Code's "Executing actions with
  care" doctrine (`CLAUDE.md`).
- Anchor case informing Rule 5: HD-013 (lost diagnostic logs masking
  operator-side debuggability) applied inverse: the operator surface
  lost helpful context; the founder surface needs analogous resolution
  guidance for the same root cause.
