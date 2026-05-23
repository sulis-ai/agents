---
name: status
description: >
  Show the current journey state in plain English — what phase, what's
  been done, what's blocked, what's next. Read-only; does not modify the
  journey.
user_invocable: true
---

# /sulis:status — Journey Status

When invoked, produce a plain-English snapshot of the founder's current
journey state. Read-only.

## Workflow

1. **Read `.concierge/{project}/JOURNEY.md`.** If it doesn't exist, tell
   the founder: *"No journey started yet for this project. Run `claude
   --agent sulis` to begin."*
2. **Read produced artifacts** to verify what's actually on disk matches
   what JOURNEY.md says. If there's drift (artifacts exist that JOURNEY.md
   doesn't reflect), note it.
3. **Compose the status report** in plain English:

   ```
   ## Where you are

   Current step: {plain-English phase description}
   Last activity: {what completed most recently, plain English}

   ## What's been done

   - {translated phase 1 outcome}
   - {translated phase 2 outcome}
   - ...

   ## What's blocked (if anything)

   - {plain-English blocker description}; needed: {action to unblock}

   ## What's next

   {plain-English next action with the exact slash command if applicable}
   ```

4. **Apply AAF-08:** the report is action-then-report shape. Never
   close with *"Want me to do anything?"*. The user can request a next
   action explicitly if they want one.

## When to use

- The founder wants to remember where they left off.
- The founder is debugging — wants to see what artifacts exist and what
  decisions were captured.
- The founder is showing a collaborator (engineer, designer) the current
  state.

## Output discipline

- No marketplace internal IDs (UC-08, FR-11, ADR-203, WP-007 etc.).
- No methodology jargon (RGB, AAF, CP, OODA, Two-Model Reconciliation
  etc.).
- Phase numbers translated to activity names (per
  `references/founder-english.md`).
- Decisions captured with the principle that drove them (e.g. "easy
  activation" rather than "P8").
