# `sulis-business-strategy`

> **Business strategy work, Kind-schema variant.** Drives identity, brand positioning, voice, principles, and strategic foundation through the new Kind-schema workflow.

## What it does

Provides a `business-strategist` agent that drives strategic-foundation work through the four-stage Kind schema (find → generate → evaluate → decide), replacing the three-lens triad model of the legacy outcomes.

At v0.1, two Kinds are wired up:

1. **`BusinessContext`** (entry point) — captures structured business context across 9 domains × 34 questions through conversational intake. Replaces the legacy `business-context-intake` outcome's Domain Expert / Assumption Challenger / Completeness Monitor triad.
2. **`Identity`** (first consumer) — depends on BUSINESS_CONTEXT.md. Articulates the organisation's identity through the Golden Circle. Replaces the legacy `identity-articulation` outcome's Belief Crystallizer / Authenticity Validator / Expression Architect triad.

Sibling Kinds (Brand, ToneOfVoice, Principles, Vision, Strategy, Commercial, GTM) follow once these two validate the pattern.

## How to use it

From a project workspace — run in this order:

```bash
# Step 1 (ALWAYS FIRST): capture business context
/sulis-business-strategy:context

# Step 2 (after BUSINESS_CONTEXT.md exists): articulate identity
/sulis-business-strategy:identity
```

If you invoke `:identity` without `BUSINESS_CONTEXT.md` present, the agent halts cleanly with a prerequisite message and offers to switch to `:context` immediately. No silent degradation.

**BusinessContext** scans your workspace for existing artifacts (transcripts, prior identity / vision / strategy, research, ledger), pre-populates candidate answers from existing content, then drives conversational intake for the gaps. Tags every answer Validated / Assumed / Unknown with provenance. Three modes (greenfield, baseline, progressive) auto-detect from workspace state.

**Identity** consumes BUSINESS_CONTEXT.md (especially Q1–Q4 from the Identity & Team domain), drafts IDENTITY.md following the Golden Circle (WHY → HOW → WHAT), evaluates against the identity rubric (authenticity, distinctiveness, voice, evidence quality), iterates up to three times.

## What it produces

| File | From which Kind | What it covers |
|---|---|---|
| `product/context/BUSINESS_CONTEXT.md` | BusinessContext | 9 domains × 34 questions with V/A/U scoring and SHA-256 provenance. Canonical input for every downstream business-strategy Kind. |
| `product/organization/IDENTITY.md` | Identity | WHY (tension + belief + cause), HOW (3-5 principles with trade-offs), WHAT (primary persona + value proposition), Success Looks Like, Time Horizon, Authenticity Validation, Tone Validation. |
| `find-output/CONTEXT_BRIEF_PACK.md` | BusinessContext | Context the agent gathered before intake (mode, existing artifacts, candidate answers, gaps). |
| `find-output/CONTEXT_VERDICT.md` | BusinessContext | Structured Verdict from BusinessContext evaluate. |
| `find-output/IDENTITY_BRIEF_PACK.md` | Identity | Context the agent gathered before drafting. |
| `find-output/IDENTITY_VERDICT.md` | Identity | Structured Verdict from Identity evaluate. |

## What it doesn't do (yet)

- **No BRAND.md** — `Brand` Kind not built yet.
- **No TONE_OF_VOICE.md** — `ToneOfVoice` Kind not built yet.
- **No PRINCIPLES.md** — `Principles` Kind not built yet.
- **No vision, strategy, commercial, GTM, roadmap.** Those live in the established `sulis-strategy` plugin (legacy triad model) until their Kind variants exist.

## Why this plugin exists

To exercise the new Kind schema against real methodology workloads (business-context intake + identity articulation) and validate that the schema can hold the work the legacy three-lens triads did. The triad's *function* (multi-perspective evaluation + consensus + reasoned routing) is preserved structurally in the evaluate + decide stages; the triad's *mechanism* (three parallel agent lanes) is replaced.

Two Kinds together test the "Kind A depends on Kind B's output" pattern — BusinessContext produces BUSINESS_CONTEXT.md; Identity declares it as a required input via `prerequisite_inputs`. This is the dependency model every future Kind will use.

## Relationship to `sulis-strategy`

The established `sulis-strategy` plugin uses the legacy triad-orchestrated outcomes (vision, strategy, principles, commercial, GTM, roadmap). It still works and produces real artifacts. This plugin (`sulis-business-strategy`) is the **Kind-schema variant** — it exercises the new schema on the same domain.

Both plugins can be installed simultaneously. Choose per skill:

- For business-context intake with the new schema: `/sulis-business-strategy:context`
- For business-context intake with the legacy outcome: run `business-context-intake` via outcome-executor against the studios repo
- For identity work with the new schema: `/sulis-business-strategy:identity`
- For identity work with the legacy outcome: `/sulis-strategy:identity`
- For everything else (vision, strategy, principles, commercial, GTM, roadmap): use `sulis-strategy` until Kind variants exist.

## Status

**v0.1.0 — test fixture.** Two Kinds (BusinessContext + Identity) exercise the schema end-to-end including the cross-Kind dependency pattern. The platform engine in `sulis-ai/platform` currently wires only the find stage (Slice 1); generate / evaluate / decide are declared in the schema and driven manually by the agent until the engine catches up (Slices 2-4).

When the engine wires generate / evaluate / decide, this plugin's agent simplifies — it invokes each Kind via `KindHandler` and the engine runs the four stages. The Kind YAMLs, rubrics, and instance schemas don't change.

## Files

- `agents/business-strategist.md` — the agent definition (drives both Kinds)
- `skills/context/SKILL.md` — user-facing entry point for BusinessContext
- `skills/identity/SKILL.md` — user-facing entry point for Identity
- `references/kinds/BusinessContext.yaml` — Kind 1 (entry point)
- `references/kinds/Identity.yaml` — Kind 2 (depends on BUSINESS_CONTEXT.md)
- `references/kinds/rubrics/business-context-rubric.md` — what evaluate checks for BusinessContext
- `references/kinds/rubrics/identity-rubric.md` — what evaluate checks for Identity
- `references/kinds/schemas/business-context-instance.md` — shape of BUSINESS_CONTEXT.md
- `references/kinds/schemas/identity-instance.md` — shape of IDENTITY.md
- `CLAUDE.md` — local dev notes

## Related

- **`sulis-strategy`** — the legacy business strategy plugin (triad model)
- **`sulis-ai/platform`** — the platform repo where the Kind schema lives (`platform/.specifications/kinds-and-tools/`)
- **`sulis-ai/studios`** — the methodology repo where the business-strategy studio lives (`studios/methodology/studios/business-strategy/`)
