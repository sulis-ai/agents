---
name: draft-architecture
description: "Turns a requirements document into a technical blueprint."
---

# Blueprint — Greenfield Technical Design

When invoked, produce a Technical Design Document and supporting ADRs for a
project, driven by the upstream SRD specification.

If arguments are provided, treat them as the path to the spec folder (e.g.
`/sulis:draft-architecture .specifications/payments-service`). If no path is provided,
use the most recently modified folder in `.specifications/`.

If no SRD specification exists, stop and tell the user — refer them to
`srd:requirements-analyst`. **Do not invent requirements.**

---

## Required Reading (load before drafting)

These standards shape the TDD + the new contract artifacts (step 3.5):

- `../../references/standards/CONTRACT_FIRST_STANDARD.md` — the **data
  contract** seam discipline (two-axis model, three-category error model,
  stubs include error/empty cases, transport binding).
- `../../references/standards/UX_VISUAL_DESIGN_STANDARD.md` — the **visual
  contract** (Identity/Visual/Experience/Governance layers + the agentic-
  interface principles for AI surfaces); produced as a design-time artifact
  per UXD-14.
- `../../references/standards/WP_BACKEND_STANDARD.md` — backend patterns
  the TDD's backend components implement (ports & adapters, repository,
  handler, in-memory adapter first, etc.).
- `../../references/standards/WP_FRONTEND_STANDARD.md` — frontend patterns
  the TDD's user-facing components implement (component tiers, typed client,
  loading/error/empty, design tokens, agentic UX).
- `../../references/standards/WORK_PACKAGE_STANDARD.md` — the `kind:` enum
  (incl. `kind: contract`) and the cross-kind decomposition WP-08.5 that
  `plan-work` will apply to the TDD this skill produces.

---

## Inputs You Read

**Read in this order. Context index first — it constrains everything else.**

| File | Why |
|---|---|
| `.context/{project}/INDEX.md` (sulis-context v0.1.0+) | **Read first.** Authoritative sources to reference (not restate); External ADR Registry's highest ADR number (so new ADRs start at N+1); Known Gaps (your licence to add new artifacts). Apply Respect-Don't-Restate to everything that follows. |
| Authoritative sources listed in the index | Load on demand when their topic is touched by your TDD work |
| `SRD.md` | Functional requirements, use cases, business rules, per-use-case Negative Requirements → Form pillar (and seeds Armor) |
| `NFR.md` | Non-functional requirements → drives Armor pillar + pattern selection |
| `MISUSE_CASES.md` (SRD v1.11.0+) | Abuse cases, misuse flows, **System Response (REQUIRED)** for each → seeds Armor primitives (rate limits, audit logging, replay protection, integrity guards) and shapes the TDD's security boundary |
| `PRIMITIVE_TREE.jsonld` | Structural decomposition of building blocks → component inventory |
| `GLOSSARY.md` | Locked vocabulary from SRD Phase 3.5 Disambiguation Sweep — use preferred terms exactly in the TDD and ADRs |
| `.architecture/{project}/probe-raw/synthesis.json` → `reserved_vocabulary_hint` | YAML kinds in use + universally K8s/Sulis-reserved words. Feeds the Reserved-Vocabulary Sweep at step 7. If the field is missing, the probe is older than v0.9.1 — recommend re-running. |
| `diagrams/*.md` | Sequence, process, data-flow diagrams → integration design |
| `EXPLORATION_JOURNAL.md` `## Deferred to SEA` (if present) | Architecture-and-implementation content parked by SRD mid-session — treat as additional design intent from the user |
| `HANDOVER.md` (if present) | Suggested implementation sequence → may inform WP ordering |
| `HANDOFF_TO_SEA.md` (if present, instead of SRD.md) | SRD took the Early Handover path — user arrived with predominantly technical content. Read it as the sole upstream context; fill business-intent gaps by asking the user, not by inventing. |

Read all of them. If any are missing, list them and ask the user how to
proceed before writing anything.

**Context index is required reading when present.** If `.context/{project}/INDEX.md`
exists and you do not read it, you will produce TDD content that restates or
contradicts existing authoritative sources. The auto-suggest in the agent's Phase 0
check should have either loaded the index or surfaced the "continue without context"
override before you got here — but if you somehow find yourself in blueprint with no
loaded index on a non-trivial codebase, stop and surface that.

**MISUSE_CASES.md is required reading when present.** Each MUC's System Response
becomes Armor input. Skipping it means you write a TDD that addresses the happy
path but not the adversarial path SRD already specified.

---

## Outputs You Write

```
.architecture/{project}/
├── ARCH.yaml
├── TDD.md
└── adrs/
    ├── ADR-001-{slug}.md
    └── ...
```

### `ARCH.yaml`

```yaml
id: ARCH-001
title: Payments Service Architecture
status: designed                 # draft | designed | decomposed | implemented | verified
sourced_from: ../../.specifications/payments-service/SPEC.yaml
created: 2026-05-12
pillars:
  form: covered
  armor: covered
  proof: covered
```

### `TDD.md` — Required Sections

The TDD has a fixed structure. Each section maps to MECE-3 pillars. See
`references/tdd-template.md` for the full template; the headline structure is:

1. **Overview** — one-paragraph summary of what is being designed and why.
2. **Source Specification** — link to `SRD.md`, `NFR.md`, key requirements.
3. **Form — Structural Design**
   - Component inventory (from `PRIMITIVE_TREE.jsonld`)
   - Module boundaries and dependency graph
   - Ports (interfaces in the domain)
   - Adapters (implementations in infrastructure)
   - Composition root layout
4. **Armor — Operational Hardening**
   - External dependency table — every cross-process call lists timeout, retry policy, circuit-breaker config
   - Security boundary — what's authenticated, authorised, encrypted (mTLS, TLS, at-rest)
   - Secrets — where they live, how they rotate
   - Observability — trace coverage, log structure, metrics (RED per operation, USE per resource)
5. **Proof — Verification Protocol**
   - Contract tests per port
   - Integration tests against real adapters (testcontainers, ephemeral DBs)
   - Chaos assertions per resiliency primitive
6. **Trade-offs** — patterns chosen, alternatives rejected, with one-line reasons
7. **Open questions** — anything the SRD does not specify that the architecture needs

### ADRs

Emit one ADR per non-trivial decision. "Non-trivial" means: the decision
affects more than one component, locks in a technology choice, or rejects
a viable alternative.

**ADR numbering (MUST):** If `.context/{project}/INDEX.md` exists and contains
an External ADR Registry with `Highest ADR number: ADR-N`, your new ADRs MUST
start at `ADR-{N+1}`. Reading the index's External ADR Registry section gives
you this number directly. Do not start at ADR-001 unconditionally — that
collides with the existing registry and produces ambiguous references.

**Before writing each ADR, check the External ADR Registry for an existing
ADR on the same topic.** If one exists:

- If your decision **aligns** with the existing ADR: don't write a new ADR.
  Reference the existing one in your TDD instead.
- If your decision **extends** the existing ADR: write a new ADR with
  `extends: external:ADR-NN` in frontmatter, and explain in Context what's
  new.
- If your decision **supersedes** the existing ADR: write a new ADR with
  `supersedes: external:ADR-NN` in frontmatter. Surface the supersession to
  the user before finalising — the team owns its existing decisions, and you
  shouldn't quietly overrule them.

ADR file format:

```markdown
---
id: ADR-023
title: Use PostgreSQL with logical replication for the order store
status: accepted              # proposed | accepted | superseded
date: 2026-05-14
deciders: [iain]
supersedes: external:ADR-007  # optional — when overriding an existing ADR
extends: external:ADR-012     # optional — when extending an existing ADR
---

## Context
{What forced the decision; constraints from NFR/SRD; existing system shape.
If extending or superseding, reference the existing ADR by path.}

## Decision
{One paragraph stating the choice in active voice.}

## Options Considered
- PostgreSQL with logical replication — chosen
- DynamoDB — rejected because {reason}
- MySQL — rejected because {reason}

## Consequences
- Positive: {what becomes easier}
- Negative: {what becomes harder; what new operational concerns appear}
- Neutral: {what stays the same}
```

---

## Workflow

0. **Load the context index (if present).** Read `.context/{project}/INDEX.md` first.
   Parse Authoritative Sources, External ADR Registry, Conventions & Standards,
   Patterns Library, Known Gaps. Hold these in working memory — every subsequent
   step respects what you found. If the index is missing and the codebase has
   signals of existing architecture material, stop and recommend
   `/sulis:discover-context` (the agent's Phase 0 check should have done this
   already — if you got here without an index on a non-trivial codebase, surface
   that).
1. **Discover** — locate the spec folder; read all inputs in the table above; report what's missing. If `HANDOFF_TO_SEA.md` is present and `SRD.md` is absent, read the handoff file first and ask the user for any business intent it doesn't capture before proceeding.
2. **Inventory** — parse `PRIMITIVE_TREE.jsonld` for components. List them. Map each to a TDD section.
3. **Compute SIZING.md (MUST).** Per `references/right-sizing.md`:
   - **If `.architecture/{project}/SIZING.md` already exists and is current**
     (all source artifact mtimes are older than SIZING.md's `Generated`
     timestamp): read it, honour the recorded tier, skip to step 4.
   - **Otherwise**, compute sFPC + ASR + per-pillar coverage:
     - sFPC: count ILF (PRIMITIVE_TREE domain-entity + data-store nodes) +
       EIF (integration nodes) + EI/EO/EQ (use cases classified by whether
       their flow mutates / derives / retrieves)
     - ASR: count NFRs + integrations + MUCs + cross-cutting policies +
       hard data constraints
     - Pillar coverage: from `.context/{project}/INDEX.md` Authoritative
       Sources — judge whether Form, Armor, Proof are fully / partially /
       uncovered for the work in scope
     - Tier: from the table in the standard (take higher of sFPC-tier and
       ASR-tier; promote to XL on multi-bounded-context)
   
   **Announce to the user before writing SIZING.md:**
   
   > "Inputs analysed:
   >
   > - **sFPC ≈ {N}** ({breakdown})
   > - **ASR ≈ {M}** ({breakdown})
   >
   > **Tier: {S|M|L|XL}**. Target TDD ~{range} lines. Expected ADRs {range}.
   >
   > Pillar coverage from context index:
   > - Form: {status} {— sources}
   > - Armor: {status} {— sources}
   > - Proof: {status} {— sources}
   >
   > Proceed, override the tier, or stop?"
   
   Wait for the user response. Record their choice (computed tier accepted,
   or overridden to X). Write `.architecture/{project}/SIZING.md` per the
   schema in `references/right-sizing.md`.
3.5. **Define the contracts (MUST when cross-kind or user-facing).** Before
   pillar design, identify the **producer/consumer seams** in the proposed
   architecture and the **user-facing surfaces**. For each, produce a
   contract artifact as a design-time deliverable — the same way the TDD is.

   **(a) Data contracts** — per
   [`CONTRACT_FIRST_STANDARD.md`](../../references/standards/CONTRACT_FIRST_STANDARD.md).
   For every backend↔frontend seam (or tool↔caller seam) in the TDD, produce
   a schema sketch:
   - **operations** (named units the seam exposes)
   - **input + output types** (named, reusable; not inline-per-endpoint)
   - **the three error categories** (Protocol / Expected / Internal per CF-03)
     mapped to the chosen transport (HTTP statuses / NDJSON event types /
     subprocess exit codes / library exceptions)
   - **example stubs** covering **happy + error + empty** cases (CF-04)
   - **the transport binding** (HTTP/REST + OpenAPI 3.1 for web seams;
     JSON-RPC/MCP for agent tools; subprocess+NDJSON for streaming local
     pipes; library for in-process)

   Write the contract sketch to `.architecture/{project}/contracts/{seam}.md`
   (or `.yaml`/`.json` if you can already commit to OpenAPI/JSON Schema at
   this stage). `plan-work` will emit a `kind: contract` WP from it (WP-08.5)
   so the build conforms.

   **(b) Visual contract (MUST for any user-facing surface)** — per
   [`UX_VISUAL_DESIGN_STANDARD.md`](../../references/standards/UX_VISUAL_DESIGN_STANDARD.md).
   This is a **hard gate** (#45): if the TDD has any user-facing surface, the
   visual contract is mandatory and `plan-work` cannot emit frontend WPs
   without it (the toolchain enforces this — see below). Produce two things:

   **(i) The contract record + mockup.** Cover the four layers' essentials:
   - **Identity** (referenced — not re-articulated here) — point at the
     project's identity artifacts; flag if missing.
   - **Visual** — the token tiers the surface will consume (semantic +
     component tokens, not raw values); brand traits → measurable visual
     parameters; the structural profile (navigation / layout / density /
     elevation).
   - **Experience** — the HIG sections needed (the surface's components +
     their variants/states/focus + the three UI states loading/empty/error);
     accessibility decisions taken at design time (AA contrast on the
     chosen token pairs; keyboard model; colour-independence check); if
     the surface is AI-facing, the agentic-interface principles in play
     (UXD-10: outcome-oriented, human-in-the-loop gates, transparency).
   - **Governance** — provenance label on the artifact.

   **Run the Mobbin inspiration probe FIRST (UXD-15 — gated on MCP
   availability).** Before producing the mockup, search Mobbin for real-world
   patterns matching this surface so the mockup is grounded in what's been
   shipped, not invented in isolation. Strict scope: **structural patterns
   are transferable; visual choices are NOT** — our tokens, type stack, and
   identity stay authoritative (UXD-15).

   1. **Detect availability.** Probe the Mobbin MCP (e.g.
      `mcp__plugin_honest_mobbin__search_screens` if connected via the honest
      plugin, or a sulis-native equivalent). If unavailable or unauthenticated:
      log one line ("Mobbin: MCP unavailable, skipping inspiration probe —
      mockup will proceed without external references."), set
      `inspiration: none` on the visual-contract WP, and continue. **Never
      fabricate references** — no MCP = no `_mobbin-context.md`.
   2. **Query.** Compose a search from the surface description (e.g.
      "settings screen with org switcher") + the change intent. Cap results
      to ~6; keep 2–3 most relevant.
   3. **Capture per reference.** App name, Mobbin URL, 2–4 *structural*
      observations (transferable — section ordering, density, spacing rhythm,
      micro-interaction beats) and the *visual* observations explicitly marked
      NOT transferable (our tokens authoritative).
   4. **Synthesise.** Write a 2–4 line paragraph extracting the cross-cutting
      structural patterns the mockup should consider folding in.
   5. **Worked-example carve-out.** If the project's own design-instance
      `reference/` or `examples/` already covers this surface tightly, log
      "Worked example covers this surface; skipping Mobbin probe" and skip.
   6. **Persist** the probe output to
      `.architecture/{project}/contracts/visual/_mobbin-context.md`. Because
      `.architecture/` travels with the change branch (#42), the research is
      durable and discoverable — `review` can later verify the shipped surface
      honoured the inspiration cited here. The visual-contract WP's
      `inspiration:` frontmatter field cites the relative path so the link
      is explicit.

   **(b.ii) Produce the real-token HTML mockup** at
   `.architecture/{project}/contracts/visual/<surface>.html` — composed
   page(s), the product's actual design-instance tokens (never invented hex),
   and **the webfonts its type tokens reference actually loaded** (L-13: a
   mockup whose fonts don't load passed "tokens match" while the founder saw
   no brand — sign-off is *visual*, not value-equality). The mockup's
   **structure** may reflect the Mobbin synthesis (section ordering, density,
   spacing rhythm); the mockup's **visual identity** stays bound to the
   design instance — never embed Mobbin screenshots and never adopt their
   palettes/type stacks. Note the perceptual delta vs the current surface so
   the founder can see what changes.

   **(b.iii) The visual-contract WP.** Emit a WP with frontmatter:
   ```yaml
   kind: contract
   contract_type: visual          # marks it as the visual-contract WP
   mockup: contracts/visual/<surface>.html
   inspiration: contracts/visual/_mobbin-context.md   # or "none" if MCP unavailable
   signed_off_at:                 # EMPTY until the founder signs off
   provenance: draft              # → production-approved on sign-off
   ```
   `plan-work` makes every `kind: frontend` WP carry `visual_contract: <this
   WP id>` and `dependsOn` it; the WP only reaches `done` once `signed_off_at`
   is set + `provenance: production-approved` (enforced at `wpx-index
   flip-status`). So no frontend WP is dispatchable until the founder has
   signed off the rendered mockup.

   Identity/brand *values* (palette, type, look-and-feel) remain
   founder-owned — if absent, STOP, surface as the first Open Question, and
   route to the design flow rather than inventing them.

   **(c) Single-kind non-visual work + `--prototype` changes are exempt** from
   this step (the gate honours a `prototype: true` WP and a logged
   `visual_contract: exempt — <reason>`).

4. **Select patterns** — for each NFR, pick patterns from `references/architecture-patterns.md`. Surface trade-offs explicitly. Skip pattern selection for any pillar marked "fully covered" in the sizing announcement; reference the authoritative source instead.
5. **Translate misuse cases** — for each MUC in `MISUSE_CASES.md`, translate its `System Response (REQUIRED)` into one or more Armor-pillar primitives in the TDD. Cross-reference: every MUC ID must appear in the TDD's Armor section. See `references/hardening-deltas.md` for the MUC → delta/primitive translation pattern (the same translation applies to greenfield TDD entries).
6. **Cover all three pillars at tier-appropriate depth.** For every component, ensure Form, Armor, and Proof are addressed. Per the sizing decision:
   - Fully covered pillar → one line + reference to the authoritative source
   - Partially covered pillar → section addresses only the gap
   - Uncovered pillar → full tier-sized section per `references/right-sizing.md`
   If you cannot address one pillar for a component, flag it in Open Questions; do not silently skip.
7. **Reserved-Vocabulary Sweep (MUST).** Before naming abstract types, classes, registries, or dispatch keys in the TDD, run this check. It catches polysemy collisions between proposed design vocabulary and infrastructure-coded vocabulary already in use in the repo. The kind/Kind collision (a generative-pipeline abstract sharing a name with the Sulis YAML discriminator) is the canonical failure mode this step exists to prevent.

   a. **Load reserved words.** Read `.architecture/{project}/probe-raw/synthesis.json`'s `reserved_vocabulary_hint` block (emitted by `/sulis:analyse-codebase` v0.9.1+). It contains:
   - `yaml_kinds_in_use` — every value seen in `apiVersion: <x>` / `kind: <y>` pairs across the repo (Sulis kinds, k8s sub-kinds, Argo, Flux). These are reserved because re-using one of these names imports its dispatch shape.
   - `infrastructure_reserved` — universally K8s/Sulis-coded words (`kind`, `apiVersion`, `metadata`, `spec`, `status`, `apply`, `reconcile`, `manifest`, `resource`).
   
   If the hint is missing (older probe output), recompute it on the fly by reading `1_16_deployment.json` directly, or surface the gap and recommend re-running `/sulis:analyse-codebase`.
   
   Also load `GLOSSARY.md` (if present) — its preferred-terms list is already a vocabulary lock.

   b. **List proposed abstracts.** Enumerate every new abstract type, class, registry, or dispatch concept the TDD will introduce. For tier-S this is usually 3-8; for tier-XL it can be 20+.

   c. **Score each proposed abstract against the reserved set.** For every proposed abstract `P`:
   - If `P` does not appear in `yaml_kinds_in_use` or `infrastructure_reserved` and is not flagged in GLOSSARY: proceed.
   - If `P` matches (case-insensitive) any reserved word: trigger the lifecycle check below.

   d. **4-cell lifecycle check.** For each colliding name, fill this table — for both the existing manifest resource and the proposed abstract:

   | Question | Manifest resource `kind: X` | Proposed abstract `X` |
   |---|---|---|
   | Does it persist (DB/repo-stored)? | yes/no | yes/no |
   | Does it converge (drift-reconciled)? | yes/no | yes/no |
   | Does it have a natural key? | yes/no | yes/no |
   | What does `apply -f X.yaml` mean? | bring resource into desired state / invoke a pipeline / N/A | … |
   | Delete semantics? | convergent / explicit-only / N/A | … |

   e. **Decision rule (MUST):**
   - **All five cells match** → proceed; the shared name reflects shared semantics. Note in the TDD that the dispatch is intentionally shared.
   - **Any cell diverges** → BLOCK. The agent MUST do one of:
     1. **Rename the proposed abstract.** Pick a name that anchors on what's distinct (e.g. Kind → Recipe because the abstract is "instructions for producing", not "type of thing"). Update GLOSSARY.md with a "Where else this word appears" note on the old term.
     2. **Write an ADR justifying the shared dispatch.** Cite the lifecycle differences explicitly; explain why the runtime path is genuinely the same despite different semantics. This is the rare case (e.g. when the new abstract is genuinely a new manifest resource).
   - **Do not proceed to TDD draft until the table is filled and the decision recorded** for every collision.

   f. **Report the sweep result in the TDD's "Open Questions" or "Design Decisions" section.** Even when no collisions were found, the report demonstrates the check ran: "Reserved-Vocabulary Sweep: {N} proposed abstracts checked against {M} reserved words; no collisions found."

8. **Draft TDD** — write `TDD.md` following the template. Use GLOSSARY.md's preferred terms exactly. Apply Respect-Don't-Restate throughout.
9. **Extract ADRs** — for each non-trivial decision in the TDD, factor it out into an ADR file. The TDD references the ADR by ID. **Before writing each ADR**, check the External ADR Registry — if an existing ADR covers the same decision, reference it instead. New ADR numbering starts at one past the registry's highest. Do not write ADRs to fill a quota.
10. **Sizing self-check (MUST).** Before writing, review your draft against the tier targets:
    - Total TDD length > 1.5× tier target? → write a "Why is this big?" paragraph or refactor
    - Any section restates content from an authoritative source? → refactor to a reference
    - ADR count > tier maximum? → write an "ADR rationale" paragraph or remove the marginal ones
    - Any pillar marked "fully covered" but actually contains content? → refactor to reference-only
11. **Write `ARCH.yaml`** — link back to the source SPEC.
12. **Append a Sizing Report appendix to TDD.md (MUST).** Add this as the last
    section, cross-referencing the full SIZING.md:

    ```markdown
    ## Sizing Report
    
    See `SIZING.md` for the full sFPC + ASR breakdown. Highlights:
    
    - Tier: {S/M/L/XL} ({computed | user-overridden})
    - TDD length: {N} lines (target: {range})
    - ADRs produced: {N} (target: {range})
    - Pillar coverage applied: Form={covered|gap-filled|full}; Armor={...}; Proof={...}
    - Authoritative sources referenced: {count, listed in SIZING.md}
    - Sections that referenced rather than restated: {list}
    - Circuit breakers triggered: {none | list}
    - Reserved-Vocabulary Sweep: {N} abstracts checked / {M} collisions / {K} renames / {L} shared-dispatch ADRs
    ```
    
    Full breakdown stays in SIZING.md to avoid duplication.
13. **Report** — summarise what was produced, what patterns were chosen, what open questions remain, which misuse cases drove which Armor primitives, and the Sizing Report headlines.

After the blueprint is accepted, the user typically runs `/sulis:plan-work`
next.

---

## Adapting Depth

Depth is governed primarily by the tier detected in step 3 of the workflow.
The modes below are user-facing overrides — they apply on top of tier
detection, not instead of it.

- **Quick** ("draft a TDD shape") — produce a tier-skeleton only. Each
  pillar gets one paragraph + bullet placeholders. Useful for early
  alignment before full detail. ~30 minutes.
- **Full** (default) — complete TDD sized to the detected tier and
  addressable scope. ADRs for genuinely non-trivial decisions (not as a
  quota).
- **Audit-mode** ("compare proposed TDD to MECE-3") — read an existing TDD,
  score it against the three pillars, return a gap list. No new TDD
  produced.
- **Manual tier override** — accepted at step 3 of the workflow. Up-tier
  for growth-projection / junior-team / regulatory contexts; down-tier for
  spike / POC / pair-programmed contexts. Recorded in the Sizing Report.

See `references/right-sizing.md` for the full sizing standard, including
when to up- or down-tier manually.

---

## Gotchas

- **No SRD, no TDD — except for Early Handover.** If `SRD.md` does not exist and `HANDOFF_TO_SEA.md` does not exist, the skill blocks. Refer the user back to `srd:requirements-analyst`. Do not invent requirements. If `HANDOFF_TO_SEA.md` exists, you may proceed with a lightweight TDD provided you record the absent SRD as an explicit gap in the first ADR.
- **No NFR, no Armor.** The NFRs determine which resiliency and security patterns are needed. If `NFR.md` is missing or thin, surface that as the first Open Question — do not pick patterns by guesswork.
- **No MISUSE_CASES.md when one is expected.** If `SRD.md` exists but `MISUSE_CASES.md` does not, the SRD was produced by a pre-v1.11.0 facilitation or the adversarial sweep was skipped. Note this in the TDD's Open Questions: "Adversarial spec absent — Armor primitives derived from NFR only. Recommend the user re-run `requirements-analyst` for the misuse-case sweep, or accept the gap."
- **One ADR per decision.** Resist bundling. "Why we chose PostgreSQL" and "Why we chose logical replication" are two ADRs if both decisions had viable alternatives.
- **TDD is design, not implementation.** No code in the TDD beyond illustrative type signatures. Implementation lives in Work Packages.
- **Cross-reference the PRIMITIVE_TREE.** Every node in the tree should map to at least one TDD component. Nodes that don't map are gaps — flag them.
- **Cross-reference MISUSE_CASES.md.** Every MUC should map to at least one Armor primitive in the TDD. MUCs that don't map are gaps — flag them.
- **Use the locked vocabulary.** Use only the preferred terms from `GLOSSARY.md` — do not introduce synonyms or use forms the glossary marks as deprecated.
- **Reserved-Vocabulary Sweep is non-optional.** Step 7 catches polysemy collisions between proposed design vocabulary and YAML kind values already used as dispatch keys in the project's infrastructure. The canonical failure it prevents: a new abstract called `Kind` for content generation that shares a name with the Sulis YAML discriminator (`apiVersion: sulis.io/v1, kind: Workload`) — same dispatch shape, opposite lifecycle (one persists and converges, the other is a one-shot pipeline invocation). The sweep table forces lifecycle differences visible *before* TDD authorship, when renames cost minutes rather than days. If the probe synthesis is missing the `reserved_vocabulary_hint` block, re-run `/sulis:analyse-codebase` (v0.9.1+) before drafting.
- **Respect, Don't Restate (MUST).** If `.context/{project}/INDEX.md` exists and lists authoritative sources, your TDD references those sources for topics they already cover — it does not reproduce or paraphrase their content. The most common SEA failure mode is generating a 600+ line TDD that re-derives Clean Architecture, then writing 10 ADRs that overlap with the project's existing registry. The context index is the antidote. Read it, respect it, surface contradictions instead of silently overruling them.
- **New ADRs start past the highest external ADR.** Check the External ADR Registry in the context index. If it shows `Highest ADR number: ADR-22`, your first new ADR is ADR-23. Starting at ADR-1 collides with the existing registry and creates ambiguous references.
- **Size to addressable scope, not to the template (MUST).** The "Full" TDD template is a maximum, not a target. A 4-NFR change does not deserve a 600-line TDD. Compute the tier (S/M/L/XL) in step 3 of the workflow, then *shrink* the target by per-pillar coverage from the context index. A tier-L project with rich existing coverage may justifiably produce a 200-line TDD. See `references/right-sizing.md`. The Sizing Report you append to TDD.md makes this calibration visible.
- **ADRs are not a quota.** They emerge when a decision affects more than one component, locks a technology choice, or rejects a viable alternative — AND no existing ADR covers it. A tier-L project where the team has already made all the major decisions may justifiably produce zero new ADRs. Resist the urge to write ADRs for "we used X" when X was the obvious choice.
- **Chaos tests need a named NFR or MUC.** Each chaos test in the Proof section must defend a specific NFR or MUC. A chaos test for "what happens when the cache is down" without a corresponding NFR or MUC is testing imagination, not requirements — drop it.

---

## See Also

- `references/tdd-template.md` — full TDD section structure with prompts
- `references/architecture-patterns.md` — pattern catalogue (plugin root)
- `references/mece-3-architecture.md` — the three pillars (plugin root)
