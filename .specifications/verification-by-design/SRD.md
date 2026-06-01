# SRD — Verification by design

**Change:** CH-01KT2B · `change/extend-verification-by-design` · primitive: extend
**Date:** 2026-06-01
**Status:** draft v1
**Scope:** design-side only (infrastructure-side explicitly deferred per the
founder's two-sides-of-coin framing — see NFR-008)
**Dogfood:** the SRD itself ships with a populated `## Verification Plan` section
(the worked example future designs copy)

---

## Summary

Verification cannot be bolted on at the end of a change. This refinement makes it a
**design-time question**, asked alongside "what does it do?", and recorded in a new
**Verification Plan** section that lives in every SRD, every TDD, and every
Work Package frontmatter from this refinement onwards.

The work has two halves. **This change ships only the first half** — the design-side:
- A canonical 20-question set in a new reference standard (`VERIFICATION_QUESTIONS.md`).
- A per-kind verification adapter taxonomy.
- A `## Verification Plan` section in the SRD and TDD templates.
- A `verification:` field on every Work Package frontmatter.
- A new rubric check (P-VER) that fails design completion when the section is
  missing, placeholder, hallucinated, or cites an unmapped change-kind.
- Skill prose + agent prompt updates so `/sulis:specify`,
  `/sulis:draft-architecture`, and `/sulis:plan-work` ask the questions during
  the existing design conversation.
- A slice-end review hook that auto-drafts follow-on changes when an infrastructure
  need is flagged by 2+ designs.

The **second half** — actually building the verification infrastructure (test auth,
recording mocks for notification providers, seed-data fixture pipelines, etc.) —
is explicitly out of scope. Those pieces appear as their own follow-on changes
the moment a real design surfaces a real need.

The dogfood acceptance criterion: this very SRD must itself include a populated
Verification Plan section. It does — see `## Verification Plan` at the bottom.

---

## Why this is now

Path A (canonical-as-spec + drift-detector bridge) shipped twice in the last
fortnight — the release-train workflow and the discovery workflow. Both surfaced
the same shape of gap during dogfood: **after a change ships to dev, no one has
actually verified the behaviour end-to-end.** The release-train code merged but no
one runs the actual release-train against a real change. The discovery skill prose
merged but no one runs it against a fresh consumer repo. Unit tests + code reviews
validated "the code looks right"; nobody verified "the thing does what we said it
would do."

Two latent defects became live after merge. Both would have been caught by a
single end-to-end verification run. Both shipped because the methodology had no
gate that asked "how would we verify this works?" during design.

The founder framing — verbatim — that drove this change:

> "Verification can't be bolted on at the end. It has to start as a design
> question — 'how would we actually verify this works?' — alongside the design
> question 'what does it do?'"

> "The OAuth example is exactly the right canary. To verify a logged-in flow
> end-to-end, automated tests need a way to authenticate. That means real test
> accounts (which need credentials, which need a secrets pipeline, which needs
> to work in CI and local), or an auth-bypass mechanism (which has its own
> security implications), or a mocked identity layer (which has to behave
> identically to the real one or the test isn't actually testing the real thing)."

> "Two sides of the same coin: design-side asks the verification questions;
> infrastructure-side builds the mechanisms to answer them."

---

## Stakeholders

- **Founder (Iain)** — primary author of designs; runs `/sulis:specify`,
  `/sulis:draft-architecture`, `/sulis:plan-work`. Reads + populates Verification
  Plan sections in plain English.
- **requirements-analyst agent** — extended to ask the foundational +
  per-integration verification questions during Phase 3 of facilitation.
- **engineering-architect agent** — extended to ask the real-vs-mock concretion
  questions and to bind the SRD's plan to implementation-side specifics in the TDD.
- **plan-work skill** — extended to require each WP carry a `verification:`
  field in frontmatter.
- **Slice-end review (automated pattern)** — extended to scan deferred
  infrastructure needs across the slice and auto-draft follow-on changes when
  the same need appears in 2+ designs.
- **Grandfathered changes** (everything shipped before this refinement merges)
  — must continue to pass all rubrics without retroactive Verification Plan
  requirement.
- **Future infrastructure follow-on changes** — out of scope for this change,
  but receive the deferred-need ledger as input.

---

## Use Cases

### UC-001 — Founder runs `/sulis:specify` on a new change; the SRD produced includes a populated Verification Plan

**Actor:** Founder
**Trigger:** Founder invokes `/sulis:specify <change-name>` for a new change.
**Preconditions:** A change record exists (e.g., `CH-NNNNNN`). The
`/sulis:specify` skill prose has been updated by this refinement. The
canonical question set exists at `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`.

**Main flow:**
1. Founder invokes the skill.
2. The skill dispatches the requirements-analyst subagent.
3. Phases 1 and 2 of facilitation run unchanged.
4. During Phase 3 (Convergent Specification), the agent reads the canonical
   question set from `VERIFICATION_QUESTIONS.md`.
5. The agent asks each foundational question (Q1-Q4) one at a time in plain
   English. Answers are recorded in the journal.
6. For every integration the change touches, the agent asks the relevant
   per-integration questions (Q5-Q13).
7. The agent infers the change's `kind:` (or asks if ambiguous) and applies
   the per-kind adapter (Q14-Q20) — exactly one of the seven adapters.
8. The agent drafts the SRD with a `## Verification Plan` section at the
   bottom, populated with the recorded answers in plain English.
9. Phase 5 (completeness verification) runs the rubric P-VER against the
   draft. PASS allows Phase 6 (handover).

**Alternate flow A:** Founder answers "I don't know yet" to a per-integration
question. The agent records `deferred — need infrastructure to answer X` under
the "Infrastructure needs surfaced (deferred)" subsection with a canonical
identifier. The rubric accepts this; it is not a placeholder.

**Alternate flow B:** The change is a trivial-change-carveout candidate (typo
fix, comment-only edit). The agent populates the section with `n/a —
trivial-change carveout` plus a one-line justification. The rubric accepts this
populated form.

**Exception flow:** Founder answers with `TBD` / blank / `?`. The rubric
P-VER fails. The agent re-enters Phase 3 and re-asks only the unresolved
questions. Phase cannot exit until populated.

**Postconditions:** `.specifications/{change}/SRD.md` exists with a `## Verification Plan`
section that passes rubric P-VER.

**Business rules applied:** FR-001, FR-002, FR-003, FR-006, FR-009.

**Negative requirements:**
- The system MUST NOT accept `TBD`, `?`, empty, or fewer than 30 characters of
  substantive content as a populated subsection (MUC-001).
- The system MUST NOT inline-duplicate the question set inside the
  requirements-analyst prompt (MUC-003, MUC-004).
- The system MUST NOT auto-fill the section with hallucinated infrastructure
  (MUC-002).

---

### UC-002 — Founder runs `/sulis:draft-architecture` on the produced SRD; the TDD includes a Verification Plan

**Actor:** Founder
**Trigger:** Founder invokes `/sulis:draft-architecture .specifications/{change}/`.
**Preconditions:** The SRD exists and includes a populated Verification Plan
section. The engineering-architect agent prompt has been updated by this
refinement.

**Main flow:**
1. Founder invokes the skill.
2. The skill dispatches the engineering-architect subagent.
3. The agent reads the full SRD including the Verification Plan section.
4. The agent reads the canonical question set + adapter taxonomy.
5. For each strategy named in the SRD's Verification Plan, the agent asks the
   implementation-side concretion question — "for the SRD's 'mock the SendGrid
   client' plan, which existing mock or new build?" / "for the SRD's
   'integration test' plan, which test runner and fixture set?"
6. For the foundational bootstrap-from-zero question, the agent verifies the
   answer still holds given the chosen technology stack.
7. The agent populates the TDD's `## Verification Plan` section with
   concretised, implementation-side answers, citing files / fixtures / mock
   paths.
8. The rubric P-VER runs against the TDD. PASS allows TDD finalisation.

**Alternate flow A:** The TDD plan contradicts the SRD plan (e.g., SRD claims
"real Stripe sandbox" but SEA discovers no sandbox credentials exist and
proposes recording-mock instead). The agent surfaces the contradiction; the
founder decides whether the SRD plan should change or the TDD plan should
change. Either artifact is amended.

**Alternate flow B:** The SRD's Verification Plan recorded a deferred
infrastructure need. The TDD's plan carries the deferred entry through
verbatim, with a `deferred-to-follow-on:` field listing the canonical
identifier of the (not-yet-drafted) follow-on change.

**Exception flow:** SEA proposes infrastructure that does not exist in the
repo. The rubric P-VER fails at the citation-resolution check. SEA re-classifies
the proposal as `deferred` and surfaces the need.

**Postconditions:** `.specifications/{change}/TDD.md` exists with a populated
Verification Plan section that passes rubric P-VER and is consistent with the
SRD's plan.

**Business rules applied:** FR-001, FR-004, FR-006, FR-007, FR-009, FR-010.

**Negative requirements:**
- The system MUST NOT propose infrastructure classified as `existing` whose
  path does not resolve in the repo (MUC-002).
- The system MUST NOT produce a TDD plan that silently contradicts the SRD
  plan (UC-002 alt-A is the explicit surfacing path).
- The system MUST NOT bypass the rubric by editing skill prose (MUC-003).

---

### UC-003 — Founder runs `/sulis:plan-work`; each emitted WP carries a `verification:` frontmatter field

**Actor:** Founder
**Trigger:** Founder invokes `/sulis:plan-work .specifications/{change}/`.
**Preconditions:** The TDD exists with a populated Verification Plan section
that passes P-VER.

**Main flow:**
1. Founder invokes the skill.
2. The skill reads the TDD including its Verification Plan section + the
   canonical kind-to-adapter map.
3. For each Work Package the skill is about to emit, the skill determines the
   adapter that applies (from the change's `kind:` and the WP's specific scope).
4. The skill writes the WP markdown with frontmatter containing `verification:`
   — a structured field naming the adapter and either a concrete test artifact
   path (when the artifact exists or can be specified) or
   `deferred-to-follow-on: <identifier>` (when the infrastructure is deferred).
5. The rubric P-VER runs against the WP set. PASS allows the WP set to ship.

**Alternate flow A:** A WP's scope spans multiple adapters (e.g., a WP that
touches both async and contract concerns). The skill records the primary
adapter and an `additional-adapters:` array listing the others.

**Alternate flow B:** A WP's verification is fully deferred (the WP itself
ships pre-infrastructure). The `verification:` field is `deferred-to-follow-on:
<identifier>` and the slice-end review (UC-004) tracks the dependency.

**Exception flow:** A WP's adapter does not fit the change's `kind:` (e.g., a
backend-kind change emitting a WP claiming the documentation adapter). The
rubric P-VER fails. The skill re-evaluates the adapter selection.

**Postconditions:** Every WP in `.specifications/{change}/work-packages/` has
a populated `verification:` field. The behavioural test ledger entry exists
per claim.

**Business rules applied:** FR-005, FR-007, FR-008, FR-009, FR-013.

**Negative requirements:**
- The system MUST NOT emit a WP without a `verification:` field (MUC-006).
- The system MUST NOT accept a `verification:` value whose adapter does not
  appear in the canonical kind-to-adapter mapping (MUC-007).
- The system MUST NOT silently treat empty `verification:` as `n/a` (MUC-008).

---

### UC-004 — Slice-end review identifies a real infrastructure need and auto-drafts a follow-on change

**Actor:** Slice-end review (automated pattern, no human trigger)
**Trigger:** End-of-slice marker reached (slice ships).
**Preconditions:** One or more changes in the slice have populated Verification
Plans containing "Infrastructure needs surfaced (deferred)" subsections.

**Main flow:**
1. Slice-end review begins.
2. The review scans every change in the slice for its Verification Plan's
   deferred-needs subsection.
3. The review extracts each entry's canonical need identifier.
4. The review tallies identifiers across the slice.
5. For each identifier flagged by ≥2 changes, the review auto-drafts a new
   follow-on change targeting that infrastructure need. The follow-on enters
   the normal `/sulis:specify` pipeline at the next opportunity.
6. For singletons (identifiers flagged by exactly one change), the review
   surfaces them to the founder: "These needs were flagged by one change each.
   Defer further to the next slice's scan, or draft as follow-on now?"
7. Founder responds per-need. Defer-further re-enters the next slice's input.
   Draft-now triggers the same auto-draft path as the repeated case.

**Alternate flow A:** A need identifier is flagged 3+ times. The auto-draft is
still emitted once (idempotent); no duplicate drafts.

**Alternate flow B:** A previously-deferred singleton is flagged again in a
later slice. It now qualifies as repeated; the follow-on is auto-drafted.

**Exception flow:** The slice-end review is skipped (manual operator override
or bug). Nothing auto-drafts. Verification Plans remain in deferred state until
the next slice-end runs. The rubric P-VER does not retroactively fail
already-shipped changes.

**Postconditions:** `.specifications/{follow-on}/` exists for each repeated
need + each founder-drafted singleton. The behavioural test ledger references
the follow-on identifier for each deferred claim.

**Business rules applied:** FR-011, FR-012, FR-015.

**Negative requirements:**
- The system MUST NOT auto-draft duplicate follow-ons for the same need
  identifier (idempotency — MUC-005).
- The system MUST NOT silently let singletons rot — they must be surfaced at
  least once per slice-end (MUC-005).
- The system MUST NOT consume deferred entries that lack a canonical need
  identifier; such entries surface as malformed plans and re-enter design.

---

### UC-005 — Grandfathered changes do not break the new rubric

**Actor:** Founder (re-running any methodology gate on an older change), or
automated rubric scan
**Trigger:** Rubric P-VER runs against a change whose shipped-on date precedes
the merge date of this refinement.
**Preconditions:** This refinement has shipped to dev. An older change exists.

**Main flow:**
1. Rubric P-VER begins evaluating the older change's artifacts.
2. The rubric reads the change's shipped-on date (from the change record /
   git metadata).
3. The rubric compares to the merge date of this refinement.
4. Shipped-on precedes merge → rubric returns `PASS — grandfathered` and skips
   all P-VER checks for that change.
5. The change's existing rubric verdict (whatever it was before this refinement)
   is unchanged.

**Alternate flow A:** A grandfathered change is later modified (a follow-on
edit, a backfill, etc.). Two interpretations exist (Open Question 6); the
recommended interpretation is that the modification does **not** retroactively
require a Verification Plan unless the modification is itself a new change
record (CH-NNNNNN).

**Exception flow:** A change's shipped-on date is missing or unparseable. The
rubric falls back to "not grandfathered" and applies P-VER normally. The
founder can override with an explicit grandfathered-flag in the change record.

**Postconditions:** Grandfathered changes continue to ship and re-ship without
new requirements. Backfill of Verification Plans into grandfathered changes is
out of scope (per Out of Scope).

**Business rules applied:** FR-014, FR-016.

**Negative requirements:**
- The system MUST NOT retroactively fail grandfathered changes (NFR-003).
- The system MUST NOT allow backdating a new change's shipped-on date to claim
  grandfathering (MUC variant — out of scope for this SRD, surfaced as an
  open question for future hardening).

---

## Functional Requirements

### FR-001 — Verification Plan section in SRD template

**Source:** UC-001 main flow step 8.

The SRD template (`plugins/sulis/skills/requirements-templates/SKILL.md`) MUST
be extended with a `## Verification Plan` section, located after the
existing standard sections and before any change-specific appendices. The
section MUST contain the following subsections (each is required-present;
content may be `n/a — <justification>` only under trivial-change carveout):

1. `### What user-observable behaviour are we verifying?`
2. `### Verification environment(s)`
3. `### Bootstrap-from-zero case`
4. `### Per-integration verification strategy`
5. `### Per-kind verification adapter`
6. `### Infrastructure needs surfaced (deferred)`

**Acceptance criteria:**
- The template file contains the heading + six subsections in order.
- The template references `VERIFICATION_QUESTIONS.md` for the canonical
  question set.
- A fresh `/sulis:specify` run on a new change produces an SRD whose
  Verification Plan section has all six subsections (populated or `n/a`).

### FR-002 — Verification Plan section in TDD template

**Source:** UC-002 main flow step 7.

The TDD template (produced by `/sulis:draft-architecture`) MUST be extended
with a `## Verification Plan` section of identical shape to FR-001. The TDD's
section concretises the SRD's plan into implementation-side terms (specific
test artifact paths, specific mock identities, specific fixture locations).

**Acceptance criteria:**
- The TDD template contains the heading + six subsections.
- The TDD's plan references the corresponding SRD's plan (by relative path).
- The TDD's plan resolves the SRD's "real vs mocked" abstractions into concrete
  choices.

### FR-003 — requirements-analyst agent extended to ask the canonical questions

**Source:** UC-001 main flow steps 4-7.

`plugins/sulis/agents/requirements-analyst.md` MUST be updated so that during
Phase 3 (Convergent Specification) the agent reads the canonical question set
from `VERIFICATION_QUESTIONS.md` and asks each applicable question to the
founder in plain English (one question at a time, per existing facilitation
rules). The agent prompt MUST cite the canonical by relative path; it MUST NOT
inline-duplicate the question text.

**Acceptance criteria:**
- The agent prompt contains a section instructing the agent to read
  `VERIFICATION_QUESTIONS.md` during Phase 3.
- A grep across `plugins/sulis/agents/requirements-analyst.md` for the literal
  question strings returns zero hits (no inline duplication).
- An integration test (per the dogfood Verification Plan) demonstrates a
  `/sulis:specify` run producing an SRD with all six Verification Plan
  subsections populated from agent-asked questions.

### FR-004 — engineering-architect agent extended to ask concretion questions

**Source:** UC-002 main flow step 5.

`plugins/sulis/agents/engineering-architect.md` MUST be updated to: (a) read
the SRD's Verification Plan section as part of its standard input ingestion;
(b) ask the implementation-side concretion questions for each strategy named
in the SRD; (c) populate the TDD's Verification Plan section with the
concretised answers; (d) surface explicit contradictions between SRD plan and
TDD plan rather than silently overriding.

**Acceptance criteria:**
- The agent prompt cites `VERIFICATION_QUESTIONS.md`.
- The agent prompt includes a contradiction-surfacing instruction (UC-002 alt-A).
- An integration test demonstrates the TDD's plan referencing the SRD's plan
  and the TDD's section passing P-VER.

### FR-005 — plan-work skill extended to require `verification:` field

**Source:** UC-003 main flow steps 3-4.

`plugins/sulis/skills/plan-work/SKILL.md` MUST be updated so that each emitted
Work Package's frontmatter contains a `verification:` field. The field's value
MUST conform to one of:
- A structured map naming the adapter + a concrete test artifact path (when
  applicable): `verification: { adapter: backend, artifact: tests/api/test_orders.py::test_post_creates_order }`
- A structured map naming the adapter + an additional-adapters list (when the
  WP spans multiple): `verification: { adapter: backend, additional-adapters: [contract] }`
- A deferred entry: `verification: { adapter: backend, deferred-to-follow-on: CH-NNNNNN }`
- A trivial carveout: `verification: n/a — trivial-change carveout: <justification>`

**Acceptance criteria:**
- The skill prose cites `VERIFICATION_QUESTIONS.md` for the adapter mapping.
- Every WP emitted by a fresh `/sulis:plan-work` run has the field.
- The rubric P-VER fails on a WP without the field.

### FR-006 — Canonical question set lives at `VERIFICATION_QUESTIONS.md`

**Source:** UC-001 step 4, UC-002 step 4, UC-003 step 2 (Path A: single source
of truth).

A new reference standard MUST be created at
`plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` containing:
- The 20 canonical questions verbatim (Q1-Q4 foundational, Q5-Q13
  per-integration, Q14-Q20 per-kind-adapter).
- The kind-to-adapter mapping table.
- A version field (semver-style).
- A short usage block instructing skills/agents to cite, not duplicate.

**Acceptance criteria:**
- The file exists and contains all 20 questions verbatim from the dispatch brief.
- The file contains the seven kind→adapter rows (methodology, backend,
  frontend, async, infrastructure, documentation, contract).
- The file's version field is `1.0.0`.

### FR-007 — Per-kind verification adapter taxonomy enumerated

**Source:** UC-002 step 5, UC-003 step 3.

`VERIFICATION_QUESTIONS.md` (FR-006) MUST enumerate exactly seven adapter
entries, one per recognised change-kind, each with: the kind value, a one-line
adapter description, the concrete verification shape (e.g., "structural
assertions + integration test where a fresh design produces output with the
new section" for methodology). The seven adapters map 1:1 to the seven kinds
listed in the dispatch brief.

**Acceptance criteria:**
- The taxonomy contains exactly seven rows (or whatever final count Open
  Question 3 resolves to).
- Every existing change-kind in the marketplace lexicon has a row.
- The rubric P-VER references this taxonomy by relative path.

### FR-008 — Kind-to-adapter mapping enforced

**Source:** UC-003 step 3, MUC-007.

The rubric P-VER MUST verify that the change's `kind:` value has a
corresponding adapter row in the canonical mapping. If no row exists, the
rubric MUST fail with an explicit instruction: "Add a new adapter row to
`VERIFICATION_QUESTIONS.md` mapping `kind: {value}` to a verification adapter,
then re-run." Adding a new adapter row is itself a methodology change requiring
its own design + rubric satisfaction.

**Acceptance criteria:**
- The rubric reads `VERIFICATION_QUESTIONS.md` for the mapping.
- A test fixture with an unmapped kind triggers the failure message verbatim.
- A test fixture with a mapped kind passes the check.

### FR-009 — Rubric P-VER added to decompose-validation rubric

**Source:** UC-001 step 9, UC-002 step 8, UC-003 step 5.

`plugins/sulis/references/decompose-validation-rubric.md` MUST be extended
with a new rubric check (P-VER, or numbered P10) that fails design completion
when any of the following hold against an SRD/TDD/WP-set:
- The Verification Plan section is missing.
- A required subsection (FR-001's six) is empty or contains only placeholder
  content (`TBD`, `?`, `to be determined`, fewer than 30 characters of
  substantive content per subsection, or any of the block-listed strings).
- An `n/a` answer lacks an accompanying one-line justification.
- A named infrastructure piece classified as `existing` has no resolvable
  path in the repository.
- The change's `kind:` value has no adapter mapping in
  `VERIFICATION_QUESTIONS.md`.
- The Verification Plan section contains no citation to
  `VERIFICATION_QUESTIONS.md`.
- A WP's `verification:` field is missing or invalid.

**Acceptance criteria:**
- The rubric reference contains the P-VER entry.
- The `/sulis:requirements-validation` skill (and equivalent for TDD/WPs)
  invokes the new check.
- Each failure mode above has a test fixture that triggers it.

### FR-010 — Infrastructure classification check

**Source:** UC-002 step 7, MUC-002.

When the Verification Plan's "Per-integration verification strategy" subsection
names an infrastructure piece (a file path, a mock identity, a fixture
location), the rubric P-VER MUST classify it as one of `existing`, `deferred`,
or `out-of-scope`. The classification MUST be either explicit in the section
content (preferred) or inferrable from the wording. `existing` requires a
path that resolves at design time.

**Acceptance criteria:**
- The rubric implementation contains the classification logic.
- A test fixture with a hallucinated path triggers the classification failure.
- A test fixture with a deferred entry (named follow-on identifier) passes.

### FR-011 — Deferred infrastructure needs recorded with canonical identifier

**Source:** UC-004 step 3.

Every entry under "Infrastructure needs surfaced (deferred)" MUST include a
canonical need identifier — a stable, slug-style name for the need (e.g.,
`recording-mock-sendgrid`, `test-oauth-accounts`, `seed-data-fixtures-orders`).
The identifier MUST be machine-readable by the slice-end review scan.

**Acceptance criteria:**
- The Verification Plan template (FR-001) instructs the agent to assign an
  identifier per deferred entry.
- The slice-end review scan parses the identifiers from real Verification
  Plans without ambiguity.

### FR-012 — Slice-end review scans deferred needs and auto-drafts follow-ons

**Source:** UC-004 main flow.

The existing slice-end review pattern MUST be extended to: (a) scan every
change in the slice for "Infrastructure needs surfaced (deferred)" entries;
(b) tally entries by canonical identifier across the slice; (c) auto-draft a
follow-on change for each identifier flagged by 2+ changes; (d) surface
singletons to the founder for explicit decision (defer further or draft now).
The scan MUST be idempotent.

**Acceptance criteria:**
- The slice-end review pattern is updated (its reference standard or the
  skill that implements it).
- A test fixture with two changes flagging the same identifier produces
  exactly one follow-on auto-draft.
- A test fixture with one change flagging an identifier produces a singleton
  surface to the founder, not an auto-draft.

### FR-013 — Per-WP `verification:` field in frontmatter

**Source:** UC-003 step 4.

Every Work Package emitted by `/sulis:plan-work` after this refinement MUST
carry a `verification:` frontmatter field per the schema in FR-005.

**Acceptance criteria:**
- The plan-work skill prose enforces the field.
- The rubric P-VER fails on a WP without the field.
- The behavioural test ledger (FR-015) reads from the field.

### FR-014 — Grandfathered-change detection

**Source:** UC-005 main flow.

The rubric P-VER MUST detect grandfathered changes by reading the change's
shipped-on date (from the change record metadata) and comparing to the merge
date of this refinement. Shipped-on precedes merge → P-VER returns `PASS —
grandfathered` and does no further checks against that change.

**Acceptance criteria:**
- The rubric implementation reads the change record's shipped-on date.
- The rubric stores the refinement's merge date in a configurable constant.
- A test fixture with a pre-merge shipped-on date passes without running
  per-subsection checks.

### FR-015 — Behavioural test ledger records each claim and its artifact

**Source:** NFR-007 (claim-to-artifact traceability), MUC-006.

A behavioural test ledger MUST be maintained at
`.specifications/{change}/verification-ledger.md` (or an equivalent path the
engineering-architect specifies in the TDD). The ledger records, for each
claim in the Verification Plan, the test artifact path that satisfies it OR
the `deferred-to-follow-on:` identifier. The slice-end review MUST scan the
ledger and flag any row that has neither.

**Acceptance criteria:**
- The TDD template (FR-002) instructs the engineering-architect to specify
  the ledger path.
- The plan-work skill (FR-005) writes ledger entries as it emits WPs.
- The slice-end review scan reads the ledger and flags orphan rows.

### FR-016 — Refinement merge date stored and referenced

**Source:** FR-014 dependency.

The merge date of this refinement (CH-01KT2B) MUST be stored in a
machine-readable location (e.g., a constant in the rubric reference standard,
or a marker file under `.architecture/`) so FR-014's grandfather check can
reference it deterministically.

**Acceptance criteria:**
- The merge date is committed alongside the rubric extension.
- The rubric reads the date at evaluation time, not at compile time.

---

## Non-Functional Requirements

See `NFR.md` for the full non-functional specification:

- **NFR-001** — Plain-English answerability (Flesch-Kincaid Grade Level ≤ 10
  for the Verification Plan section)
- **NFR-002** — Honest classification of real vs deferred infrastructure
- **NFR-003** — Backward compatibility for grandfathered changes
- **NFR-004** — Single source of truth for the question set
- **NFR-005** — Dogfood acceptance (this very SRD must pass its own rubric)
- **NFR-006** — Canonical question set is citable from every consumer
- **NFR-007** — Claim-to-artifact traceability
- **NFR-008** — Design-side ships without infrastructure-side dependency

---

## Open Questions

These are surfaced explicitly to the founder; they are not resolved
autonomously.

1. **Naming.** "Verification Plan" vs "Acceptance Strategy" vs "How We'll
   Verify". *Recommendation:* "Verification Plan" — it reads as plain
   English, signals design-time intent (a plan, not a result), and pairs
   cleanly with the existing "Plan-work" lexicon.
2. **Required-for-every-change vs first-N-WPs-only.** *Recommendation:* MUST
   for every new change from this refinement's merge date onwards; existing
   changes grandfathered.
3. **Per-WP `verification:` field shape.** Single adapter + artifact, or
   structured map with additional-adapters / deferred-to-follow-on alternatives?
   *Recommendation:* the structured map shape in FR-005, which handles all
   three cases.
4. **Where the 20-question set lives.**
   `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` (separate
   standard) vs embedded inside the existing decompose-validation rubric.
   *Recommendation:* the separate standard (FR-006), so the same canonical can
   be cited from multiple skills + agent prompts without duplication.
5. **Follow-on auto-draft trigger timing.** Fire immediately when a deferred
   need is flagged the 2nd time, or wait for slice-end? *Recommendation:*
   wait for slice-end, matching the existing follow-on pattern.
6. **Grandfathered-change modifications.** If a grandfathered change is later
   edited (a follow-on fix, a typo), does the edit trigger a Verification Plan
   requirement? *Recommendation:* No — only new change records (`CH-NNNNNN`)
   created after the merge date trigger P-VER. Edits to grandfathered changes
   inherit grandfathered status.
7. **Per-kind adapter count.** Is the seven-kind taxonomy in the dispatch
   brief stable, or will new kinds (e.g., `data-migration`, `experiment`) need
   immediate slots? *Recommendation:* ship the seven, and treat new kinds via
   the FR-008 mechanism — each new kind requires a new methodology change to
   add its adapter row.

---

## Out of Scope

- Building any verification infrastructure (test auth, mock notifications,
  seed-data pipelines, recording mocks for specific vendors). Each is its own
  follow-on change triggered by the FR-012 auto-draft pattern.
- Retroactively backfilling Verification Plans into shipped changes (e.g.,
  release-train, discovery). Grandfathered.
- Behavioural test framework selection (pytest vs vitest vs others). The
  adapter names *what* gets verified, not the framework.
- ServiceSpec extension to include verification. Could be a future change;
  not this one.
- Cross-language test orchestration (Python ↔ TypeScript test harness). Out
  of scope.
- Renaming or deprecating "post-hoc verification" as a concept — the
  refinement adds Verification Plan; it does not abolish other forms of review.

---

## Verification Plan

**This section is the dogfood.** It populates the new structure for THIS change
— a methodology refinement. Every future SRD will copy this shape.

### What user-observable behaviour are we verifying?

That the methodology refinement actually changes how design happens, in three
observable ways:

1. **The founder is asked the verification questions during `/sulis:specify`.**
   Concretely: when the founder runs `/sulis:specify` on a fresh new change
   after this refinement merges, the requirements-analyst agent asks at least
   the four foundational questions in plain English, one at a time, and the
   produced SRD contains a `## Verification Plan` section with the six
   subsections populated.
2. **The produced SRD's Verification Plan section passes rubric P-VER on a
   fresh run.** Concretely: `/sulis:requirements-validation` (or equivalent)
   against the produced SRD returns PASS with no P-VER failures.
3. **A WP emitted by `/sulis:plan-work` after this refinement carries a
   `verification:` frontmatter field whose adapter matches the change's
   `kind:`.** Concretely: grep across a freshly-produced
   `.specifications/{test-change}/work-packages/` shows every `.md` file has
   a `verification:` line in its frontmatter.

### Verification environment(s)

- **Local developer machine.** The verification happens on the founder's
  laptop running `/sulis:specify`, `/sulis:draft-architecture`,
  `/sulis:plan-work`, and `/sulis:requirements-validation`. No CI dependency.
- **CI (GitHub Actions).** The rubric P-VER runs as part of the existing
  rubric evaluation step on every PR. No new CI infrastructure needed —
  P-VER plugs into the existing rubric harness.
- **Dev tier.** Not applicable for this change (no deployed runtime
  behaviour to verify in dev).

**What differs between environments:** Local has the live skill prose + agent
prompts and can produce real SRDs. CI runs the rubric against committed SRDs.
There is no behavioural difference in P-VER itself between local and CI.

### Bootstrap-from-zero case

A fresh consumer marketplace clone (no prior `.specifications/`, no
grandfathered-merge-date constant set, no canonical `VERIFICATION_QUESTIONS.md`
present yet — i.e., the moment immediately before this refinement's first
commit) MUST be able to:
1. Have this refinement merged in.
2. Immediately run `/sulis:specify` on a new change.
3. Produce an SRD with a populated Verification Plan section.

This is verifiable by running step 1-3 in a fresh git clone with no other
state. The refinement ships everything it needs: the canonical question set,
the rubric extension, the skill prose updates, the agent prompt updates, and
the merge-date constant. Bootstrap requires nothing else.

### Per-integration verification strategy

This change has limited external integrations (it's a methodology refinement,
not a system that talks to vendors). The integrations it touches:

| Integration | Strategy | Classification |
|---|---|---|
| **requirements-analyst agent** (existing) | Real — the refinement's integration test runs the actual agent prompt against a test change and asserts the produced SRD's structure. | `existing` (the agent itself exists at `plugins/sulis/agents/requirements-analyst.md`) |
| **engineering-architect agent** (existing) | Real — same shape as above against a fresh TDD production. | `existing` (`plugins/sulis/agents/engineering-architect.md`) |
| **plan-work skill** (existing) | Real — the test runs the skill against a fresh TDD and greps the emitted WPs for the `verification:` field. | `existing` (`plugins/sulis/skills/plan-work/SKILL.md`) |
| **decompose-validation rubric** (existing) | Real — fixture-driven; P-VER's pass/fail behaviour is asserted against a curated set of SRD/TDD/WP fixtures (one per failure mode in FR-009). | `existing` (`plugins/sulis/references/decompose-validation-rubric.md`) |
| **slice-end review pattern** (existing) | Real — fixture-driven; the auto-draft idempotency property is asserted by running the scan twice over a fixture set of two changes flagging the same need. | `existing` (referenced from the existing methodology) |
| **Git metadata (shipped-on date)** | Real — the grandfather check (FR-014) reads real commit dates from the git history. | `existing` (git is git) |

**No vendor sandboxes, no real OAuth flows, no notification providers, no
external APIs are involved.** This is intentional — the methodology side is
deliberately decoupled from the infrastructure side (NFR-008).

### Per-kind verification adapter

This change's `kind:` is **methodology** (predominantly — skill prose updates,
agent prompt updates, a new reference standard, a rubric extension; per the
dispatch brief: "this is a methodology refinement, kind=docs predominantly").

**Adapter for kind: methodology:** *structural assertions that the new content
exists + has substance + is referenced from the expected places. Plus an
integration test where a fresh design dispatch produces output that meets the
new shape.*

**Concrete verification shape for this change:**

1. **Structural assertions:**
   - `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` exists, is
     ≥ 100 lines, contains 20 questions verbatim from the dispatch brief,
     contains a kind-to-adapter table with at least 7 rows.
   - `plugins/sulis/skills/requirements-templates/SKILL.md` contains a
     `## Verification Plan` template block with the six required subsections.
   - `plugins/sulis/agents/requirements-analyst.md` contains a citation to
     `VERIFICATION_QUESTIONS.md` and an instruction to ask the questions in
     Phase 3.
   - `plugins/sulis/agents/engineering-architect.md` contains an equivalent
     citation + concretion-question instruction.
   - `plugins/sulis/skills/plan-work/SKILL.md` contains the
     `verification:`-field-enforcement language.
   - `plugins/sulis/references/decompose-validation-rubric.md` contains the
     P-VER check with each failure mode from FR-009 enumerated.

2. **Integration test — fresh design dispatch produces output with the new
   shape:**
   - Spin up a test change (a fresh `CH-NNNNNN` record).
   - Run `/sulis:specify` against it with a scripted/replayable founder
     persona that answers the foundational verification questions in plain
     English.
   - Assert: the produced `SRD.md` contains the `## Verification Plan`
     section with all six subsections populated (not placeholder, not blank).
   - Assert: `/sulis:requirements-validation` against the produced SRD
     returns PASS verdict for P-VER specifically.

3. **Dogfood proof-of-life:** This SRD's `## Verification Plan` section
   (this section) is itself the worked example. The rubric P-VER, when
   eventually live, MUST return PASS against this very section.

### Infrastructure needs surfaced (deferred)

This change deliberately surfaces zero infrastructure needs — every
verification path above resolves to existing assets in the repo. The whole
point of NFR-008 is that the methodology refinement ships without requiring
any new verification infrastructure first.

**However**, the change *enables* future infrastructure needs to be surfaced.
The very first time a downstream design's Verification Plan flags
`recording-mock-sendgrid` (or any specific vendor mock, test OAuth account
pipeline, seed-data fixture, etc.), the FR-012 slice-end review scan picks it
up. Two such flags trigger an auto-draft. **That follow-on change becomes the
first real exercise of the infrastructure side.**

**Trivial-change carveout disposition:** Does NOT apply to this change. This
change is non-trivial — it modifies methodology assets that downstream changes
depend on. The Verification Plan section above is fully populated, not
`n/a`-carveout.

---

## Cross-references

- **`MISUSE_CASES.md`** — Adversarial cases MUC-001 through MUC-008. Every
  MUC has a defined system response that maps to an FR or NFR.
- **`PRIMITIVE_TREE.jsonld`** — 15 nodes. Domain entities (Verification Plan
  section, canonical question set, infrastructure need, behavioural test
  ledger); policies (adapter taxonomy, rubric check, grandfathered policy,
  trivial-change carveout, dogfood acceptance); processes (follow-on
  auto-draft, slice-end review); integrations (requirements-analyst,
  engineering-architect, plan-work, decompose-validation rubric).
- **`NFR.md`** — Eight non-functional requirements covering plain-English
  readability, classification honesty, backward compatibility, single source
  of truth, dogfood, citation, traceability, and design-side decoupling.
- **`GLOSSARY.md`** — Locked vocabulary, "Also Known As" entries, "NOT the
  Same As" disambiguations.
- **`diagrams/`** — Use cases, process flows, sequence diagrams, state
  diagrams, data flows.
- **`HANDOFF_TO_SEA.md`** — Design hints for `/sulis:draft-architecture`.
- **Canonical reference (to be created by this change):**
  `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`.
