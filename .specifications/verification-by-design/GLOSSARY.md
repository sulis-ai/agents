# Glossary — verification-by-design

**Change:** CH-01KT2B · `change/extend-verification-by-design` · primitive: extend
**Date:** 2026-06-01
**Status:** draft

This glossary locks the vocabulary used across SRD.md, MISUSE_CASES.md, and
PRIMITIVE_TREE.jsonld. New terms enter here first; artifacts cite them by their
preferred form.

---

## Preferred terms

| Term | Definition | Also Known As |
|---|---|---|
| **Verification Plan** | A required section in every new design artifact (SRD, TDD) and a required frontmatter field on every Work Package, recording how the change's user-observable behaviour will be verified end-to-end. Distinct from unit tests and code review. | acceptance strategy; "how we'll verify it" |
| **Verification question set** | The canonical, numbered list of 20 questions the design phase must ask (4 foundational + 9 per-integration + 7 per-kind-adapter). Lives at `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` as a single source of truth referenced by every skill that asks them. | the 20 questions; the canonical question set |
| **Verification adapter** | The per-kind strategy that says, given the kind of change (methodology, backend, frontend, async, infrastructure, documentation, contract), what concrete shape verification takes. Each kind has exactly one adapter. | per-kind strategy; kind→strategy mapping |
| **Kind-to-adapter mapping** | The lookup table inside `VERIFICATION_QUESTIONS.md` that names which adapter applies to which `kind:` of change. Every recognised `kind:` value maps to exactly one adapter. | adapter map; kind taxonomy |
| **Infrastructure need** | A piece of verification infrastructure that a design's Verification Plan identifies as required but not yet built — e.g., test OAuth accounts, a recording mock for SendGrid, a seed-data fixture pipeline. Surfaced during design; deferred to a follow-on change. | infra surface; deferred infra requirement |
| **Follow-on change** | A change auto-drafted at slice-end review when one or more Verification Plans flagged the same infrastructure need. The follow-on builds the infra piece; the original changes that flagged it then become verifiable. | derivative change; infra-backed change |
| **Bootstrap-from-zero** | A verification environment with no seed data, no pre-existing credentials, no warmed caches, no prior runs. The Verification Plan must explicitly answer whether the change still works under this condition. | cold start; from-zero environment; greenfield env |
| **Verification environment** | The runtime context in which verification executes — local developer machine, CI runner, dev tier, staging tier, or production. Each has different infrastructure available. | env; verification tier |
| **Recording mock** | A test double that captures the calls made to it (arguments, frequency, ordering) and exposes those captures for assertion. Distinct from a stub (returns canned data) and a fake (working in-memory implementation). | call-capturing mock; spy |
| **Sandbox provider** | The vendor-supplied non-production endpoint for an external service (e.g., Stripe test mode, SendGrid sandbox). Behaves like real but does not move money / send mail / leave permanent side-effects. | test mode; sandbox endpoint |
| **Auth bypass** | A mechanism that lets automated tests skip the interactive auth flow (e.g., signed session token issued directly by the test harness). Lives only in test/dev tiers; production deployments forbid it. | test-mode auth; bypass token |
| **Verification rubric check** | A rubric item (analogous to P1..P9 in the decompose-validation rubric) that fails the design if the Verification Plan section is missing or contains placeholder content (`TBD`, blank, "see infra change"). | the rubric gate; P-VER |
| **Trivial-change carveout** | The existing carveout (CW-05) for changes whose entire scope is a typo, comment fix, or other genuinely no-behaviour-impact edit. Such changes still record a Verification Plan but populate it with `n/a — trivial-change carveout` and a one-line justification. | CW-05; typo carveout |
| **Grandfathered change** | A change that shipped before this methodology refinement and therefore did not produce a Verification Plan. The rubric does not retroactively penalise these. New changes from this refinement onwards do not qualify. | pre-refinement change; legacy change |
| **Dogfood acceptance** | The acceptance criterion that this change's own design artifacts (THIS SRD, the TDD produced by `/sulis:draft-architecture`, the work packages produced by `/sulis:plan-work`) themselves include populated Verification Plans. The change ships only when it satisfies its own rubric. | self-application; eat-own-dogfood |
| **Behavioural test ledger** | The append-only record of "Verification Plan claimed X; behavioural test Y was written that verifies X." Closes the loop between design-time claim and implementation-time evidence. Lives in the change's evidence record. | claim-to-test ledger; verification ledger |

---

## NOT the Same As (disambiguation)

| Term A | Term B | Distinction |
|---|---|---|
| **Verification Plan** | **Test plan** | The Verification Plan is design-time and answers *what user-observable behaviour proves this works + which infrastructure pieces are needed*. A test plan is implementation-time and lists specific test cases. A Verification Plan can call for "an integration test against the deployed endpoint" without enumerating the assertions. |
| **Verification Plan** | **Post-hoc verification** | Verification Plan is asked **during design** (alongside "what does it do?"). Post-hoc verification is whatever a reviewer happens to check after the code merges. The refinement replaces the latter with the former. |
| **Verification** | **Unit test** | Verification is *user-observable behaviour proves the change works end-to-end*. A unit test proves a function's internal behaviour. Unit tests are necessary but never sufficient for the Verification Plan. |
| **Verification** | **Code review** | Code review proves *the code looks right*. Verification proves *the thing does what we said it would do*. The methodology refinement exists because the marketplace has been shipping changes that passed code review but were never actually run end-to-end. |
| **Verification adapter** | **Test framework** | The adapter names *what gets verified and in what shape* (e.g., "structural assertions + integration test against a fresh design"). It does not name the framework (pytest, vitest). Framework choice is out of scope for this change. |
| **Sandbox provider** | **Recording mock** | A sandbox is provider-supplied and runs real code paths against a non-production endpoint. A recording mock is a test double inside the test process that captures call signatures. Sandboxes have rate limits and quirks; recording mocks do not. |
| **Auth bypass** | **Mocked identity** | Auth bypass issues a real signed token via a back-door path; the application stack runs unchanged. Mocked identity replaces the identity provider entirely; the application talks to a fake. Bypass tests more of the real system. |
| **Bootstrap-from-zero** | **Steady-state verification** | Bootstrap-from-zero asks whether the change works in a fresh environment with no prior runs. Steady-state asks whether it works in an environment with realistic prior state. Both can be required by a single Verification Plan. |
| **Infrastructure need** | **Verification gap** | An infrastructure need is a missing *capability* (e.g., "no recording mock for SendGrid exists yet"). A verification gap is a missing *answer* in the Verification Plan itself (e.g., "the per-integration question for SendGrid is blank"). The rubric catches gaps. The slice-end review converts repeated needs into follow-on changes. |
| **Follow-on change** | **Backlog item** | A follow-on change is a fully-typed change record (CH-NN...), with its own SRD/TDD/WPs pipeline, auto-drafted by slice-end review when ≥2 Verification Plans flag the same infrastructure need. A backlog item is just a note. |

---

## Acronyms

| Acronym | Expansion |
|---|---|
| **TDD** | Technical Design Document (the artifact `/sulis:draft-architecture` produces) |
| **SRD** | Software Requirements Document (this artifact) |
| **WP** | Work Package (atomic shippable unit) |
| **n/a** | not applicable |
| **TBD** | to be determined (forbidden as a populated value in a Verification Plan section — the rubric fails on it) |
