# VERIFICATION_REPORT.md — sulis:consolidate-into-sulis

**Skill:** `plugins/sulis/skills/consolidate-into-sulis`
**Iteration:** 1 (first run — Greenfield mode)
**Produced:** 2026-05-25
**Methodology:** `sulis:add-skill` v0.7.0 applied to author consolidate-into-sulis

---

## Spiral Summary

**Tier:** heavy
**Template base:** HEAVY_TIER_DEFAULT
**Iterations used:** 1
**Termination reason:** sufficient (all thresholds met on first iteration; 5 advisory refinements from Independence Check all applied)
**Verdict:** PASS

**Publication decision:** APPROVED

---

## Gate 1 — Find (BI / SI / CC + Primitive Discovery)

**BRIEF_PACK generated:** ran `python3 plugins/sulis/skills/add-skill/scripts/inventory.py --marketplace-root . --target-plugin sulis --target-skill consolidate-into-sulis --proposed-description "Use when folding a specialist plugin into sulis — runs the proven 5-commit recipe (scripts+CI / skills / agents / references / wrap-up) with collision detection and external ref sweep." --proposed-vocabulary "consolidation, source plugin, collision rename, external ref sweep, DEPRECATED shell, qualifier rename, wrap-up commit"`. Output covered 90 skills across 11 plugins + 68 reference files.

**BI counter-search performed:** yes

- Searched `grep -rli "consolidat" plugins/*/skills/*/SKILL.md` — matched 4 unrelated skills (add-agent body mentions consolidation; business-strategy:context; feature-lifecycle; ivs-authoring) — none cover plugin consolidation
- Searched `grep -rli "plugin.*migration\|fold.*into\|move.*plugin"` — matched 5 references and skills mentioning migration tangentially; none codify plugin consolidation
- Searched `find docs plugins/*/docs -name "*.md"` for prior consolidation docs — only `plugins/sulis/docs/change-as-primitive-design.md` (Phase 3 narrative) and `plugins/sulis/docs/executor-e2e-test.md` (the precedent's own test doc) — confirms greenfield

**SI verification:** 4 standards cited from sulis (CRITICAL_THINKING, DECOMPOSITION_PROCEDURE, SPIRAL_TEMPLATES, REFERENTIAL_INTEGRITY); 2 sibling skills cited (add-skill, add-agent, code-health). All independent — no echo chamber.

**CC verdict on "no existing skill covers this":** VALIDATED (5+ checks: marketplace skill inventory, BI counter-searches across `consolidat`/`migration`/`fold-into` patterns, design doc Phase 3 narrative, executor-e2e-test.md prior-art review)

**"Could this be a skill instead?" answered:** YES — runbook-pattern skill. Not an agent (no conversational context needed; deterministic ops). Not a slash command alone (slash commands invoke skills).

### Primitive Discovery

**Level of analysis:** the 7-gate consolidation sequence (Gate 0 + Commits 1-5 + Gate 6)

**Primitives identified:**

| Primitive | Provenance | Independence test | Termination test |
|---|---|---|---|
| Gate 0 — Inventory + Plan + Baseline | extracted (from precedent + design doc Phase 3) | PASS — independently changeable (helper scripts evolve without affecting commit gates) | PASS — further decomposition would make sub-steps not separate primitives |
| Commit 1 — scripts + tests + CI | extracted (precedent commit `02c1e77`) | PASS | PASS |
| Commit 2 — skills (with tin-test rename) | extracted (precedent commit `6621e5b`) | PASS | PASS |
| Commit 3 — agents (with subagent_type sweep) | extracted (precedent commit `99607e8`) | PASS | PASS |
| Commit 4 — references (with external ref sweep) | extracted (precedent commit `5278a85`) | PASS | PASS |
| Commit 5 — wrap-up (docs + DEPRECATED + bumps) | extracted (precedent commit `fa882b1`) | PASS | PASS |
| Gate 6 — code-health verification | inferred (new — was informal in precedent) | PASS — independently optional but mandatory at HEAVY tier | PASS |

**Dependencies (typed per PD-05):** each Commit N `depends_on` Gate 0; Commit N+1 `depends_on` Commit N (sequential); Gate 6 `depends_on` Commit 5; all primitives `conflicts_with` running another consolidation in parallel.

**Scale check (PD-02):** fan-out = 7 (one Gate 0 + 5 commits + Gate 6) ≤ 7 ✓; depth = 2 (gate → sub-step) ≤ 5 ✓

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `consolidate-into-sulis` |
| Plugin home | `sulis` |
| Audience | **operator-facing** (founder doesn't run; sulis-agent or operator does; output is git commits not chat) |
| Category | Runbook (operator-facing) |
| Trigger condition | "Use when folding a specialist plugin into the sulis plugin — runs the proven 5-commit recipe (scripts+CI / skills / agents / references / wrap-up) with code-health gating, deterministic helpers for inventory and collision detection, and a tin-test rename pass on incoming founder-visible skill names." |
| Standards-phase classification | input: REFERENTIAL_INTEGRITY_STANDARD / processing: CRITICAL_THINKING_STANDARD + DECOMPOSITION_PROCEDURE / output: CRITICAL_THINKING_STANDARD (no COACHING/TONE — operator-facing) |
| Verification tier | HEAVY (methodology skill; Independence Check is high-value first-of-kind) |
| Tool stack | None in the audit sense; uses bash + git + grep + find + python3 + jq + 4 helper scripts in this skill's own scripts/ — operator runbook, not audit scanner |
| Top-N gotchas | 7 gotchas — each grounded in either precedent commit narratives or the proven failure modes in the sulis-execution → sulis migration |
| Related skills + agents | depends_on: add-skill + code-health + 4 standards; related_to: add-agent (sibling) |
| Depth modes | none (single mode — the 5-commit recipe with mandatory verification gates) |
| Mode-selection strategy | N/A |

**Vocabulary terms introduced:** 7 terms (Source plugin, Tin test, External ref sweep, Qualifier rename, DEPRECATED shell, Code-health gate, Run directory)

---

## Gate 3 — Generate

**Files produced:**

- `plugins/sulis/skills/consolidate-into-sulis/SKILL.md` (~470 LOC after refinements)
- `plugins/sulis/skills/consolidate-into-sulis/references/methodology.md` (~125 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/references/conflict-resolution.md` (~145 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/references/external-ref-sweep.md` (~175 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/references/code-health-gating.md` (~140 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/templates/CONSOLIDATION_PLAN.md.template` (~140 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/templates/VERIFICATION_REPORT.md.template` (~150 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/scripts/inventory.py` (~110 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/scripts/detect_collisions.py` (~210 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/scripts/find_external_refs.py` (~190 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/scripts/compare_baseline.py` (~175 LOC)
- `plugins/sulis/skills/consolidate-into-sulis/runs/` (empty placeholder for per-consolidation outputs)

**Scope lock adherence:** all 12 Gate 2 items reflected in SKILL.md and supporting files. No drift.

**Frontmatter validation:**

- `standards:` block present + parses ✓
- `verification_spiral:` block present + parses (HEAVY tier with 2 custom dimensions, both with principle_reference) ✓
- `related_skills:` block present + parses ✓
- No `register:` block (operator-facing, single-register; no founder-mode obligation)

**Pyramid structure:** SKILL.md leads with `## Conclusion (Pyramid Principle — lead with the answer)` stating the 5-commit + 2-gate methodology before any detail ✓

**Linguistic audit (NH-02):** zero prohibited terms detected. Manual scan for "comprehensive", "robust", "powerful", "magic", "leverage", "seamless", "revolutionary", "game-changing", "amazing", "incredible", "utilize" — none present.

**Smoke tests against sulis-context (first Phase 3 consolidation target):**

- `inventory.py` → produced clean JSON (3 skills, 1 agent, 3 references)
- `detect_collisions.py` → found 0 direct collisions, **3 tin-test failures** (`discover`, `refresh`, `show` — all bare verbs); matches the rename table in `references/conflict-resolution.md`
- `find_external_refs.py` → initially 4 refs; **caught a bug** during smoke (missed `../../sulis-context/` relative-path refs in `related_skills:` blocks); fixed (now catches both absolute `plugins/{source}/` and relative `(../)+{source}/` patterns); re-run found 5 refs across 5 files

**Referenced files verified present:** YES — Independence Check confirmed all cited paths exist (see Gate 4 Codebase Referential Integrity below).

---

## Gate 4 — Evaluate (Spiral Verification)

**Scoring source:** Independence Check sub-agent (Agent subagent_type=Explore in fresh context, no access to author reasoning).

### ACCA (required all tiers)

| Sub-dimension | Threshold | Score | Evidence (from Independence Check) |
|---|---|---|---|
| Accurate | >= 4 | 5 | Every claim cites specific evidence: precedent commits 02c1e77..fa882b1 verified; SKILL.md lines 50-61 ground 7-gate recipe in sulis-execution migration; all 4 scripts exist on disk |
| Clear | >= 4 | 5 | Unambiguous language; each gate has explicit pass criteria; vocabulary defined; gotchas list concrete failure modes with precedent citations (commit 5278a85) |
| Complete | >= 4 | 5 | All required sections present (Conclusion, recipe table, preconditions, 7 gates each with sub-steps, publishing, gotchas, vocabulary, invocation criteria); no TODOs |
| Actionable | >= 4 | 5 | Copy-paste-ready commands throughout; every pass criterion mechanically evaluable; templates provided for both run artifacts |

**ACCA minimum:** 5/5 — **PASS**

### Evidence Grounding (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **4/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (BI, SI, AT-01)
**Evidence:** BI grounded in single deeply-examined precedent (02c1e77..fa882b1); counter-evidence implicit (methodology.md lines 33-40 enumerate four regression sources). SI: precedent is a primary source (actual commit chain); no echo-chamber sources. AT-01: skill states adversarial assumptions (methodology.md line 9: "every plugin has shape variations the script can't predict"). Minor gap: no explicit counter-search for "are there other consolidation recipes used elsewhere?" — low-risk given precedent is proven and Phase 3 adoption is planned.

### Structural Coherence (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **5/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (MECE, PP, DF)
**Evidence:** MECE — 5-commit recipe is mutually exclusive (each commit moves one artifact category) and collectively exhaustive (scripts, skills, agents, references, wrap-up covers all plugin contents). Pyramid — SKILL.md leads with the conclusion, then supports with recipe table, then per-gate details. DF (SCQA): complication clearly stated (50 files, 0-finding self-test precedent); question implicit; answer is the runbook.

### Honest Uncertainty (STANDARD + HEAVY)

**Threshold:** >= 3/5 — Score: **4/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (HU, CC)
**Evidence:** Skill explicitly flags open questions and deferrals: `--auto` flag deferred (methodology.md lines 88-95); "first 4 Phase 3 consolidations are the calibration dataset" (code-health-gating.md); rollback threshold introduced via refinement 4. CC: HIGH confidence on precedent (one proven migration with audit trail); MEDIUM on generalisation (four upcoming consolidations are the test set).

### Codebase Referential Integrity (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **5/5**
**Standard reference:** SPIRAL_TEMPLATES.md (derived from platform ADR-164)
**Evidence (per pre-existing entity named):**

| Entity | Path | Verified exists |
|---|---|---|
| Precedent commit 02c1e77 | `git log --oneline 02c1e77` | YES |
| Precedent commit fa882b1 | `git log --oneline fa882b1` | YES |
| CRITICAL_THINKING_STANDARD | `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md` | YES |
| DECOMPOSITION_PROCEDURE | `plugins/sulis/references/standards/DECOMPOSITION_PROCEDURE.md` | YES |
| SPIRAL_TEMPLATES | `plugins/sulis/references/standards/SPIRAL_TEMPLATES.md` | YES |
| REFERENTIAL_INTEGRITY_STANDARD | `plugins/sulis/references/standards/REFERENTIAL_INTEGRITY_STANDARD.md` | YES |
| add-skill | `plugins/sulis/skills/add-skill/SKILL.md` | YES |
| add-agent | `plugins/sulis/skills/add-agent/SKILL.md` | YES |
| code-health | `plugins/sulis/skills/code-health/SKILL.md` | YES |
| inventory.py (this skill) | `plugins/sulis/skills/consolidate-into-sulis/scripts/inventory.py` | YES |
| detect_collisions.py (this skill) | `plugins/sulis/skills/consolidate-into-sulis/scripts/detect_collisions.py` | YES |
| find_external_refs.py (this skill) | `plugins/sulis/skills/consolidate-into-sulis/scripts/find_external_refs.py` | YES |
| compare_baseline.py (this skill) | `plugins/sulis/skills/consolidate-into-sulis/scripts/compare_baseline.py` | YES |
| CONSOLIDATION_PLAN.md.template | `plugins/sulis/skills/consolidate-into-sulis/templates/CONSOLIDATION_PLAN.md.template` | YES |
| VERIFICATION_REPORT.md.template | `plugins/sulis/skills/consolidate-into-sulis/templates/VERIFICATION_REPORT.md.template` | YES |

No unresolved citations. No hallucinated entities.

### Outcome-Specific Rigor (HEAVY only) — three sub-perspectives

#### Sub-perspective 1 — Recipe-trigger precision

**Verdict:** PASS — Score: **4/5**
**Result:** Description routes correctly for "fold plugin X into sulis", "consolidate sulis-context", "Phase 3 plugin migration"; possibly under-dispatches for non-plugin migrations or partial moves (correctly handled by `When NOT to invoke` section).

#### Sub-perspective 2 — Internal consistency

**Verdict:** PASS — Score: **5/5**
**Result:** Every script invocation in SKILL.md uses paths matching actual files on disk; every step's pass criteria can be evaluated mechanically (e.g., `find plugins/{source}/scripts -type f returns empty`); templates provided for the two run artifacts.

#### Sub-perspective 3 — Functional completeness (smoke test)

**Verdict:** PASS — Score: **5/5**
**Result:** Smoke-tested against sulis-context. Scripts produce expected output shapes; CONSOLIDATION_PLAN.md template is populatable from the script outputs; one bug found and fixed (relative-path refs); re-run confirmed.

**Outcome-Specific Rigor aggregate:** 4/5 (min of sub-perspectives)

### Custom Dimensions

#### Recipe Self-Consistency (Custom Dimension 7)

**Threshold:** >= 4/5 — Score: **5/5**
**Standard reference:** SKILL.md applied to sulis-execution → sulis precedent
**Principle reference:** CRITICAL_THINKING_STANDARD BI-01
**Evidence:** Each gate/commit in SKILL.md maps exactly to a real move in the precedent — verified by Independence Check via `git log` on commits `02c1e77`, `6621e5b`, `99607e8`, `5278a85`, `fa882b1`. Every gate grounds in the precedent; no shortcuts; no undocumented assumptions.

#### Code-Health Gate Effectiveness (Custom Dimension 8)

**Threshold:** >= 4/5 — Score: **5/5**
**Standard reference:** Gate 0 + Gate 6 must catch regression types
**Principle reference:** CRITICAL_THINKING_STANDARD AT-01
**Evidence:** Gate 0 baseline + Gate 6 verification cover all 5 regression types named in `code-health-gating.md`: broken imports (check-build), path drift (check-readability), coverage drop (check-tests), lint regression (all tiers), security finding (check-security). Rollback-vs-fix-forward threshold added per refinement 4.

### Independence Check (HEAVY only)

**Threshold:** >= 3/5 — Score: **5/5**
**Scorer:** Agent (subagent_type=Explore) in fresh context (no access to author reasoning)
**Sub-agent verdict:** PASS across all dimensions
**Independence Check report:** captured at task ID `ab0959fde044083cc` (in-session transcript)

**Five refinements identified by Independence Check (all applied in v0.1.0):**

1. ✅ Added explicit `git log --oneline 02c1e77^..fa882b1` verifier in SKILL.md Conclusion
2. ✅ Added "Step numbering note" clarifying 5-commit recipe vs precedent's step-N/8 labelling
3. ✅ Added inline note in sub-step 0c documenting the `inventory.json .agents` field format + the relative-path bug-fix narrative
4. ✅ Added "Fix-forward vs rollback" subsection at end of Gate 6 with > 3 fix-forward = rollback threshold
5. ✅ Added `<!-- Template syntax: manual substitution -->` HTML comment to both templates

---

## Gate 5 — Adversarial Review (AT / FR)

### Audience-agnostic misuse cases

#### Misuse case 1: External ref left behind

- **What might go wrong:** A reference cited from CLAUDE.md or another plugin's reference doc is missed during the sweep — silent break on dispatch or read
- **Status:** PREVENTED
- **Mitigation:** `find_external_refs.py` catches both absolute (`plugins/{source}/`) and relative (`(../)+{source}/`) patterns; Commit 4 pass criteria requires `git grep "plugins/{source}/" .` to return zero non-historical hits; bug-fix during smoke test confirmed the relative-path catch works

#### Misuse case 2: Subagent_type silent break

- **What might go wrong:** Renaming an agent in Commit 3 without sweeping every dispatch site means Sulis dispatches to a nonexistent agent at runtime
- **Status:** PREVENTED
- **Mitigation:** `find_external_refs.py` enumerates every subagent_type dispatch site; Commit 3 pass criteria includes manual smoke test (invoke agent once after move)

#### Misuse case 3: Tin-test rename without description rewrite

- **What might go wrong:** Skill is renamed but the SKILL.md `description:` field still references the old name's vocabulary — founder reads the description and is confused
- **Status:** PREVENTED
- **Mitigation:** Commit 2 edit pass explicitly includes description verification; `references/conflict-resolution.md` contains the description-rewrite rubric with worked example for `decompose` → `plan-work`

#### Misuse case 4: Atomic commits violated under pressure

- **What might go wrong:** Operator batches Commits 2-4 to "save time", losing reviewability and rollback safety
- **Status:** PREVENTED
- **Mitigation:** SKILL.md preconditions + gate-level pass criteria require per-commit verification; methodology.md §"Why no `--auto` flag" explains the discipline rationale

#### Misuse case 5: Code-health baseline drift

- **What might go wrong:** Stale baseline from a prior session is reused, false negatives mask real regressions
- **Status:** PREVENTED
- **Mitigation:** Gate 0 sub-step 0d explicitly captures a fresh baseline in the run directory at consolidation start; baseline path is per-run, not global

### Open risks

#### Risk 1: Recipe generalisation beyond the 4 Phase 3 plugins

- **Description:** The recipe is calibrated against one proven precedent (sulis-execution) and four upcoming consolidations (sulis-context, sulis-security, sea, srd). A future "Plugin X" with unusual shape (e.g., complex scripts, cross-plugin shared infrastructure, non-standard manifests) may expose recipe gaps.
- **Why accepted:** Phase 3 is explicitly the calibration data set; v0.2.0 incorporates learnings. Recipe-improvement signal threshold (> 3 fix-forward commits per consolidation) catches this proactively.
- **revisit_by:** event — after Phase 3 (4 consolidations) is complete; recipe revision lands as v0.2.0 if patterns warrant

#### Risk 2: code-health JSON shape evolution

- **Description:** `compare_baseline.py` uses a best-effort signature function for findings. If the `/sulis:code-health --raw` JSON shape changes materially, comparison may produce false positives or miss real regressions.
- **Why accepted:** Code-health JSON is currently stable; signature function is conservative (uses file + line + rule, falls back to hash). First sign of trouble surfaces at Gate 6 of the next consolidation.
- **revisit_by:** event — first time `compare_baseline.py` produces a NEW finding count that disagrees with operator inspection of the raw JSON; if that happens, update the signature function

---

## Fixes Applied During Spiral

Five refinements applied in v0.1.0 based on Independence Check feedback (listed in Gate 4 Independence Check section above). All five were advisory (no blocking issues); each was a small targeted edit.

One in-flight bug fix during smoke testing: `find_external_refs.py` initially missed relative-path references in `related_skills:` blocks. Fixed by adding a second regex pattern catching `(../)+{source}/` alongside the absolute `plugins/{source}/` pattern. Re-run against sulis-context confirmed the fix surfaces all 5 refs (was 4 before fix).

---

## Irreducible Blockers

None.

---

## Open risks accepted at publication

See Gate 5 "Open risks" section. Two risks (recipe generalisation, code-health JSON shape) both have concrete revisit triggers tied to Phase 3 progress and operational observation respectively.

---

## Vocabulary changes during authoring

None — all 7 introduced terms (Source plugin, Tin test, External ref sweep, Qualifier rename, DEPRECATED shell, Code-health gate, Run directory) remained stable from Gate 2 lock through Gate 5.

---

## Meta-Notes

- This skill ate its own dogfood by being authored via `add-skill` v0.7.0 — the methodology mirrors what `add-agent` v0.1.0 went through, both passing on first iteration with refinements applied.
- The five Independence Check refinements landed in <10 minutes total — small-scope edits that improved precision without changing structure. Pattern: HEAVY-tier first-of-kind methodology skills benefit substantially from Independence Check even when self-scoring suggests PASS.
- The relative-path bug in `find_external_refs.py` was caught during smoke testing rather than Independence Check — evidence that smoke-testing against the first real consolidation target (sulis-context) is itself a load-bearing step in Gate 3 functional completeness, not just Gate 4 verification.
- Next step after publication: run this skill against sulis-context as the first Phase 3 consolidation. The run's `VERIFICATION_REPORT.md` (separate file in `runs/sulis-context-YYYY-MM-DD/`) is the consolidation-run's own report; this report (here) is the skill's own.

---

## Naming history

- v0.1.0 (this iteration): VERIFICATION_REPORT.md
