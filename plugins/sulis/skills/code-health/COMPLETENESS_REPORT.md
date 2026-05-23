# Completeness Report — sulis:code-health

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run #3 of sulis:add-skill v0.4.0)
**Methodology:** `sulis:add-skill` v0.4.0 (five-gate)
**Source of design:** `.architecture/sulis-checkup/TDD.md` +
`.architecture/sulis-checkup/CTS-ANALYSIS.md`

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 description overlaps (4 coincidental, 1 expected parent-child with sulis:check-readability); 1 vocab collision on `tier` (disambiguated — three semantically distinct uses) |
| 2 — Scope Lock | PASS | 7 items locked. v1 wires tier 5 only; other 6 tiers stubbed as "not yet checked" |
| 3 — Generate | PASS | SKILL.md + scripts/orchestrator.py + references/tier-registry.md produced |
| 4 — Evaluate | PASS-with-note | Functional test: v1 orchestrator correctly invokes check-readability and renders tiered report; stubbed tiers visually distinct from passing tiers |
| 5 — Adversarial Review | PASS | 3 audience-agnostic + 3 of MUC-F1..F5 addressed; 2 OPEN_RISK documented |

**Publication decision:** APPROVED (v1 — 1 of 7 tiers wired; framework established for future tier additions)

---

## Gate 1 — Find

**Description overlaps:**

- `sea:code-review` (7 tokens) — per-PR review with multiple lenses; code-health is multi-tier comprehensive. Different scope/audience. Coincidental.
- `sulis:check-readability` (7 tokens) — **expected parent-child relationship**; code-health wraps check-readability for tier 5. Resolved via "When NOT to invoke" section pointing to check-readability for single-tier use.
- `sea:suggest-split` (6 tokens) — splits PRs; orthogonal. Coincidental.
- `sea:probe` (5 tokens) — raw structural analysis. Coincidental.
- `sea:verify` (4 tokens) — post-WP architecture completeness. Different focus.

**Vocabulary collisions:** 1 — `tier`.

- `idc:market-research` uses "tier" for research source tiers (Tier 1 / Tier 2 sources)
- `sea:code-review` uses "tier" for report tiers (tier-1 founder, tier-2 technical)
- `sulis:code-health` uses "tier" for Maslow-for-code levels (1 Exists, 2 Safe, ..., 7 Polished)

All three are semantically distinct. Resolution: explicit definition in Vocabulary section; document the three marketplace uses of "tier" so future authors don't conflate.

**No existing skill covers** a multi-tier comprehensive code-health wrapper.

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `code-health` |
| Plugin home | `sulis` (canonical front-door) |
| Audience | **both**. Founder default; `--raw` flag for operator JSON output. Mode-selection: explicit-flag (same pattern as check-readability) |
| Category | **Founder UX & Navigation** (specifically wrapper-shape, per the dogfood gap noted in v0.4.0) |
| Trigger condition | "Use when the founder wants to know if everything is OK — runs a comprehensive code-health check across multiple tiers (safety, works, reliability, readability, maintainability) and produces one prioritised report. Read-only; never modifies code." |
| Top-5 gotchas | (below) |
| Depth modes | None for v1. (Future: `quick` = top-line per tier only; `full` = expanded per-tier findings.) |

### Top-5 gotchas (with concrete source)

1. **Stubbed tiers vs passing tiers must be visually distinct.** A "not yet checked" tier looks like "passing" if rendered with the same colour. Founder sees 6 green lights, thinks everything passes — but 5 are "we didn't look."
   *Source: author-experience* — the canonical UX failure for any partial-coverage check. Mitigation: explicit `⏳ not yet checked` badge with distinct styling vs `✅ passed` and `❌ failed`.

2. **Don't fabricate verdicts for stubbed tiers.** Tempting to mark them "presumed pass" so the report looks cleaner. They're NOT checked. Honesty matters.
   *Source: founder-facing-conventions Rule 5 (errors explain what + what-to-do) — applies equally to "I didn't check this."* Mitigation: stubbed tiers explicitly report "not yet checked — planned for v{N}".

3. **Tier-gating is no-op until tiers 1+2 wired.** Tier-gating ("hard-stop on tier 1/2 critical") was specified in `.architecture/sulis-checkup/TDD.md` ADR-002. In v1, tiers 1+2 aren't wired, so the rule literally never fires. Document explicitly so future readers don't think gating logic is broken.
   *Source: this skill's own scope* — v1 ships 1/7 tiers; gating is forward-architecture, not active logic.

4. **Founder might press [N] expecting code-health to fix.** Same destructive-action ambiguity as check-readability — the founder sees suggestions and assumes Claude will act.
   *Source: founder-facing-conventions Rule 3; check-readability gotcha #5 (PREVENTED)* — Mitigation: explicit "this skill never modifies code — only reports" in three places (description, gotchas, when-NOT-to-invoke).

5. **Tier-name jargon leakage.** Tier names ("Exists / Safe / Works / Survives / Understandable / Evolves / Polished") were workshopped to be founder-vocab. The operator-side primitive names (MEA-04, CQ-01, SEC-07) MUST NOT appear in founder mode.
   *Source: founder-translation.md from check-readability* — Mitigation: tier-registry.md table mapping operator-primitive-IDs to founder-readable tier names; SKILL.md presentation template uses founder names only.

### Vocabulary terms introduced

- **code-health** — the umbrella property this skill measures. Multi-tier well-formedness of a codebase.
- **tier** — a Maslow-for-code level (1 through 7). Disambiguates from `idc:market-research`'s research-source tiers and `sea:code-review`'s report tiers.
- **checkup** — the report produced by this skill (tiered traffic-light + findings).
- **tier-gating** — the rule that lower-tier failures de-prioritise higher tiers. Forward-architecture per `.architecture/sulis-checkup/TDD.md` ADR-002; no-op in v1 (tiers 1+2 not wired).
- **not-yet-checked** — explicit state for tiers without operator-skills wired. Distinct from "passed" and "failed." Always renders with `⏳` badge.

---

## Gate 3 — Generate

**Files produced:**

- `plugins/sulis/skills/code-health/SKILL.md` — entrypoint; tier-walking flow; tier registry; two-mode output; gotchas; vocabulary; when-to/when-not-to
- `plugins/sulis/skills/code-health/scripts/orchestrator.py` — walks tier registry; invokes wired tier skills; collects findings; renders CHECKUP.md
- `plugins/sulis/skills/code-health/references/tier-registry.md` — the canonical list of 7 tiers; per-tier metadata (name, founder description, wired-status, operator-skill, founder-skill); v1 marks 6 of 7 as `not_yet_wired`
- `plugins/sulis/skills/code-health/COMPLETENESS_REPORT.md` — this file

**Scope lock adherence:** verified. All 7 Gate 2 items reflected in files; founder-mode/operator-mode split via `--raw` flag matches check-readability convention; tier-registry as a separate reference document allows future-tier additions to update the registry without modifying SKILL.md.

**Referenced files verified present:**

- `plugins/sulis/skills/check-readability/SKILL.md` (the only wired tier — tier 5) — exists
- `plugins/sulis/skills/check-readability/scripts/audit.py` — exists; orchestrator invokes via subprocess
- `plugins/sulis/references/founder-facing-conventions.md` — exists
- `.architecture/sulis-checkup/TDD.md` — exists (cited as design source)

---

## Gate 4 — Evaluate

### Perspective 1 — Trigger accuracy

**Verdict:** PASS

**Method:** mental walkthrough of 10 representative invocations.

| Scenario | Should trigger? | Likely to trigger? |
|---|---|---|
| "is everything OK?" | YES | YES (verbatim trigger) |
| "give me a full code-health check" | YES | YES |
| "check the codebase comprehensively" | YES | YES |
| "is my code in good shape?" | YES | YES |
| "is the code readable?" | NO → use check-readability single-tier | maybe (description mentions readability; could trigger; not catastrophic — code-health includes readability as one tier) |
| "is the code secure?" | NO (tier 2 not wired yet; would mislead) | maybe (description mentions safety) |
| "run the tests" | NO | NO |
| "what's blocking the build?" | NO (→ sulis:inbox or check-build) | NO |
| "show me the inbox" | NO | NO |
| "deploy this" | NO | NO |

**Result:** ~80-85% precision. The two ambiguous cases ("is my code readable?" and "is my code secure?") are real — code-health does include those concerns but as ONE tier each. Mitigation in SKILL.md "When NOT to invoke": point to check-readability for single-tier reads; point to check-security (future) for security-only.

### Perspective 2 — Gotchas coverage

**Verdict:** PASS

All 5 gotchas have documented sources:
- Stubbed vs passing distinction → author-experience (canonical partial-coverage UX failure)
- Don't fabricate verdicts → founder-facing-conventions Rule 5
- Tier-gating no-op in v1 → this skill's scope (1/7 tiers)
- Destructive-action ambiguity → check-readability gotcha #5 (cross-skill prior art)
- Tier-name jargon leakage → founder-translation.md prior art

5 items, ordered by likelihood × impact (stubbed-vs-passing is highest — direct misreading; jargon-leakage is lowest — UX polish).

### Perspective 3 — Functional completeness

**Verdict:** PASS

**Scenarios tested:**

1. **v1 against this marketplace (codebase scope).** orchestrator.py invokes check-readability tier successfully; collects findings (13 from check-readability's audit); renders CHECKUP.md with tier 5 result + 6 stubbed tiers visually distinct.

2. **Stubbed-tier rendering distinct from passing-tier rendering.** Tier 1-4, 6, 7 show `⏳ not yet checked (planned)`; tier 5 shows `🟡 needs attention` (because of the `_wpxlib.py` kitchen-sink finding). Clearly distinct.

3. **--raw mode produces operator JSON.** Validates structure for future tier-additions.

**Failure modes captured:** none new. v1's tier-5-only scope limits what could fail.

---

## Gate 5 — Adversarial Review

### MUC-F1: Operator jargon leak in error string — PREVENTED

- **What Claude might do wrong:** orchestrator can't find a wired tier's script; raw subprocess error bubbles up.
- **Mitigation:** orchestrator catches subprocess errors per tier; renders founder-readable "couldn't check this tier — see logs for details" in founder mode; raw error in `--raw` mode.

### MUC-F3: Destructive action triggered by ambiguous founder phrasing — PREVENTED

- **What Claude might do wrong:** founder says "fix the readability issues" after reading the report; Claude treats it as authorisation to edit code.
- **Mitigation:** SKILL.md says "this skill never modifies code — only reports" in three places. Any fix is a separate action requiring its own explicit founder consent.

### MUC-F4: Number-of-items overwhelm — PARTIALLY PREVENTED

- **What Claude might do wrong:** when more tiers are wired, the CHECKUP.md grows to hundreds of findings.
- **Mitigation in v1:** only 13 findings (from check-readability's tier 5); well below overwhelm.
- **OPEN_RISK for v2+:** when tier 2 (security ~16 findings) + tier 4 (reliability) + tier 6 (maintainability) wire in, total finding count could exceed 50.
  - **revisit_by:** trigger — "second tier wired, total findings >30 on any real project"
  - **Mitigation in the meantime:** "summary line per tier + drill-down" report shape is already in place; expanding tier sections will be a presentation-template iteration.

### Audience-agnostic — Trigger condition matches too broadly — PARTIALLY PREVENTED

- **What Claude might do wrong:** "is my code secure?" triggers code-health which then reports tier 2 is "not yet checked" — founder gets less than they asked for.
- **Mitigation:** SKILL.md's "When NOT to invoke" explicitly points to check-readability for single-tier and (future) check-security for tier 2.
- **OPEN_RISK:** until check-security and other single-tier skills exist, code-health is the only entry point for those concerns.
  - **revisit_by:** trigger — "check-security or another single-tier skill ships"
  - **Mitigation in the meantime:** stubbed-tier renders explicitly say "tier 2 (Safe) check not yet built — will land in a future release."

### Audience-agnostic — Premature reference commitment — PREVENTED

- **Mitigation:** the only wrapped reference is `.architecture/sulis-checkup/TDD.md` (cited as design source). No version coupling; the TDD is internal artefact.

### Audience-agnostic — Silent failure of progressive disclosure — PREVENTED

- **Mitigation:** Gate 3 verified all referenced files exist; tier-registry.md cross-references the tier-skills.

---

## Open risks accepted at publication

1. **Overwhelm risk when more tiers wire (MUC-F4 partial).** Single-tier v1 is fine; 50+ findings post-wave-2 may overwhelm. **revisit_by:** trigger — second tier wired AND >30 total findings on real project. **Workaround:** SKILL.md gotcha #1 (stubbed-vs-passing distinct rendering) helps founders mentally model what's checked.

2. **Single-tier scope masks scope-overlap with future single-tier skills.** Founders asking "is the code secure?" get code-health which reports tier 2 stubbed. **revisit_by:** trigger — check-security or any single-tier skill ships. **Workaround:** stubbed-tier rendering explicitly names what's not built yet.

---

## Vocabulary changes (during authoring)

None — vocabulary locked at Gate 2 used unchanged through Gate 3.

---

## Methodology feedback (running notes for add-skill v0.5.0)

Gaps surfaced during this run:

1. **Wrapper-pattern skills are a sub-family** (third confirmation, alongside aggregator-pattern from inbox and audit-pattern from check-readability). Wrapper shared concerns: stubbed-vs-active state rendering, tier-registry separation from skill body, subprocess invocation of underlying skills with error translation. Worth a Pattern entry in methodology.md.

2. **Scope auto-detection is the THIRD instance of this same pattern.** Both check-readability and code-health (and inbox indirectly) use git-state-based scope detection. The pattern is reusable: `if --pr-number: gh; elif --scope: explicit; else: detect from HEAD divergence`. Worth extracting into a shared helper available to all founder skills.

3. **Three uses of "tier" in the marketplace** is a marketplace-vocabulary smell. `idc:market-research` (source tiers), `sea:code-review` (report tiers), `sulis:code-health` (Maslow tiers). Not a problem because the contexts are non-overlapping, but if any context expands, collision risk rises. Worth tracking in a marketplace-level vocabulary registry.

4. **Stubbed-tier rendering** is the wrapper-pattern's MUC-F-equivalent — partial-coverage skills always face this. Worth promoting to a sixth audience-conditional MUC (MUC-F6: stubbed-vs-active distinction) in add-skill v0.5.0.

(These 4 join the 5 from check-readability and 2 from inbox = 11 methodology gaps queued for add-skill v0.5.0.)