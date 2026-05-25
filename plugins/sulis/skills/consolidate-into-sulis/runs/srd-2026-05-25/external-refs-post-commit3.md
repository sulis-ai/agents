# External references to `srd`

All file paths and agent dispatch points that mention `plugins/srd/` or the source plugin's agents.
Every line below needs updating during Commits 2–4 of the consolidation.

## 1. Files citing source-plugin paths

### `.architecture/sulis-checkup/TDD.md`

- L216: `| **Escalate to SRD** | `/srd:requirements-analyst` referral | When the gap is a missing requirement, not missing code. …`

### `.architecture/sulis-checkup/adrs/ADR-003-healing-prototype-taxonomy.md`

- L18: `5. **Escalate to SRD** (`/srd:requirements-analyst`)`

### `.architecture/sulis-checkup/adrs/ADR-006-srd-gap.md`

- L12: `refer the user back to `/srd:requirements-analyst` when no`
- L74: `1. **Run `/srd:requirements-analyst`** at `.specifications/sulis-checkup/`.`
- L87: `4. **Run `/srd:requirements-validation`** for the five-perspective`
- L119: `- Skill scope creep. `/sea:blueprint` is not `/srd:requirements-analyst`.`

### `.claude-plugin/marketplace.json`

- L8: `"description": "Sulis AI plugin marketplace — methodology studios, requirements analysis, facilitation, context cartogra…`

### `CLAUDE.md`

- L41: `1. Create a directory under `plugins/srd/skills/` named after the skill.`
- L61: `3. Run the skill via its slash command (e.g. `/srd:critical-thinking`).`
- L145: `For full detail on these principles, see `plugins/srd/references/engineering-principles.md`,`
- L146: ``plugins/srd/references/security-standard.md`,`
- L147: ``plugins/srd/references/convention-preference-standard.md`,`
- L148: ``plugins/srd/references/audience-adapted-framing-standard.md`,`
- L149: ``plugins/srd/references/git-workflow-standard.md` (GIT-01..GIT-10 —`
- L153: ``plugins/srd/references/executor-loop-standard.md` (EL-01..EL-08 —`
- L157: `and `plugins/srd/references/founder-english.md` (FE-01..FE-10 —`

### `CONTRIBUTING.md`

- L9: `plugins/srd/skills/your-skill-name/`
- L22: `Reference standards live in `plugins/srd/references/` and define governing rules`
- L59: `1. Create the file at `plugins/srd/references/your-standard.md`.`
- L61: `3. Update `plugins/srd/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` with the`

### `README.md`

- L53: `| **[srd](plugins/srd/)** | Facilitates building the Software Requirements Document; also home of marketplace-wide stand…`
- L73: `- `.specifications/{project}/SRD.md` — produced by `/srd:start``
- L90: `/srd:start <project-slug>`

### `docs/skill-authoring-guide.md`

- L26: `plugins/srd/skills/your-skill/`

### `plugins/idc/CHANGELOG.md`

- L15: `Investor Deck Coach — facilitates Sequoia-style pitch deck creation through guided conversation. Stage-aware (angel, pre…`

### `plugins/idc/agents/investor-deck-coach.md`

- L150: `| `plugins/srd/references/convention-preference-standard.md` (CP-) | Always recommend the established convention (Sequoi…`
- L151: `| `plugins/srd/references/audience-adapted-framing-standard.md` (AAF-) | Non-technical founder is the default audience. …`
- L533: `See `plugins/srd/references/convention-preference-standard.md` for`
- L547: ``plugins/srd/references/founder-english.md``
- L574: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +`
- L600: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor`
- L626: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and`
- L686: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`

### `plugins/sea/CHANGELOG.md`

- L15: `Senior Engineering Architect — designs hardened architectures, audits brownfield code for primitive gaps, and decomposes…`

### `plugins/sea/README.md`

- L8: `SEA is the technical counterpart to [SRD](../srd/) — where SRD handles`
- L50: `| `/code-review <PR\|branch\|range>` | PR-scoped review implementing the Code Review Standard ([CR-01..CR-09](references…`
- L101: ``plugins/srd/references/change-work-standard.md`), SEA's artifacts`
- L298: `| `plugins/srd/references/pr-hygiene-standard.md` | The PR Hygiene Standard (PH-01..PH-08) — Scope / Size / Safety / Com…`

### `plugins/sea/agents/engineering-architect.md`

- L69: `See `plugins/srd/references/convention-preference-standard.md` for`
- L85: ``plugins/srd/references/founder-english.md``
- L112: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +`
- L138: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor`
- L165: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and`
- L231: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`

### `plugins/sea/references/code-review-standard.md`

- L259: ``plugins/srd/references/pr-hygiene-standard.md`.)`
- L357: ``plugins/srd/references/pr-hygiene-standard.md` (PH-01..PH-08) alongside`

### `plugins/sea/skills/blueprint/SKILL.md`

- L320: `- **No MISUSE_CASES.md when one is expected.** If `SRD.md` exists but `MISUSE_CASES.md` does not, the SRD was produced b…`

### `plugins/sea/skills/code-review/SKILL.md`

- L7: `Standard (PH-01..PH-08) at `plugins/srd/references/pr-hygiene-standard.md`.`
- L175: ``plugins/srd/references/pr-hygiene-standard.md` (PH-01..PH-08). Compute`
- L893: `- `plugins/srd/references/pr-hygiene-standard.md` — **PR Hygiene Standard** (PH-01..PH-08) applied via CR-09; Scope / Si…`

### `plugins/sea/skills/suggest-split/SKILL.md`

- L315: `- `plugins/srd/references/pr-hygiene-standard.md` — PH-01 Scope and`

### `plugins/sulis-builder/CHANGELOG.md`

- L15: `Self-service studio creation for the Outcome-First Methodology. Create new domain expertise packages (7-file studio bund…`

### `plugins/sulis-builder/agents/studio-builder.md`

- L47: `See `plugins/srd/references/convention-preference-standard.md` for`
- L61: ``plugins/srd/references/founder-english.md``
- L88: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +`
- L114: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor`
- L190: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`

### `plugins/sulis-design/CHANGELOG.md`

- L15: `Design studio for the Outcome-First Methodology. Provides design foundation, visual identity, customer experience, and d…`

### `plugins/sulis-design/agents/design.md`

- L58: `See `plugins/srd/references/convention-preference-standard.md` for`
- L72: ``plugins/srd/references/founder-english.md``
- L99: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +`
- L125: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor`
- L151: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and`
- L214: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`

### `plugins/sulis-execution/.architecture/hardening-deltas/HD-004-plugin-manifest-description-bloat.md`

- L37: `- `plugins/srd/CHANGELOG.md` — same migration`
- L45: `- `plugins/srd/.claude-plugin/plugin.json` — 5,353 → 288 chars`
- L95: `'plugins/srd/.claude-plugin/plugin.json',`

### `plugins/sulis-execution/sdk/docs/recipes/ship-change-end-to-end.md`

- L123: ``../../../../srd/references/change-work-standard.md``

### `plugins/sulis-product-development/CHANGELOG.md`

- L15: `Product development studio for the Outcome-First Methodology. Provides design, plan, implement, and complete skills for …`

### `plugins/sulis-product-development/agents/product.md`

- L70: `See `plugins/srd/references/convention-preference-standard.md` for`
- L84: ``plugins/srd/references/founder-english.md``
- L111: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +`
- L137: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor`
- L163: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and`
- L219: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`

### `plugins/sulis-security/CHANGELOG.md`

- L110: `Security & Viability Reviewer — runs a 25-primitive codebase viability assessment (security, data protection, code quali…`

### `plugins/sulis-security/agents/security-reviewer.md`

- L61: `See `plugins/srd/references/convention-preference-standard.md` for`
- L75: ``plugins/srd/references/founder-english.md``
- L102: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +`
- L128: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor`
- L153: `lexicon at `plugins/srd/references/audience-adapted-framing-standard.md``
- L218: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`

### `plugins/sulis-strategy/CHANGELOG.md`

- L15: `Business strategy studio for the Outcome-First Methodology. Provides vision, strategy, principles, commercial, GTM, and …`

### `plugins/sulis-strategy/agents/strategy.md`

- L54: `See `plugins/srd/references/convention-preference-standard.md` for`
- L68: ``plugins/srd/references/founder-english.md``
- L95: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +`
- L121: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor`
- L146: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and`
- L208: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`

### `plugins/sulis/CHANGELOG.md`

- L556: `| 4 — References | `5278a85` | `lifecycle.md` (2292 LOC), `primitive-scaffolds.md`, `self-heal-budget.md` moved; 4 cross…`

### `plugins/sulis/agents/context-cartographer.md`

- L64: `See `plugins/srd/references/convention-preference-standard.md` for`
- L89: `lexicon at `plugins/srd/references/audience-adapted-framing-standard.md``
- L148: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`

### `plugins/sulis/agents/executor.md`

- L63: `8. **`plugins/srd/references/git-workflow-standard.md`** — GIT-01..10:`
- L66: `9. **`plugins/srd/references/executor-loop-standard.md`** — EL-01..08:`
- L70: `11. **`plugins/srd/references/engineering-principles.md`** — EP-02`
- L73: `12. **`plugins/srd/references/convention-preference-standard.md`** —`

### `plugins/sulis/agents/orchestrator.md`

- L64: `4. **`plugins/srd/references/executor-loop-standard.md`** —`

### `plugins/sulis/agents/requirements-analyst.md`

- L93: `See `plugins/srd/references/convention-preference-standard.md` for`
- L107: ``plugins/srd/references/founder-english.md``
- L134: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +`
- L160: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor`
- L190: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03`
- L295: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`
- L613: ``plugins/srd/skills/srd-templates/SKILL.md` § RECONCILIATION_MAP template at`
- L835: ``plugins/srd/references/convention-preference-standard.md` → dominant industry`
- L1265: `in `plugins/srd/references/audience-adapted-framing-standard.md` before any`
- L1937: ``plugins/srd/references/convention-preference-standard.md` (canonical IETF/W3C/`
- L2178: ``plugins/srd/references/convention-preference-standard.md` — CP worked-examples`

### `plugins/sulis/agents/sulis.VERIFICATION_REPORT.md`

- L153: `| FE + AAF standards | `plugins/srd/references/{founder-english,audience-adapted-framing-standard}.md` | YES |`
- L158: `| requirements-analyst | `plugins/srd/agents/requirements-analyst.md` | YES |`

### `plugins/sulis/agents/sulis.md`

- L80: `skill: ../../srd/references/founder-english.md`
- L83: `skill: ../../srd/references/audience-adapted-framing-standard.md`
- L643: ``plugins/srd/references/founder-english.md`.`
- L662: `See `plugins/srd/references/convention-preference-standard.md` for`
- L675: ``plugins/srd/references/founder-english.md``
- L708: `See `plugins/srd/references/founder-english.md` for the full`
- L735: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03`
- L795: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the`
- L837: `| Internal IDs anywhere (UC-NN, WP-NN, ADR-NN, MUC-NN, FR-NN, NFR-NN, P15/P16, Tier 1-7) | AAF-03 violation | Translate …`
- L957: ``plugins/srd/references/audience-adapted-framing-standard.md` and the`
- L958: `project-specific table in `plugins/srd/references/founder-english.md`) or dropped.`
- L1072: `(per AAF-03 lexicon and `plugins/srd/references/founder-english.md`) or`
- L1147: `| 3 | **Specify** | Requirements, NFRs, use cases, glossary | `srd:requirements-analyst` — recommend `/srd:start` (alway…`
- L1194: `When you recommend `/srd:start`, tell the founder to run it from`
- L1369: `> *`/srd:start`*`
- L1389: ``/srd:requirements-validation` (the SRD's own gate).`

### `plugins/sulis/docs/change-as-primitive-design.md`

- L88: `The branch architecture is already specified by `CW-04` in the Change Work Standard (`plugins/srd/references/change-work…`
- L121: `Plus one clarifying amendment to `plugins/srd/references/repository-contract-standard.md` (`RC-04`): merge-queue source …`
- L218: `| Audience detection | **AAF** (existing — `plugins/srd/references/audience-adapted-framing-standard.md`) | Who am I tal…`
- L219: `| Vocabulary translation | **FE** (existing — `plugins/srd/references/founder-english.md`) | Have I stripped jargon, tra…`

### `plugins/sulis/docs/executor-research/agent-consumable-sdk-docs-spec.md`

- L613: `- [`plugins/srd/references/founder-english.md`](../../../srd/references/founder-english.md) — FE-04 (scannable in 30 sec…`
- L614: `- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-standard.md…`

### `plugins/sulis/docs/executor-research/agent-consumable-sdk-spec.md`

- L1036: `- [Sulis Convention Preference Standard (CP-01)](../../../srd/references/convention-preference-standard.md)`

### `plugins/sulis/docs/executor-research/agent-consumable-sdk-wpx-mapping.md`

- L914: `- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-standard.md…`
- L916: `- [`plugins/srd/references/change-work-standard.md`](../../../srd/references/change-work-standard.md)`

### `plugins/sulis/docs/executor-research/integration-change-review-prompt.md`

- L423: `- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-standard.md…`
- L424: `- [`plugins/srd/references/founder-english.md`](../../../srd/references/founder-english.md) — FE for plain-English outpu…`

### `plugins/sulis/docs/executor-research/sdk-implementation-validation-rubric.md`

- L592: `- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-standard.md…`

### `plugins/sulis/references/convention-preference-standard.md`

- L90: `OODA Reconciliation rule fires (see `plugins/srd/agents/requirements-analyst.md``

### `plugins/sulis/references/founder-english.md`

- L796: `> *When you're ready to answer, run `/srd:start`. I'll pick up`
- L847: `| 1.0.0 | 2026-05-19 | Promoted to marketplace-wide standard at `plugins/srd/references/founder-english.md`. Numbered as…`

### `plugins/sulis/references/founder-facing-conventions.md`

- L9: ``plugins/srd/references/founder-english.md`. This document is the`
- L307: `- Founder English standard: `plugins/srd/references/founder-english.md``

### `plugins/sulis/references/git-workflow-standard.md`

- L427: ``plugins/srd/references/` or `plugins/sea/references/` follow the`

### `plugins/sulis/references/journey-model.md`

- L88: `- Recommend `/srd:start` to the founder.`

### `plugins/sulis/references/lifecycle.md`

- L49: ``plugins/srd/references/change-work-standard.md`, every WP exists`

### `plugins/sulis/references/subagent-dispatch.md`

- L57: `| srd:requirements-analyst | `/srd:start` | recommend | recommend (always; long conversation) |`
- L58: `| srd:requirements-validation | `/srd:requirements-validation` | recommend | spawn (short, returns COMPLETENESS_REPORT.m…`

### `plugins/sulis/scripts/README.md`

- L138: `to dev). Per `plugins/srd/references/git-workflow-standard.md``

### `plugins/sulis/scripts/_wpxlib.py`

- L3039: `# The Change Work Standard at plugins/srd/references/change-work-standard.md`

### `plugins/sulis/scripts/sulis-change`

- L26: `Specification: plugins/srd/references/change-work-standard.md`
- L472: `"dedicated worktree. See plugins/srd/references/change-work-standard.md."`

### `plugins/sulis/skills/add-agent/VERIFICATION_REPORT.md`

- L164: `| requirements-analyst (example cited) | `plugins/srd/agents/requirements-analyst.md` | YES | |`

### `plugins/sulis/skills/add-agent/references/agent-shape-conventions.md`

- L246: `| Specialist facilitator | `plugins/srd/agents/requirements-analyst.md` |`

### `plugins/sulis/skills/check-readability/COMPLETENESS_REPORT.md`

- L42: `- `plugins/srd/references/founder-english.md` (36K) — FE-01..FE-11. Required for the founder-vocab translation in audien…`

### `plugins/sulis/skills/check-readability/references/founder-translation.md`

- L68: `- Terms in `plugins/srd/references/founder-english.md`'s glossary section`

### `plugins/sulis/skills/consolidate-into-sulis/SKILL.md`

- L389: `- **External ref rot is the silent killer.** A source plugin's reference is cited from CLAUDE.md at the repo root → move…`

### `plugins/sulis/skills/consolidate-into-sulis/references/external-ref-sweep.md`

- L28: `Pattern: descriptions sometimes cite `/sea:blueprint`, `/srd:critical-thinking`, etc. These break on consolidation.`

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/CONSOLIDATION_PLAN.md`

- L6: `**Source plugin:** `plugins/srd/``
- L116: `- [ ] `git mv plugins/srd/skills/codebase-mapping plugins/sulis/skills/codebase-mapping``
- L117: `- [ ] `git mv plugins/srd/skills/critical-thinking plugins/sulis/skills/critical-thinking``
- L118: `- [ ] `git mv plugins/srd/skills/requirements-validation plugins/sulis/skills/requirements-validation``
- L119: `- [ ] `git mv plugins/srd/skills/spec-index plugins/sulis/skills/index-specifications` (renamed)`
- L120: `- [ ] `git mv plugins/srd/skills/srd-templates plugins/sulis/skills/requirements-templates` (renamed)`
- L121: `- [ ] `git mv plugins/srd/skills/tree-synthesis plugins/sulis/skills/map-architecture` (renamed)`
- L129: `- [ ] `git mv plugins/srd/agents/requirements-analyst.md plugins/sulis/agents/requirements-analyst.md``
- L131: `- [ ] Sweep `/srd:requirements-analyst` references across marketplace if any (slash-command form sometimes used in narra…`
- L140: `- [ ] `git mv plugins/srd/references/audience-adapted-framing-standard.md plugins/sulis/references/``
- L141: `- [ ] `git mv plugins/srd/references/change-work-standard.md plugins/sulis/references/``
- L142: `- [ ] `git mv plugins/srd/references/coaching-without-conflict.md plugins/sulis/references/` (coexists with sulis/standa…`
- L143: `- [ ] `git mv plugins/srd/references/cognitive-load.md plugins/sulis/references/``
- L144: `- [ ] `git mv plugins/srd/references/content-quality.md plugins/sulis/references/``
- L145: `- [ ] `git mv plugins/srd/references/convention-preference-standard.md plugins/sulis/references/``
- L146: `- [ ] `git mv plugins/srd/references/engineering-principles.md plugins/sulis/references/``
- L147: `- [ ] `git mv plugins/srd/references/executor-loop-standard.md plugins/sulis/references/``
- L148: `- [ ] `git mv plugins/srd/references/founder-english.md plugins/sulis/references/``
- L149: `- [ ] `git mv plugins/srd/references/git-workflow-standard.md plugins/sulis/references/``
- L150: `- [ ] `git mv plugins/srd/references/pr-hygiene-standard.md plugins/sulis/references/``
- L151: `- [ ] `git mv plugins/srd/references/repository-contract-standard.md plugins/sulis/references/``
- L152: `- [ ] `git mv plugins/srd/references/security-standard.md plugins/sulis/references/``
- L154: `- [ ] CLAUDE.md needs 9 updates (`plugins/srd/references/...` → `plugins/sulis/references/...`)`
- L155: `- [ ] `git grep "plugins/srd/" .` after sweep returns only historical hits`
- L163: `- [ ] Mark `plugins/srd/.claude-plugin/plugin.json` DEPRECATED (version bump + description prefix + `deprecated: true`)`
- L164: `- [ ] `plugins/srd/CHANGELOG.md` final [DEPRECATED] entry naming the commit chain`
- L165: `- [ ] Rewrite `plugins/srd/README.md` with deprecation notice + what-moved-where + historical preservation`
- L166: `- [ ] `plugins/srd/settings.json` — review/remove if no longer needed (or leave as-is)`
- L188: `- **`/srd:requirements-analyst` slash-command form** — used in narrative ("escalate via `/srd:requirements-analyst`") bu…`

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/external-refs.md`

- L3: `All file paths and agent dispatch points that mention `plugins/srd/` or the source plugin's agents.`
- L10: `- L216: `| **Escalate to SRD** | `/srd:requirements-analyst` referral | When the gap is a missing requirement, not missi…`
- L14: `- L18: `5. **Escalate to SRD** (`/srd:requirements-analyst`)``
- L18: `- L12: `refer the user back to `/srd:requirements-analyst` when no``
- L19: `- L74: `1. **Run `/srd:requirements-analyst`** at `.specifications/sulis-checkup/`.``
- L20: `- L87: `4. **Run `/srd:requirements-validation`** for the five-perspective``
- L21: `- L119: `- Skill scope creep. `/sea:blueprint` is not `/srd:requirements-analyst`.``
- L29: `- L41: `1. Create a directory under `plugins/srd/skills/` named after the skill.``
- L30: `- L61: `3. Run the skill via its slash command (e.g. `/srd:critical-thinking`).``
- L31: `- L145: `For full detail on these principles, see `plugins/srd/references/engineering-principles.md`,``
- L32: `- L146: ``plugins/srd/references/security-standard.md`,``
- L33: `- L147: ``plugins/srd/references/convention-preference-standard.md`,``
- L34: `- L148: ``plugins/srd/references/audience-adapted-framing-standard.md`,``
- L35: `- L149: ``plugins/srd/references/git-workflow-standard.md` (GIT-01..GIT-10 —``
- L36: `- L153: ``plugins/srd/references/executor-loop-standard.md` (EL-01..EL-08 —``
- L37: `- L157: `and `plugins/srd/references/founder-english.md` (FE-01..FE-10 —``
- L41: `- L9: `plugins/srd/skills/your-skill-name/``
- L42: `- L22: `Reference standards live in `plugins/srd/references/` and define governing rules``
- L43: `- L59: `1. Create the file at `plugins/srd/references/your-standard.md`.``
- L44: `- L61: `3. Update `plugins/srd/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` with the``
- L48: `- L53: `| **[srd](plugins/srd/)** | Facilitates building the Software Requirements Document; also home of marketplace-wi…`
- L49: `- L73: `- `.specifications/{project}/SRD.md` — produced by `/srd:start```
- L50: `- L90: `/srd:start <project-slug>``
- L54: `- L26: `plugins/srd/skills/your-skill/``
- L62: `- L150: `| `plugins/srd/references/convention-preference-standard.md` (CP-) | Always recommend the established conventio…`
- L63: `- L151: `| `plugins/srd/references/audience-adapted-framing-standard.md` (AAF-) | Non-technical founder is the default a…`
- L64: `- L533: `See `plugins/srd/references/convention-preference-standard.md` for``
- L65: `- L547: ``plugins/srd/references/founder-english.md```
- L66: `- L574: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +``
- L67: `- L600: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor``
- L68: `- L626: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and``
- L69: `- L686: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L77: `- L8: `SEA is the technical counterpart to [SRD](../srd/) — where SRD handles``
- L79: `- L101: ``plugins/srd/references/change-work-standard.md`), SEA's artifacts``
- L80: `- L298: `| `plugins/srd/references/pr-hygiene-standard.md` | The PR Hygiene Standard (PH-01..PH-08) — Scope / Size / Saf…`
- L84: `- L69: `See `plugins/srd/references/convention-preference-standard.md` for``
- L85: `- L85: ``plugins/srd/references/founder-english.md```
- L86: `- L112: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +``
- L87: `- L138: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor``
- L88: `- L165: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and``
- L89: `- L231: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L93: `- L259: ``plugins/srd/references/pr-hygiene-standard.md`.)``
- L94: `- L357: ``plugins/srd/references/pr-hygiene-standard.md` (PH-01..PH-08) alongside``
- L102: `- L7: `Standard (PH-01..PH-08) at `plugins/srd/references/pr-hygiene-standard.md`.``
- L103: `- L175: ``plugins/srd/references/pr-hygiene-standard.md` (PH-01..PH-08). Compute``
- L104: `- L893: `- `plugins/srd/references/pr-hygiene-standard.md` — **PR Hygiene Standard** (PH-01..PH-08) applied via CR-09; S…`
- L108: `- L315: `- `plugins/srd/references/pr-hygiene-standard.md` — PH-01 Scope and``
- L116: `- L47: `See `plugins/srd/references/convention-preference-standard.md` for``
- L117: `- L61: ``plugins/srd/references/founder-english.md```
- L118: `- L88: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +``
- L119: `- L114: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor``
- L120: `- L190: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L128: `- L58: `See `plugins/srd/references/convention-preference-standard.md` for``
- L129: `- L72: ``plugins/srd/references/founder-english.md```
- L130: `- L99: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +``
- L131: `- L125: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor``
- L132: `- L151: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and``
- L133: `- L214: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L137: `- L37: `- `plugins/srd/CHANGELOG.md` — same migration``
- L138: `- L45: `- `plugins/srd/.claude-plugin/plugin.json` — 5,353 → 288 chars``
- L139: `- L95: `'plugins/srd/.claude-plugin/plugin.json',``
- L143: `- L123: ``../../../../srd/references/change-work-standard.md```
- L151: `- L70: `See `plugins/srd/references/convention-preference-standard.md` for``
- L152: `- L84: ``plugins/srd/references/founder-english.md```
- L153: `- L111: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +``
- L154: `- L137: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor``
- L155: `- L163: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and``
- L156: `- L219: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L164: `- L61: `See `plugins/srd/references/convention-preference-standard.md` for``
- L165: `- L75: ``plugins/srd/references/founder-english.md```
- L166: `- L102: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +``
- L167: `- L128: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor``
- L168: `- L153: `lexicon at `plugins/srd/references/audience-adapted-framing-standard.md```
- L169: `- L218: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L177: `- L54: `See `plugins/srd/references/convention-preference-standard.md` for``
- L178: `- L68: ``plugins/srd/references/founder-english.md```
- L179: `- L95: `See `plugins/srd/references/founder-english.md` for FE-01..FE-10 +``
- L180: `- L121: `See `plugins/srd/references/founder-english.md` (FE-11 + Anchor``
- L181: `- L146: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03 and``
- L182: `- L208: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L190: `- L64: `See `plugins/srd/references/convention-preference-standard.md` for``
- L191: `- L89: `lexicon at `plugins/srd/references/audience-adapted-framing-standard.md```
- L192: `- L148: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L196: `- L63: `8. **`plugins/srd/references/git-workflow-standard.md`** — GIT-01..10:``
- L197: `- L66: `9. **`plugins/srd/references/executor-loop-standard.md`** — EL-01..08:``
- L198: `- L70: `11. **`plugins/srd/references/engineering-principles.md`** — EP-02``
- L199: `- L73: `12. **`plugins/srd/references/convention-preference-standard.md`** —``
- L203: `- L64: `4. **`plugins/srd/references/executor-loop-standard.md`** —``
- L207: `- L153: `| FE + AAF standards | `plugins/srd/references/{founder-english,audience-adapted-framing-standard}.md` | YES |``
- L208: `- L158: `| requirements-analyst | `plugins/srd/agents/requirements-analyst.md` | YES |``
- L212: `- L80: `skill: ../../srd/references/founder-english.md``
- L213: `- L83: `skill: ../../srd/references/audience-adapted-framing-standard.md``
- L214: `- L92: `skill: ../../srd/agents/requirements-analyst``
- L215: `- L643: ``plugins/srd/references/founder-english.md`.``
- L216: `- L662: `See `plugins/srd/references/convention-preference-standard.md` for``
- L217: `- L675: ``plugins/srd/references/founder-english.md```
- L218: `- L708: `See `plugins/srd/references/founder-english.md` for the full``
- L219: `- L735: ``plugins/srd/references/audience-adapted-framing-standard.md` AAF-03``
- L220: `- L795: `See `plugins/srd/references/audience-adapted-framing-standard.md` for the``
- L222: `- L957: ``plugins/srd/references/audience-adapted-framing-standard.md` and the``
- L223: `- L958: `project-specific table in `plugins/srd/references/founder-english.md`) or dropped.``
- L224: `- L1072: `(per AAF-03 lexicon and `plugins/srd/references/founder-english.md`) or``
- L225: `- L1147: `| 3 | **Specify** | Requirements, NFRs, use cases, glossary | `srd:requirements-analyst` — recommend `/srd:sta…`
- L226: `- L1194: `When you recommend `/srd:start`, tell the founder to run it from``
- L227: `- L1369: `> *`/srd:start`*``
- L228: `- L1389: ``/srd:requirements-validation` (the SRD's own gate).``
- L232: `- L88: `The branch architecture is already specified by `CW-04` in the Change Work Standard (`plugins/srd/references/cha…`
- L233: `- L121: `Plus one clarifying amendment to `plugins/srd/references/repository-contract-standard.md` (`RC-04`): merge-queu…`
- L234: `- L218: `| Audience detection | **AAF** (existing — `plugins/srd/references/audience-adapted-framing-standard.md`) | Who…`
- L235: `- L219: `| Vocabulary translation | **FE** (existing — `plugins/srd/references/founder-english.md`) | Have I stripped ja…`
- L239: `- L613: `- [`plugins/srd/references/founder-english.md`](../../../srd/references/founder-english.md) — FE-04 (scannable …`
- L240: `- L614: `- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-st…`
- L244: `- L1036: `- [Sulis Convention Preference Standard (CP-01)](../../../srd/references/convention-preference-standard.md)``
- L248: `- L914: `- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-st…`
- L249: `- L916: `- [`plugins/srd/references/change-work-standard.md`](../../../srd/references/change-work-standard.md)``
- L253: `- L423: `- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-st…`
- L254: `- L424: `- [`plugins/srd/references/founder-english.md`](../../../srd/references/founder-english.md) — FE for plain-Engl…`
- L258: `- L592: `- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-st…`
- L262: `- L9: ``plugins/srd/references/founder-english.md`. This document is the``
- L263: `- L307: `- Founder English standard: `plugins/srd/references/founder-english.md```
- L267: `- L88: `- Recommend `/srd:start` to the founder.``
- L271: `- L49: ``plugins/srd/references/change-work-standard.md`, every WP exists``
- L275: `- L57: `| srd:requirements-analyst | `/srd:start` | recommend | recommend (always; long conversation) |``
- L276: `- L58: `| srd:requirements-validation | `/srd:requirements-validation` | recommend | spawn (short, returns COMPLETENESS_…`
- L280: `- L138: `to dev). Per `plugins/srd/references/git-workflow-standard.md```
- L284: `- L3039: `# The Change Work Standard at plugins/srd/references/change-work-standard.md``
- L288: `- L26: `Specification: plugins/srd/references/change-work-standard.md``
- L289: `- L472: `"dedicated worktree. See plugins/srd/references/change-work-standard.md."``
- L293: `- L164: `| requirements-analyst (example cited) | `plugins/srd/agents/requirements-analyst.md` | YES | |``
- L297: `- L246: `| Specialist facilitator | `plugins/srd/agents/requirements-analyst.md` |``
- L301: `- L42: `- `plugins/srd/references/founder-english.md` (36K) — FE-01..FE-11. Required for the founder-vocab translation i…`
- L305: `- L68: `- Terms in `plugins/srd/references/founder-english.md`'s glossary section``
- L313: `- L28: `Pattern: descriptions sometimes cite `/sea:blueprint`, `/srd:critical-thinking`, etc. These break on consolidati…`
- L317: `- L103: `| Plus: `plugins/sea/agents/*.md`, `plugins/sea/skills/*/SKILL.md`, `plugins/srd/agents/*.md` (4 slash-command …`
- L321: `- L21: `command being recommended (e.g. `/srd:start`, `/sea:blueprint`,``
- L325: `- L64: `*Source: prior-art* — `plugins/srd/references/founder-english.md` anchor cases 3 + 4. Mitigation: every display …`
- L330: `- L104: `pass the FE-06 check (see `plugins/srd/references/founder-english.md`).``
- L334: `- L57: ``/srd:requirements-analyst` or `/sea:blueprint` to fill them``
- L349: `git grep "plugins/srd/" .`

### `plugins/sulis/skills/consolidate-into-sulis/runs/sulis-context-2026-05-25/VERIFICATION_REPORT.md`

- L103: `| Plus: `plugins/sea/agents/*.md`, `plugins/sea/skills/*/SKILL.md`, `plugins/srd/agents/*.md` (4 slash-command hits) | —…`

### `plugins/sulis/skills/handoff/SKILL.md`

- L21: `command being recommended (e.g. `/srd:start`, `/sea:blueprint`,`

### `plugins/sulis/skills/inbox/COMPLETENESS_REPORT.md`

- L64: `*Source: prior-art* — `plugins/srd/references/founder-english.md` anchor cases 3 + 4. Mitigation: every display string p…`
- L105: `**Referenced files verified present:** Yes. SKILL.md references `references/sources-of-truth.md` (present), `plugins/srd…`

### `plugins/sulis/skills/inbox/SKILL.md`

- L104: `pass the FE-06 check (see `plugins/srd/references/founder-english.md`).`

### `plugins/sulis/skills/show-context/SKILL.md`

- L57: ``/srd:requirements-analyst` or `/sea:blueprint` to fill them`

## 2. Subagent_type dispatch references

None.

## 3. Sweep checklist (apply during Commits 2–4)

For each line above:
- Replace `plugins/{source}/` with `plugins/sulis/`
- Apply any skill / agent / reference renames from CONSOLIDATION_PLAN.md
- For subagent_type references: update to the new agent location after Commit 3 lands

After Commit 4:
```bash
git grep "plugins/srd/" .
# Expected: zero hits outside the source plugin's own DEPRECATED shell
```

## Summary

- Path references: **333** across **65** files
- Subagent_type references: **0** across **0** files

