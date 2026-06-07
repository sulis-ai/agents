# ADR-003 — The gate trusts recorded evidence; it does not re-run the stub flow

> Status: accepted · change_id: 01KT9HJMZC4731H0TAVW1E5QCD · Tier S

## Context

The gate predicate `interaction_flow_exercised(fm)` reads frontmatter and
decides pass/block. There are two possible enforcement philosophies:

1. **Attestation gate** — the predicate trusts the recorded evidence
   (timestamp + source + attestation) and does not itself re-execute the flow.
   This is exactly how `visual_contract_signed_off` works: it checks that
   `signed_off_at` + `provenance` are present and correct; it does not
   re-render the mockup.
2. **Executing gate** — the predicate (or the enforcer) re-runs the
   interaction flow over stub adapters at flip-to-done and passes only on a
   live green run.

## Decision

**Attestation gate.** The runtime predicate trusts the recorded evidence and
does not re-execute the flow. The *act of exercising the flow over stubs* is a
step the author (agent or human) performs and records; the gate verifies the
record, not the run.

The stub adapters (PATH-shim + canned-JSON, per the
`scripts/tests/fixtures/drift_check/gh-stubs/` precedent) are the harness the
**spike WP** uses to exercise the clinics flow and produce the
`exercised_at` / `exercised_by` / `exercised_attestation` evidence. They are
not invoked by the gate.

## Rationale

- **Mirror, don't reinvent.** The visual gate is an attestation gate; making
  the interaction gate an executing gate would diverge from the sibling the
  spec tells us to mirror.
- **Separation of concerns.** The gate's job is "is the evidence present and
  well-formed?" — a pure, fast, deterministic frontmatter check at the
  `flip-status` chokepoint. Re-running a multi-step flow inside the flip-status
  command would couple a CLI status mutation to flow execution, slow every
  flip, and require the gate to know how to drive arbitrary flows.
- **`agent-observed` already means a real run happened.** The evidence source
  encodes that the flow *was* run over stubs; trusting it is consistent with
  how every other Sulis done-oracle treats recorded state.
- **Falsifiability lives in the attestation, not in re-execution.** ADR-001
  requires `exercised_attestation` to point at the run (a transcript path for
  agent-observed; a named human for human-attested), so the record is
  checkable without the gate re-running anything.

## Alternatives considered

- **Executing gate.** Rejected for the reasons above: diverges from the
  visual sibling, couples status-flip to flow execution, and has no precedent
  in the codebase's done-oracles.

## Consequences

- The gate is pure and unit-testable on frontmatter dicts alone (no harness
  needed for the predicate's tests) — symmetric with the visual gate's tests.
- The **spike WP** owns the stub harness and the act of exercising the flow;
  the **gate WPs** own only the recorded-evidence check. This keeps the
  dependency order clean: gate predicate + enforcement land first, the spike
  (which produces evidence the gate then reads) lands after.
