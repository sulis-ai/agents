# The Working Set + the session-chain (draft spec — pre-road-test)

> **Status:** draft. Converged via two `/sulis-brain:critical-thinking` spiral runs
> (chain-of-sessions review + Working Set structure review, 2026-06-04). NOT yet
> road-tested. Do not treat as a standard until the K3 acceptance test below
> passes on one real session.

## The problem this fixes

Long single-session changes **drift**: the locked requirements / decisions live in
the conversation — the most volatile place they could live — and as context grows,
judgment degrades and "locked" things quietly un-lock. The structural fix is a
**chain of shorter sessions** with the brain as the durable handoff between them.

But the handoff today is **incomplete**: the four contracts (UI / service / data /
platform) capture the *what*, never the *why* — the rejected alternatives and the
reasoning behind each lock. A boundary that passes only the contracts forward
silently drops the *why* → it trades drift for **amnesia**. The Working Set is the
mechanism that makes the handoff carry the *why*.

## The model

- **The change** is the thread that outlives sessions (the branch + its brain state).
- **Sessions** are time-slices against it. Each session: **reload** locked truth from
  the brain → do **one locked unit of decision** → **crystallize** the result back →
  end. (Granularity is *per locked decision*, not per calendar-stage — an iterative
  diverge/converge stage may take several sessions; a bounded convergent one may
  share a session. Never force a boundary mid-exploration.)
- **The brain** (Opportunity / Design / Decision / Scenario / contracts) is the durable
  store. **The conversation is disposable.**
- **The Working Set** is the *live reasoning state* during a session — the staging
  area that crystallizes into the durable entities at the boundary.

## The Working Set (the artifact to start capturing)

One small file per session, at a known path, **read at the start of every turn**,
updated as a **side-effect of reasoning** (never a separate chore). Six sections:

| # | Section | Purpose | Crystallizes → |
|---|---------|---------|----------------|
| 1 | **Problem** (situation / complication / question) | current framing of what we're solving | Opportunity |
| 2 | **Current best solution** (answer / approach) | the leading solution shape right now | Design |
| 3 | **Decisions in flight** | each non-trivial choice being weighed: the choice, options considered, rejected alternatives + rationale, status `proposed` | Decision (on lock: `proposed`→`accepted`) |
| 4 | **Open questions / unknowns** | the live "what we still don't know" parking lot | drains, or → a Decision's `open_questions` |
| 5 | **Rejected so far** | paths tried and abandoned, **with the why** (the bit that kept getting lost) | each Decision's `rejected_alternatives` |
| 6 | **Working log** (append-only tail) | terse timestamped "what just changed and why"; the crash-safe trail | — (history) |

Sections **1–5 are mutable** (current state, overwritten as thinking moves);
section **6 is append-only** (never edited). That split reconciles "continuously
updated" with the rule that decision records aren't rewritten.

**Relationship to existing artifacts (no duplication):** the Working Set is *current
reasoning state* — distinct from `SPEC.md` (*what to build*) and the run journal
(*what happened operationally*). It is the staging area; Opportunity/Design/Decision
are the locked records.

## The Decision convention extension (the durable "why")

Extend the existing **Decision** entity — by convention, additive — with three fields:
- `rejected_alternatives` — paths considered and not taken.
- `rationale` — the *why* behind the choice.
- `open_questions` — unresolved items carried with the decision.

Use Decision's **existing `proposed` → `accepted` status** to model a decision still
in flight vs locked. No new entity. (This is a source-ontology schema change — a
DR + minor version bump + recompile + re-vendor — so it comes **after** the road-test,
per sequencing below.)

## The session protocol

- **Session start:** read the Working Set at its known path (this is the chain-of-
  sessions reload — it carries the *why* from the prior session).
- **During:** update the relevant section the moment a decision is made or an
  alternative rejected. The agent reads it every turn as its single source of current
  state.
- **Session boundary (crystallize):** each mutable section distils into its target
  entity; `proposed` decisions that locked become `accepted` Decisions carrying their
  `rejected_alternatives` + `rationale`; unresolved items move to `open_questions`.
- **Crash-safe:** if a session ends without crystallizing, the persisted Working Set
  *is* the handoff — the next session reads it as working memory. No loss of the *why*.

## Acceptance test + falsifiers

- **K3 (the make-or-break):** is the Working Set **actually read at the start of every
  turn**? If it's written but not read every turn, it will rot exactly like an
  abandoned "living doc" — and it should not exist. This is the road-test's primary
  check.
- **K2/K4 (residual uncertainty):** does "current thinking" reliably fan out to exactly
  Opportunity / Design / Decision, or does a big mid-session problem-reframe sometimes
  need a richer staging shape? Only a real road-test settles this.

## Sequencing (the disciplined order — cheapest, lowest-regret first)

1. **Now / first piece:** define the Working Set template (the six sections above) and
   road-test it as a **plain file** on one real session. This needs **no schema
   change** — crystallization-into-Decision-fields comes later. Check K3 (read every
   turn?) and K2/K4 (clean fan-out?).
2. **After the road-test proves the shape:** add `rejected_alternatives` + `rationale`
   + `open_questions` to the Decision entity (source ontology, DR + minor bump), and
   wire the session-start-read + boundary-crystallize protocol.
3. **Then:** make the boundary gate check the *why* is present (the handoff-
   completeness gate), and fold the whole thing into the session-chain rule.

Do **not** make the schema change ahead of the road-test — committing the
fan-out-to-three-entities before seeing it hold is the exact "build ahead of use"
trap.

## Convention grounding (lean on these, not bespoke)

- **ADR** (Nygard / MADR / Y-Statement) — the Alternatives-Considered slot +
  `Proposed → Accepted → Superseded` status → sections 3 & 5.
- **Minto SCQA / Pyramid** — the problem/answer framing → sections 1 & 2 (also the
  shape the critical-thinking workflow already outputs).
- **Agent scratchpad / working-memory** — the read-every-turn live-update discipline +
  the session-boundary handoff.

## Provenance

- Chain-of-sessions review: `/sulis-brain:critical-thinking` spiral, 2026-06-04
  (verdict: chain-of-sessions sound; handoff incomplete — carries *what*, not *why*).
- Working Set structure review: `/sulis-brain:critical-thinking` spiral, 2026-06-04
  (verdict: runtime Working Set + thin Decision convention; do NOT mint a new entity;
  six-section structure; K3 acceptance test).
- Recurring pattern: this is the system's draft→locked / staging→committed split a
  fourth time (Scenario→Workflow→TestRun; Tool-def→binding→call; Action→Workflow→
  LifecycleRun; **Working Set→Decision**).
