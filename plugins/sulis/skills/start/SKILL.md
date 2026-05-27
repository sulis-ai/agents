---
name: start
description: "Resumes an existing journey where you left off."
user_invocable: true
---

# /sulis:start — Resume Journey

When invoked, read `.sulis/{project}/JOURNEY.md` and resume from the
current phase.

## Workflow

1. **Look for journey state.** Check for `.sulis/{project}/JOURNEY.md`
   in the current project directory.
2. **If no journey exists:** the founder is starting fresh. Route to the
   concierge agent's Phase 1 (Greet) directly: respond with the canonical
   greeting and capture the founder's goal.
3. **If a journey exists:** read it. Extract:
   - Current phase (1-7)
   - Last action completed
   - Pending blockers (if any)
   - Next action
4. **Resume with the welcome-back pattern** (action-then-report shape,
   AAF-08 compliant):

   > *"Welcome back. You were on [plain-English phase description]. The
   > last thing that happened was [translated last action]. The next step
   > is to [run X / answer this question / etc.]. Want to continue from
   > there, or pick a different direction?"*

5. **Read produced artifacts since last session.** Check
   `.specifications/`, `.architecture/`, `.context/`, `.security/`,
   `.architecture/{project}/work-packages/` for new files that have
   appeared since JOURNEY.md was last updated. If new artifacts exist, the
   founder likely ran a specialist and is returning — update journey state
   and translate the new artifacts in plain English.
6. **Auto-progress** to the next phase if exit criteria are met (Phase
   Auto-Progression per AAF-08).

## When to use

- The founder runs `claude --agent sulis` in a project where a
  journey already exists.
- The founder returns to the concierge session after running a specialist
  slash command.
- The founder hasn't been seen for a while and the concierge needs to
  re-establish context.

## When NOT to use

- A fresh project with no JOURNEY.md — the concierge agent prompt handles
  Phase 1 (Greet) directly without needing this skill.

## Composition

- Updates `.sulis/{project}/JOURNEY.md` `## Phase History` and
  `## Triage Trace` sections as it works.
- Respects AAF-01..AAF-09; never asks permission-theater questions during
  resume.
- Applies AAF-09 retroactive triage if a plugin version delta is detected
  since the last session.
