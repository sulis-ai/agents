---
id: WP-001
change_id: 01KT9HJMZC4731H0TAVW1E5QCD
title: Interaction-flow gate predicate + recognition (_wpxlib.py)
kind: backend
primitive: create
group: expand
status: pending
dependsOn: []
blocks: [WP-002, WP-004]
estimated_token_cost: { input: "~6k", output: "~3k" }
verification:
  adapter: backend
  artifact: tests/unit/test_interaction_flow_gate.py
tdd_section: "TDD §2 Form (recognition predicate + runtime done-gate predicate), §4 Proof (Unit)"
---

# WP-001 — Interaction-flow gate predicate + recognition

## Context

TDD §2 (Form). Add the two pure `_wpxlib.py` functions that the runtime
done-gate (WP-002) will call. Direct sibling of `is_visual_contract_wp`
(`_wpxlib.py` ~L463) and `visual_contract_signed_off` (~L472). Pure functions
on a frontmatter dict — no I/O, no harness.

## Contract

Add to `plugins/sulis/scripts/_wpxlib.py`, placed immediately after
`visual_contract_signed_off`:

```python
def is_interaction_contract_wp(fm: dict) -> bool:
    """True if a WP is the interaction-contract WP
    (kind: contract + contract_type: interaction). Sibling of
    is_visual_contract_wp."""

def interaction_flow_exercised(fm: dict) -> str | None:
    """None if the interaction flow's exercise evidence is present and
    well-formed, else a founder-readable error. Mirrors
    visual_contract_signed_off (the runtime done-gate predicate)."""
```

Evidence rule (ADR-001) — `interaction_flow_exercised` returns `None` iff:
1. `exercised_at` is a non-empty string,
2. `exercised_by` ∈ {`agent-observed`, `human-attested`} (case-insensitive),
3. `exercised_attestation` is non-empty.

Each failure returns a distinct, founder-readable message naming the missing
field and the gate (style: the visual gate's messages, e.g. "interaction flow
not exercised — `exercised_at` is empty …"). `exercised_by` with an unknown
token returns a message naming the two valid sources.

## Definition of Done

### Red
- [ ] New file `tests/unit/test_interaction_flow_gate.py` mirroring
      `test_visual_contract_gate.py`, importing the two new symbols. Tests:
  - [ ] `is_interaction_contract_wp` true for `{kind: contract, contract_type: interaction}`.
  - [ ] `is_interaction_contract_wp` false for `{kind: contract, contract_type: visual}` and for `{kind: frontend}`.
  - [ ] `interaction_flow_exercised` rejects: no evidence; empty `exercised_at`; blank `exercised_by`; unknown `exercised_by` token; missing `exercised_attestation`.
  - [ ] `interaction_flow_exercised` passes: `agent-observed` + who/when + attestation.
  - [ ] `interaction_flow_exercised` passes: `human-attested` + who/when + attestation.
  - [ ] `exercised_by` is case-insensitive (`Agent-Observed` passes).
- [ ] Run the new test file; confirm import-error / assertion failures (Red).

### Green
- [ ] Implement `is_interaction_contract_wp` and `interaction_flow_exercised`
      exactly per the contract above. Boring, explicit: read each field with
      `str(fm.get(...) or "").strip()`, compare lowercased tokens against a
      literal frozenset, return early on each failure.
- [ ] `pytest tests/unit/test_interaction_flow_gate.py` green.
- [ ] `pytest tests/unit/test_visual_contract_gate.py` still green (no shared-symbol regression).

### Blue
- [ ] Refactor any literal duplicated between the two source functions only if
      a genuine shared primitive emerges (e.g. a `_controlled_token` helper) —
      do NOT force-extract; the two gates have different token sets and
      different messages. Document any deliberate non-extraction inline.
- [ ] Docstrings cross-reference the visual sibling and ADR-001.
