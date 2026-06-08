---
id: WP-004
change_id: 01KT9HJMZC4731H0TAVW1E5QCD
title: Clinics-scheme spike — block → exercise-over-stubs → release
kind: backend
primitive: create
group: expand
status: pending
dependsOn: [WP-002]
blocks: []
estimated_token_cost: { input: "~9k", output: "~5k" }
verification:
  adapter: backend
  artifact: tests/integration/test_interaction_gate_clinics_spike.py::test_clinics_scheme_block_exercise_release
tdd_section: "TDD §3 Armor (stub-only), §4 Proof (End-to-end spike)"
---

# WP-004 — Clinics-scheme spike

## Context

TDD §4 (End-to-end). The spike is both the proof and this change's own
verification: author the real clinics-scheme interaction flow as a
`contract_type: interaction` card and demonstrate the full
block → exercise-over-stubs → release cycle against the live gate
(`wpx-index flip-status`). Depends on WP-002 (the enforcer must exist for the
block to fire). Exercises over **stub adapters only** — no live platform write
(TDD §3).

## Contract

Produce:

1. **The clinics-scheme interaction-contract card** — a WP file with
   `kind: contract`, `contract_type: interaction`, describing the multi-step
   clinics-scheme founder flow (the steps the user actually walks). Authored in
   a spike workspace under `.architecture/interaction-flow-gate/spike/` so it
   does not perturb a production INDEX. Its frontmatter starts with **no**
   exercise evidence (so the gate blocks).
2. **A stub harness for the clinics flow** under
   `.architecture/interaction-flow-gate/spike/stubs/` (or a test fixture dir),
   following the PATH-shim + canned-JSON precedent at
   `plugins/sulis/scripts/tests/fixtures/drift_check/gh-stubs/`: a `gh`-style
   shim (or the clinics equivalent) on `PATH` returning canned responses for
   each step of the flow, logging invocations.
3. **The spike test** `tests/integration/test_interaction_gate_clinics_spike.py`
   driving the live `wpx-index flip-status` against the card:
   - **block** — flip-to-done with no evidence is refused, founder-readable reason;
   - **exercise** — run the flow over the stub harness; record evidence into the
     card frontmatter (`exercised_at`, `exercised_by: agent-observed`,
     `exercised_attestation` pointing at the stub-run transcript/log);
   - **release** — flip-to-done now succeeds.

## Definition of Done

### Red
- [ ] Author the clinics-scheme card with empty evidence + seed a minimal INDEX
      in the spike workspace referencing it.
- [ ] Write `test_clinics_scheme_block_exercise_release` asserting the three
      phases in order against `wpx-index flip-status`.
- [ ] Run; confirm the **block** assertion passes (gate already wired by
      WP-002) but **release** fails because evidence isn't recorded yet — Red on
      the release leg.

### Green
- [ ] Build the stub harness (PATH-shim + canned JSON per the precedent;
      `STUB_MODE`-style switch if the flow has variant steps; invocation log).
- [ ] In the test's "exercise" phase, run the flow over the stub harness and
      write the evidence fields into the card frontmatter
      (`exercised_by: agent-observed`, `exercised_attestation` = the stub-run
      log path).
- [ ] Confirm: block refuses → exercise records evidence → release flips to done.
- [ ] `pytest tests/integration/test_interaction_gate_clinics_spike.py` green.

### Blue
- [ ] Add a second assertion path proving the `human-attested` branch also
      releases (set `exercised_by: human-attested` + a named attestation), so the
      spike demonstrates both evidence sources, not just agent-observed.
- [ ] Confirm no live third-party call occurred (assert against the stub
      invocation log; no real `gh`/platform binary on PATH during the run).
- [ ] README in the spike stub dir explaining the PATH-shim, mirroring the
      `gh-stubs/README.md` style; one source of stub logic.
