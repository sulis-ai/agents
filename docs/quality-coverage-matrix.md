# Quality Coverage Matrix

**Status:** working note · **Last reviewed:** 2026-05-23 · **Owner:** maintainer

What this is: a map of every quality concern the marketplace tries (or should
try) to address, with the skill that currently owns it, the coverage level,
and the gap. Use it to decide where to invest next in skill authoring.

How to read it:
- **✅** owns it (skill exists and the concern is in its remit)
- **🟡** partial (a skill touches it but the lens is wrong or scope mismatched)
- **❌** gap (no owner)

## Skill inventory

The skills + agents below are the ones that exercise a quality lens of some
kind. Other skills (forward-design, execution, concierge handoff) are out
of scope here.

| Skill | Owns |
|---|---|
| `sea:code-review` | Per-PR correctness, behaviour preservation, PR hygiene (CR-NN + PH-NN) |
| `sea:codebase-audit` | Architecture primitive-gap audit against MECE-3 pillars (produced the 8 Hardening Deltas) |
| `sea:probe` | Deterministic structural analysis (ast-grep, lizard, scc, git stats) |
| `sea:verify` | Post-WP architecture completeness (6 perspectives: wrapper rot, port-adapter sanity, etc.) |
| `sea:suggest-split` | Splits too-big PRs |
| `sea:harden` | Turns HD findings into code changes |
| `sea:blueprint` / `sea:decompose` | SRD → TDD → WPs (forward-design, not quality — listed for context) |
| `sulis-security:codebase-assess` | 25 primitives × 5 categories (Security / Data Protection / Code Quality / Supply Chain / Infrastructure) |
| `sulis-context:discover` | Inventories existing docs / ADRs / conventions |

## Coverage matrix

| # | Quality concern | Today's owner(s) | Coverage | What's missing | Recommended owner |
|---|---|---|---|---|---|
| 1 | Per-change correctness | `sea:code-review` | ✅ | — | (current) |
| 2 | PR hygiene + sizing | `sea:code-review` + `sea:suggest-split` | ✅ | — | (current) |
| 3 | Architecture primitive gaps (greenfield + brownfield) | `sea:codebase-audit` + `sea:harden` | ✅ | — | (current) |
| 4 | Post-WP architecture completeness | `sea:verify` | ✅ | — | (current) |
| 5 | Cyclomatic complexity | `sea:probe` + `sulis-security:CQ-01` | ✅ (overlap) | — | Consolidate to one owner |
| 6 | Test coverage ratio | `sulis-security:CQ-02` | ✅ | — | (current) |
| 7 | Code duplication | `sulis-security:CQ-03` | ✅ | — | (current) |
| 8 | Tech-debt markers (TODO/FIXME/HACK density) | `sulis-security:CQ-04` | ✅ | — | (current) |
| 9 | Review practices (git log signals) | `sulis-security:CQ-05` | ✅ | — | (current) |
| 10 | Security vulnerabilities | `sulis-security:codebase-assess` | ✅ | — | (current) |
| 11 | Data protection / PII | `sulis-security:codebase-assess` | ✅ | — | (current) |
| 12 | Supply chain | `sulis-security:codebase-assess` | ✅ | — | (current) |
| 13 | Infrastructure posture | `sulis-security:codebase-assess` | ✅ | — | (current) |
| 14 | Doc / ADR inventory | `sulis-context:discover` | ✅ | — | (current) |
| 15 | **Naming / legibility / module cohesion** | none | ❌ | Stranger-reader lens on names, module concept-count, jargon density | *new `sea:code-hygiene`* |
| 16 | **Failure-mode enumeration** | partial via `sea:codebase-audit` | 🟡 | Per-operation FMEA: "for each call site, what can fail, where does the failure go?" Architecture audit is one-shot, not ongoing | *new `sea:failure-mode-audit`* |
| 17 | **Observability / diagnosability** | none | ❌ | "Can an operator diagnose this op from logs alone?" — bit us in HD-013 | *extend `sea:code-review` checklist + new module-level skill* |
| 18 | **Cross-surface contract drift** (CLI ↔ SDK ↔ MCP ↔ OpenAPI) | none | ❌ | Enforce parity between surfaces; HD-012 was a real bug from this gap | *new `sea:surface-parity-audit`* |
| 19 | **Doc drift** (does prose match code?) | partial via `sulis-context:discover` | 🟡 | `discover` inventories docs but doesn't validate them against current code | *extend `sulis-context` with `validate` skill* |
| 20 | **Dead code / dead config / stale deprecations** | partial via `sea:probe` | 🟡 | Probe can spot-check unused imports; doesn't hunt cold paths or untouched shims | *new `sea:dead-code-audit`* (covers #21 too) |
| 21 | **Migration completion** (did all callers actually move?) | partial via `sea:code-review` | 🟡 | Reviewer sees one diff; can't tell if migration is N/M complete cumulatively | *same skill as #20* |
| 22 | **Test quality beyond coverage** (brittleness, over-mocking, layer balance) | partial via `sea:code-review` | 🟡 | We count tests; we don't judge whether they test the right things | *new `sea:test-audit` or extend `sea:probe`* |
| 23 | **CLI / founder ergonomics** | none | ❌ | Non-technical-user lens on commands, error messages, defaults, discoverability | *new — possibly `sulis-concierge:ergonomics-audit`* |
| 24 | **Manifest hygiene** (plugin.json, marketplace.json) | partial via `sea:code-review` | 🟡 | HD-004 was systemic; caught only when JSON unparseable | *extend `sea:code-review` checklist* |

## Summary of gaps

### Structural gaps (no owner at all)

- **#15** naming / legibility / module cohesion
- **#17** observability / diagnosability
- **#18** cross-surface contract drift
- **#23** founder ergonomics

### Partial gaps (an owner exists but the lens is wrong)

- **#16** failure modes — architecture audit is one-shot, not per-module ongoing
- **#19** doc drift — we inventory docs but don't validate them
- **#20 / #21** dead code + migration completion — delta-scoped reviewers can't see cumulative state
- **#22** test quality — we count, we don't judge
- **#24** manifest hygiene — only caught when JSON unparseable

### Consolidation opportunity

- **#5** cyclomatic complexity is owned by *both* `sea:probe` and
  `sulis-security:CQ-01`. Pick one. `probe` runs deeper; `CQ-01` is part of
  the codebase-assess flow. Either move complexity entirely to `probe` and
  have CQ delegate, or vice versa.

## Recommended new work (4 new skills + 2 extensions)

1. **`sea:code-hygiene`** — concern #15 (naming, legibility, module cohesion).
   Module- or directory-scoped; runs cumulatively rather than per-diff;
   applies stranger-reader lens explicitly.
2. **`sea:failure-mode-audit`** — concern #16 (per-operation FMEA). Walks a
   module's operations and produces a table of failure paths.
3. **`sea:surface-parity-audit`** — concern #18 (CLI ↔ SDK ↔ MCP ↔ OpenAPI
   drift). Enforces that every CLI subcommand has an SDK method, every SDK
   method has TS parity, every typed method is an MCP tool.
4. **`sea:dead-code-audit`** — concerns #20 + #21 (dead code, dead config,
   stale deprecations, incomplete migrations). Asks "is this still being
   called?" and "is this migration N/M done?".
5. **Extend `sea:code-review` checklist** — add observability check (#17) and
   manifest-hygiene check (#24) to the per-PR review.
6. **Extend `sulis-context` with `validate` skill** — concern #19 (doc-drift
   validation against current code).

Second-wave (real gaps but more taste-driven, lower-frequency):

- **#22** test quality beyond coverage
- **#23** founder ergonomics

## Why this matters

Existing coverage is strong on three axes: per-change correctness, measurable
code-quality metrics, and security / data-protection. That's where the most
mature work has gone.

The recurring production issues in the recent rollout traced back to gaps
that *no skill owned*:

- HD-003 (partial merge failure) → gap #16 (failure modes)
- HD-012 (SDK lagged CLI) → gap #18 (surface parity)
- HD-013 (dropped diagnostic log) → gap #17 (observability)
- The whole "wpx/wp/lib" naming critique → gap #15 (legibility)

If every concern in the matrix has a named owner, the marketplace's quality
story becomes "we have a skill for each lens" rather than "we have
code-review and hope it catches everything."
