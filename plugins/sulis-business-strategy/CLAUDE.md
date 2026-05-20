# Business Strategy (Kind-schema variant) — Local dev notes

This plugin is the **Kind-schema variant** of the business-strategy studio work. It coexists with the established `sulis-strategy` plugin (which uses the legacy triad-orchestrated outcome model). The two are complementary during the migration window.

## What's inside

```
sulis-business-strategy/
├── .claude-plugin/plugin.json
├── agents/business-strategist.md           # The manual Kind executor (drives both Kinds)
├── skills/
│   ├── context/SKILL.md                    # /sulis-business-strategy:context  (entry point — run first)
│   └── identity/SKILL.md                   # /sulis-business-strategy:identity (depends on context)
├── references/kinds/
│   ├── BusinessContext.yaml                # Kind 1: entry-point intake → BUSINESS_CONTEXT.md
│   ├── Identity.yaml                       # Kind 2: identity articulation → IDENTITY.md (depends on BUSINESS_CONTEXT.md)
│   ├── rubrics/
│   │   ├── business-context-rubric.md      # What evaluate checks for BusinessContext
│   │   └── identity-rubric.md              # What evaluate checks for Identity
│   └── schemas/
│       ├── business-context-instance.md    # Shape of BUSINESS_CONTEXT.md
│       └── identity-instance.md            # Shape of IDENTITY.md
├── CLAUDE.md                               # (this file)
└── README.md
```

## The Kind sequence

Two Kinds at v0.1, run in order:

1. **`BusinessContext`** (entry point) — captures structured business context across 9 domains × 34 questions through conversational intake. Produces `product/context/BUSINESS_CONTEXT.md`. Replaces the legacy `business-context-intake` outcome's Domain Expert / Assumption Challenger / Completeness Monitor triad.
2. **`Identity`** (first consumer) — depends on `BUSINESS_CONTEXT.md`. Produces `product/organization/IDENTITY.md` through the Golden Circle (WHY → HOW → WHAT). Replaces the legacy `identity-articulation` outcome's Belief Crystallizer / Authenticity Validator / Expression Architect triad.

**Prerequisite enforcement:** `Identity` halts cleanly if `BUSINESS_CONTEXT.md` is missing, directing the founder to run `:context` first. No silent degradation.

## How the manual Kind run works

The platform engine (in `sulis-ai/platform`) currently wires only the find stage of the Kind schema (Slice 1). Generate, evaluate, and decide are declared in the schema but not yet executable by the engine.

To exercise the schema end-to-end **today**, the business-strategist agent walks the four stages of each Kind manually. The same four-stage pattern applies to both:

1. **find** — agent reads the Kind YAML's `spec.find.inputs_to_scan`, gathers context per the declared globs, synthesises a BRIEF_PACK.md within the 8000-token budget. For BusinessContext: also computes SHA-256 hashes for existing artifacts and identifies candidate answers vs. true gaps. For Identity: pre-checks BUSINESS_CONTEXT.md exists (halts if missing).
2. **generate** — agent reads BRIEF_PACK + instance schema + constraints. For BusinessContext: drives the 9-domain × 34-question conversational intake with V/A/U scoring + provenance; produces BUSINESS_CONTEXT.md. For Identity: drafts IDENTITY.md following Golden Circle (WHY → HOW → WHAT) holding to the constraints.
3. **evaluate** — agent reads the rubric, runs each criterion against the produced artifact, emits a structured Verdict.
4. **decide** — agent reads the Verdict, routes per `spec.decide.reason_class_routing`. On `pass`, commits. On `retry`, increments the iteration counter and re-runs the relevant stage. On `stop`, surfaces honestly.

This is the **manual phase** of the Kind-schema migration. When the engine wires generate / evaluate / decide:

- The agent's system prompt simplifies — it stops walking stages by hand.
- It invokes the Kind via `mcp__github__get_file_contents` to read the Kind YAML and `KindHandler` (when available) to dispatch.
- The Kind YAML, rubric, and instance schema do NOT change — they're already conformant to the schema as it will be wired.

## How identity work changes vs. the legacy outcome

| Aspect | Legacy `identity-articulation` outcome | New `Identity` Kind |
|---|---|---|
| Lenses | 3-lens triad (parallel) | Single evaluate stage with rubric (sequential) |
| Multi-artifact output | 3 files (IDENTITY + BRAND + TONE_OF_VOICE), cross-validated at end | 1 unified IDENTITY.md; brand and tone are sibling Kinds (not yet built) |
| Dual mode (creation / extraction) | Two separate process flows in OUTCOME.md | Single Kind; find stage adapts to input availability; mode surfaced in BRIEF_PACK |
| Verification spiral | C-07 STANDARD_TIER spiral on top of the outcome | Built into decide stage (`max_iterations: 3`, structured Verdict, reason-class routing) |
| Iteration cap | C-07 max 3 | `spec.max_iterations: 3` (default; platform cap 10) |
| Standards binding | Declared in OUTCOME.md (6 mandatory + 2 cross-cutting) | Encoded as rubric criteria + generate constraints |

## Studio context fetch (when needed)

The agent fetches the studio's standards and vocabulary from `sulis-ai/studios` via GitHub MCP:

```
mcp__github__get_file_contents(owner="sulis-ai", repo="studios", path="methodology/studios/business-strategy/FUNCTION.md", ref={ref})
mcp__github__get_file_contents(owner="sulis-ai", repo="studios", path="methodology/studios/business-strategy/STANDARDS.md", ref={ref})
mcp__github__get_file_contents(owner="sulis-ai", repo="studios", path="methodology/studios/business-strategy/VOCABULARY.md", ref={ref})
```

Where `{ref}` comes from `ofm-bindings.yaml` `methodology.ref` (default: `main`).

## Future Kinds (not yet built)

Once BusinessContext + Identity validate the pattern, sibling Kinds will follow:

- **`Brand`** — produces `product/organization/BRAND.md` with positioning, brand essence, distinctive assets per Romaniuk's triangle.
- **`ToneOfVoice`** — produces `product/organization/TONE_OF_VOICE.md`.
- **`Principles`** — produces `product/organization/PRINCIPLES.md` with codified decision rules.
- **`Vision`** — produces `product/offerings/primary/VISION.md`.
- **`Strategy`** — produces `product/offerings/primary/STRATEGY.md` with H1/H2 bets.
- **`Commercial`** — produces `product/offerings/primary/COMMERCIAL.md` with pricing tiers and unit economics.
- **`GTM`** — produces `product/offerings/primary/GTM.md` with channel and motion strategy.

Each will live as a sibling Kind YAML in `references/kinds/`, with its own rubric and instance schema. Each declares BUSINESS_CONTEXT.md as a required input via `prerequisite_inputs`. The business-strategist agent's prompt extends to drive each.

## Local testing

To exercise the plugin in a workspace:

```bash
# Step 1 (ALWAYS FIRST): capture business context
claude --plugin-dir /Users/iain/Documents/repos/agents/plugins/sulis-business-strategy
/sulis-business-strategy:context

# Step 2 (after BUSINESS_CONTEXT.md exists): articulate identity
/sulis-business-strategy:identity
```

If you invoke `:identity` without `BUSINESS_CONTEXT.md` present, the agent halts cleanly with a prerequisite message — no silent degradation. The agent will offer to switch to `:context` immediately.

For repeat testing across the same workspace, `:context` in **progressive mode** (when valid provenance hashes exist) detects what's changed and drives intake only on diffs — fast iteration.

## Validation criteria for v0.1

The test is successful if:

1. Both Kind YAMLs (BusinessContext, Identity) parse as conformant to the schema (manifest engine YAML parse-clean check).
2. **BusinessContext run:** find stage produces CONTEXT_BRIEF_PACK.md within budget against a real project; mode detection (greenfield / baseline / progressive) is deterministic from on-disk state; generate produces BUSINESS_CONTEXT.md with V/A/U scoring + provenance frontmatter; evaluate emits a structured Verdict; decide routes cleanly.
3. **Identity run:** prerequisite check halts cleanly when BUSINESS_CONTEXT.md is missing; with BUSINESS_CONTEXT.md present, find produces IDENTITY_BRIEF_PACK.md; generate produces IDENTITY.md following Golden Circle; evaluate runs the rubric; decide routes.
4. **Two-Kind sequence:** running `:context` followed by `:identity` produces both artifacts cleanly; the Identity run's find stage successfully consumes BUSINESS_CONTEXT.md (B-06 protocol — candidate answers from BUSINESS_CONTEXT.md surface as confirmation hypotheses, not re-asked questions).
5. Iterations terminate cleanly for both Kinds (`pass`, blocking `stop`, or `stopped_by_iteration_exhausted`).
6. The agent's plain-English narration through both runs is followable by a non-technical founder.
6. The agent's plain-English narration through the run is followable by a non-technical founder.

## Promotion path

When v0.1 validates:

- Move `references/kinds/Identity.yaml` to `studios/methodology/studios/business-strategy/kinds/Identity.yaml` (canonical location).
- Move the rubric and instance schema to `studios/methodology/studios/business-strategy/kinds/rubrics/` and `.../schemas/`.
- Update the plugin agent to fetch the Kind YAML from studios via GitHub MCP instead of reading the local file.
- Bump plugin version to v0.2.0.
- Start writing sibling Kinds (Brand, ToneOfVoice, Principles).
