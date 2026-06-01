# Non-Functional Requirements — verification-by-design

**Change:** CH-01KT2B · `change/extend-verification-by-design` · primitive: extend
**Date:** 2026-06-01
**Status:** draft

These NFRs constrain *how* the methodology refinement behaves, in addition to
the functional requirements in SRD.md.

---

## Summary

The Verification Plan must be founder-readable in plain English, must
honestly distinguish real verification from deferred infrastructure, must not
retroactively break grandfathered changes, must keep the question set citable as
a single source of truth, must dogfood itself in this change's own artifacts,
must keep a claim-to-artifact trace, and must not require any infrastructure
to be built before this change ships.

---

## NFR-001 — Plain-English answerability

**Category:** Usability / founder-readability
**Requirement:** The Verification Plan section MUST be answerable by a founder
in plain English without requiring knowledge of testing jargon (no
"characterisation test", "stub vs fake vs mock" required in the answer; "we'll
record what the mock sees and check it" is acceptable).
**Measurement:** A non-technical reader reading the section answers the
question "do I understand how this change will be verified?" with yes. CQ-04
readability target: Flesch-Kincaid Grade Level ≤ 10 for the Verification Plan
section.
**Rationale:** The founder is the primary author; the Verification Plan must
not become another technical artifact the founder cannot read.

## NFR-002 — Distinguish real verification from deferred infrastructure

**Category:** Honesty / accuracy
**Requirement:** Every Verification Plan section MUST clearly partition its
content into "verification we will do" (with concrete strategy + named
infrastructure if any) versus "infrastructure not yet built; deferred to
follow-on" (with canonical need identifier). The rubric (FR-010) MUST fail
when these two are conflated or when the section's content does not classify
itself.
**Measurement:** Every named piece of infrastructure resolves either to an
existing repo path or to a deferred-need entry. Zero ambiguous claims.
**Rationale:** Path A's premise — design-side and infra-side are decoupled —
depends on Plans being honest about which side an answer lives on.

## NFR-003 — Backward compatibility for grandfathered changes

**Category:** Migration safety
**Requirement:** Changes that shipped before this methodology refinement merged
MUST continue to pass all existing rubrics without retroactive penalty. The
rubric P-VER (FR-009) MUST NOT execute against changes whose shipped-on date
predates the merge date of this change. Every new change from this refinement
onwards MUST satisfy P-VER.
**Measurement:** Running the full rubric suite against an existing released
change (e.g., release-train, discovery) produces PASS, identically to its
pre-refinement verdict.
**Rationale:** Retroactively breaking existing changes would block release
trains and stall delivery; the founder explicitly scoped backfill as out-of-scope.

## NFR-004 — Single source of truth for the question set

**Category:** Maintainability / consistency
**Requirement:** The 20-question canonical set + the kind-to-adapter mapping
MUST live in exactly one file (`plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`).
Every consuming skill / agent prompt MUST cite that file by relative path and
MUST NOT inline-duplicate the question list. Changes to the question set or
adapter mapping MUST increment the canonical's version field; consumers MUST
fail rubric when their cited version is more than one minor version stale.
**Measurement:** A grep across the repo for any of the canonical question
strings returns occurrences only in `VERIFICATION_QUESTIONS.md`. Skills/agents
contain citations only, not the question text.
**Rationale:** MUC-004 (question set drift between agents) is structural; the
only durable defence is a single source of truth.

## NFR-005 — Dogfood acceptance

**Category:** Self-application / proof-of-life
**Requirement:** This change's own SRD (this document), TDD (produced by
`/sulis:draft-architecture`), and Work Packages (produced by `/sulis:plan-work`)
MUST themselves include populated Verification Plan sections that answer the
new question set for a methodology change. This change MUST NOT ship until
its own rubric P-VER passes against its own artifacts.
**Measurement:** Rubric P-VER PASS against this change's SRD, TDD, and WP set
prior to merge to dev.
**Rationale:** A methodology refinement that does not self-apply is not a
methodology refinement; it is a suggestion.

## NFR-006 — Canonical question set is citable from every consumer

**Category:** Architectural integrity
**Requirement:** `VERIFICATION_QUESTIONS.md` MUST be reachable by a stable
relative path from every skill prose file and agent prompt that asks
verification questions. The rubric P-VER MUST include a citation-presence
check (the artifact's Verification Plan section MUST contain a literal
citation by relative path or stable identifier — `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`
or `VERIFICATION_QUESTIONS.md`).
**Measurement:** Every artifact passing P-VER contains exactly one such citation.
**Rationale:** Closes the loop on MUC-003 (skill-prose loophole bypass) — the
artifact itself proves the canonical was consulted.

## NFR-007 — Claim-to-artifact traceability

**Category:** Honesty / closing the loop
**Requirement:** Every Verification Plan claim ("we'll verify X via Y") MUST
be traceable from the SRD / TDD into the work-package set and either to a
concrete test artifact path or to a `deferred-to-follow-on:` identifier. The
slice-end review (FR-012) MUST flag any claim with neither.
**Measurement:** The behavioural test ledger (per NFR-007's traceability)
contains a row per claim; zero rows are orphans at ship time (unless explicitly
deferred to a named follow-on).
**Rationale:** MUC-006 — a Verification Plan claim with no resulting test is
silent failure of the methodology. The ledger makes it loud.

## NFR-008 — Design-side ships without infrastructure-side dependency

**Category:** Decoupling / shippability
**Requirement:** This methodology refinement MUST ship to dev without
requiring any verification infrastructure (test auth, mock notifications, seed
fixtures, etc.) to be built first. The rubric P-VER MUST accept "deferred to
follow-on" answers as valid populated content. Infrastructure pieces become
their own follow-on changes triggered by the auto-draft pattern (UC-004).
**Measurement:** This change ships with zero new infrastructure code; only
methodology assets (skill prose, agent prompts, rubric reference, canonical
question set). The Verification Plan section of this very SRD is the proof.
**Rationale:** The founder's two-sides-of-coin framing — verbatim: "Two sides
of the same coin: design-side asks the verification questions; infrastructure-side
builds the mechanisms to answer them. The two interact — design surfaces what
infrastructure is needed; infrastructure unblocks verification." Shipping
design-side first is the explicit plan.
