<!-- Template syntax: manual substitution of {{variable}} blocks. No templating engine required. -->

# VERIFICATION_REPORT.md — consolidate-into-sulis run: sulis-security → sulis

**Skill:** `plugins/sulis/skills/consolidate-into-sulis` v0.1.2
**Run:** `runs/sulis-security-2026-05-25/`
**Operator:** Iain + Sulis agent (this session)
**Produced:** 2026-05-25
**Methodology:** `sulis:consolidate-into-sulis` v0.1.2 (with move-then-sweep ordering fix)

---

## Run Summary

**Source plugin:** `plugins/sulis-security/`
**Target plugin:** `plugins/sulis/`
**Commit chain:** `bdea2e8` (steps 2-4/5 combined) → wrap-up (this commit)
**Sulis version bump:** v0.39.0 → v0.40.0
**Source plugin version bump:** v0.6.0 → v0.7.0 [DEPRECATED]
**Marketplace metadata version bump:** v1.82.0 → v1.83.0
**Files moved:** 5 (1 skill + nested refs, 1 agent, 1 reference)
**Tin-test renames applied:** 0 (`codebase-assess` already verb-noun + already-DEPRECATED → kept name)
**External refs updated:** 52 substitutions across 32 files
**Verdict:** PASS (Gate 6 pending)
**Fix-forward commits needed:** 0 (vs sea which needed 2 for the same bug now prevented by v0.1.2)

---

## Gate 0 — Inventory + Plan + Baseline

- inventory.json: 1 skill, 1 agent, 1 reference, 0 docs/scripts/tests/CI
- collisions.md: 0 direct, 0 tin-test failures
- external-refs.md: 67 path refs across 38 files
- code-health-baseline.json: 75 findings, tier-2 hard-stop (same shape as prior baselines)

**Pass:** yes

---

## Steps 2-4 (combined `bdea2e8`)

### v0.1.2 move-then-sweep ordering applied

1. **Move all content first**:
   - `git mv plugins/sulis-security/skills/codebase-assess plugins/sulis/skills/codebase-assess`
   - `git mv plugins/sulis-security/agents/security-reviewer.md plugins/sulis/agents/security-reviewer.md`
   - `git mv plugins/sulis-security/references/viability-framework.md plugins/sulis/references/viability-framework.md`

2. **Source plugin now empty** of active content (only plugin.json + CHANGELOG.md + README.md remain)

3. **Then bulk_rewrite.py** with replacements table (13 entries: paths + relative paths + slash command + GitHub URLs). Output: 52 substitutions across 32 files. **No un-swept self-references** (the v0.1.2 fix worked — source-plugin exclusion is now a no-op because the directory is empty).

4. **Then manual edits** (3):
   - `.architecture/sulis-checkup/TDD.md`: 2 narrative refs using `/sulis-security:CQ-XX` primitive-ID shorthand → `/sulis:codebase-assess (CQ-XX)`
   - `README.md` L56: bulk_rewrite updated the URL but left the row text; manual edit added [DEPRECATED] + what-moved-where

5. **`git add -A` then commit** — single combined commit covering steps 2, 3, 4.

### Results

- plugins/sulis-security/{skills,agents,references}/ all empty (verified)
- `git grep "plugins/sulis-security/"` outside historical = only the intentional [DEPRECATED] listing in README.md
- `git grep "/sulis-security:[a-zA-Z]"` outside historical = clean
- **Zero fix-forward commits needed** — direct comparison to sea (2 fix-forwards) demonstrates the v0.1.2 ordering fix worked

---

## Step 5 — Wrap-up (this commit)

- Source plugin marked DEPRECATED in plugin.json (v0.6.0 → v0.7.0; `deprecated: true`; description updated), CHANGELOG.md (new v0.7.0 entry), README.md (full rewrite with what-moved-where + Phase 3 complete note)
- Sulis plugin.json v0.39.0 → v0.40.0
- Sulis CHANGELOG.md: new v0.40.0 entry — Phase 3 complete table
- marketplace.json: sulis-security entry → v0.7.0 [DEPRECATED]; sulis entry → v0.40.0; metadata version → v1.83.0 + new narrative
- README.md L56: sulis-security entry already marked [DEPRECATED] (in steps 2-4 manual edit); now amended to mention "Phase 3 complete"

---

## Adversarial Review

### Misuse case 1: Move-then-sweep ordering bug recurrence

- **What might have gone wrong:** Same bug as sea — bulk sweep runs while source content still in `plugins/sulis-security/`, leaving un-swept self-references.
- **Mitigation:** v0.1.2 SKILL.md encoded the ordering as non-negotiable. Operator followed: moved 3 files, ran bulk_rewrite.py, confirmed source-plugin exclusion was a no-op because the source directory was already empty.
- **Status:** PREVENTED by v0.1.2 discipline.

### Misuse case 2: `codebase-assess` skill already DEPRECATED — double-deprecation

- **What might have gone wrong:** The skill is already DEPRECATED per its own SKILL.md banner (superseded by `/sulis:code-health` since v0.22.0). After consolidation, it's also implicitly DEPRECATED via the parent plugin's DEPRECATED marker. Risk: confusion about which deprecation applies.
- **Mitigation:** Documented explicitly in this VERIFICATION_REPORT.md + sulis-security README.md: the skill-level deprecation banner stays, the plugin shell adds an additional DEPRECATED marker, both deprecations are independent and intentional.
- **Status:** PREVENTED via documentation.

### Misuse case 3: Narrative primitive-ID references in TDD

- **What might have gone wrong:** `/sulis-security:CQ-01..05` and `/sulis-security:CQ-02` are NOT real slash commands — they're narrative shorthand for primitive IDs. The bulk_rewrite.py didn't catch them as path+slash-command patterns; manual edit needed.
- **Mitigation:** Caught during pre-commit verification scan; manual edits to point at `/sulis:codebase-assess (CQ-XX)` notation.
- **Status:** PREVENTED (caught + fixed before commit).

---

## Gate 6 — Code-health verification

**Verdict: PASS (first try, 0 NEW findings).**

- NEW: 0
- PRE-EXISTING: 10
- RESOLVED: 0

The cleanest Gate 6 of all four Phase 3 consolidations:
- sulis-context: 1 NEW (false attribution) → PASS after rubric
- srd: 1 NEW (PH-103 desc-too-long) → PASS after 1 fix-forward
- sea: 5 NEW (false attribution) → PASS after rubric
- sulis-security: 0 NEW → **PASS, no rubric application needed**

The v0.1.2 + v0.1.1 patches (signature improvements + ordering discipline + bulk_rewrite.py) compounded into a clean run.

---

## Verdict (final)

**Steps 2-5:** PASS (0 fix-forward commits)
**Gate 6:** PASS (0 NEW findings, first try)
**Overall:** **Phase 3 complete** — all four specialist plugins consolidated into sulis. Clean run; recipe v1.0-ready.

---

## Meta-Notes

- **Cleanest run of the 4 Phase 3 consolidations.** Smallest scope (3 files), 0 fix-forwards, single combined commit. The v0.1.2 patches paid off.
- **Phase 3 calibration loop:** sulis-context (calibration) → 6 v0.1.1 signals → srd (validation #1) → 3 v0.1.2 signals → sea (validation #2) → 6 v0.1.2 signals + 2 fix-forwards → sulis-security (validation #3) → 0 signals + 0 fix-forwards. The recipe matured monotonically.
- **The marketplace surface is now reduced to one front-door plugin (sulis) + DEPRECATED shells** for backward compatibility. Pure functionality lives in sulis going forward.
- **Recipe ready for v1.0.** No more signals to capture from sulis-security. Future consolidations (if any external plugins arrive) should land cleanly with v0.1.2.
