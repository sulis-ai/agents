# Integration Change Review Prompt

**Version:** 0.1.0
**Date:** 2026-05-21
**Status:** Reusable prompt template + methodology
**Standards applied:** Critical Thinking Standard (all 13 principles)
**Audience:** Agents reviewing a proposed change to a system that other systems
integrate with, to propose downstream updates

---

## What this prompt does

Run this when a change is proposed to **System A** that other systems
(**System B, C, D, …**) depend on, and you need to evaluate the downstream
impact and propose specific updates to each affected system.

**Outputs:**

1. **Per-integration impact assessment** — what each dependent system needs to
   know or change
2. **Recommended updates** — concrete changes per integration, with confidence
   tier
3. **Falsification criteria** — what would change the recommendation
4. **Blindspot register** — what we don't know

The methodology is CTS-driven. Every conclusion is grounded in CTS principles,
not in the reviewer's hunches.

---

## Inputs (what the prompt needs)

Before starting, the invoker provides:

| Input | Required | Description |
|---|---|---|
| **Proposed change** | MUST | What is changing. Be specific — "we're renaming `pipelineRun` to `pipeline_execute`", not "we're improving the API." |
| **Source system** | MUST | The system being changed. e.g., "wpx-pipeline v0.12.0" |
| **Motivation** | SHOULD | Why this change is being made. The motivation will be probed in BI step. |
| **List of integrated systems** | MAY | If known; otherwise the prompt enumerates them as Step 1. |
| **Target completion date** | MAY | Bounds the urgency of cross-team coordination. |
| **Reversibility** | MAY | Can this change be undone? How easily? Bounds the AT pass. |

If the invoker doesn't have one or more of these, the prompt's Step 1 surfaces
the missing context and either fills it in (via investigation) or pauses with
an explicit ask.

---

## The prompt

```
You are reviewing a proposed change to {SOURCE_SYSTEM} and proposing downstream
updates to integrated systems. Apply the Critical Thinking Standard.

## The change
{PROPOSED_CHANGE}

## Motivation
{MOTIVATION}

## Known integrations
{LIST_OF_INTEGRATIONS or "Enumerate as Step 1"}

## Your task

Run the following steps. Each step produces explicit output. Do not skip steps.
If a step requires information you don't have, surface that as an explicit ask
rather than guessing.

### Step 1 — Enumerate integrations (OI — outside-in)

Start from the consumers, not from the source system. Ask:

- What systems CALL into {SOURCE_SYSTEM}? Direct callers.
- What systems READ {SOURCE_SYSTEM}'s output? Indirect consumers — anything
  that parses logs, reads emitted files, watches state.
- What systems SHARE STATE with {SOURCE_SYSTEM}? Filesystem, database, queue,
  cache.
- What systems are DOWNSTREAM in a pipeline that includes {SOURCE_SYSTEM}?
- What systems DOCUMENT or CITE {SOURCE_SYSTEM}? Standards files, READMEs,
  other plugin manifests.
- What agents / users INVOKE {SOURCE_SYSTEM} interactively?

For each integration, capture:
- Integration name + path/location
- Integration type (caller / consumer / shared state / downstream / docs / agent)
- Coupling strength (tight if a contract change breaks it; loose if it
  adapts gracefully; informational if it just references)

Output: a numbered list of integrations.

### Step 2 — Per-integration impact (PG — primitive grounding)

For each integration from Step 1, identify the PRIMITIVE that the integration
depends on:

- Operation signature (method name, parameters, return shape)
- Error envelope (specific error code or class the consumer catches)
- Output format (JSON shape, file location, filename pattern, exit code)
- Behaviour (idempotency guarantee, ordering, retries)
- Documentation (a section the integration cites)

For each primitive, state:
- Is this primitive affected by the proposed change? YES / NO / UNCLEAR
- If YES, how (renamed / removed / added / behaviour changed)
- If UNCLEAR, what investigation would resolve it

If an integration depends on MULTIPLE primitives, list each separately.

Output: a per-integration table of primitive impacts.

### Step 3 — Balanced investigation (BI)

For each impacted integration, run:

- **Supporting search**: "this change benefits {INTEGRATION} because …" —
  list at least one benefit.
- **Counter-search**: "this change harms {INTEGRATION} because …" — list at
  least one harm, even if you have to invent the worst-case scenario.
- **Status quo search**: "if we don't make this change, what does
  {INTEGRATION} look like in 6 months?" — does the status quo also degrade?

For each integration, the OUTPUT is three short paragraphs: benefit, harm,
status-quo. If the counter-search produces nothing real, say so explicitly.

### Step 4 — Source independence (SI)

The motivation for the change came from one source. List who and from where:

- Author of the change proposal
- Team / domain
- Evidence cited (issues, bug reports, customer feedback, internal data)

Check for echo-chamber risk:
- Is the evidence all from one team?
- Are the integrations affected represented in the evidence pool? Or are we
  hearing from the source system only?
- Is the change driven by a recent incident (recency bias risk per AP-06)?

Output: a SI assessment — independent / partial / echo-chamber.

### Step 5 — Falsifiability (FR)

For each recommended update (you'll produce these in Step 8), state:

- **What evidence would change our mind on this update?** ("If we observed
  that {X}, we would not make this update.")
- **What's the pre-mortem?** ("If this update fails, the most likely reason
  is …")
- **Review trigger:** when should we re-check this update? After 1 release?
  After 30 days of integration data?

Output: per-update falsification criteria.

### Step 6 — Confidence calibration (CC)

For each recommended update, label the confidence tier:

- **VALIDATED** — 5+ independent sources / past examples that this approach worked
- **SUPPORTED** — 3-4 sources, consistent pattern
- **EMERGING** — 2 sources, consistent
- **UNVALIDATED** — <2 sources or unique situation
- **CONTRADICTED** — evidence actively refutes the update

Don't overclaim. UNVALIDATED is fine if it's a unique case. Override only
when evidence is real.

### Step 7 — Adversarial testing (AT) + Honest uncertainty (HU)

For each recommended update, run an adversarial pass:

- Where would this update fail?
- What edge case would break it?
- What assumption does it depend on that might be wrong?
- What did we not check?

Output: per-update AT findings + an explicit HU section listing things we
couldn't determine.

### Step 8 — Recommended updates (PP — pyramid + DF — SCQA)

For each impacted integration, produce a recommendation in this shape:

**Situation**: {integration's current state — what it does, what it depends on}
**Complication**: {what changes with the proposed change}
**Question**: {what should be done about it?}
**Answer**: {the specific update}

Then for each Answer:

- **Concrete steps**: numbered list of what to change
- **Owner**: who in the integrated system should do the work (if known)
- **Effort estimate**: small / medium / large
- **Confidence tier** (from Step 6)
- **Falsification** (from Step 5)
- **AT findings** (from Step 7)

### Step 9 — Anti-pattern self-check (AP-01..AP-09)

Before finalising, run the anti-pattern checklist:

- [ ] AP-01 Cherry-picking — Did you cite only supportive evidence?
- [ ] AP-02 Echo validation — Are your sources actually independent?
- [ ] AP-03 Optimistic interpretation — Did you read ambiguity as positive?
- [ ] AP-04 Premature rejection — Did you dismiss any alternative without analysis?
- [ ] AP-05 Confirmation search — Did you only search for evidence that
      confirms the change is needed?
- [ ] AP-06 Recency bias — Did a recent incident drive this disproportionately?
- [ ] AP-07 Volume conflation — Did you treat "many people complain about this"
      as evidence of impact, without checking what those complaints actually
      were about?
- [ ] AP-08 Authority assumption — Did you cite a senior person's preference
      as evidence?
- [ ] AP-09 Over-decomposition — Did you split impacts at a level that
      doesn't change the recommendation?

If any box is checked, fix the analysis before producing the final output.

### Step 10 — Output: structured impact report

Produce the final report in this structure:

# Integration Change Review: {SOURCE_SYSTEM} — {CHANGE_TITLE}

## Decision summary (SCQA)
- **Situation**: {context}
- **Complication**: {what changes}
- **Question**: {what should we do about integrations?}
- **Answer**: {recommended updates summary in 1-3 sentences}

## Impacted integrations
| # | Integration | Type | Coupling | Impact | Update needed |
|---|---|---|---|---|---|
| 1 | {name} | caller | tight | rename | yes (see §1.A) |
| ... | | | | | |

## Per-integration recommendations

### 1. {Integration name}

**Current state**: {what it does today}
**Impact of the proposed change**: {specific primitive affected, how}
**Recommended update**: {action}

| Field | Value |
|---|---|
| Concrete steps | {numbered list} |
| Owner | {team / agent / unknown} |
| Effort | small / medium / large |
| Confidence | VALIDATED / SUPPORTED / EMERGING / UNVALIDATED / CONTRADICTED |
| Falsification | "If we observed X, we would not make this update." |
| AT findings | "This update fails if Y." |
| Review trigger | {when to re-check} |

### 2. {next integration}
... (same shape)

## Blindspot register (HU)
{Things we couldn't determine; questions for the invoker.}

## Anti-pattern self-check (AP-01..AP-09)
{Summary of checks; any that fired and how they were addressed.}

## Falsification summary (FR)
{What would change the entire review's recommendation.}

## Confidence summary (CC)
{Tier counts across all updates: e.g., "5 SUPPORTED, 2 EMERGING, 1 UNVALIDATED."}
```

---

## How to invoke this prompt

In a session, paste the prompt block above (filling in `{SOURCE_SYSTEM}`,
`{PROPOSED_CHANGE}`, `{MOTIVATION}`, `{LIST_OF_INTEGRATIONS}`) and let the
agent walk through Steps 1-10.

For repeated use, save it as a skill (e.g., `/sea:integration-review`) that
takes those four arguments and runs the workflow.

---

## Worked example

To illustrate, here's a hypothetical run for a change to `wpx-pipeline`:

**Input:**

- **Proposed change**: Add a `--base-branch` parameter to `wpx-pipeline run`
  (which we did in CW Phase 3); current behaviour assumes `dev`.
- **Source system**: `sulis-execution v0.11.0` (becoming v0.12.0)
- **Motivation**: Per CW-04, the executor needs to ship WPs to the change
  branch when running inside a change worktree, not directly to `dev`.

**Walkthrough condensed:**

Step 1 (OI — enumerate integrations):
- Callers: `/sulis:run-wp` skill; `/sulis:run-all` skill;
  `sulis-concierge` (indirect via run-wp / run-all)
- Consumers: `wpx-step12 wrap` (reads pipeline result JSON)
- Shared state: INDEX.md (`step-7-complete` / `done` transitions)
- Downstream: `wpx-train run` (uses same `_rebase_on_dev` / `_merge_squash`
  helpers, also needs the parameter)
- Docs: `lifecycle.md`, `run-wp/SKILL.md`, `run-all/SKILL.md`, `status/SKILL.md`
- Agents: the executor agent (Steps 1-7) doesn't invoke pipeline directly;
  unaffected

Step 2 (PG — primitive impact):
- `--dev-sha-at-creation` parameter SEMANTICS change (still SHA but now of the
  base branch, not specifically dev) → tight coupling on the skill callers
- `_rebase_on_dev` function signature: added optional `base_branch` parameter
  with default `dev` → loose coupling (additive)
- `_merge_squash` function signature: same → loose coupling
- INDEX.md status enum: gains `step-7-complete`, `step-7-held`, `step-7-blocked`
  → tight coupling on skills that read status
- Lifecycle docs: gain a "two-level worktree" section → loose coupling
  (informational)

Step 3 (BI):
- Supporting: enables CW-04; multiple changes in parallel without dev collisions
- Counter-evidence: more parameters for the skill author to thread; risk of
  passing wrong base if the caller doesn't detect change context; for plugins
  that don't have a deploy pipeline at all, this whole apparatus is overkill
- Status quo: dev gets stomped if two changes proceed in parallel — already
  observed as a real problem this conversation identified

Step 4 (SI):
- Driver: ADR-212 amendment + the CW standard's CW-04 rule. Multiple
  conversation turns + multiple committed standards. Independent.
- Risk: all from the same conversation thread; no external testing yet.
  Recency-bias risk surfaced.

Step 5 (FR):
- Would change mind if: 90-day calibration shows the carve-out (default `dev`)
  is rarely used in practice → meaning everyone's on the change-bounded path →
  the parameter could become mandatory.
- Pre-mortem: skills forget to pass `--base-branch`, the train defaults to dev,
  silent merge into dev when the developer expected change-branch only.

Step 6 (CC):
- The `--base-branch` parameter addition: SUPPORTED (gRPC, HTTP, similar
  patterns have configurable base refs)
- The two-level worktree hierarchy: UNVALIDATED (novel in this marketplace;
  no prior literature)
- The status enum extensions: SUPPORTED (per ADR-212)

Step 7 (AT):
- Fails if: caller passes a base-branch that doesn't exist on origin → silent
  rebase failure
- Fails if: change branch's CI has different requirements than dev's CI → CI
  poll might wait for the wrong checks

Step 8 (Recommendations — abbreviated):

| Integration | Recommendation | Confidence |
|---|---|---|
| `/sulis:run-wp` | Step 0 detects change context, passes `--base-branch` | SUPPORTED |
| `/sulis:run-all` | Same detection, passes through to `wpx-train run` | SUPPORTED |
| `wpx-train run` | Mirror `--base-branch` parameter (already done in v0.11.0) | VALIDATED |
| `wpx-step12 wrap` | No change needed — reads result JSON, not base-branch | VALIDATED |
| `lifecycle.md` | New "Where a WP sits — inside a change (CW-04)" section | SUPPORTED |
| `status/SKILL.md` | Render change context if on a change branch | SUPPORTED |
| Hypothetical "wpx-pipeline as an HTTP service" deployment | N/A — doesn't exist; flag as future concern | UNVALIDATED |

Step 9 (AP self-check):
- AP-05 Confirmation search: only searched evidence supporting the change.
  Adjustment: counter-search for "do plugin authors actually want this?" —
  result: yes, the CW-04 design discussion confirmed this with the user.
- AP-08 Authority: the user proposed CW-04; checked: did external evidence
  also support it? Yes (GitLab merge trains; Bors; the cicd-batching-analysis
  research).

Step 10: produce final report (as already happened in CW Phase 3).

This is a sample. Real runs go deeper per step.

---

## When to use this prompt

- A backwards-compatible change to a system with multiple consumers (most cases)
- A breaking change that requires consumer updates (where the review is
  load-bearing)
- A "small" change where the team isn't sure how many things break (the review
  often surfaces more integrations than expected)
- A change being proposed where the team needs to justify it to consumers
  before merging

## When NOT to use this prompt

- A trivial change (single-character bug fix; no consumer impact)
- A change to a system with no integrations (rare; usually integrations
  exist and just aren't documented yet — running Step 1 surfaces them)
- An exploratory change that hasn't been decided yet (use a regular CTS
  research pass instead; this prompt assumes the change is being proposed,
  not investigated)

---

## Sources

### Critical Thinking Standard
- [`platform/methodology/standards/CRITICAL_THINKING_STANDARD.md`](../../../../platform/methodology/standards/CRITICAL_THINKING_STANDARD.md)
  — all 13 principles plus AP-01..AP-09 anti-patterns

### Established review conventions
- [Architecture Decision Records (ADRs)](https://adr.github.io/) — Michael Nygard
  pattern for capturing decisions
- [RFC process](https://datatracker.ietf.org/) — IETF Standards Process for
  large-scale change reviews with consumer representation
- [Python PEP process](https://peps.python.org/pep-0001/) — language-design
  change proposals with explicit Backwards Compatibility section
- [Rust RFC process](https://github.com/rust-lang/rfcs/blob/master/0000-template.md)
  — explicit "Drawbacks", "Rationale and alternatives", "Prior art",
  "Unresolved questions" sections (maps onto CTS principles)

### Sulis marketplace standards used
- [`agent-consumable-sdk-spec.md`](agent-consumable-sdk-spec.md) — the SDK
  spec whose changes this prompt was originally written to review
- [`plugins/sulis/references/convention-preference-standard.md`](../../../sulis/references/convention-preference-standard.md) — CP-01
- [`plugins/sulis/references/founder-english.md`](../../../sulis/references/founder-english.md) — FE for plain-English output to the invoker
- [`plugins/sulis/references/code-review-standard.md`](../../../sulis/references/code-review-standard.md) — CR-NN (related but not identical — code review is per-PR; this review is per-integration)

---

## Version history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-21 | Initial prompt + methodology. CTS-driven workflow in 10 steps. Worked example using the CW Phase 3 `--base-branch` change. AT + FR + CC + HU + AP-checklist embedded throughout. |
