# VERIFICATION_REPORT.md — sulis:check-polish

**Skill:** `sulis/check-polish`
**Iteration:** 1 (first upsurge against v0.7.0 methodology)
**Produced:** 2026-05-24
**Methodology:** `sulis:add-skill` v0.7.0 (standards-grounded) in deepening mode

## Spiral Summary

**Tier:** standard / **Template:** STANDARD_TIER_DEFAULT / **Iterations:** 1 of 3 / **Verdict:** APPROVED

(check-polish is the simplest upsurge — no new tool wrappers; CQ-04 already implemented; methodology compliance + canonical ownership declaration.)

## Gate 1 — Find + Primitive Discovery

**Primitives identified (level: skill-scope):**

| Primitive | Provenance | Status |
|-----------|------------|--------|
| Docs completeness (existing — README, CHANGELOG) | extracted | PASS |
| File hygiene (existing — trailing whitespace, mixed line endings) | extracted | PASS |
| CQ-04 technical debt (TODO/FIXME/HACK density — TD-001/TD-002) | extracted; canonical ownership claimed | PASS — check-polish is now the canonical CQ-04 owner; codebase-assess defers here post-Phase 5 |

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Verification tier | STANDARD |
| Tool stack | regex (TD-001/TD-002 patterns are simple density counters; no external tool required) |
| Audience | both |

## Gate 4 — Spiral Verification

| Dimension | Threshold | Score |
|-----------|-----------|-------|
| ACCA (min) | >= 4 | 4 |
| Evidence Grounding | >= 4 | 4 |
| Structural Coherence | >= 4 | 4 |
| Honest Uncertainty | >= 3 | 5 |
| Codebase Referential Integrity | >= 4 | 5 (all entities exist: code-health, _lib/baseline, _lib/allowlist, _lib/scope; supersedes-target codebase-assess exists) |
| CQ-04 Canonical Ownership (custom) | >= 4 | 4 (declared in frontmatter; cross-validation per Phase 4 will confirm no duplication after retirement) |

**Verdict:** PASS — all dimensions meet threshold.

## Gate 5 — Adversarial Review

### Misuse case 1: CQ-04 still calculated in codebase-assess (during transition window)

- **Status:** OPEN_RISK during Phase 4-5 transition window; revisit_by: trigger | Phase 5 codebase-assess deprecation banner directs founders to check-polish.

### Misuse case 2: TODO/FIXME density threshold tuning

- **Status:** PREVENTED — existing thresholds already validated in v0.12.0 cleanup iteration loop (per-cluster allowlist documents legitimate-by-design findings).

### Misuse case 3: README presence misjudged on monorepos

- **Status:** OPEN_RISK; revisit_by: trigger | per-project allowlist supports monorepo per-module docs declaration.

## Open risks

### Risk 1: CQ-04 transition window

- **Description:** during Phase 4-5 transition, both check-polish and codebase-assess calculate CQ-04 — minor duplication in founder-visible output.
- **revisit_by:** trigger | Phase 5 codebase-assess deprecation banner.
- **Workaround:** founders running both will see consistent CQ-04 findings (both compute density from same TODO/FIXME pattern set).
