# Critical Thinking Analysis — Three-Layer Architecture + Naming

> **Methodology:** `/Users/iain/Documents/repos/platform/methodology/standards/CRITICAL_THINKING_STANDARD.md` (v1.5.0).
> **Decision context (PG-03):** how the founder-facing code-health system should be architected in the sulis marketplace; level = plugin layout + skill granularity + orchestration architecture.
> **Status:** analysis result — author's recommendation, not a locked decision.

---

## Decision Summary (SCQA — DF-01)

**Situation.** The marketplace has a 24-row quality-coverage matrix mapping concerns to skills. A founder asked for one comprehensive code-health check rather than a menu of operator-specific tools. SEA's earlier TDD proposed a two-layer architecture: operator skills underneath, single `/sulis:checkup` wrapper on top.

**Complication.** A subsequent reframe proposed a *three*-layer architecture — operator skills, founder wrappers (one per tier), comprehensive wrapper on top. The reframe felt right but had not been tested against the Critical Thinking Standard. Naming was also not locked.

**Question.** Does the three-layer model survive CTS scrutiny? Are all primitives accounted for? What are the right action names?

**Answer.** The model collapses to **two primitives** (operator skill + founder skill) with founder skill having a sub-shape (translator vs orchestrator). The "three-layer" framing is visually useful but is over-decomposition (AP-09) at the primitive level. **All 11 primitives SEA identified are real; 4 additional gaps surface** (build verification, tests-pass verdict, no-data-loss, feature-vs-spec). **Names should use verb-first `/sulis:check-X` convention** for tier skills and `/sulis:code-health` for the wrapper.

**Confidence (CC).** SUPPORTED — the analysis is grounded in the existing primitive catalogues and the add-skill methodology, but the model has not yet been validated by building 3+ founder wrappers. The translator-vs-orchestrator distinction in particular needs empirical confirmation.

---

## Recommendation (PP-01..PP-04)

**Conclusion:** Two primitives, not three. Build 5 tier-specific founder skills + 1 wrapper, on top of the 8 operator skills + 3 extensions SEA already specified. Use verb-first `/sulis:check-<noun>` for tier skills; `/sulis:code-health` for the wrapper.

**Supporting Legs:**

| Leg | Summary | Evidence |
|---|---|---|
| 1. Two primitives, not three | "Orchestrator" is a complex *shape* of founder skill, not a separate kind of thing | PG-02 independence test + PG-04 termination check (Section 1) |
| 2. 4 additional primitive gaps exist beyond SEA's 11 | Build verification, tests-pass verdict, no-data-loss, feature-vs-spec — none have formal primitive coverage today | Section 2 — primitive cross-check against sulis-security 25 + MECE-3 10 + matrix 24 |
| 3. Verb-first `/sulis:check-X` is the least-corny convention | Founders say "check security" not "do security check"; matches add-skill v0.4.0 founder-facing-conventions | Section 3 — name evaluation against not-corny + does-what-it-says criteria |

**Leg test:** removing any leg weakens the conclusion. Leg 1 prevents over-decomposition. Leg 2 prevents shipping with known gaps. Leg 3 settles a question the user explicitly asked.

---

## Section 1 — Primitive Grounding (PG) on the layer model

### Level of analysis (PG-03)

**Decision context:** how should the founder-facing code-health system be architected in the marketplace?
**Level:** plugin layout + skill granularity + orchestration

### Candidate primitives + independence test (PG-01, PG-02)

| Candidate | Definition | Independently changeable? | Independently validatable? | Independently falsifiable? | Primitive? |
|---|---|---|---|---|---|
| Operator skill | A skill with `audience=operator`; technical vocabulary; deterministic check | YES (own SKILL.md, own tests) | YES (run + verify output) | YES (failing characterisation test) | **YES** |
| Founder skill | A skill with `audience=founder` or `both`; founder-facing-conventions apply | YES | YES | YES | **YES** |
| Translator-shape founder skill | A founder skill that wraps ONE operator skill | NO — fully derivable from "founder skill" + "wraps a single dependency" | — | — | **NO** (shape, not primitive) |
| Orchestrator-shape founder skill | A founder skill that wraps MULTIPLE skills + has tier-gating/OODA | NO — fully derivable from "founder skill" + "wraps multiple dependencies with conditional routing" | — | — | **NO** (shape, not primitive) |

**Independence detail.** Operator skill and founder skill change independently (different file paths, different authors, different audience conventions). The shape distinction (translator vs orchestrator) is a property of the founder skill's *implementation*, not a different kind of thing — a translator can grow into an orchestrator if it gains more dependencies; both follow the same five-gate add-skill methodology; both produce a SKILL.md + COMPLETENESS_REPORT.

### Termination check (PG-04) — does further splitting change any decision?

| Candidate split | Would it change a decision? | Verdict |
|---|---|---|
| Split "skill" → operator skill / founder skill | YES — affects audience conventions, vocab, gotchas, adversarial sweep catalogue | **SPLIT** (irreducible at this level) |
| Split "founder skill" → translator / orchestrator | NO — same SKILL.md template, same five gates, same COMPLETENESS_REPORT structure; differences are implementation details inside the body | **STOP** (over-decomposition; AP-09) |
| Split "operator skill" → checking / fixing | YES — checking skills are read-only audits; fixing skills mutate code (different testing requirements, different safety profiles) | **SPLIT** (relevant; covered today by sea:codebase-audit + sea:harden split — different primitives) |

### Verdict

The layer model has **two primitives**, not three. The "three-layer architecture" framing is a useful *visual organisation* but is NOT primitive-grounded — Layer 2 (founder-translator skills) and Layer 3 (founder-orchestrator skill) are the same primitive with different complexity. This matters because:

- COMPLETENESS_REPORT.md.template doesn't need a third entry-shape
- add-skill methodology applies identically to both
- The five gates run the same way regardless of how many dependencies the skill has

The **practical implication** for building: when authoring `/sulis:code-health`, run it through the same `sulis:add-skill` methodology that `/sulis:tidy` runs through. No new authoring pattern needed.

---

## Section 2 — Primitive coverage (MECE-01, MECE-02)

### Catalogues consulted

1. **sulis-security:codebase-assess primitives** — 25 across 5 categories: Security (SEC-01..07), Data Protection (DAT-01..05), Code Quality (CQ-01..05), Supply Chain (SC-01..04), Infrastructure (INF-01..04).
2. **MECE-3 (sea) primitives** — 10 across 3 pillars: Form (MEA-01..03), Armor (MEA-04..07), Proof (MEA-08..10).
3. **Quality coverage matrix** — 24 rows at `docs/quality-coverage-matrix.md`.
4. **SEA's TDD gap list** — 8 new skills + 3 extensions at `.architecture/sulis-checkup/TDD.md` Part 9.

### Primitive-to-tier mapping

| Tier | Existing primitive coverage | Coverage strength | Identified gaps |
|---|---|---|---|
| 1 Exists | MEA-01..03 (structural integrity — touches "code is well-formed") | **WEAK** — no primitive directly tests "does it build?" or "are tests runnable?" | **GAP A — build-artefact verification.** SEA's "extend sea:probe with `--build-artefact`" addresses this. **GAP F — manifest hygiene** (matrix #24, HD-004 pattern). |
| 2 Safe | SEC-01..07, DAT-01..05, SC-01..04, INF-02, MEA-05, MEA-06 | **STRONG** — sulis-security catalogue covers tier 2 comprehensively | No gaps identified at primitive level. |
| 3 Works | CQ-02 (test coverage), MEA-08 (contract tests), MEA-09 (integration tests) | **WEAK** — CQ-02 measures coverage but not pass/fail; no primitive directly verifies "tests pass" or "deploy succeeds" | **GAP B — tests-pass verdict.** SEA's "extend sea:probe with `--run-tests`" addresses this. **GAP E — feature-vs-spec parity.** sea:verify covers this when SRD+TDD+WPs exist; nothing covers it otherwise. |
| 4 Survives | MEA-04 (timeouts/retries/CB), MEA-07 (observability), INF-04 (error handling), MEA-10 (chaos tests) | **MEDIUM** — MEA-04 + MEA-07 well-covered; MEA-10 weaker | **GAP D — no-data-loss / data integrity.** No primitive in either catalogue directly tests "if crashed mid-write, is state recoverable?" Adjacent to MEA-10 but distinct. |
| 5 Understandable | CQ-01 (complexity), MEA-03 (modules expose contracts) | **WEAK** — CQ-01 measures complexity but not legibility; no primitive for naming/jargon/cohesion | Covered by SEA gap list: `sea:code-hygiene` (matrix #15), `sulis-context:validate` (matrix #19 — doc drift). |
| 6 Evolves | CQ-03 (duplication), CQ-04 (tech debt), MEA-01 + MEA-02 (dependency direction) | **WEAK** — CQ-03/04 are mechanical metrics; no primitive for dead code, migration completion, surface drift, test quality | Covered by SEA gap list: `sea:dead-code-audit`, `sea:surface-parity-audit`, `sea:test-audit`, `sea:failure-mode-audit`. |
| 7 Polished | INF-01 (container security touches polish), CQ-05 (review practices) | **WEAK** — explicitly deferred by SEA per ADR-006 | Performance, accessibility, UX checks deferred to v2 (per SEA). |

### Cross-tier primitives (MECE-01 partial-violation, acknowledged)

Three primitives genuinely span tiers — accepted compromise per SEA's ADR-002 + ADR-003:

| Primitive | Tiers spanned | Why cross-tier |
|---|---|---|
| MEA-05 / DAT-04 / INF-02 (secrets management) | 2 (safe — leaked secret harms) + 4 (survives — rotation handling) | Same primitive seen through two lenses |
| MEA-07 (observability — trace/log/metric) | 4 (survives — diagnosable) + 6 (evolves — maintainable) | Diagnosability serves both failure-handling and maintainability |
| CQ-01 (complexity) | 5 (understandable — complex code is unreadable) + 6 (evolves — complex code is hard to change) | Same measure, two consequences |

### Identified gaps not in SEA's TDD

| Gap | Tier | Why needed | Suggested owner |
|---|---|---|---|
| **A — Build-artefact verification** | 1 | Tier 1 needs "does the Dockerfile build? does the binary produce?" not just "does the code parse?" | Extend `sea:probe` Phase 1.9 with `--build-artefact` flag (SEA already noted) |
| **B — Tests-pass verdict** | 3 | CQ-02 measures coverage; no primitive verifies pass/fail | Extend `sea:probe` with `--run-tests` flag (SEA already noted) |
| **D — No-data-loss / data integrity** | 4 | If crashed mid-write, can state be recovered? Not directly tested by any existing primitive | Could be new operator skill OR added as a perspective inside `sea:codebase-audit`'s Armor pillar |
| **E — Feature-vs-spec parity (spec-less mode)** | 3 | sea:verify covers this WITH SRD+TDD+WPs; no fallback for spec-less projects | Extend `sea:verify` with a spec-less mode OR add to the wrapper logic |
| **F — Manifest hygiene** | 1 + 5 | HD-004 was exactly this; no primitive covers "is plugin.json semantically correct beyond JSON-parseability?" | Extend `sea:code-review` checklist OR `sea:probe` Phase 1.16 (SEA already noted F overlap) |

**Tally.** SEA identified 8 new skills + 3 extensions. CTS analysis surfaces **4 additional gaps** (A, B, D, E, F — with A/B/F already noted by SEA as extensions, so the net-new gaps are D + E). All other matrix rows + catalogue primitives map cleanly to a tier.

### MECE verdict on tiers

- **Mutually exclusive:** PARTIAL — three cross-tier primitives exist. Acknowledged compromise per SEA's ADR-003.
- **Collectively exhaustive:** PASS for "code health" scope. Some adjacent concerns excluded by scope (UX research, customer feedback, business metrics — none of these are code-health).
- **Leg test (MECE-03):** removing any tier weakens the model. Tier 7 stub is the weakest leg but defensibly carries "polish exists as a concept; just not assessed yet."
- **So-what test (MECE-04):** every tier maps to a founder action (fix/defer/accept). No fluff.

---

## Section 3 — Action names

### Criteria (from the user)

1. **Not corny / clever / metaphor-heavy**
2. **Does what it says on the tin**
3. **Plain English** — founder understands intent from name alone
4. **No collision** with existing skills
5. **Verb-shape** ("action names")

### Verb evaluation

Candidate verbs for the read-only check operation:

| Verb | Plain? | Verb-shape? | Collision? | Verdict |
|---|---|---|---|---|
| **check** | YES | YES | No | **WINNER** — most plain, most non-corny |
| audit | partial | YES | No | Operator-y (per founder-facing-conventions) |
| review | YES | YES | YES (`sea:code-review`) | Collides |
| verify | partial | YES | YES (`sea:verify`) | Collides |
| assess | partial | YES | No | Operator-y |
| inspect | partial | YES | No | Slightly technical |
| scan | YES | YES | No | OK but implies surface-level |
| examine | partial | YES | No | Slightly formal |
| look-at | YES | YES | No | Too informal |

**`check` chosen.** It's the verb a founder would actually say. "Check the security." "Check the build." "Check everything."

### Naming convention — verb-first vs noun-suffix

Two patterns considered:

| Pattern | Example | Reads like |
|---|---|---|
| Verb-first: `check-<noun>` | `/sulis:check-security` | "Check the security" — imperative |
| Noun-first: `<noun>-check` | `/sulis:security-check` | "Security check" — labelled domain |

Verb-first wins on the "action names" criterion the user specified. Verb-first also reads more like a command, which matches what `/sulis:` invocations are.

### Tier-specific founder skills (Layer 2)

| Tier | Name | Trigger condition (draft) |
|---|---|---|
| 1 Exists | `/sulis:check-build` | "Use when the founder asks if the project builds, if the basics are in place, or if anything is fundamentally broken." |
| 2 Safe | `/sulis:check-security` | "Use when the founder asks if there are security issues, leaked passwords, or anything that could harm users or the business." |
| 3 Works | `/sulis:check-tests` | "Use when the founder asks if the tests pass or if the code does what it should." |
| 4 Survives | `/sulis:check-reliability` | "Use when the founder asks how the code handles failure — timeouts, errors, things going wrong." |
| 5 Understandable | `/sulis:check-readability` | "Use when the founder asks if the code is clear, if a new person could read it, or if it's getting messy." |
| 6 Evolves | `/sulis:check-maintainability` | "Use when the founder asks if the code will be easy to change later, or if technical debt is accumulating." |
| 7 Polished | `/sulis:check-polish` (deferred) | (not built in v1; placeholder for performance / accessibility / UX) |

### The wrapper (Layer 3 — but actually Layer 2 per Section 1)

| Candidate | Plain? | Founder-natural? | Collision? | Verdict |
|---|---|---|---|---|
| **`/sulis:code-health`** | YES | YES — your suggestion | No | **PRIMARY RECOMMENDATION** |
| `/sulis:checkup` | YES | YES (medical metaphor, universal) | No | Strong alternative; slightly cuter |
| `/sulis:check-everything` | YES | YES (literally "check everything") | No | Most explicit; verbose |
| `/sulis:health-check` | YES | partial — risks conflation with operational health (smoke tests) | No | Avoid |
| `/sulis:full-check` | YES | YES | No | Reasonable alternative |

**`/sulis:code-health` recommended.** Rationale:
- Founder explicitly proposed this name
- "Code" qualifies what's being checked
- "Health" is universal vocabulary without medical-jargon overhead
- Distinct from `/sulis:status` (current state) and `/sulis:inbox` (waiting items)
- Noun-shape matches precedent set by `start`, `status`, `handoff`, `inbox`, `add-skill`

### Hyperbole audit (NH)

Names checked against the prohibited-terms list:

| Prohibited term | Found in name? | Action |
|---|---|---|
| revolutionary, disruptive, unprecedented, game-changing, best-in-class, cutting-edge, world-class, amazing | NONE | ✓ |

Quantitative terms requiring metrics: none used in skill names.

**Verdict:** linguistic audit PASS.

---

## Section 4 — Adversarial test (AT-01..AT-03)

### Strongest arguments against the recommendation

#### Argument 1 — Cumulative authoring cost

**Claim:** 6 new founder skills + 1 wrapper + 8 new operator skills + 3 extensions = ~18 authoring runs. Each carries a full five-gate methodology pass + COMPLETENESS_REPORT. At ~2-4 hours per skill, that's 40-70 hours of work before code-health ships meaningfully.

**Strength:** SUPPORTED. The cumulative cost is real.

**Mitigation:** ship in tiers. Build tiers 5 + 6 first (the matrix gaps we already prioritised); the wrapper at minimum-viable shape (just tier 5 + 6 invocation); add tiers 1-4 + 7 as adapters over existing skills. This sequences the work so each batch ships value.

#### Argument 2 — Wrapper-pattern is unproven

**Claim:** `sulis:inbox` is the ONE existing founder-wrapper example. We don't know if the translator shape composes well. Building 5 more before validation is speculative.

**Strength:** SUPPORTED. Inbox is the only data point.

**Mitigation:** build `/sulis:check-security` next (already wraps `sulis-security:codebase-assess`, which exists). If the translator shape holds for that one, build the others. If not, refactor before scaling.

#### Argument 3 — Audience boundaries fuzzy

**Claim:** "Founder" vs "operator" isn't binary. Most skills will end up as `audience=both`, defeating the lock.

**Strength:** EMERGING. Inbox is the only existing founder-audience skill; we don't yet know how `both` plays out in practice.

**Mitigation:** the `add-skill` methodology already accommodates `both` with a mode-selection strategy. If `both` becomes the default, we revisit whether the audience lock has the right granularity.

#### Argument 4 — Tier 1+2 hard-stop blocks diagnostic path

**Claim:** What if the founder asks "the build is broken because the names are wrong, fix the names first"? Hard-stop at tier 1 blocks reaching tier 5.

**Strength:** EMERGING. Edge case; not the typical flow.

**Mitigation:** SEA's `--check-everything` override (ADR-002) addresses this. Document the override in the wrapper's gotchas section.

#### Argument 5 — LangGraph dependency adds surface

**Claim:** Marketplace currently takes no graph-engine dependency. LangGraph adds installs, version coupling, learning curve.

**Strength:** SUPPORTED.

**Mitigation:** dependency scoped to the wrapper skill only (per Section 1 analysis — Layer 2 has no graph needs). Individual tier skills don't use LangGraph. The wrapper is the only consumer. If LangGraph proves too heavy, replace with a simple Python orchestrator inside the wrapper without touching tier skills.

### Invalidation signals (FR-01)

This recommendation is wrong if:

| Signal | What it would mean | Test |
|---|---|---|
| Building 3+ tier skills reveals they're all the same trivial translator | The translator shape adds no value over invoking operator skills directly; founder vocab translation could be a shared helper, not a skill | Build tiers 2, 5, 6; compare bodies. If <100 LOC of distinct logic each, collapse into a shared translator + the wrapper. |
| LangGraph install/version churn exceeds orchestration value | The dependency cost dominates the benefit | Pilot wrapper with one tier; measure install pain over 30 days. |
| Founders invoke wrapper >95%, tier skills <5% | Individual tier skills are dead weight | Telemetry over 10 real uses across multiple projects. If individual <5%, deprecate them; keep the wrapper. |
| `audience=both` becomes the default for every new skill | The founder/operator distinction was an over-decomposition | Track audience locks across next 5 skills; if 4+ are `both`, revisit the audience taxonomy. |

### Pre-mortem (FR-03)

If this architecture fails, the most likely reasons:

1. **Over-investment before validation.** Building all 6 tier skills + wrapper before any have run against a real founder project.
2. **Translator shape doesn't compose.** Each founder skill ends up with its own bespoke vocabulary translation; no shared pattern emerges; cumulative complexity grows.
3. **LangGraph orchestration breaks down.** The graph state model doesn't fit the resumable cross-tier flow we need; we end up reimplementing orchestration inside LangGraph.

---

## Section 5 — Honest uncertainty (HU-01..HU-04)

### What I couldn't determine

| Question | Why undetermined |
|---|---|
| How real non-technical founders will actually invoke these | Sample size is 1 (you, who are technical-with-founder-hat). Real founders' invocation patterns unknown until shipped. |
| Whether LangGraph is the right engine | Not piloted. Decision could be revisited after the first wrapper builds. |
| The 6 healing prototypes' fitness | SEA reasoned this (ADR-003) but no empirical data on which prototypes get used most. |
| Tier 7 contents (perf / a11y / UX) | Deferred per SEA. Granularity TBD. |
| The translator-vs-orchestrator distinction in practice | Inbox is the only data point. The distinction might collapse on building (per Argument 1's mitigation). |

### Research limitations

- The CTS analysis is structural — it tests whether the model is well-grounded, not whether it works empirically. Empirical validation requires building.
- The primitive cross-check assumes the catalogues (sulis-security 25, MECE-3 10, matrix 24) are themselves complete. They probably aren't — but they're the best available.
- "Founder will understand" criteria for names is judged by me, not by an actual founder test.

---

## Section 6 — Quality checklist (CTS final verify)

| Item | Status |
|---|---|
| **BI** — counter-evidence sought | ✓ (Section 4 — 5 arguments against) |
| **SI** — sources independent | ✓ (separate catalogues consulted) |
| **FR** — falsification stated | ✓ (Section 4 — 4 invalidation signals + pre-mortem) |
| **CC** — confidence matches evidence | ✓ (SUPPORTED, not VALIDATED — explicitly) |
| **MECE-01** — mutually exclusive | ✓ partial (cross-tier primitives acknowledged) |
| **MECE-02** — collectively exhaustive | ✓ for code-health scope |
| **MECE-03** — leg test | ✓ each leg essential |
| **MECE-04** — so-what test | ✓ each tier → founder action |
| **NH** — no hyperbole | ✓ linguistic audit clean |
| **PP** — leads with conclusion | ✓ Section "Recommendation" first |
| **HU** — uncertainty disclosed | ✓ Section 5 |
| **EH** — weak evidence framed as exploration, not dismissal | ✓ (Tier 7 stub; translator distinction) |
| **DF** — SCQA framing | ✓ Decision Summary at top |
| **PG-01** — primitives identified | ✓ Section 1 |
| **PG-02** — independence test passed | ✓ Section 1 table |
| **PG-03** — level-of-analysis declared | ✓ Decision context at top |
| **PG-04** — termination check applied | ✓ Section 1 table; "three-layer" collapsed |
| **OI** — outside-in reasoning | partial — started from founder-need (good), but consulted internal primitive catalogues early (acceptable per OI-01 scoping — this is an implementation-architecture outcome, not a function-identification outcome) |
| **AT-01** — adversarial posture | ✓ Section 4 |
| **AT-02** — riskiest assumption tested first | ✓ "cumulative cost" is highest-risk argument |
| **AP-09** — over-decomposition flagged and corrected | ✓ three-layer → two-primitive |

---

## Appendix — Working primitives map (for downstream use)

For each tier, the operator skills the wrapper would invoke:

```
Tier 1 (check-build):       sea:probe (extended --build-artefact)
                            sea:code-review (extended manifest hygiene)
Tier 2 (check-security):    sulis-security:codebase-assess
Tier 3 (check-tests):       sea:verify (or sea:probe --run-tests if no SRD)
Tier 4 (check-reliability): sea:codebase-audit (Armor pillar)
                            sea:failure-mode-audit (NEW)
Tier 5 (check-readability): sea:code-hygiene (NEW)
                            sulis-context:validate (NEW)
Tier 6 (check-maintain.):   sea:dead-code-audit (NEW)
                            sea:surface-parity-audit (NEW)
                            sea:test-audit (NEW)
Tier 7 (check-polish):      deferred
Wrapper (code-health):      invokes all of the above in tier order
                            with LangGraph orchestration + tier-gating
```

Net new skills required: 7 (5 operator + 1 wrapper + 1 founder-side aggregation skill if translator pattern collapses per Argument 1).

Existing skill extensions: 3 (sea:probe x2 flags, sea:code-review checklist).
