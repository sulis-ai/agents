---
founder_facing: false
status: APPROVED 2026-05-28 — building
---
# Design — /sulis:resolve-lessons (proactive lesson-backlog drain)

> **Locked decisions (founder-approved 2026-05-28):**
> - **Autonomy:** plan-then-approve ONLY in v1. The loop always shows the
>   computed schedule + drafted specs and waits for "go"; no
>   fully-autonomous mode (that's a later, separate opt-in).
> - **Scope:** mechanical lessons only (TASK + clear-fix SEA).
>   Design-heavy SEA lessons are flagged + DEFERRED; no agent-teams
>   coupling in v1 (the teams-debate slot is a documented v2 extension).
> - **Backlog read:** new `sulis-issues list --descriptor lesson`
>   subcommand (Sulis-owned technical call).
> - **First batch:** {#53, #52}.

**Change:** create · resolve-lessons
**Resolves (as first batch, once built):** #53, #52

## What it does (the loop)

Proactively drains the `lesson` backlog. One run:

1. **Read** open `lesson`-labelled GitHub issues (number, title, body,
   labels, disposition).
2. **Triage** each against founder disposition (see Guardrail 2): in /
   skip / defer.
3. **Draft** a change spec per in-scope lesson from its issue body
   (the auto-draft-from-finding pattern, #43).
4. **Predict file-touch** per lesson via the recon code-area pointers
   (`_locate_code_areas(issue_body, repo_root)`).
5. **Collision-schedule**: group lessons by overlapping file-touch.
   Serialise within a group (same files → one at a time); parallelise
   across disjoint groups.
6. **Dispatch a worker** per scheduled lesson through the EXISTING ship
   pipeline: `sulis-change start` → spec → tests → implement →
   **step-4.5 review gate** → branch-ci → squash-merge → mark shipped.
7. **Close the issue** on merge via the PR `Closes #N` trailer.
8. **Batch-report**: resolved / blocked / deferred, per the AAF-06
   three-list shape.

## Architecture (the load-bearing constraint)

**The loop runs INLINE in the calling Sulis session — NOT as a spawned
orchestrator subagent.** This mirrors `/sulis:run-all` and is forced by
the same harness property: spawned subagents are leaves of the agent
tree, so an orchestrator-subagent could not itself spawn the per-lesson
executor subagents. So `/sulis:resolve-lessons` is a skill whose loop
the calling session executes directly, spawning one executor per
scheduled lesson via the Agent tool.

This also means resolve-lessons is **structurally a sibling of run-all** —
same dispatch shape, different backlog source (open lessons vs WP INDEX)
and different per-item unit (a fix-change vs a WP).

## Components

| Component | Build / reuse |
|---|---|
| Backlog read | **NEW** — `sulis-issues list --descriptor lesson [--repo R]` → JSON of open lessons (number, title, body, disposition parsed from the body's `disposition:` line + labels). sulis-issues today only `capture`s; this adds the symmetric read. |
| Disposition triage | reuse `_issues.is_actionable` + a founder-disposition gate (Guardrail 2) |
| Per-lesson spec draft | **NEW (skill prose)** — draft `.changes/{slug}.SPEC.md` from the issue body, like the auto-draft-WP skeleton (#43) |
| File-touch prediction | reuse `_change_context._locate_code_areas(body, repo_root)` |
| Collision scheduler | **NEW** — `_schedule_collision_groups(lesson→files) -> list[wave]` (pure, testable) |
| Worker dispatch | reuse the change-as-primitive flow + the executor (per-lesson) |
| Review gate | reuse `/sulis:review` (step-4.5) — UNCHANGED |
| Issue close | reuse the `Closes #N` PR trailer (#34) |
| Reporter | **NEW (skill prose)** — AAF-06 three-list batch summary |
| Optional design-debate | agent-teams (experimental) for SEA-design-heavy lessons — see below |

## Collision scheduler (the heart of "orchestrator > self-claim")

```
inputs:  {lesson_id: set(predicted_files)}
build an undirected graph: edge(a, b) iff files(a) ∩ files(b) ≠ ∅
connected components = collision groups
within a component: serialise (topological by issue age, oldest first)
across components: parallelise (one wave dispatches one lesson per
  component, up to max_parallel)
```

This is why a central orchestrator beats agent-teams self-claim here:
the schedule is computed up front from predicted file-touch, not
negotiated at runtime by teammates who might miss an overlap. The
#39–#42 anonymiser lessons (all touched `_anonymiser.py`) would land in
ONE component → serialised, never colliding.

**Prediction is imperfect** — `_locate_code_areas` reads backticked
tokens; a lesson may touch files it didn't name. Mitigation: treat the
predicted set as a LOWER bound; if a worker's actual diff touches a file
another in-flight worker is touching, the branch-ci / merge conflict
surfaces it (fail-safe, not silent), and that lesson re-queues. Belt +
braces.

## Guardrails (non-negotiable — all proven this session)

1. **The step-4.5 review gate stays.** It caught the #50 silent-
   fail-open before merge. Every auto-resolved lesson passes it; a
   CRITICAL finding pauses that lesson + surfaces it, never auto-merges
   past it.
2. **Founder disposition.** The founder approves which lessons are
   in-scope before dispatch (the AAF-06 three-list: "N actionable / M
   design-heavy-defer / K skip — resolve the N?"). The loop NEVER
   silently decides scope; mechanical SEA/TASK lessons are candidates,
   design-heavy ones (e.g. #30 SQLite store) default to defer/debate.
3. **Collision-aware scheduling, never naive-parallel.** No two
   in-flight workers touch the same predicted file.
4. **Supervised first run.** Like the platform wave: report per lesson,
   founder watching, validate-one-then-scale. Unsupervised mode is a
   later, separate opt-in.

## Disposition routing

| Lesson disposition | Routing |
|---|---|
| TASK (mechanical) | auto-resolve candidate |
| SEA (clear fix in body) | auto-resolve candidate |
| SEA (design unclear, e.g. competing approaches) | **defer** by default; optionally route to an agent-teams design-debate that produces an approved approach, THEN auto-resolve |
| FIX-NOW / FIXED / note | not in the backlog (never became issues) |

## The optional agent-teams slot

For the design-heavy SEA subset, an agent-team (lead + 2-3 teammates
debating approaches) produces a chosen design, which the founder
approves, after which the resolution loop builds it. **This is the ONE
place teams earn their keep** (workers debating > workers reporting).
v1 ships WITHOUT this (defer design-heavy lessons); the teams hook is a
documented v2 extension so we don't couple the core loop to an
experimental feature.

## First batch (the dogfood)

**{#53, #52}** — chosen because they OVERLAP (both touch the
git-workflow standard / change skill). The collision scheduler must put
them in one component and serialise them. If it does, the pattern's
proven on a low-stakes pair. #53 (git-stash audit) is mechanical; #52
(CI pre-flight check) is lightly design-y — a good range.

## How we'll know it's done

- `sulis-issues list --descriptor lesson` returns open lessons with
  bodies; unit + integration tested (mirrors the capture tests).
- `_schedule_collision_groups` is pure + unit-tested: overlapping
  lessons → one serialised group; disjoint → parallel waves;
  the #39–#42 case → one group.
- `/sulis:resolve-lessons` SKILL.md drives the inline loop, dispatching
  the existing change/executor flow per lesson, review gate intact.
- A **dry-run mode** (`--plan`): show the schedule + per-lesson drafted
  spec WITHOUT dispatching — so the founder approves the plan first.
- Supervised live run resolves {#53, #52} end-to-end: both shipped,
  both issues closed, the scheduler proven to serialise them.
- Full suite green; review gate PASS on this capability's own change.

## Open questions for founder approval

1. **`sulis-issues list` vs skill-direct `gh`** — I lean `sulis-issues
   list` (symmetric, testable, reusable). OK?
2. **v1 scope: defer design-heavy lessons** (no agent-teams debate yet),
   ship the mechanical-resolution loop first. OK, or want the teams
   debate in v1?
3. **Dry-run-plan-then-approve as the default** (the loop always shows
   the schedule + drafted specs and waits for "go" before dispatching),
   vs a fully-autonomous mode behind a flag. I lean plan-then-approve as
   the only v1 mode; autonomous is a later opt-in. OK?
4. **First batch {#53, #52}** confirmed?

## What to avoid

- **Do NOT make the loop a spawned subagent** — it must run inline (the
  run-all constraint).
- **Do NOT bypass the review gate** for speed.
- **Do NOT naive-parallel** lessons without the collision scheduler.
- **Do NOT auto-decide scope** — founder disposition gates every run.
- **Do NOT couple v1 to agent-teams** (experimental) — defer
  design-heavy lessons instead.

## References

- `plugins/sulis/skills/run-all/SKILL.md` — the inline-loop template
- `plugins/sulis/scripts/sulis-issues` + `_issues.py` — backlog +
  the new `list` read-path
- `plugins/sulis/scripts/_change_context.py::_locate_code_areas` —
  file-touch prediction
- `/sulis:review` — the step-4.5 gate; `/sulis:change` — the per-lesson
  ship flow; the `Closes #N` trailer (#34)
- Issues #53, #52 (first batch)
