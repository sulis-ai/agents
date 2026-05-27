---
name: inbox
description: "Shows everything waiting on you, in one list."
---

# Inbox

The one place the founder looks to see everything waiting on them.

This skill is the founder-facing equivalent of opening eight terminal tabs to
check eight different state files. It walks the known state sources for the
project, translates operator vocabulary into founder English, and presents one
prioritised list.

If you have not read `references/sources-of-truth.md`, read it once. It maps
each attention-item category to the underlying file paths.

## When invoked

1. **Resolve project + repo root.** If the user is in a project directory,
   read `.sulis/{project}/JOURNEY.md` to confirm the project slug. If
   ambiguous, ask: *"Which project — {list of projects with concierge state}?"*

2. **Run the aggregator script:**

   ```bash
   python3 plugins/sulis/skills/inbox/scripts/aggregator.py \
     --project {project} \
     --repo-root {repo-root} \
     --format json
   ```

   The script returns a JSON envelope:

   ```json
   {
     "project": "salon-app",
     "total_count": 5,
     "categories": {
       "paused_work": [...],
       "review_needed": [...],
       "blocked_tasks": [...],
       "decisions_waiting": [...]
     },
     "errors": [],
     "sources_unavailable": []
   }
   ```

3. **Translate to founder English.** For each item:
   - **WP IDs**: include the slug as the headline; put the ID in
     parentheses. `WP-AUTO-018-observability-adapter.md` →
     `"Observability adapter (WP-AUTO-018)"`.
   - **Train IDs**: use `"Build run {short_id}"` where short_id is the
     last 8 chars.
   - **Phase names**: translate via the table in
     `references/sources-of-truth.md`.
   - **Reasons**: pass through if already plain English; otherwise
     summarise in one sentence.

4. **Present the inbox.** Use this template (omit empty categories):

   ```
   📥 Inbox — {project}

   You have {N} thing{s} waiting:

   ⏸ Paused work ({M})
     • {founder name} — paused: {reason}
       → To resume: press [1]   To dismiss: press [d1]

   🔍 Things to review ({K})
     • {founder name} — {one-line summary}
       → To open: press [2]   To dismiss: press [d2]

   🚫 Blocked tasks ({L})
     • {founder name} — blocked: {reason}
       → To investigate: press [3]   To skip: press [d3]

   ⚖️  Decisions waiting on you ({P})
     • {founder name} — needs: {decision}
       → To decide: press [4]
   ```

5. **Handle a shortcut.** When the founder presses a numbered shortcut:
   - **Echo the action FIRST**: *"Resuming build run a3f2c1d8 — picking up
     from where it paused."*
   - **For destructive actions** (abort, force-push, delete), ALWAYS
     prompt: *"This will discard the partial work on branch xyz. Are you
     sure?"* — wait for confirmation.
   - **For safe actions** (resume, open, view), proceed immediately.

## Gotchas

- **Source-discovery brittleness.** If a state source moves (e.g., findings
  relocate), the aggregator silently misses items. Run
  `python3 aggregator.py --project NAME --doctor` periodically to check that
  all expected sources exist; the doctor reports any missing.
  *Source: HD-008's INDEX-drift class applies to any cross-source aggregator.*

- **Operator-jargon leakage to founder.** Easy to display
  "BLOCKER: rebase failed on dev" when the founder needs "blocked because
  the code couldn't be merged together cleanly." Every display string MUST
  pass the FE-06 check (see `plugins/sulis/references/founder-english.md`).
  *Source: anchor cases 3 and 4 in founder-english.md.*

- **Stale-on-read.** The aggregator must recompute on every invocation; no
  caching. If you cache, the founder sees state from N minutes ago and acts
  on it incorrectly.
  *Source: same pattern HD-008 fixed for INDEX (compute-on-read).*

- **Ambiguous one-keystroke dispatch.** Each shortcut MUST echo its action
  AND the affected item before performing. "[1]" alone is ambiguous;
  "Resuming build run a3f2c1d8" is not.
  *Source: every CLI tool that doesn't echo before acting produces "wait,
  what did I just do?" moments.*

- **Destructive action without confirmation.** Shortcuts MUST never
  trigger destructive operations silently. Allow-list of safe actions
  (resume, view, open, dismiss-from-view); destructive actions (abort,
  force-push, delete) always prompt.
  *Source: Claude Code "Executing actions with care" doctrine — destructive
  operations require user confirmation.*

## Vocabulary

- **inbox** — this aggregator; the screen showing all attention-items
  for the project.
- **attention-item** — a single thing waiting for the founder. Has a
  category, a founder-readable name, an operator-side reference (WP ID,
  train ID, finding ID), and a one-line reason.
- **waiting-action** — the category-class. "What's waiting for the
  founder to act on?" — distinguished from "what's happening right now"
  (which is `sulis:status`'s domain).
- **paused work / paused-train** — a train run that stopped mid-flight.
  Defers to sulis-execution's `phase: paused` semantics (see
  `plugins/sulis-execution/scripts/_wpxlib.py`).
- **review-needed / gate-finding** — a code-review or security finding
  awaiting triage. Defers to sulis-execution + sulis-security semantics.
- **blocker** — a WP whose executor cannot progress. Defers to
  sulis-execution's BLOCKER record format.

The inbox CONSUMES these concepts; it does not redefine them. Source-of-
truth pointers are in `references/sources-of-truth.md`.

## When to invoke this skill

- Founder asks "what's waiting for me?", "what needs my attention?",
  "where do I look first?"
- After a long break / new session — founder wants a quick orientation
- Concierge wants to ground a "next step" recommendation in actual
  pending items rather than guess

## When NOT to invoke this skill

- Founder asks "where am I?" or "what phase am I in?" — use `sulis:status`
  instead (current state, not waiting items)
- Founder asks "what should I do next?" — use `sulis:next` instead (when
  built; recommendation engine over inbox + journey state)
- Operator wants per-WP detail — use `/sulis-execution:status` instead
  (operator-facing INDEX summary)
