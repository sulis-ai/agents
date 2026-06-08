---
wp: WP-006
change_id: 01KTHP2NYQ1A3WHPJD75VP31NT
title: Cross-language grammar conformance + live likely→exact round-trip
kind: integration
primitive: reinforce-test
group: reinforce
status: ready
dependsOn: [WP-004, WP-005]
estimated_token_cost: { input: ~14k, output: ~5k }
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_assisted_grammar_conformance.py
---

# WP-006 — Cross-language grammar conformance + live round-trip

## Context

TDD §2 (cross-language seam) / §4 / §5 (component 6). Two proofs that CI alone
cannot give:
1. **Grammar conformance** — the TS relay emits the assisted `SULIS_ORIGIN` string;
   the Python hook parses it. A CI test must lock that the TS-emitted shape is exactly
   what #216's `parse_origin_env` accepts, so the two languages cannot drift.
2. **Live round-trip** (the green-but-broken guard) — CI stubs the `claude` child, so
   likely→exact end-to-end is only provable on the founder's machine with a real child.

## Contract

- **Grammar conformance test** (`test_assisted_grammar_conformance.py`): take the
  canonical assisted string the TS helper produces (mirror the exact format in the
  test, sourced from WP-003's output shape) and assert `parse_origin_env` returns
  `{kind:'assisted', conversation, turn}` with the expected fields — and that a
  malformed/control-char variant returns `None` (#216 boundary guard intact).
- **Live round-trip** (founder machine, observed evidence, NOT a CI gate):
  - One real cockpit-chat message that results in a commit → assert
    `git log -1 --format='%(trailers:key=Sulis-Origin)'` shows
    `assisted; conversation=…; turn=…`, and the cockpit origin view reports the file
    as **exact (recorded)**, not likely.
  - One real executor run that commits → assert the trailer shows
    `autonomous; run=…`, and the cockpit shows **exact**.
  - Two different chat conversations → two different conversation ids.
  - Degradation: force a stamp failure (e.g. unwritable hook path) → the commit still
    lands and origin falls back to inferred (no crash, no lost commit).

## Definition of Done

### Red
- [ ] `test_assisted_grammar_conformance.py` fails until it asserts the round-trip of
      the TS-emitted assisted string through `parse_origin_env` (and the malformed →
      None case).

### Green
- [ ] Grammar conformance test green in CI.
- [ ] Live round-trip OBSERVED on the founder machine; capture evidence:
      - `git log` trailer output for one assisted + one autonomous commit,
      - the cockpit origin view showing exact for each,
      - the two-conversation distinct-id observation,
      - the forced-degradation observation (commit lands, origin = inferred).
      Record evidence under the change's acceptance evidence (per wpx-step12 wrap).

### Blue
- [ ] Confirm CI is green with the wiring covered (WP-001..005) AND the live
      round-trip evidence is attached — both halves of the SPEC acceptance.
- [ ] Note in evidence that the interactive terminal-spawn ASSISTED stamping is a
      documented non-goal (not observed here) per the SPEC boundary.
