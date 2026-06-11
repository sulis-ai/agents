# ADR-001 — Completion is owned by a recorded verdict, enforced in the ship mechanism

> **Status:** Accepted
> **Change:** gate-done-on-verdict (#118)
> **Date:** 2026-06-11

## Context

Work was repeatedly reported "completed" when it was not. A converged
critical-thinking analysis located the root cause as **self-asserted
artifact-completion**: "done" was checked against *artifact-written*, graded by
the *same agent that did the work*, against a bar that lived as *prose*. The
deepest hole is the conjunction of (a) outcome-not-verified and (b)
verifier-is-the-builder.

Grounded recon then pinned the proximate defect to an exact seam: the
observed-or-blocked Definition-of-Done verdict — every touched Requirement has
a passing `TestResult` (`_verify_requirements` / `gate_decision`) — was
*enforced only as prose* in `change/SKILL.md` (gates 4.8 / 4.9). The
`sulis-change` ship **script ran it zero times**. So a change could be marked
*shipped* with no observed verdict, by an agent skipping the prose step or a
hand-merge bypassing the skill. The observed-or-blocked *logic* was correct and
already existed (#83, #95, #98); only its *invocation at ship* was skippable.

## Decision

**Completion is owned by the recorded verdict, and the verdict is enforced in
the ship mechanism — not asserted by the builder and not requested by prose.**

Concretely: `sulis-change mark-shipped` runs the observed-verdict check as a
**hard precondition** (sibling of the #111 merge guard). It refuses to flip a
change to `shipped` unless every touched SRD's DoD verdict is `pass`. The only
escape is a conscious, logged `--force` (recorded as `dod_override` on the
change record), identical in shape to the #111 ship-integrity override.

The verdict is read from **deposited brain evidence** (passing `TestResult`s),
not a self-stampable frontmatter field — chosen deliberately over a frontmatter
attestation because a stampable field would reintroduce the self-assertion that
is the root cause. The verifier (`sulis-verify-acceptance` / `sulis-attest-scenario`)
deposits the evidence; the builder cannot.

## Consequences

- The gate is the mandate; agent-body prose only points at it. An agent that
  skips the SKILL's gate-4.9 prose, or a hand-merge that bypasses the skill,
  still cannot mark a change shipped with unverified requirements.
- **Scope (Phase 1):** the gate keys on touched SRDs (`verify_requirements`),
  which is self-contained (no journey-id resolution). A founder-facing change
  with scenarios but no SRD is **not yet** covered by this hard gate at ship —
  captured as the follow-on (the scenario-coverage route + the per-WP
  done-transition sibling). The dangerous, substantive (SRD-bearing) path is
  closed first.
- **Degrade-open on inability-to-evaluate, never on inability-to-verify.** No
  touched SRD, or a git/brain error, returns "ok" (out of scope / can't
  evaluate). It never fabricates a `pass` it did not verify.
- The residual honesty risk is unchanged and lives elsewhere: "observed green"
  is only as honest as the verifier's stub/fake detection (`/sulis:prove` +
  the #98 isolation-ladder), not in this gate's structure.

## Alternatives considered

- **Per-WP `flip_status` gate (third sibling of `visual_contract_signed_off` /
  `interaction_flow_exercised`).** Rejected for Phase 1: per-WP `done` is
  cosmetic-until-ship, the WP→scenario mapping for an arbitrary WP is
  ill-defined, and it is surgery on the most central lifecycle function. The
  ship-level gate closes the dangerous boundary with far lower blast radius.
- **Frontmatter attestation** (a stamped `acceptance_observed_at` field).
  Rejected: self-stampable by the builder → relocates the lie rather than
  killing it.
