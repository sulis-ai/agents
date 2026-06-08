---
founder_facing: false
---

# Spec — Interaction-flow done-gate

**Change:** CH-01KT9H · gate

## Intent

Stop a founder-facing capability from being marked **done** until its
multi-step interaction flow has actually been run end-to-end over **stub
adapters** — either watched by the agent (agent-observed) or signed off by a
person (human-attested). This closes the "green-but-broken" gap: today a
capability's pieces can pass their own checks while the round-trip the user
actually walks was never exercised.

The mechanism mirrors the **existing visual-contract done-gate** (which blocks
`done` on a `contract_type: visual` work package until a person signs off the
mockup). We add a sibling: `contract_type: interaction`, blocked on
`done` until an `interaction_flow_exercised` predicate is satisfied.

## Scope (this change — Phase 1: mechanism + spike)

- **New contract type `interaction`.** Recognised in work-package frontmatter
  alongside `visual`. A WP carrying `contract_type: interaction` is subject to
  the new gate.
- **Done-gate extension.** Extend the runtime done-gate (`wpx-index`
  `cmd_flip_status` → a new `_enforce_interaction_flow_on_done`, mirroring
  `_enforce_visual_contract_signoff_on_done`) plus its `_wpxlib.py` predicate
  (`interaction_flow_exercised()`, mirroring `visual_contract_signed_off()`).
  The predicate passes when the WP records evidence that the flow was
  exercised end-to-end over stubs, attributed to one of two sources:
  - **agent-observed** — the agent ran the flow over stub adapters and
    recorded the observation, or
  - **human-attested** — a person ran it and attested, recorded with who +
    when (the same shape as the visual gate's `signed_off_at` / `provenance`).
- **Decomposition-rule amendment (documentation).** Amend WP-08.5 in
  `WORK_PACKAGE_STANDARD.md` (and the contract-first doctrine in
  `CONTRACT_FIRST_STANDARD.md`) so the `interaction` contract type has a
  defined home in cross-kind decomposition: a founder-facing capability
  spanning a flow **SHOULD** emit a `kind: contract` / `contract_type:
  interaction` child whose done-gate is the exercised-flow predicate. (Phase 1
  states the policy as SHOULD; the MUST flip is Phase 2 — see Non-goals.)
- **Spike on the live clinics-scheme card.** Prove the gate end-to-end on the
  real clinics-scheme interaction flow: author it as a `contract_type:
  interaction` WP, confirm the gate **blocks** `done` while un-exercised, run
  the flow over stub adapters, confirm the gate **releases** `done` once the
  evidence is recorded. The spike is both the proof and this change's own
  verification.

## Non-goals (captured for Phase 2 / explicitly out)

- **Mandatory enforcement across all founder-facing work.** The end-state
  decision is *mandatory* — every founder-facing capability must carry an
  interaction contract. Phase 1 builds and proves the mechanism; the
  decomposition-rule **MUST** flip (founder-facing ⟹ interaction contract
  required, blocking decomposition validation) is **Phase 2**, so in-flight
  founder-facing WPs aren't all blocked the day this lands. Captured to the
  backlog, not dropped.
- **Exercising flows over real (non-stub) integrations.** The gate is
  satisfied by a stub-adapter run by design. Real-integration conformance is
  the existing CF-07 integration concern, unchanged here.
- **Net-new UI / founder-visible surface.** This is internal methodology and
  tooling; it adds no screen, page, or route.
- **Replacing the visual-contract gate.** The two gates are siblings and
  coexist; a user-facing seam can pair a visual contract and an interaction
  contract.

## Acceptance

- A WP with `contract_type: interaction` and **no** recorded exercised-flow
  evidence **cannot** flip to `done` — the gate blocks it with a clear,
  founder-readable reason (mirroring the visual gate's block message).
- The same WP, once the flow is exercised end-to-end over stub adapters and
  the evidence is recorded (agent-observed **or** human-attested with who +
  when), **can** flip to `done`.
- A WP **without** `contract_type: interaction` is unaffected — no new
  friction on existing work (regression-safe).
- The clinics-scheme card demonstrates the full block→exercise→release cycle
  on a real flow.
- The decomposition standards (WP-08.5, contract-first doctrine) document
  where the `interaction` contract type sits, at SHOULD strength.

## Constraints

- **Mirror the visual-contract gate, don't reinvent it.** Same enforcement
  shape (write-time recognition + runtime block at flip), same evidence
  pattern (timestamp + provenance/attestation), same founder-readable block
  message style. Reuse the existing helpers' structure in `_wpxlib.py`.
- **Exercise over stubs only — no live platform writes.** The clinics-scheme
  spike runs against stub adapters (the existing PATH-shim + canned-JSON
  pattern under `scripts/tests/fixtures/.../gh-stubs/` is the precedent). No
  Platform Contract hard-gate is triggered, because the change makes no
  write/deploy touch to a third-party platform.
- **Regression-safe.** WPs not declaring `contract_type: interaction` must
  behave exactly as before. The gate is additive.
- **Test-first (EP-02).** The gate predicate and the runtime enforcement each
  land behind a failing test first, characterising both the block and the
  release path.

## Verification Plan

- **How "done" is decided here.** The blocking gate is the `wpx-index`
  `flip-status` enforcement itself — the same code path the methodology uses
  in production. The spike on the clinics-scheme card exercises that real
  gate, so the change is verified against the gate that actually blocks, not
  an advisory check.
- **Unit level.** Tests for `interaction_flow_exercised()`: returns false with
  no evidence; true with agent-observed evidence; true with human-attested
  evidence (who + when present); false with malformed/partial evidence.
- **Enforcement level.** Tests for `_enforce_interaction_flow_on_done`: a
  `contract_type: interaction` WP is blocked at flip-to-done without evidence;
  released with evidence; a non-interaction WP flips unaffected.
- **End-to-end (the spike).** The clinics-scheme card walks
  block → exercise-over-stubs → release on the real interaction flow. This is
  the change demonstrating its own thesis: nothing is "done" until its flow is
  exercised — including this gate.
- **Adapter:** stub adapters (PATH-shim + canned-JSON precedent); no live
  third-party calls.
