---
id: WP-002
change_id: 01KT9HJMZC4731H0TAVW1E5QCD
title: Enforce interaction gate at flip-to-done (wpx-index)
kind: backend
primitive: extend
group: reinforce
status: pending
dependsOn: [WP-001]
blocks: [WP-004]
estimated_token_cost: { input: "~7k", output: "~3k" }
verification:
  adapter: backend
  artifact: tests/integration/test_wpx_index.py::test_interaction_contract_wp_cannot_go_done_unexercised
tdd_section: "TDD §2 Form (enforcer at flip-to-done), §4 Proof (Enforcement)"
characterisation_test: "tests/integration/test_wpx_index.py::test_non_interaction_wp_done_flip_is_unaffected (regression oracle — ordinary WP flips unaffected)"
---

# WP-002 — Enforce interaction gate at flip-to-done

## Context

TDD §2 (Form). Wire the WP-001 predicate into the runtime done-gate at the
`flip-status` chokepoint. Direct sibling of
`_enforce_visual_contract_signoff_on_done` (`wpx-index` ~L380) and its call
site in `cmd_flip_status` (~L404). REINFORCE/extend: adds a second enforcer to
an existing chokepoint; the visual enforcer is untouched.

## Contract

In `plugins/sulis/scripts/wpx-index`:

```python
def _enforce_interaction_flow_on_done(args: argparse.Namespace) -> None:
    """Runtime gate — an interaction-contract WP cannot flip to `done`
    until its flow's exercise evidence is recorded. No-op for any other
    WP / status. Sibling of _enforce_visual_contract_signoff_on_done."""
    if args.to != "done":
        return
    paths = paths_from_args(args)
    try:
        wp_path = paths.wp_file(args.wp)
    except (FileNotFoundError, ValueError):
        return
    fm = read_frontmatter(wp_path)
    if not is_interaction_contract_wp(fm):
        return
    err = interaction_flow_exercised(fm)
    if err is not None:
        emit_error(f"{args.wp}: {err}")
```

Call it from `cmd_flip_status`, immediately after the existing visual call:

```python
def cmd_flip_status(args: argparse.Namespace) -> None:
    _enforce_visual_contract_signoff_on_done(args)
    _enforce_interaction_flow_on_done(args)
    ...
```

Add `is_interaction_contract_wp` and `interaction_flow_exercised` to the
`_wpxlib` import block at the top of `wpx-index` (~L31–41).

## Definition of Done

### Red
- [ ] In `tests/integration/test_wpx_index.py`, add a section mirroring the
      visual cases (~L301–357), using the existing `_write_wp` / `seed_index`
      / `run_tool` helpers:
  - [ ] `test_interaction_contract_wp_cannot_go_done_unexercised` — a
        `kind: contract` / `contract_type: interaction` WP with empty
        `exercised_at` is **refused** at `flip-status --to done`; error mentions
        the flow not being exercised.
  - [ ] `test_interaction_contract_wp_goes_done_when_exercised` — same WP with
        `exercised_at` + `exercised_by: agent-observed` + `exercised_attestation`
        **flips to done**.
  - [ ] `test_non_interaction_wp_done_flip_is_unaffected` — `WP-002` (no WP file)
        flips to done untouched (regression oracle).
- [ ] Run; confirm the new cases fail (enforcer not yet wired) — Red.

### Green
- [ ] Add the import line and implement `_enforce_interaction_flow_on_done`
      verbatim per the contract; add the call in `cmd_flip_status`.
- [ ] `pytest tests/integration/test_wpx_index.py` green (new + existing visual cases).
- [ ] `pytest tests/unit/test_interaction_flow_gate.py` still green.

### Blue
- [ ] Confirm the two enforcers are independent and order-insensitive (a WP is
      gated by whichever predicate matches its `contract_type`); leave a
      comment at the call site noting both gates run and why an ordinary WP is
      a double no-op (regression-safety).
- [ ] No duplication introduced between the two enforcer bodies beyond the
      unavoidable structural mirror; if the bodies are byte-identical except for
      predicate names, that is acceptable and intentional (legibility over a
      premature higher-order extraction) — note it.
