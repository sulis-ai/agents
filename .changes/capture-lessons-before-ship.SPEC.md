---
founder_facing: false
status: BUILT — founder-directed ("all lessons captured before shipping, not a post question")
---
# Spec — lesson-capture is a mandatory pre-merge gate, never a founder question

**Change:** fix · capture-lessons-before-ship
**Source:** founder directive after observing the spawned #52 session end its
review with *"Want me to turn those 4 findings into durable lessons before or
after you ship?"* — an optional post-ship question.

## Root cause

Lesson-capture is not wired into the ship flow at all. `grep` confirms
`/sulis:change ship` and `/sulis:review` never reference `capture-lessons`;
the `capture-lessons` skill frames itself as *post-ship* ("After a piece of
work ships…"). With no mandated step, the agent improvises an optional
*"before or after?"* question — the same permission-theatre class (AAF-08) as
the `/sulis:specify` depth ask. Capturing lessons is a process step the agent
owns, not a founder decision.

## What this does

1. **`/sulis:change ship` gains step 4.6 — Capture lessons (REQUIRED, before
   the merge).** Run automatically, after the review gate (4.5) and before the
   squash-merge (5). A no-op when there are no actionable findings, so it's
   safe to run on every ship. Never a *"want me to? before/after?"* question.
   The ship report (step 7) surfaces what was captured ("Captured 4 lessons as
   issues #60-63"), never a choice.
2. **`/sulis:review` routes tooling/process observations to ship-time
   capture**, not to a founder question. Findings about the *change* shape the
   verdict; observations about *Sulis's machinery* are carried to step 4.6.
3. **`/sulis:capture-lessons` is reframed from post-ship to ship-time
   (before the merge)** and its primary trigger is "automatic step of
   `/sulis:change ship`", with the manual ad-hoc trigger secondary.

## How we'll know it's done

- The ship flow has a required pre-merge capture step; the founder is never
  asked whether/when to capture.
- The three skills are internally consistent (no "post-ship" / "want me to
  capture?" framing remains).
- Skill frontmatter validates; release bump applied.

## What to avoid

- Don't expand into the run-all/train ship path here — that's a scoped
  follow-up (the train auto-drafts from findings via a different mechanism).
  This change fixes the interactive change-ship flow the founder observed.
- Don't change the capture *mechanism* (`sulis-issues` / descriptors) — only
  WHEN it runs and that it's mandatory, not optional.

## References

- `plugins/sulis/skills/change/SKILL.md` — ship flow (new step 4.6 + step 7)
- `plugins/sulis/skills/review/SKILL.md` — observations → ship-time capture
- `plugins/sulis/skills/capture-lessons/SKILL.md` — reframed to pre-merge
- AAF-08 (decided actions are not questions); the `/sulis:specify` depth ask
  is the sibling defect (parked).
