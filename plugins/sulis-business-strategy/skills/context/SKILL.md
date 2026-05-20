---
name: context
description: >
  Capture structured business context across 9 domains (34 questions) through
  conversational intake. Runs the four-stage BusinessContext Kind manually
  (find → generate → evaluate → decide) via the business-strategist agent.
  Produces product/context/BUSINESS_CONTEXT.md — the canonical input for every
  downstream business-strategy Kind (Identity, Vision, Strategy, Brand, etc.).
user_invocable: true
---

# Business Context Skill

Captures structured business context across nine domains through conversational intake, with V/A/U scoring (Validated / Assumed / Unknown) and SHA-256 provenance tracking. The output, `BUSINESS_CONTEXT.md`, is the canonical input for every downstream business-strategy Kind.

Replaces the legacy three-lens triad (Domain Expert / Assumption Challenger / Completeness Monitor) with a single evaluate stage and rubric — the rubric encodes what the three lenses collectively checked.

## What this produces

The canonical artifact:

**`product/context/BUSINESS_CONTEXT.md`** — covering:

- **Identity & Team** (5 questions) — why the organisation exists, the core tension, principles, brand identity, team fit
- **Problem & Market** (4 questions) — the specific problem, evidence, market size, anti-goals
- **Solution & Product** (4 questions) — what the product does, value prop, development stage, strategic bets
- **Customers** (3 questions) — segments and JTBD, user journeys, traction
- **Business Model** (4 questions) — pricing, unit economics, tier structure, partnerships
- **Competition** (3 questions) — top competitors, defensible advantage, category
- **Go-to-Market** (4 questions) — channels, sales motion, activation, retention
- **Technology & Deployment** (4 questions) — stack, security, deployment, observability
- **Risks** (3 questions) — top risks, pivot triggers, runway

Each answer is tagged Validated (concrete evidence), Assumed (defensible hypothesis), Unknown (acknowledged gap), or Skipped (with rationale). Assumed answers in load-bearing domains include a validation path. SHA-256 hashes track provenance from input artifacts.

Plus three supporting artifacts at `find-output/`:

- **`CONTEXT_BRIEF_PACK.md`** — the context the agent gathered from your workspace before intake (mode, existing artifacts, candidate answers, gaps).
- **`CONVERSATION_TRACE.md`** — the agent's audit log of how the conversation actually unfolded: which phase, which turn, what was asked, what was captured. Read this if you want to verify the agent followed the diverge-then-converge rhythm rather than form-walking. Includes a Phase B self-check where the agent verifies its own narrative against the Claude Code session log.
- **`CONTEXT_VERDICT.md`** — the structured Verdict from the evaluation stage (pass / retry / stop with rationale).

## How to invoke

```
/sulis-business-strategy:context
```

## What this feels like

**This is a conversation, not a form.** The agent opens with the broadest possible question — typically "what are you building, and why now?" (or a hypothesis drawn from your existing materials if any exist). You answer freely, in your own language, following whatever thread feels alive. The agent listens, captures across multiple domains as you talk (a single rich answer often covers 3-4 domains at once), reflects back every few turns to make sure it's hearing you right, and only after the conversation has saturated does it check for gaps in specific domains and ask targeted follow-ups.

The 9 domains × 34 questions is the **coverage target** for the output — what BUSINESS_CONTEXT.md ends up covering. It's NOT a script the agent reads to you. You should never hear "next question, Q5" or "we still need to cover domain 7." If you do, push back — that's form mode, not conversation mode.

If you have existing materials (transcripts, prior identity / strategy docs, a ledger), the agent reads them first and surfaces candidates as hypotheses to confirm or correct — editing is faster than creating from scratch.

## What happens when you run it

1. **Context scan (find stage).** The agent scans your workspace for existing context artifacts (prior BUSINESS_CONTEXT.md, INTAKE_RESPONSES.md, identity / vision / strategy artifacts, transcripts, research, ledger entries, architecture docs). Determines mode (greenfield / baseline / progressive). Computes SHA-256 hashes for any existing artifacts. Identifies candidate answers from existing content vs. true gaps that need conversational intake.
2. **Conversational intake (generate stage) — diverge then converge.** Phase A: divergent. Agent opens with the broadest thread, follows where you lead, captures answers across multiple domains as they arise, reflects every 3-4 turns. Phase B: saturation check. Once the last few turns stop adding new concepts, agent surfaces the coverage map and asks whether to keep exploring or pin down the lighter areas. Phase C: convergent. Targeted gap questions only. Phase D: consolidation. Every answer is tagged internally as Validated / Assumed / Unknown / Skipped with source attribution.
3. **Evaluation (evaluate stage).** Applies the business-context rubric — coverage (all 9 domains addressed, ≥70% question coverage), defensibility (provenance on Validated, rationale on Assumed), domain coherence (no internal contradictions, no drift from existing artifacts), boundary compliance (no strategic prescription). Emits a structured Verdict.
4. **Decision (decide stage).** On pass, commits BUSINESS_CONTEXT.md with provenance frontmatter. On retry (content_deficient), re-questions weak domains. On retry (context_deficient), re-scans for missed artifacts. On stop, surfaces why and stops cleanly — partial context with explicit gaps is better than fabricated answers.

Up to 3 iterations by default. Expect 30-60 minutes for a fresh greenfield capture; 10-20 for baseline refresh; 5-15 for progressive updates.

## When to use this

**Always run this first** before any other business-strategy Kind. Every downstream Kind (Identity, Vision, Strategy, Brand, Commercial, GTM) declares BUSINESS_CONTEXT.md as a required input.

Three modes auto-detect:

- **Greenfield** — no prior BUSINESS_CONTEXT.md. Full conversational intake.
- **Baseline** — BUSINESS_CONTEXT.md exists but no provenance hashes (legacy outcome run, or hand-drafted). Computes hashes, surfaces any drift, refreshes weak answers.
- **Progressive** — BUSINESS_CONTEXT.md exists with valid provenance. Detects what's changed since last run via hash diff, drives intake only on changed/new content, enumerates downstream artifacts that may need propagation.

## What this is NOT

- **Not strategic recommendation.** This Kind captures WHAT the founder knows. It does NOT prescribe positioning, pricing, identity, or GTM. Those are downstream Kinds. (Boundary B1 in the rubric blocks prescription drift.)
- **Not a form.** It's a guided dialogue. The agent will surface candidates from existing artifacts, ask only when genuine information is missing, and respect explicit Skip with rationale ("pre-commercial, no pricing yet").
- **Not exhaustive in one pass.** Realistic context-capture takes 30-60 minutes for greenfield, 10-20 minutes for baseline refresh, 5-15 minutes for progressive. The Kind supports incremental capture across multiple sessions (progressive mode).

## When NOT to use this

- You already have a current, hash-tracked BUSINESS_CONTEXT.md and nothing has changed since last run. The agent will detect this in find and recommend skipping intake.
- You want to articulate identity, vision, strategy, brand, pricing, or GTM. Those have their own Kinds (Identity Kind is the first one wired up; siblings follow).

## Status

**v0.1 — test fixture.** This skill exercises the Kind-schema migration for the entry-point intake outcome. The legacy `business-context-intake` outcome at `methodology/outcomes/utility/business-context-intake/` in studios remains available via the outcome-executor path for direct use; this Kind is the schema-aligned replacement.

The conversational generate stage validates the most novel pattern in the schema (LLM-driven multi-turn intake) against a real outcome that already does this in the legacy model.

## Related

- **`/sulis-business-strategy:identity`** — runs after this; consumes BUSINESS_CONTEXT.md to produce IDENTITY.md
- **The Kind YAML:** `references/kinds/BusinessContext.yaml`
- **The rubric:** `references/kinds/rubrics/business-context-rubric.md`
- **The instance schema:** `references/kinds/schemas/business-context-instance.md`
- **Legacy outcome:** `methodology/outcomes/utility/business-context-intake/` in `sulis-ai/studios`
- **B-06 protocol** — downstream Kinds read-before-ask using BUSINESS_CONTEXT.md as the primary context
