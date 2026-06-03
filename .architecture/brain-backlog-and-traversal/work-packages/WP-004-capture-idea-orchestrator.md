---
id: WP-004
title: Create capture_idea orchestrator (quick + full, why-first gate)
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-004
dependsOn: [WP-001, WP-002, WP-003, WP-005]
blocks: [WP-006]
estimated_token_cost:
  input: 12k
  output: 4k
tdd_section: Form — dependency picture (_brain_capture.capture_idea); ADR-003, ADR-004, ADR-005
adrs: [ADR-003, ADR-004, ADR-005, ADR-002]
primitive: create
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_brain_capture.py::test_quick_capture_rejects_missing_why
---

## Context

The heart of the **Capture path** — `_brain_capture.capture_idea(...)`, the
orchestrator that roots an idea in an Opportunity, ensures the backing chain,
and emits a draft Requirement sourced from the real Opportunity id. Per
ADR-003 it is **one function, two depths** (`why_intensity` = `quick` |
`full`) so the why-first invariant lives in exactly one place. Per ADR-004
the `full` branch composes with the opportunity-analyst *through the store*
(by entity id), not via a function call. Per ADR-005 it calls the
`compose_*_from_idea` functions directly (imports the module; does not shell
out). EXPAND-Create: consumes ports the domain owns.

This WP is the gate that makes "no orphan requirements" real in code: it
refuses to emit a Requirement whose `source` doesn't resolve to an
Opportunity it just wrote (or read back).

## Contract

```python
# plugins/sulis/scripts/_brain_capture.py  (this WP adds capture_idea + the result type)

from typing import Literal

def capture_idea(
    *,
    repo_foundation: EntityRepository,
    repo_pd: EntityRepository,
    repo_org_slash_name: str,
    why_intensity: Literal["quick", "full"],
    why: str = "",                       # one-line why (quick path)
    what: str | None = None,             # requirement statement; None ⇒ Opportunity stands alone
    seed: str,                           # stable seed → idempotent ids (NFR-04)
    opportunity_id: str | None = None,   # full path: id the analyst already emitted (ADR-004)
    roadmap: bool = False,               # FR-05 — mark Roadmap at capture time
) -> dict:
    """Returns a result dict consumed by the CLI envelope (WP-006):
       {"opportunity_id": ..., "requirement_id": ... | None, "roadmap": bool,
        "chain": {"tenant_id":..., "product_id":...}, "bootstrapped": bool}
       OR raises CaptureError (translated to {"ok":false,"error":...} by the CLI).
    """
```

Behaviour (ADR-003 / ADR-004 / ADR-005):
- **quick + blank why → reject:** raise `CaptureError("an idea needs a why before it can be captured")`; emit nothing (FR-02 enforcement).
- **quick:** bootstrap chain (WP-003) → `compose_opportunity_from_idea(job_statement=flatten(why), for_product=chain.product_id, seed=..., state="hypothesis")` → `repo_pd.save` → `compose_requirement_from_idea(source=<opp id>, ...)` when `what` given → `repo_pd.save`.
- **full:** bootstrap chain → require `opportunity_id` → `find_by_id(opportunity_id)`; if it doesn't resolve or its `for_product` chain isn't whole → raise `CaptureError` (NFR-01; **no orphan requirement emitted**) → else emit the Requirement with `source=opportunity_id`.
- **`what is None`:** Opportunity stands alone as `hypothesis`; no Requirement (FR-03 tail clause); `requirement_id: None`.
- **roadmap=True:** after emits, call `roadmap_add([opp_id, *([req_id] if req_id else [])])` (WP-005) — idempotent set semantics.
- **Emit order is bottom-up + opportunity-before-requirement:** the Requirement is the last write and only fires after its `source` resolves (ADR-002 Armor / ADR-003 invariant).
- **Idempotent:** same `seed` ⇒ same opportunity/requirement ids ⇒ overwrite-in-place, no duplicate (NFR-04).

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_brain_capture.py::test_quick_capture_rejects_missing_why` — `why_intensity="quick"`, blank `why` → `CaptureError`; store unchanged (nothing emitted).
- [ ] `tests/unit/test_brain_capture.py::test_quick_capture_lands_opportunity_and_requirement` — why + what → an Opportunity (hypothesis) + a draft Requirement whose `source` == the opp id; chain whole.
- [ ] `tests/unit/test_brain_capture.py::test_quick_capture_what_none_opportunity_stands_alone` — what=None → Opportunity only, `requirement_id` None.
- [ ] `tests/unit/test_brain_capture.py::test_full_capture_reads_analyst_opportunity_by_id` — given a pre-emitted opportunity id, capture reads it back and sources the Requirement from it (ADR-004 store hand-off).
- [ ] `tests/unit/test_brain_capture.py::test_full_capture_dangling_opportunity_degrades` — `opportunity_id` that doesn't resolve → `CaptureError`, no Requirement emitted (NFR-01, no orphan).
- [ ] `tests/unit/test_brain_capture.py::test_capture_is_idempotent_on_seed` — capture twice with same seed → same ids, no duplicate instance files (NFR-04).
- [ ] `tests/unit/test_brain_capture.py::test_roadmap_flag_appends_members` — roadmap=True → opp + req ids appear in the roadmap sidecar (WP-005).

### Green — Implementation makes tests pass
- [ ] All Red tests pass against a temp `.brain/instances` + real vendored schemas (MEA-09).
- [ ] Calls `compose_opportunity_from_idea` / `compose_requirement_from_idea` directly (no shelling to the CLI, ADR-005).
- [ ] Adopts the existing `_brain_emit_helper` `_try_adapter`/`_safely` degradation discipline so a brain-unavailable store yields `CaptureError`, never an uncaught crash (NFR-01).
- [ ] Boring code: explicit `Literal` branch, no dynamic dispatch; the why-first gate is a literal `if`.

### Blue — Refactor complete
- [ ] The quick/full branches share the chain-bootstrap + requirement-emit tail; only the opportunity-acquisition differs — keep that the single point of divergence (ADR-003 "one function, two depths").
- [ ] No new behaviour in Blue.
- [ ] All tests green after refactor.

## Sequence
- **dependsOn:** WP-001 (opportunity compose), WP-002 (requirement compose), WP-003 (bootstrap), WP-005 (roadmap_add)
- **blocks:** WP-006 (CLI imports this)
- **Parallelisable with:** WP-007, WP-008 (traverse side)

## Estimated Token Cost
- **Input:** ~12k (this WP + the four dependency contracts + `_brain_emit_helper`)
- **Output:** ~4k (orchestrator + CaptureError + test file)
- **Total:** ~16k

## Notes
- `flatten(why)` mirrors `_opportunity_emission`'s single-line flatten — reuse it, don't reimplement.
- The `full` path does not spawn the analyst; it accepts an already-emitted `opportunity_id` (ADR-004). The CLI/skill is responsible for recommending the analyst out-of-band; the orchestrator only reads the id back.
