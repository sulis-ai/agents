---
id: ADR-007
title: Ship seven adapters; new kinds require a methodology-change to add a row
status: accepted
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
date: 2026-06-01
resolves: SRD Open Question 7
---

# ADR-007 — Ship seven adapters; new kinds require a methodology-change to add a row

## Decision

`VERIFICATION_QUESTIONS.md` v1.0.0 ships with **exactly seven**
per-kind verification adapter rows:

| kind          | adapter (one-liner)                                                                                   |
|---|---|
| `methodology` | Structural assertions + integration test where a fresh design dispatch produces output with the new shape |
| `backend`     | Behavioural API test against a running service + persistence assertion + (where applicable) idempotency / replay check |
| `frontend`    | Component-rendering test with axe-core a11y + visual diff against the design-system tokens + interaction test |
| `async`       | Producer-publishes + consumer-receives integration test against a real broker (or test-container) + dead-letter / replay assertion |
| `infrastructure` | Apply-and-rollback integration test against ephemeral target + drift-check + cost / quota guardrail |
| `documentation` | Link-resolution check + readability score (FK ≤ 10 for founder-facing) + freshness-of-cited-sources check |
| `contract`    | Contract conformance test on both sides of the seam (provider + consumer) + schema-evolution compatibility check |

The seven kinds map 1:1 to the seven `kind:` values currently
recognised by the marketplace's change-primitive taxonomy.

When a new `kind:` value appears in the marketplace (e.g.,
`data-migration`, `experiment`, `vendor-swap`), the P-VER rubric
**fails** with an explicit instruction:

> *"This change has `kind: data-migration`, but no adapter row maps
> that kind in `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`.
> Add a new adapter row mapping `kind: data-migration` to a verification
> adapter, then re-run. Adding a new adapter row is itself a
> methodology change requiring its own design + rubric satisfaction."*

So the extension mechanism is **self-applying**: adding the eighth
adapter is itself a methodology change that must produce a Verification
Plan answering "how will we verify that the new adapter row is sound?"

## Context

SRD Open Question 7 surfaced the stability question. Two competing
pressures:

1. **Future-proofing pressure.** Anticipated upcoming kinds
   (`data-migration`, `experiment`) want immediate slots so they're
   not blocked when they appear.
2. **YAGNI pressure.** The seven kinds match the actual lexicon
   today. Adding speculative rows means the rubric carries adapter
   rows for kinds nobody has used, with no anchor case to inform the
   adapter's content.

The self-applying extension mechanism resolves the tension. The seven
rows ship covering current usage; adding row eight is cheap (a
methodology change touching `VERIFICATION_QUESTIONS.md` plus its own
Verification Plan section), and the bar for adding it is exactly the
same bar as for any other design-time methodology decision.

This pattern also has a useful side-effect: any team that wants a new
kind has to *articulate* the adapter — what would verification look
like for a `data-migration`? — which is itself useful design pressure.
Without the rubric, new kinds slip into the taxonomy without an
opinion on how to verify them.

## Alternatives considered

1. **Ship a larger initial set (e.g., 10-12 adapters) anticipating
   future kinds (rejected).** No anchor cases for `data-migration`,
   `experiment`, `vendor-swap` adapters today means the content of
   those rows would be speculative. Speculative methodology rarely
   survives contact with reality — the row would either be ignored
   or be wrong on first use. Adding the row when the kind actually
   appears is cheap and produces better adapter content.

2. **Allow agents to invent an adapter on first use (rejected).**
   Defeats the single-source-of-truth invariant. Agents would
   independently invent adapters, drift, and the rubric could not
   distinguish "this was authorised" from "this was guessed".

3. **A catch-all "unknown" adapter (rejected).** Makes the rubric
   silent on the verification approach for new kinds — exactly the
   failure mode this change exists to prevent. The whole point of
   the per-kind adapter is to *not* leave the answer to "how do we
   verify?" unspecified.

## Mechanical detail

The P-VER check on `kind` is:

```pseudocode
def check_kind_adapter_mapping(change_record, canonical):
    kind = change_record.kind
    adapter_table = canonical.parse_adapter_table()
    if kind not in adapter_table:
        return FAIL(
            f"kind: {kind} has no adapter row in {canonical.path}. "
            f"Add a new adapter row, then re-run. Adding a new adapter "
            f"row is itself a methodology change."
        )
    return PASS
```

## Consequences

**Positive.**
- Ship-ready coverage for the seven kinds currently in use.
- New kinds get explicit, anchor-case-grounded adapters at the
  moment they're needed.
- The methodology-change-to-extend pattern reuses existing flows
  (no new mechanism).

**Negative.**
- A team coining a new `kind:` for the first time hits a hard stop
  at the rubric. Mitigation: the failure message is precise and
  names the exact remediation path.

**Neutral.**
- Calibration data on adapter row sufficiency (whether the
  one-liners are precise enough to drive consistent verification
  strategies) feeds back through the 90-day standards-authorship
  window.
