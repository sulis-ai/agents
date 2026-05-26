# Brainstorm, Prototype, and the Routing Rubric — a design brainstorm

> Status: **brainstorm** (diverge → converge, research-grounded). Not yet a
> committed design. Produced by the Sulis agent embodying the brainstorm
> behaviour it proposes. The recommendation at the end is what would
> graduate into one or more changes.
>
> Method: Double Diamond (Design Council, 2005) — separate the problem space
> from the solution space, and within each separate idea *generation*
> (divergent) from idea *selection* (convergent). See Sources.

---

## Why this brainstorm exists

Three threads converged in conversation:

1. A founder often wants to **explore an idea before committing to it** —
   `/sulis:change start` is a commitment (branch + worktree + terminal).
2. That exploration has two distinct shapes: a **brainstorm** (a
   research-grounded, critically-rigorous conversation) and a **prototype**
   (throwaway scratch code to answer a question only code can answer).
3. The founder's sharper observation: Sulis has no single **rubric** telling
   it when to invoke which skill/agent — and *part of that routing could be
   handled programmatically* rather than by judgment.

This doc explores all three as one coherent piece of work, because they
share a spine: **how Sulis decides what to do when you bring it an intent.**

---

## Diamond 1 — the problem space

### Discover (diverge on "what's actually going on")

Routing in Sulis today happens through **three uncoordinated mechanisms**:

| Mechanism | Covers | Form |
|---|---|---|
| Journey-model table | 7 phases → 5 specialist agents | Hand-written table in agent body |
| Stage auto-routing | 6 change stages → stage skills | `SULIS_CHANGE_ID` + which artifacts exist |
| `routes_to` + `delegation` frontmatter | The 5 specialist **agents** + artifact ownership | Declared, with trigger phrases |
| *(implicit)* skill descriptions + judgment | The other ~40 **skills** | Emergent — no central rule |

The first three are explicit and auditable. The fourth is not: ~40 skills
(the `check-*` family, `code-health`, `dashboard`, `inbox`,
`address-findings`, the meta-skills, and the not-yet-built brainstorm +
prototype) are reached by Sulis's judgment plus Claude Code's own
description-matching. Nothing proves every skill is reachable; nothing stops
a new skill being added and never routed to.

Two observations from research (Sources below):

- **Routing has a deterministic core.** The semantic-router literature
  treats intent→action mapping as a *deterministic middle layer* (rules /
  embeddings / classifier), explicitly to avoid the failure mode where a
  free-running LLM router "hallucinates over periods of extended use."
- **But fuzzy intent needs judgment.** "Explore this idea" is not a keyword
  — it's a posture. Pure deterministic routing can't catch it; pure
  model-based routing is unreliable at scale. The literature's answer is a
  **hybrid**.

### Define (converge on the core problem)

> **Sulis has no single, validated source of truth for "given an intent,
> what do I invoke?" Routing is emergent, unauditable, and mixes a
> deterministic core (explicit invocations, inventory, coverage) with
> judgment (fuzzy-intent classification) that should be separated.**

The brainstorm + prototype modes are downstream of this: they are two new
routes that need a home in whatever routing mechanism we choose.

---

## Diamond 2 — the solution space

### Develop (diverge — options per decision)

#### Decision A — the rubric's form & maintenance

- **A1 — Hand-maintained central table** in the agent body. Simple; but
  drifts from each skill's own triggers and bloats a 2,200-line agent.
- **A2 — Derived/generated** from each skill's frontmatter routing
  declaration. No drift (single source); requires every skill to declare a
  routing signal.
- **A3 — Authored + CI-validated for coverage**: the rubric is written, and
  a check asserts every skill is *either* routed-to *or* explicitly
  excluded. Catches orphans; rubric and skills can still disagree on wording
  but never on existence.
- **A4 — Hybrid (A2 + A3)**: skills declare the signal; a build step
  assembles the rubric; CI validates coverage + no-orphan + no-duplicate.
  Most robust; most work.

#### Decision B — the deterministic / judgment seam (the founder's point)

- **B1 — All judgment** (status quo). Flexible; brittle; drifts; degrades
  over long sessions.
- **B2 — All deterministic** (rules / semantic router, no LLM). Reliable;
  cannot handle fuzzy intent like "explore this."
- **B3 — Hybrid** (the literature's recommendation). A `sulis-route` tool
  (sibling to `sulis-change`) owns the deterministic layer: the skill/agent
  inventory, the closed route-set, explicit-invocation lookup, and the
  coverage check. The LLM (Sulis) does one thing only — classify *fuzzy*
  intent **into that validated closed set**. Choosing from a proven menu,
  not free-forming.

#### Decision C — where "brainstorm" lives

- **C1 — Skill only** (`/sulis:brainstorm`). Explicit + repeatable + produces
  an artifact; but misses the "I just arrived with a fuzzy idea" moment.
- **C2 — Agent behaviour only** (woven into Sulis). Always available; but no
  durable, sourced artifact; not repeatable as a named thing.
- **C3 — Both-and** (founder's lean). A *lightweight* brainstorm posture is
  Sulis's **default behaviour** when intent is fuzzy (don't rush to
  `start`); a dedicated **`/sulis:brainstorm` skill/agent** is the "go deep"
  escalation — full diverge → research → converge producing a durable,
  sourced write-up that can **graduate** into a change.

#### Decision D — where "prototype" lives

- **D1 — Separate command/system.** Parallel machinery; duplicates the
  change lifecycle.
- **D2 — A flavour of change** (`/sulis:change start --prototype`). A
  disposable change: reuses branch / worktree / dashboard / nuke; tagged
  throwaway; never expected to ship to `dev`; nuke is the expected exit.
- **D3 — A new primitive** (`prototype`) in the 22-primitive vocabulary.
  Clean semantics; but a prototype is a *lifecycle flavour* (disposable),
  not a *kind of change* — it cross-cuts the existing primitives.

### Deliver (converge — critical-thinking gates → recommendation)

Gates applied (per CRITICAL_THINKING_STANDARD):

- **Assumption test.** "A central rubric won't drift." False for A1 — a
  hand-written duplicate always drifts. → reject A1.
- **Falsifiability.** The rubric is *correct* iff a check can prove every
  skill is reachable. That demands a deterministic inventory + coverage gate.
  → B-layer must be deterministic; favour A3/A4.
- **Convention preference.** Both the routing literature (hybrid
  deterministic + model) and our own REFERENTIAL_INTEGRITY_STANDARD
  (validated cross-references, no orphans) point the same way. Reuse the
  pattern; don't invent.
- **Simplicity / sequencing (anti over-build).** Don't ship A4 + B3 + C3 +
  D2 at once. Stage it.

**Recommendation:**

1. **Build the deterministic spine first.** A `sulis-route` tool + a
   `references/routing-rubric.md` (the closed route-set as data) + a CI
   coverage check (no skill orphaned, no duplicate route). This is the
   programmatic layer the founder identified. Start at **A3**, evolve toward
   **A4** once skills carry a routing signal in frontmatter.
2. **Layer judgment on top (B3).** Explicit invocations → deterministic
   lookup. Fuzzy intent → Sulis classifies into the validated route-set. The
   rubric becomes a required `context_source` for the agent.
3. **Brainstorm = both-and (C3).** Lightweight posture as default behaviour,
   gated on fuzzy intent (a new agent-body section + a routing-rubric rule:
   *fuzzy / "what if" → brainstorm; clear + bounded → proceed*). Dedicated
   `/sulis:brainstorm` skill/agent for the deep version: **diverge** (Osborn-
   Parnes idea-finding, defer judgment) → **research** (reuse the
   research-synthesis methodology) → **converge** (critical-thinking gates,
   score, pick) → a durable sourced artifact that graduates to a change.
4. **Prototype = flavour of change (D2).** `/sulis:change start --prototype`
   → disposable change; dashboard tags it throwaway; nuke is the exit.

**Suggested sequencing (each its own change):**

1. Routing rubric + `sulis-route` + coverage gate (the spine).
2. `/sulis:brainstorm` skill/agent + the default brainstorm posture.
3. `--prototype` flavour on `/sulis:change`.

The spine goes first because brainstorm and prototype are both just new
routes — cheaper to add once the rubric that governs routes exists.

---

## The brainstorm gate (how the default posture decides)

The discrimination that keeps brainstorm-first from becoming
over-exploration:

| Intent signal | Route |
|---|---|
| Fuzzy / open / "what if" / "should I" / "I'm thinking about" | Brainstorm posture (diverge/converge inline; offer the deep skill if it's substantial) |
| Clear + bounded + the founder knows the outcome | Proceed (recon / specify / change start) |
| "Try it / spike / can the code even do X" | Prototype (disposable change) |
| Explicit `/sulis:foo` | Deterministic lookup — no classification |

This is a decision procedure, not a keyword table — it layers on the
existing AAF pre-question triage.

---

## Open questions (resolve before / within the changes)

1. **Rubric generation:** authored + CI-validated (A3) first, or jump to
   frontmatter-derived (A4)? (Lean: A3 first.)
2. **Brainstorm artifact:** where does the write-up live, and how does it
   seed the change it graduates into — as the spec, or the recon
   `CONTEXT.md`?
3. **Prototype:** flag vs primitive (lean: flag), and does a prototype ever
   graduate into a real change, or is its only output a learning?
4. **Does the deterministic layer use keyword/rules or embeddings?** Rules
   are simpler and dependency-free; embeddings handle paraphrase. (Lean:
   rules first — the explicit-invocation + inventory + coverage value
   doesn't need embeddings.)

---

## Sources

Methodology (diverge/converge):
- [Double Diamond (design process model) — Wikipedia](https://en.wikipedia.org/wiki/Double_Diamond_(design_process_model))
- [What is CPS? — Creative Education Foundation](https://www.creativeeducationfoundation.org/what-is-cps/)
- [The Osborn-Parnes Creative Problem-Solving Process — Project Bliss](https://projectbliss.net/osborn-parnes-creative-problem-solving-process/)

Routing (deterministic vs model-based dispatch):
- [Semantic Routing for Enhanced Performance of LLM-Assisted Intent-Based Management — arXiv 2404.15869](https://arxiv.org/abs/2404.15869)
- [Routing / dynamic dispatch patterns — AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/routing-dynamic-dispatch-patterns.html)
- [Semantic Routing and Intent Classification in AI Agent Systems](https://notes.muthu.co/2025/11/semantic-routing-and-intent-classification-in-ai-agent-systems/)

Internal precedent:
- `plugins/sulis/references/standards/REFERENTIAL_INTEGRITY_STANDARD.md` — validated cross-references / no-orphan pattern.
- `plugins/sulis/references/audience-adapted-framing-standard.md` — the AAF pre-question triage the brainstorm gate layers on.
- `plugins/sulis/docs/change-as-primitive-design.md` — the change lifecycle `--prototype` extends.
