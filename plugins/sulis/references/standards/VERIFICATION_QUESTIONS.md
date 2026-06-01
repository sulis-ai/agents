---
id: VERIFICATION_QUESTIONS
title: Canonical Verification Questions (the 20-question set + kind-to-adapter map)
version: 1.0.0
status: active
applies_to: every-new-change-from-CH-01KT2B-onwards
purpose: |
  The single source of truth for the verification questions the
  methodology asks at design time, and the per-kind adapter rows that
  map each change's `kind:` to a concrete verification shape. Every
  consumer (skill prose, agent prompt, rubric) cites this file by
  relative path. No consumer inlines the question text.
---

# Canonical Verification Questions

> **This file is the contract.** It is the single source of truth (SSOT)
> for the design-time verification questions and the per-kind adapter
> table. Every consuming agent prompt, skill prose, and rubric reads
> this file by **relative path citation** and must not inline-duplicate
> the question text or the adapter rows.

> **Version:** 1.0.0 - **Status:** active - **Applies to:** every new
> change from this refinement's merge date (`CH-01KT2B` onwards). Edits
> to grandfathered changes inherit grandfather status per ADR-006.

## Why this exists

The verification questions exist as a standalone reference so that
three concerns evolve independently:

1. **The questions themselves** (this file) - what we ask at design
   time.
2. **The rubric that enforces the answers** (`decompose-validation-rubric.md`
   P-VER) - how we check the answers are populated and sound.
3. **The agent prompts and skill prose** that orchestrate the asking -
   when and how the questions surface to the founder.

Embedding the questions inside the rubric (the rejected alternative
in ADR-004) couples question content with pass/fail logic and creates
drift between agents reading a snapshot of the old embedded version
and the live rubric. Keeping the canonical standalone makes the
single-source-of-truth invariant (SRD FR-006, FR-007) architecturally
enforced rather than convention-only.

## How consumers cite this file

Every consumer artifact (an SRD's Verification Plan section, a TDD's
Verification Plan section, an agent prompt that asks the questions,
a rubric that enforces them) carries the canonical HTML-comment
annotation immediately before the section that depends on this file:

```html
<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->
```

The P-VER rubric (per `decompose-validation-rubric.md`) parses this
annotation and runs two checks: (1) the path resolves to a live file;
(2) the version is within currency. This is the MUC-003 defence -
consumers cannot silently skip the canonical and inline their own
question set.

**Do not inline-duplicate the question text or the adapter rows.** If
a downstream artifact needs to show the questions to the founder, it
references this file by relative path. If a downstream artifact needs
to answer the questions, it does so in its own Verification Plan
section, citing the canonical.

---

## Foundational

Asked once per change. These four questions establish the verification
posture before any per-integration or per-kind work begins.

- Q1. What user-observable behaviour are we verifying? *(Prompt: "If
  this change shipped successfully, what would a customer notice that
  is different?" Good answer: a concrete observable - a new screen,
  a faster response, an email that arrives, a button that appears.)*

- Q2. In what environment(s) does verification run - local, CI, dev,
  staging? *(Prompt: "Where do the checks actually execute? On the
  developer's laptop? In CI? After deploy to dev?" Good answer: each
  environment named, with what runs there.)*

- Q3. Can the change be verified from a fresh clone with zero prior
  state - the bootstrap-from-zero case? *(Prompt: "If someone clones
  the repo today and runs the verification, do they need anything we
  haven't shipped?" Good answer: yes/no with a list of any
  pre-shipped requirements.)*

- Q4. What is the change's `kind:` value, which drives the adapter
  choice? *(Prompt: "Is this backend, frontend, async, methodology,
  documentation, infrastructure, or contract?" Good answer: one of
  the seven canonical kinds from the table below.)*

---

## Per-integration

Asked once per touched integration (each external vendor, API, broker,
or internal service the change interacts with). A change touching zero
integrations records "none" once; a change touching three integrations
answers Q5-Q13 three times.

- Q5. Which external integrations does the change touch - vendors,
  APIs, brokers? *(Prompt: "What outside systems do we talk to?" Good
  answer: each integration named, plus the boundary surface - SDK,
  HTTP, webhook, queue.)*

- Q6. Is each integration verified real, deferred, or out-of-scope?
  *(Prompt: "Are we running this against the real thing, mocking it
  out, or skipping verification for now?" Good answer: one of the
  three classifications per integration.)*

- Q7. For real integrations - what credentials, test accounts, or
  sandboxes are required? *(Prompt: "If we're hitting the real
  service, where do the credentials come from?" Good answer: the
  test account name, the sandbox URL, or the credential source -
  never a real production secret.)*

- Q8. For deferred integrations - what is the canonical need
  identifier (slug)? *(Prompt: "If we're deferring, what's the
  follow-on we need to do later?" Good answer: a slug from
  `TDD §Canonical Identifiers`, e.g. `recording-mock-sendgrid`,
  `test-oauth-google`, `seed-data-fixtures-orders`.)*

- Q9. For out-of-scope integrations - what is the justification?
  *(Prompt: "If we're skipping verification entirely, why is that
  the right answer?" Good answer: a sentence with substance - not
  "n/a", not "later".)*

- Q10. Are there idempotency or replay concerns at the integration
  boundary? *(Prompt: "If the same request fires twice, does the
  system behave the same way?" Good answer: yes/no with the
  protection mechanism named.)*

- Q11. Are there auth or authz boundaries crossed by the integration?
  *(Prompt: "Does the integration require a logged-in user, a service
  account, an OAuth token?" Good answer: the auth shape, plus how
  it's tested.)*

- Q12. What is the failure mode if the integration is unavailable
  during verification? *(Prompt: "If the third-party service is down
  when we run the test, what happens?" Good answer: timeout, retry,
  graceful degradation, test-skip - one of these with the chosen
  rationale.)*

- Q13. What observability (trace, log, metric) is asserted at the
  integration boundary? *(Prompt: "How do we see the integration was
  exercised? What's in the logs?" Good answer: the signal name, the
  assertion shape, where it surfaces.)*

---

## Per-kind verification adapter

Asked once per change, scoped by the answer to Q4 (the change's
`kind:`). The seven adapter rows are locked by ADR-007 - new kinds
extend the table via a methodology change, not by inline invention.

- Q14. Which adapter row applies from the seven-row table below?
  *(Prompt: "Look at your `kind:` value and find the matching row -
  what does that row say verification looks like?" Good answer: the
  adapter name, plus the row's one-line shape paraphrased.)*

- Q15. What is the concrete test artifact path - Shape 1 of ADR-003?
  *(Prompt: "Where does the test live? Give the file path and the
  test name." Good answer: a pytest nodeid, a Vitest spec ref, or a
  fixture path - whatever the adapter row prescribes.)*

- Q16. If deferred (Shape 2) - what is the follow-on identifier?
  *(Prompt: "If we don't have the test yet, what's the canonical
  slug for the follow-on that adds it?" Good answer: the canonical
  need identifier from `TDD §Canonical Identifiers`.)*

- Q17. If trivial carveout (Shape 3) - what is the justification?
  *(Prompt: "If this change genuinely has nothing to verify, why is
  that true?" Good answer: a sentence with substance, at least 30
  characters, explaining the carveout - never bare "n/a".)*

- Q18. Does the change span multiple adapters? List the
  additional-adapters. *(Prompt: "Does this change touch backend AND
  contract? Frontend AND a11y? Name every adapter that applies."
  Good answer: a list, or "single adapter".)*

- Q19. What infrastructure does the adapter need - existing,
  deferred, or out-of-scope? *(Prompt: "Does the test need a database,
  a broker, a test container, a sandbox? Is that infra here today?"
  Good answer: each piece classified, with the canonical need
  identifier if deferred.)*

- Q20. Is the dogfood acceptance criterion satisfied - does the
  change's own artifacts pass P-VER? *(Prompt: "Run the rubric
  against this change's own SRD, TDD, and WPs. Do they pass?" Good
  answer: yes, plus the rubric output reference - or no, with a
  specific failure-mode pointer.)*

---

## Kind-to-adapter table (seven rows, locked by ADR-007)

| kind             | adapter (one-line shape)                                                                                                |
|---               |---                                                                                                                      |
| `methodology`    | Structural assertions + integration test where a fresh design dispatch produces output with the new shape                |
| `backend`        | Behavioural API test against a running service + persistence assertion + (where applicable) idempotency / replay check    |
| `frontend`       | Component-rendering test with axe-core a11y + visual diff against the design-system tokens + interaction test            |
| `async`          | Producer-publishes + consumer-receives integration test against a real broker (or test-container) + dead-letter / replay assertion |
| `infrastructure` | Apply-and-rollback integration test against ephemeral target + drift-check + cost / quota guardrail                       |
| `documentation`  | Link-resolution check + readability score (FK <= 10 for founder-facing) + freshness-of-cited-sources check                |
| `contract`       | Contract conformance test on both sides of the seam (provider + consumer) + schema-evolution compatibility check          |

A change whose `kind:` value does not appear in this table fails the
P-VER rubric with an explicit instruction: add a new adapter row via
a methodology change, then re-run. The extension mechanism is
self-applying (ADR-007).

---

## Usage notes

**Cite, do not duplicate.** Every consumer artifact carries the
HTML-comment annotation immediately before the dependent section.
Inlining the question text into agent prompts, skill prose, or
fixtures breaks the SSOT property (SRD FR-006) and creates drift on
the next minor-version bump.

**Per-WP frontmatter** carries the `verification:` field per ADR-003's
three shapes:

```yaml
# Shape 1 - Concrete (the common case)
verification:
  adapter: backend
  artifact: tests/api/test_orders.py::test_post_creates_order

# Shape 2 - Deferred
verification:
  adapter: backend
  deferred-to-follow-on: recording-mock-sendgrid

# Shape 3 - Trivial carveout
verification:
  na: true
  justification: "trivial-change carveout (CW-05): comment-only edit; no behaviour change"
```

The schema, the adapter values, and the field semantics are locked by
ADR-003. The `adapter` value MUST match a row in the table above.

**Section heading is `## Verification Plan`** in every SRD and TDD
(ADR-001 - exact casing, exact spacing, no abbreviation). The P-VER
rubric anchors on this literal.

**Grandfathered changes (ADR-006).** Changes whose `started_at` field
in `.changes/{slug}.yaml` precedes the merge date of `CH-01KT2B`
inherit grandfather status. Edits to those changes inherit the same
status - a typo fix on a 2025 file does not trigger P-VER. A new
change record with `started_at` postdating the merge is gated by
P-VER regardless of which files it touches.

**Cross-references:** ADR-001 (section name), ADR-003 (per-WP
frontmatter shape), ADR-004 (this file's canonical location), ADR-006
(grandfathering edit policy), ADR-007 (the seven-row adapter table).
SRD FR-006 (single source of truth invariant), SRD FR-007 (citation
discipline - no inline duplication).

---

## Version history

| version | date       | change                                                            |
|---      |---         |---                                                                |
| v1.0.0  | 2026-06-01 | Initial release - 20 questions + 7-row adapter table (CH-01KT2B). |

Bumps are minor on question addition or removal; major on a structural
break (e.g., adapter table row removed, question group restructured).
Consumers' currency check (P-VER failure mode 7) reads the `version`
field in the front matter and asserts the annotation in the consumer
artifact is within one minor version of currency.

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->
