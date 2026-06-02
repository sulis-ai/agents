---
id: WP-008
title: n=1 dogfood acceptance — the three GitHub Actions rules become real assertions
status: pending
change_id: "01KT3X2M0JHFN583DKKV77W83C"
kind: backend
primitive: create
group: EXPAND
sequence_id: WP-008
dependsOn: [WP-006, WP-007]
blocks: []
estimated_token_cost:
  input: 4k
  output: 5k
tdd_section: "Proof §3 the n=1 dogfood as the load-bearing proof (lines 177-191); FR-009; UC-005; A-3 meaning-check"
adrs: [ADR-005]
verification:
  adapter: methodology
  artifact: tests/methodology/test_github_actions_dogfood.py::test_reusable_workflow_rule_cited_to_real_github_url
---

## Context

The terminal sink. Turns the GitHub Actions contract's three grounded rules
(WP-006) into **real assertions** — the load-bearing proof that the discipline
works. This is distinct from WP-007's conformance check (which asserts the
*schema* holds): WP-008 asserts the *grounding is real* — the citations point
at live GitHub-docs URLs that resolve, the load-bearing rules are probed
`confirmed` with evidence, and the deferred rule carries the canonical
deferred-need id.

**TDD reference:** Proof leg 3 (lines 177-191) — "The GitHub Actions contract
is itself the proof the discipline works. Its three grounded rules become real
assertions." The MUST at lines 188-191 is the spine of this WP: no rule
uncited; no load-bearing rule unprobed-and-not-justifiably-deferred; the URLs
+ quotes re-retrieved at authoring.

**Why this depends on WP-006 + WP-007.** WP-006 produces the contract under
assertion. WP-007 provides the harness-refusal fixtures + the shared
claim-entry validator this WP imports. WP-008 is the highest-value assertion
and the last to land — everything precedes it.

**Why this is separate from WP-007.** WP-007 is *structural + behavioural*
(does the schema hold; does the harness refuse). WP-008 is the *dogfood
acceptance* (are the three specific rules grounded to real, resolving URLs with
real probes). The two are different assertion classes against different
subjects; bundling would hide the dogfood proof inside a generic suite.

**Pre-Work Prior-Art Check:** mirrors the verification-by-design WP-008
(E2E + dogfood) pattern — the change's own artifacts are asserted against the
new gate. Here the new gate's first instance (`github-actions.md`) is asserted
against the standard's MUST.

## Contract

### Files created

- `tests/methodology/test_github_actions_dogfood.py`:
  - `test_reusable_workflow_rule_cited_to_real_github_url` — the rule's
    `source` is a real `docs.github.com` URL that **resolves**, and the entry
    carries `probe-result: confirmed` with non-empty `probe-evidence`.
  - `test_bot_token_rule_cited_and_probed` — the bot-token rule is cited to a
    real resolving URL and `probe-result: confirmed`; a meaning-check assertion
    guards the "*new* workflow run" qualifier (MUC-002 / A-3) — the quote
    contains the "new" semantics, not just any token-trigger statement.
  - `test_branch_protection_rule_cited_and_deferred` — cited to a real
    resolving URL; `probe-result: deferred:paid-private-repo-for-branch-protection-probe`.
  - `test_no_rule_uncited` — the UC-005 MUST: every rule has a `source`
    (unless `inferred:true`); no load-bearing rule is unprobed-and-not-deferred.

### What "real assertion" means here (vs WP-007 conformance)

- WP-007 `test_contract_conformance`: the **schema invariants** hold (fields
  present, `inferred:false` ⇒ source+quote+date).
- WP-008 (this WP): the **grounding is genuine** — the URLs resolve live, the
  quotes are locatable, the probes ran (`confirmed` + evidence) or are
  justifiably deferred with the canonical id, and the meaning-check guards the
  bot-token "new" qualifier.

### The MUST this WP enforces (TDD lines 188-191)

> The GitHub Actions contract MUST NOT ship with any of the three rules
> uncited, nor with a load-bearing rule unprobed-and-not-justifiably-deferred.
> The three URLs and quotes MUST be re-retrieved at authoring — the handoff is
> not the source.

`test_no_rule_uncited` is the mechanical form of this MUST.

## Definition of Done

### Red — Failing tests written first

- [ ] All four test functions exist and **fail** against an empty/placeholder
  contract (no rules cited yet).

### Green — Implementation makes the tests pass

- [ ] `test_reusable_workflow_rule_cited_to_real_github_url` passes: real
  resolving URL + `confirmed` + evidence.
- [ ] `test_bot_token_rule_cited_and_probed` passes, including the meaning-check
  on the "new" qualifier.
- [ ] `test_branch_protection_rule_cited_and_deferred` passes with the
  canonical deferred-need id.
- [ ] `test_no_rule_uncited` passes — the UC-005 MUST holds.
- [ ] Tests import WP-007's shared claim-entry validator (no duplication).

### Blue — Refactor + polish

- [ ] The meaning-check assertion is explicit about *what* it guards (the
  "new workflow run" semantics) — a comment ties it to MUC-002 / A-3.
- [ ] URL-resolution assertions are authoring-time-hard, CI-soft (OAQ-2) —
  skip/xfail with a clear reason if the network is unavailable in CI, so a
  transient network failure does not red the build.
- [ ] No restating of the conformance checks WP-007 already covers — this WP
  asserts *grounding genuineness*, not schema shape.

## Sequence

- **Sequence ID:** WP-008
- **dependsOn:** WP-006 (the contract under assertion), WP-007 (shared
  validator + harness fixtures).
- **blocks:** — (terminal sink).
- **Parallelisable with:** — (everything precedes it).

## Estimated Token Cost

- **Input:** ~4k (the github-actions contract + the three live docs pages +
  WP-007's validator + ADR-005).
- **Output:** ~5k (four dogfood test functions).
- **Total:** ~9k.

## Notes

- **This is the load-bearing proof.** A green WP-008 is the evidence the
  Platform Contract discipline works end-to-end: the first real contract is
  grounded to real, resolving, probed sources — exactly the property the
  triggering reusable-workflow incident lacked.
- **Network discipline:** the URL-resolution assertions are the one place CI
  touches the network. Per OAQ-2 they are soft in CI (xfail-on-network-error
  with a logged reason), hard at authoring time. The build never reds on a
  transient GitHub redirect.
- The repeatable automated probe pipeline remains deferred
  (`scratch-github-actions-probe-repo`) — this WP asserts the *recorded*
  evidence from WP-006's manual one-shot run, not a live re-probe.

## Verification Plan (per-WP)

- **Adapter:** `methodology` — **Shape 1 (concrete).**
- **Artifact:** `tests/methodology/test_github_actions_dogfood.py::test_reusable_workflow_rule_cited_to_real_github_url`
  (the keystone dogfood assertion).
- **Observable:** the first Platform Contract's reusable-workflow rule is cited
  to a real `docs.github.com` URL that resolves and was probed `confirmed` — a
  founder can click the link and check.
- **Resilience:** URL-resolution is the only network touch; soft-in-CI
  (xfail-on-network-error) per OAQ-2 — a transient fault does not fail the build.
