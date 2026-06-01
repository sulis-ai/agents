# Handoff to Senior Engineering Architect — verification-by-design

**Change:** CH-01KT2B · `change/extend-verification-by-design` · primitive: extend
**Date:** 2026-06-01
**Source SRD:** `.specifications/verification-by-design/SRD.md`

This file gives SEA the context to produce the TDD without re-litigating
decisions already made during requirements facilitation. Read SRD.md, NFR.md,
MISUSE_CASES.md, GLOSSARY.md, and PRIMITIVE_TREE.jsonld first, then use this
file for design hints.

---

## Change shape

**`kind: methodology`** — predominantly skill prose + agent prompt updates +
a new reference standard + a rubric extension. No new runtime code. No new
services. No new endpoints. No new database schemas. The deliverable is
markdown and the methodology gates that read it.

**Per-kind adapter** (from this SRD's Verification Plan):
*structural assertions + integration test where a fresh design dispatch produces
output with the new shape.*

---

## Files that will change (predicted)

SEA, please verify each against the actual repo state before treating these
as authoritative. The Prior-Art Check rule applies — grep for the canonical
paths before assuming.

| File | Change |
|---|---|
| `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` | **NEW** — the canonical 20-question set + kind→adapter mapping table + version field |
| `plugins/sulis/skills/requirements-templates/SKILL.md` | **EXTEND** — add the `## Verification Plan` template block with the six required subsections |
| `plugins/sulis/agents/requirements-analyst.md` | **EXTEND** — add Phase 3 instruction to read `VERIFICATION_QUESTIONS.md` and ask the foundational + per-integration questions; cite, don't duplicate |
| `plugins/sulis/agents/engineering-architect.md` | **EXTEND** — add concretion-question instruction; add SRD Verification Plan ingestion as part of standard input |
| `plugins/sulis/skills/plan-work/SKILL.md` | **EXTEND** — enforce `verification:` frontmatter field on every emitted WP; cite kind→adapter mapping |
| `plugins/sulis/references/decompose-validation-rubric.md` | **EXTEND** — add P-VER rubric item enumerating each failure mode from FR-009 |
| `plugins/sulis/skills/requirements-validation/SKILL.md` (if exists at that path) | **EXTEND** — invoke P-VER as part of the rubric pass |
| `plugins/sulis/references/...` (slice-end review pattern reference) | **EXTEND** — add deferred-needs aggregator + auto-draft trigger |
| A merge-date marker file or constant | **NEW** — store the refinement's merge date for FR-014 grandfather check |

---

## Cross-WP identifier canonicalisation (per shipped P8 rubric)

Every cross-reference between the SRD section content and the new
`VERIFICATION_QUESTIONS.md` standard MUST cite the canonical source — don't
inline-mint identifiers, don't duplicate question text, don't restate the
adapter mapping in any consumer file. The "single source of truth" property is
load-bearing for MUC-003 and MUC-004; the P8 rubric is the existing enforcement
mechanism.

**Concretely for SEA's TDD:** Every reference to "the 20 questions" or "the
kind-to-adapter mapping" in the TDD MUST cite
`plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` by relative
path, not by enumeration.

---

## Dogfood acceptance — non-negotiable

The TDD SEA produces **MUST itself** include a populated `## Verification Plan`
section answering the new question set for a methodology change. The TDD is
the second proof-of-life artifact (after this SRD) demonstrating the new
template in action.

If SEA finds itself unable to populate the TDD's Verification Plan without
hallucinating infrastructure (MUC-002), surface the gap and stop. The change
ships only when its own rubric P-VER passes against its own artifacts (NFR-005).

The integration-test claim from this SRD's Verification Plan — "a fresh
`/sulis:specify` run produces an SRD with the new section populated" — needs
SEA to specify the concrete test fixture, the scripted founder persona, the
exact assertions, and the test artifact path. This becomes a WP in the
`/sulis:plan-work` output.

---

## Open Questions still requiring founder input

These came from SRD § Open Questions and remain unresolved. SEA, please flag
them in the TDD's "Decisions deferred to founder" section rather than
autonomously resolving:

1. **Naming.** "Verification Plan" vs "Acceptance Strategy" vs "How We'll
   Verify". SRD recommends "Verification Plan" — confirm with founder before
   committing to the literal section heading across all templates.
2. **Required-for-every-change vs first-N-WPs-only.** SRD recommends MUST
   for every new change from merge date.
3. **Per-WP `verification:` field shape.** SRD recommends the structured map
   shape in FR-005 — confirm the YAML structure with founder.
4. **Canonical location.** SRD recommends
   `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`.
5. **Follow-on auto-draft trigger timing.** SRD recommends slice-end (not
   immediate).
6. **Grandfathered-change modifications.** SRD recommends: edits to
   grandfathered changes inherit grandfathered status.
7. **Per-kind adapter count.** SRD ships with seven adapters; new kinds
   require a new methodology change to add a row (per FR-008 mechanism).

---

## Risk surface SEA should specifically address

| Risk | Likelihood | Impact | Mitigation in TDD |
|---|---|---|---|
| **Skill-prose loophole** — operator removes the question-asking block from a skill | Medium | High | Citation-presence check in P-VER (NFR-006); skill prose reads `VERIFICATION_QUESTIONS.md` at runtime |
| **Question-set drift between agents** | Medium | High | Single source of truth (NFR-004); version field with currency check (FR-006) |
| **Hallucinated infrastructure** | Medium | Medium | Classification check (FR-010); path resolution at design time |
| **Unmapped change kind** | Low | Medium | Explicit failure with instruction-message (FR-008) |
| **Idempotency of follow-on auto-draft** | Low | Medium | Idempotent scan with canonical need identifier (FR-011, FR-012) |
| **Grandfather boundary edge cases** | Low | Low | Shipped-on date heuristic; manual override (UC-005 alt-A) |
| **Founder pasting `TBD`** | High | High | Block-list + minimum-character check in P-VER (FR-009, MUC-001) |

---

## What's explicitly NOT for SEA to design

- The verification infrastructure itself (recording mocks for vendors, test
  OAuth account pipelines, seed-data fixture mechanisms). NFR-008 forbids
  building these in this change.
- The behavioural test framework. The adapter names *what* is verified; the
  framework is out of scope.
- Cross-language test orchestration. Out of scope.
- ServiceSpec extension. Possible future change.

If SEA's TDD finds itself drifting into specifying any of these, surface it
as a follow-on infrastructure need and continue with the design-side scope
intact.

---

## Recommended next step for SEA

1. Read this SRD, NFR.md, MISUSE_CASES.md, PRIMITIVE_TREE.jsonld, GLOSSARY.md
   in that order.
2. Run Prior-Art Check on each file in the "Files that will change" table —
   verify they exist at the predicted paths.
3. Ask the founder the seven Open Questions in plain English (one at a time
   per facilitation rules) before writing the TDD.
4. Produce the TDD with a dogfood-acceptance `## Verification Plan` section
   that concretises this SRD's plan into specific test artifact paths,
   specific assertions, and specific fixture locations.
5. Dispatch `/sulis:plan-work` against the TDD to emit WPs with the
   `verification:` field.

The recommended invocation:

```
/sulis:draft-architecture .specifications/verification-by-design/
```
