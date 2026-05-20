---
name: identity
description: >
  Discover, articulate, or evolve the organisation's identity (WHY, HOW, WHAT)
  using the Kind-schema workflow. Runs the four-stage Identity Kind manually
  (find → generate → evaluate → decide) via the business-strategist agent.
  Produces product/organization/IDENTITY.md.
user_invocable: true
---

# Identity Skill

Discovers, articulates, or evolves the organisation's identity using the new Kind-schema workflow. The legacy three-lens triad (Belief Crystallizer / Authenticity Validator / Expression Architect) is replaced by a single evaluate stage with a rubric that encodes what the three lenses collectively checked.

## What this produces

The canonical artifact:

**`product/organization/IDENTITY.md`** — the identity statement covering:
- WHY: tension, belief, cause
- HOW: 3-5 core principles, each with trade-off
- WHAT: primary persona, value proposition
- Success Looks Like, Time Horizon
- Authenticity and Tone validation tables

Plus three supporting artifacts at `find-output/`:

- **`IDENTITY_BRIEF_PACK.md`** — the context the agent gathered before drafting.
- **`CONVERSATION_TRACE.md`** — the agent's audit log of how the conversation actually unfolded: which phase, which turn, what was asked, what was captured. Read this if you want to verify the agent followed the diverge-then-converge rhythm rather than form-walking. Includes a Phase B self-check where the agent verifies its own narrative against the Claude Code session log.
- **`IDENTITY_VERDICT.md`** — the structured Verdict from the evaluation stage (pass / retry / stop with rationale).

## How to invoke

Run the skill via the `business-strategist` agent. The skill is the user-facing entry point; the agent does the four-stage Kind run.

```
/sulis-business-strategy:identity
```

## What this feels like

**This is a conversation, not a fill-in template.** The agent opens hypothesis-first — usually with a recurring thread it's picked up from your transcripts or business context ("the thread that jumps out is X — is that the tension that drives this?"). You confirm, contradict, or extend. The agent follows what you're energised about, asks "what would have to be true for that to work?" rather than "next question," and listens for tension, belief, and cause as they emerge across multiple turns of dialogue. Reflection checkpoints mirror back what's been heard every few turns.

The Golden Circle (WHY → HOW → WHAT) is the **output shape** — what IDENTITY.md ends up covering. It's NOT a script the agent runs through. Phase A diverges on WHY until tension / belief / cause stop shifting. Phase B converges to a hypothesis and runs the competitor substitution test inline. Phase C moves to HOW with one trade-off question per principle ("what does this rule out?"). Phase D synthesises WHAT and drafts IDENTITY.md for your review.

You can stop, redirect, or push back at any point. The agent halts cleanly if BUSINESS_CONTEXT.md isn't present — run `/sulis-business-strategy:context` first.

## What happens when you run it

1. **Prerequisite check.** Agent verifies `product/context/BUSINESS_CONTEXT.md` exists. If missing, halts with a clean prerequisite message — no silent degradation.
2. **Context gathering (find stage).** Agent reads your business context, prior identity if it exists, vision/strategy/anti-goals, personas, founder transcripts, and competitor research. Synthesises a brief pack. Surfaces the mode (creation / evolution / extraction).
3. **Conversation + drafting (generate stage) — diverge then converge.** Phase A: divergent on WHY (hypothesis-first, follow threads, reflect every 3-4 turns). Phase B: convergent — restate WHY as hypothesis, iterate up to 3 passes, run competitor substitution test inline. Phase C: HOW — trade-off question per principle, cap at 5. Phase D: WHAT + draft. The output is IDENTITY.md held to MECE, falsifiability, zero hyperbole, evidence-to-claim ratio.
4. **Evaluation (evaluate stage).** Applies the identity rubric — authenticity, falsifiability, distinctiveness, voice, evidence quality — and emits a structured Verdict.
5. **Decision (decide stage).** On pass, commits IDENTITY.md. On retry, refines and re-runs the relevant stage. On stop (blocking criterion or iteration exhaustion), surfaces why and stops cleanly.

Up to 3 iterations by default. You can intervene at any stage.

## When to use this

- **Creation mode** — no prior identity. The skill discovers it from founder conversations and existing materials.
- **Evolution mode** — prior identity exists. The skill evolves it based on new context, surfacing drift and proposing revisions.
- **Extraction mode** — extensive prior materials exist (older docs, prior strategy work) but the identity has never been codified. The skill extracts it from the materials.

The skill auto-detects the mode from the workspace state.

## When NOT to use this

- You only want to refresh the tone of voice or brand positioning. Those will live in sibling Kinds (`ToneOfVoice`, `Brand`) once they exist. For now, the legacy `sulis-strategy:vision` and related skills still cover that work.
- You want to skip the rubric and write IDENTITY.md by hand. That's fine — the rubric is opt-in via this skill.

## Status

**v0.1 — test fixture.** This skill exercises the Kind-schema migration end-to-end. The Identity Kind itself is at `references/kinds/Identity.yaml`; the rubric and instance schema live alongside. When the platform engine wires generate/evaluate/decide stages natively (Slices 2-4 of the Kind compiler), this skill simplifies — the agent will invoke the Kind via `KindHandler` and the engine will run all four stages.

## Related

- **`sulis-strategy:identity`** — the legacy triad-orchestrated identity work. Use if you want the established outcome path.
- **`sulis-strategy:vision`**, **`:strategy`**, **`:principles`** — strategic foundation work in the legacy model.
- **The Kind YAML:** `references/kinds/Identity.yaml`
- **The rubric:** `references/kinds/rubrics/identity-rubric.md`
- **The instance schema:** `references/kinds/schemas/identity-instance.md`
