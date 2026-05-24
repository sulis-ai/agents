# VERIFICATION_REPORT.md — sulis:check-build

**Skill:** `sulis/check-build`
**Iteration:** 1 (first upsurge against v0.7.0 methodology)
**Produced:** 2026-05-24
**Methodology:** `sulis:add-skill` v0.7.0 (standards-grounded) in **deepening mode**

---

## Spiral Summary

**Tier:** standard
**Template base:** STANDARD_TIER_DEFAULT
**Iterations used:** 1 of 3 max
**Termination reason:** sufficient (frontmatter + primitive catalogue + scope lock; tool wrapper integration scheduled iteration 2)
**Verdict:** APPROVED-WITH-RISK

---

## Gate 1 — Find + Primitive Discovery

**Primitives identified (level: skill-scope):**

| Primitive | Provenance | Status this iteration |
|-----------|------------|------------------------|
| Build verifies (existing) | extracted from current scanner | PASS — existing builder.py runs build commands when --run |
| Manifest hygiene (existing) | extracted | PASS — existing manifest-parse checks |
| INF-01 container security | extracted from codebase-assess primitives.md | NOT_ASSESSED — hadolint + Trivy wrappers NEW |
| INF-02 deploy-config secrets | extracted | NOT_ASSESSED — Gitleaks wrapper NEW |

**Scale check (PD-02):** fan-out = 4 primitives; depth = 2. Within constraints.

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Verification tier | STANDARD (founder-facing tier 1) |
| Tool stack | hadolint (INF-01), Trivy (INF-01 base image), Gitleaks (INF-02). Foundation present; per-tool wrappers NEW. |
| Audience | both (--raw for operator mode) |

## Gate 3 — Generate

**Files modified (iteration 1):**
- `plugins/sulis/skills/check-build/SKILL.md` — frontmatter v0.7.0
- `plugins/sulis/skills/check-build/iterations/1/VERIFICATION_REPORT.md` — this file

**Files preserved:** scripts/builder.py (existing); references/

## Gate 4 — Evaluate (Spiral Verification)

### ACCA

| Sub-dimension | Threshold | Score |
|---------------|-----------|-------|
| Accurate | >= 4 | 4 |
| Clear | >= 4 | 4 |
| Complete | >= 4 | 4 |
| Actionable | >= 4 | 4 |

**ACCA: 4/5 — PASS**

### Evidence Grounding

**Score: 4/5 — PASS** — INF-01 / INF-02 primitives sourced from codebase-assess primitives.md.

### Structural Coherence

**Score: 4/5 — PASS** — primitive table MECE; related_skills follows REFERENTIAL_INTEGRITY conventions.

### Honest Uncertainty

**Score: 5/5 — PASS** — INF-01 + INF-02 explicitly NOT_ASSESSED; wrappers flagged NEW.

### Codebase Referential Integrity

**Score: 4/5 — PASS**
- `code-health` exists; `_lib/tools` exists; `hadolint`, `trivy`, `gitleaks` NEW (flagged).

**Verdict: PASS (with deferred items per Outcome-Specific Rigor)**

## Gate 5 — Adversarial Review

### Misuse case 1: INF-01 NOT_ASSESSED without warning

- **Risk:** founder sees tier 1 ✅ Clear; assumes container security checked
- **Status:** PREVENTED in iteration 2+ (hadolint + Trivy wrappers will render NOT_ASSESSED explicitly per SPIRAL_TEMPLATES policy)

### Misuse case 2: yaml/k8s deploy-config secrets missed

- **Risk:** Gitleaks scope expansion (beyond HEAD-only regex check-security currently does) needed to cover INF-02
- **Status:** OPEN_RISK until iteration 2 (gitleaks.py wrapper integrated)

### Misuse case 3: Hadolint absent on founder's machine

- **Risk:** founder doesn't have Docker or hadolint installed
- **Status:** PREVENTED — `_lib/tools/_runner.py` returns NOT_ASSESSED ToolResult; check-build reports honestly

## Open risks

### Risk 1: INF-01 + INF-02 NOT_ASSESSED until iteration 2

- **revisit_by:** trigger | hadolint.py + trivy.py + gitleaks.py wrappers integrated

---

## Meta-Notes

Same iteration-1 scoping as check-security: frontmatter + primitive catalogue + standards citation lands; per-tool wrapper integration scheduled iteration 2.
