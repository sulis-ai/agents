# TDD — Interaction-flow done-gate (CH-01KT9H)

> change_id: 01KT9HJMZC4731H0TAVW1E5QCD · primitive: gate · Tier S
> Mirrors `#45 / UXD-14` (visual-contract done-gate). Phase 1: mechanism + spike.

## 1. What this change adds

A done-gate that blocks a work package carrying `contract_type: interaction`
from reaching `done` until its multi-step interaction flow has been exercised
end-to-end over **stub adapters** — evidenced either `agent-observed` or
`human-attested`. The gate is the **sibling** of the existing visual-contract
done-gate, built at the same two seams, with the same shape.

Phase 1 is **mechanism + spike only**. The MUST-flip that makes interaction
contracts mandatory for all founder-facing work is **Phase 2, out of scope**
(ADR-002).

## 2. Form — structural integrity

The structure is established by the visual-contract sibling and is **reused
verbatim in shape**. No new architecture is introduced; the interaction gate
slots into the existing two-seam design:

| Seam | Visual sibling (exists) | Interaction (this change) |
|---|---|---|
| **Recognition predicate** (`_wpxlib.py`) | `is_visual_contract_wp(fm)` — `kind: contract` + `contract_type: visual` | **`is_interaction_contract_wp(fm)`** — `kind: contract` + `contract_type: interaction` |
| **Runtime done-gate predicate** (`_wpxlib.py`) | `visual_contract_signed_off(fm)` → `None`/error | **`interaction_flow_exercised(fm)`** → `None`/error |
| **Enforcer at flip-to-done** (`wpx-index`) | `_enforce_visual_contract_signoff_on_done(args)` called from `cmd_flip_status` | **`_enforce_interaction_flow_on_done(args)`** called from `cmd_flip_status` |

The enforcer follows the exact control flow of its sibling
(`wpx-index` ~L380–401): no-op unless `--to done`; resolve the WP file;
no-op unless `is_interaction_contract_wp(fm)`; else run the predicate and
`emit_error` on a non-`None` result. `cmd_flip_status` calls **both** enforcers
at the top, so a WP that is somehow both kinds is gated by both; an ordinary WP
is untouched by either (regression-safety).

> Form doctrine (the `flip-status` chokepoint as the done-oracle, ports/adapters
> for stubs) is documented by the visual-contract gate at
> `plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md` WP-08.5 and is
> not restated here.

### Evidence-frontmatter shape (the one genuinely-new contract — ADR-001)

A `contract_type: interaction` WP records:

```yaml
kind: contract
contract_type: interaction
exercised_at: 2026-06-04T15:40:00Z        # ISO-8601, the WHEN
exercised_by: agent-observed              # agent-observed | human-attested
exercised_attestation: "stub run transcript at contracts/interaction/clinics-scheme.run.txt"
```

`interaction_flow_exercised(fm)` returns `None` (pass) iff all three of
`exercised_at` (non-empty), `exercised_by` (∈ {`agent-observed`,
`human-attested`}, case-insensitive), `exercised_attestation` (non-empty) are
present; otherwise a founder-readable error naming the missing field and the
gate, in the visual gate's message style. The gate **trusts the record and
does not re-run the flow** (ADR-003).

## 3. Armor — operational hardening

Not applicable to this change. The gate is a local, pure frontmatter check at a
subprocess CLI chokepoint — no external calls, no network, no secrets, no
observability surface. The single relevant operational constraint is the
**stub-only** rule: the spike exercises the clinics flow against the PATH-shim +
canned-JSON stub precedent (`scripts/tests/fixtures/drift_check/gh-stubs/`), so
no live third-party write/deploy occurs and no Platform Contract hard-gate is
triggered.

## 4. Proof — verification protocol

Every behaviour lands test-first (EP-02), characterising **both** the block
path and the release path, symmetric with the visual gate's tests.

### Unit — `interaction_flow_exercised()` + `is_interaction_contract_wp()`
New file `tests/unit/test_interaction_flow_gate.py`, mirroring
`test_visual_contract_gate.py`:

- `is_interaction_contract_wp` true for `{kind: contract, contract_type: interaction}`; false for visual contract, false for `kind: frontend`/`backend`.
- `interaction_flow_exercised`: **false** with no evidence; **false** with empty `exercised_at`; **false** with unknown/blank `exercised_by`; **false** with missing `exercised_attestation`; **true** with `agent-observed` + who/when + attestation; **true** with `human-attested` + who/when + attestation; case-insensitive on `exercised_by`.

### Enforcement — `_enforce_interaction_flow_on_done`
Added to `tests/integration/test_wpx_index.py`, mirroring the visual cases
(~L301–357):

- a `contract_type: interaction` WP with no evidence is **blocked** at `flip-status --to done` (error mentions the flow not being exercised);
- the same WP with recorded evidence **flips to done**;
- a non-interaction WP (`WP-002`, no WP file) flips to done **unaffected** — the regression-safety oracle.

### End-to-end — the clinics-scheme spike
A `contract_type: interaction` WP authoring the real clinics-scheme flow, run
over stub adapters, demonstrating block → exercise-over-stubs → release. This
is the change verifying its own thesis.

## 5. Decomposition-rule amendment (documentation, SHOULD strength)

WP-08.5 (`WORK_PACKAGE_STANDARD.md`) and the contract-first doctrine
(`CONTRACT_FIRST_STANDARD.md`) gain a defined home for `contract_type:
interaction`: a founder-facing capability spanning a multi-step flow **SHOULD**
emit a `kind: contract` / `contract_type: interaction` child whose done-gate is
the exercised-flow predicate, sibling to the visual contract. Phase 1 states
this at **SHOULD**; the MUST flip is Phase 2 (ADR-002).

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

This change's `kind:` is **backend** (Python predicate + CLI enforcer). Per the
canonical kind→adapter table, the verification artifacts are **pytest
nodeids**; the spike additionally uses a **methodology fixture** (the stub
adapter directory).

1. **User-observable behaviour verified.** A founder-facing capability cannot be
   marked `done` until its flow is exercised over stubs; an un-exercised
   interaction WP is blocked with a clear reason; once exercised, it releases.
2. **Verification environment(s).** Local + CI (`pytest` under
   `plugins/sulis/scripts/tests/`). No staging; no live integration.
3. **Bootstrap-from-zero.** A fresh clone at the merge SHA runs
   `pytest tests/unit/test_interaction_flow_gate.py tests/integration/test_wpx_index.py`
   green with no external dependency (pure frontmatter checks; stubs are
   in-repo fixtures).
4. **Per-integration verification strategy.** No external integrations. The one
   "integration" is the spike's stub adapter (in-memory PATH-shim + canned
   JSON) — strategy: **in-repo stub fixture**, classification `existing`
   (precedent at `scripts/tests/fixtures/drift_check/gh-stubs/`).
5. **Per-kind verification adapter.** `backend` → pytest nodeids.
   - Predicate: `tests/unit/test_interaction_flow_gate.py` (multiple nodeids).
   - Enforcement: `tests/integration/test_wpx_index.py::test_interaction_contract_wp_cannot_go_done_unexercised` and `::test_interaction_contract_wp_goes_done_when_exercised` and `::test_non_interaction_wp_done_flip_is_unaffected`.
   - Spike: the clinics-scheme card's own block→exercise→release walk over the stub fixture.
6. **Infrastructure needs (deferred).** None. The stub harness pattern already
   exists in-repo; the spike reuses it.

### Per-WP verification shape (for `/sulis:plan-work`)

| WP | Shape | Artifact |
|---|---|---|
| WP-001 (predicate) | concrete | `tests/unit/test_interaction_flow_gate.py::*` |
| WP-002 (enforcement) | concrete | `tests/integration/test_wpx_index.py::test_interaction_contract_wp_*` |
| WP-003 (docs amendment) | concrete | `tests/unit/` standard-shape assertion (interaction contract documented) |
| WP-004 (clinics spike) | concrete | the spike card's stub-run + flip-status walk |

## Sizing Report

- **Tier:** S (computed sFPC 4, ASR 4; confirmed). See `SIZING.md`.
- **TDD length:** within the tier-S target band (mirror-and-reference, not re-derive).
- **ADRs produced:** 3 (evidence shape; Phase-1 scope boundary; attestation-not-execution). All three are genuinely-new decisions with no External ADR Registry collision (no `.context/` index present).
- **Sections referenced rather than restated:** Form doctrine → WP-08.5; stub precedent → `gh-stubs/`; visual-gate control flow → `wpx-index` L380.
- **Circuit breakers triggered:** none.
