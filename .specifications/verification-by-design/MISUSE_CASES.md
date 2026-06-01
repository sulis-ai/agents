# Misuse Cases — verification-by-design

**Change:** CH-01KT2B · `change/extend-verification-by-design` · primitive: extend
**Date:** 2026-06-01
**Status:** draft

Adversarial cases for the methodology refinement. Each misuse case has a
defined **system response** — the negative requirement the system MUST enforce.

---

## MUC-001 — Founder skips Verification Plan with `TBD` placeholder

**Abusive actor:** Founder under time pressure (or any operator) who treats
the new section as boilerplate and pastes `TBD` / blank lines / "we'll figure
it out later" / "see follow-on change" into the populated body.

**Targets:** UC-001 (specify), UC-002 (draft-architecture), UC-003 (plan-work).
Every design entry point.

**Misuse flow:**
1. Operator runs `/sulis:specify` (or downstream skill).
2. Agent asks the verification questions; operator answers with placeholders.
3. SRD is written with a Verification Plan section whose body is empty or
   contains only `TBD` / `?` / `to be determined` / "see follow-on".
4. Operator attempts to advance to draft-architecture.

**System response (REQUIRED):** The verification rubric check (FR-009)
**MUST** fail design completion when the Verification Plan section is
missing, empty, or matches the placeholder block-list (`TBD`, `?`,
`to be determined`, `see follow-on`, `n/a` without a justification line,
or a body of fewer than 30 characters of substantive content per
required subsection). The rubric **MUST NOT** treat
placeholder text as populated. The completeness verdict **MUST**
be GAPS_FOUND until populated.

**Related NFRs:** NFR-001 (plain English answerable), NFR-005 (dogfood).

---

## MUC-002 — Agent hallucinates infrastructure that doesn't exist

**Abusive actor:** The requirements-analyst or engineering-architect agent
itself, under pressure to produce a complete-looking Verification Plan,
populates the per-integration strategy with named infrastructure that has
not been built (e.g., "verified via the recording mock at
`apps/api/tests/mocks/sendgrid_recorder.py`" — when no such file exists).

**Targets:** UC-001, UC-002. The honesty of the Verification Plan.

**Misuse flow:**
1. Agent runs the verification question set during design.
2. Operator does not know whether the named mock exists; trusts the agent.
3. SRD ships with a confidently-worded but fictional infrastructure reference.
4. Implementation phase discovers the reference is fictitious; work blocks.

**System response (REQUIRED):** Every named piece of verification
infrastructure in the Verification Plan **MUST** be classified as exactly
one of: `existing` (with a file/repo path the rubric can verify),
`deferred` (recorded under "Infrastructure needs surfaced (deferred)"
with no claim of present existence), or `out-of-scope` (with one-line
justification). The rubric (FR-010) **MUST** fail when a named
infrastructure piece classified as `existing` has no resolvable path
or grep-evidence in the repository at design time.

**Related NFRs:** NFR-002 (distinguish real-vs-deferred), NFR-006 (citable
question set so agents read the same instructions).

---

## MUC-003 — Rubric bypassed via skill-prose loophole

**Abusive actor:** A future operator (or agent) edits one of the skill
prose files (`/sulis:specify`, `/sulis:draft-architecture`,
`/sulis:plan-work`) to remove the verification-question prompt block,
effectively short-circuiting the rubric for downstream changes.

**Targets:** The integrity of the methodology change itself. UC-001/002/003.

**Misuse flow:**
1. Skill prose is edited; the verification-question section is deleted or
   commented out.
2. Future designs run through the modified skill without ever being asked
   the questions.
3. Verification Plan sections are produced from agent imagination only.
4. The rubric still passes (a section exists), but with low-quality content.

**System response (REQUIRED):** The 20-question canonical set **MUST**
live in a single citable reference standard
(`plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`) per
FR-006. Every skill that asks the verification questions **MUST** cite
that standard by relative path and **MUST NOT** inline-duplicate the
question set. The rubric (FR-009) **MUST** include a citation-presence
check: the Verification Plan section MUST contain a reference to
`VERIFICATION_QUESTIONS.md` (by relative path or a stable
identifier) so downstream verification can prove the canonical was
consulted.

**Related NFRs:** NFR-004 (single source of truth), NFR-006.

---

## MUC-004 — Question set drifts between agents

**Abusive actor:** Time and uncoordinated edits. The requirements-analyst
agent is updated to ask 22 questions; engineering-architect is updated
weeks later and still asks the original 20; plan-work is updated to ask
18. Same change, three different sets of asked questions, three
inconsistent Verification Plans.

**Targets:** Consistency across UC-001, UC-002, UC-003.

**Misuse flow:**
1. Someone edits requirements-analyst to add two new questions.
2. They do not update VERIFICATION_QUESTIONS.md or the other skills.
3. SRDs start including answers to questions Q21/Q22; TDDs do not address
   them; WPs are blind to them.
4. Downstream verification adapters cannot find the relevant section.

**System response (REQUIRED):** Per FR-006 and FR-007, the canonical
question set lives in `VERIFICATION_QUESTIONS.md`. Every agent prompt
and skill prose that asks verification questions **MUST** read the
canonical at runtime (or cite it) rather than duplicate the list. The
canonical's version field **MUST** be incremented on any change to the
question set; downstream rubric checks **MUST** fail when the cited
version is stale relative to the current canonical (within one minor
version of currency).

**Related NFRs:** NFR-004, NFR-006.

---

## MUC-005 — Real infrastructure need silently identified but never converted to follow-on change

**Abusive actor:** Slice-end review skipped, missed, or run by an agent
that does not know about the "infrastructure needs → follow-on change"
auto-draft pattern. Two designs each identify the same recording-mock
need; nothing is ever drafted; both designs sit in a deferred state
indefinitely.

**Targets:** UC-004 (auto-draft follow-on for infrastructure need). The
methodology's promise that design-side and infra-side decouple cleanly.

**Misuse flow:**
1. Verification Plan in change A says: "deferred — recording mock for
   SendGrid needed."
2. Verification Plan in change B says: "deferred — recording mock for
   SendGrid needed."
3. Slice-end review runs; the auto-draft trigger does not fire (bug, or
   the trigger was never wired).
4. Both changes block on verification indefinitely; nobody notices.

**System response (REQUIRED):** Per FR-011 and FR-012, every
"Infrastructure needs surfaced (deferred)" subsection entry **MUST** be
recorded in a machine-readable form (one entry per need, with a
canonical identifier for the need). At slice-end review, the existing
slice-end review pattern **MUST** scan for repeated needs (≥2 across the
slice) and, when found, auto-draft a follow-on change targeting that
need. The scan **MUST** be idempotent (running it twice produces one
follow-on change, not two). Singletons (one need flagged by exactly one
change) **MUST** be surfaced to the founder for explicit defer-or-draft
decision at slice-end.

**Related NFRs:** NFR-003 (decouple design-side from infra-side).

---

## MUC-006 — Verification Plan claims a behavioural test but no test is ever written

**Abusive actor:** The change progresses through SRD → TDD → WPs → merge
without anyone wiring the behavioural test that the Verification Plan
promised. The plan said "integration test against `/api/orders` asserting
201 + persisted record"; the actual test suite never gains that test.

**Targets:** UC-001, UC-002, UC-003. The honesty of the verification
claim across the design→implementation handoff.

**Misuse flow:**
1. SRD's Verification Plan claims an integration test will verify UC-X.
2. TDD inherits the claim.
3. WPs are decomposed; no WP explicitly carries the integration test as
   its deliverable.
4. Change ships; nobody verifies the claim was honoured.

**System response (REQUIRED):** Per FR-013, each WP's frontmatter
**MUST** carry a `verification:` field naming the adapter and, where
applicable, the specific test artifact path (or `deferred-to-follow-on`
with the follow-on identifier). A behavioural test ledger
(`.specifications/{change}/verification-ledger.md` or equivalent
location specified by the engineering architect) **MUST** track each
Verification Plan claim against the test artifact that satisfies it.
Slice-end review **MUST** flag claims with no corresponding artifact
and no `deferred-to-follow-on` link.

**Related NFRs:** NFR-007 (claim-to-artifact traceability).

---

## MUC-007 — New `kind:` of change appears that the per-kind taxonomy doesn't cover

**Abusive actor:** Time and new use cases. A future change is classified
as `kind: data-migration` (or `kind: experiment`, `kind: vendor-swap`,
etc.) — a value the original per-kind taxonomy never enumerated. The
agent has no mapping; the Verification Plan's per-kind adapter section
is left blank or guessed.

**Targets:** UC-001, UC-002. The taxonomy's completeness over time.

**Misuse flow:**
1. A new change-kind enters the marketplace lexicon without an adapter
   entry.
2. Design runs; agent has no canonical mapping for the new kind.
3. Verification Plan's per-kind adapter is filled with agent guess.
4. Downstream verification cannot reliably interpret the strategy.

**System response (REQUIRED):** Per FR-008, the kind-to-adapter mapping
lives in `VERIFICATION_QUESTIONS.md`. The rubric (FR-009) **MUST**
verify that the change's `kind:` value has a corresponding adapter
entry in the canonical mapping. If no mapping exists, the rubric
**MUST** fail with a clear instruction: "Add a new adapter row to
`VERIFICATION_QUESTIONS.md` mapping `kind: {value}` to a verification
adapter, then re-run." Adding a new adapter row is itself a
methodology change requiring its own design + rubric satisfaction.

**Related NFRs:** NFR-004, NFR-006.

---

## MUC-008 — Change claims "no verification needed" without justification

**Abusive actor:** Operator under pressure who marks the Verification
Plan as `n/a` for a non-trivial change, claiming trivial-change carveout
without satisfying the carveout's conditions.

**Targets:** UC-001, UC-002, UC-003. The integrity of the trivial-change
carveout (CW-05).

**Misuse flow:**
1. Operator runs `/sulis:specify` on a non-trivial change.
2. Verification Plan is populated with `n/a — trivial-change carveout`
   without a one-line justification.
3. Rubric is satisfied (section is non-empty); change advances.
4. Real verification needs go unaddressed.

**System response (REQUIRED):** Per FR-009 and the trivial-change
carveout policy, an `n/a` answer **MUST** be accompanied by an
explicit one-line justification that explains *why* the carveout
applies (e.g., "n/a — typo fix in user-facing string, no behaviour
change; CW-05 trivial-change carveout"). The rubric **MUST** fail when
`n/a` appears without a justification line in the same section.
Slice-end review **SHOULD** sample `n/a`-claimed changes and verify
the justification is sound; chronic misuse triggers a rubric-tightening
follow-on.

**Related NFRs:** NFR-001, NFR-005.
