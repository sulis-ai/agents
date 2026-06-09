---
# Identity (WP-01)
id: WP-002
title: Author the pure-decision seam-close gate module `_seam_close_gate.py`
status: pending
change_id: seam-dod-gate
kind: methodology
source: feat
primitive: create
group: GENERATE

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: low

# Lifecycle (WP-07)
sequence_id: WP-002
dependsOn: [WP-001]
blocks: [WP-003, WP-004]

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 9k
  output: 7k
tdd_section: §Form (the one new module); §How the gate hooks (detection + resolution); §Verdict semantics
adrs: [ADR-001, ADR-004, ADR-005]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_seam_close_gate.py

rollback: |
  Delete plugins/sulis/scripts/_seam_close_gate.py.
  No other module imports it until WP-003 wires it; deleting it alone is
  inert. WP-001's tests revert to Red (import failure).
---

# Author the pure-decision seam-close gate module

## Context

TDD §Form — **the one new module**. `_seam_close_gate.py` is a pure decision
over fixture-able inputs: given a just-`done` WP id + the INDEX dependency
graph + the brain store, it (1) decides whether a seam closed, (2) resolves the
closing seam to its covering Scenarios through the requirement bridge
(ADR-004), (3) drives those Scenarios via the injected runner, and (4) folds
the per-Scenario verdicts through the **reused** `_acceptance_gate.gate_decision`
into `observed` / `blocked` / `not-closed`.

It owns **no I/O of its own** beyond reading via the existing query seams
(`_brain_query`, the `_wpxlib` INDEX parser) and invoking the injected
`run_scenario` callable. The dependency direction is inward/sideways only
(ADR-003 §Consequences): the hook (WP-003) calls *into* this module; this module
never imports `wpx-step12`, `wpx-train`, or the skills.

This WP makes WP-001's failing tests pass (Green). It implements exactly the
`evaluate(...)` signature and `SeamCloseResult` shape WP-001's tests pin down.

## Contract

### File created

```
plugins/sulis/scripts/_seam_close_gate.py   (CREATE — the only file)
```

### Reused (imported, not reimplemented)

| Symbol | From | Role |
|---|---|---|
| `gate_decision`, `GateDecision`, `format_gate_message` | `_acceptance_gate` | Fold Scenario verdicts → `pass`/`blocked` with `require_observed=not allow_deferred`. **Verbatim reuse** — no second copy of the observed-or-blocked rule. |
| `find_scenarios_verifying`, `find_scenarios_for_journey`, `find_passing_testresults_for_scenario` | `_brain_query` | Requirement→Scenario resolution + the once-fired "already driven" signal. No new traversal primitive. |
| `parse_index_md`, `WPRow`, `read_frontmatter`, `parse_frontmatter` | `_wpxlib` | Read the seam graph (kind / dependsOn / status) from INDEX.md; read the contract WP's `implements:` from its frontmatter. snake→camel `dependsOn` alias (#104) inherited. |
| `AcceptanceResult` | `_scenario_runner` | The per-Scenario verdict shape the runner returns / `gate_decision` consumes. |

### Public surface (the WP-001 contract — implement exactly)

```python
@dataclass
class SeamCloseResult:
    verdict: str           # "observed" | "blocked" | "not-closed"
    seam_title: str
    reason: str
    blocking: list
    deferred_needs: list
    drove_scenarios: list

def evaluate(just_done_wp, *, index_path, brain_base_dir, repo_root,
             allow_deferred=False, run_scenario=None) -> SeamCloseResult: ...
```

### Internal decision pipeline (the algorithm, per TDD)

1. **Detect.** Parse INDEX. Find the contract roots the `just_done_wp` is part
   of (walk `dependsOn` to `kind: contract` WPs; also treat the just-done WP as
   a seam root if it is itself `kind: composite` / carries `produces:
   integration-check`). For each candidate seam, the seam is **closed** iff
   either (1) an integration/`kind: composite` WP rooted on it is `done`, or
   (2) the contract WP + **all** WPs that `dependsOn` it are `done`. No closed
   seam → `not-closed` (silent). Malformed INDEX / missing row → `not-closed`
   with a "couldn't evaluate the seam at <wp>" reason (degrade-open on
   detection; never fabricate green).
2. **Resolve requirements (ADR-004 bridge).** First source: the contract WP's
   `implements: [dna:requirement:…]` frontmatter (read via `read_frontmatter`).
   Fallback when absent: the contract WP's `journey:` → `find_scenarios_for_journey`,
   intersect each Scenario's `verifies` with the seam's requirements.
   **(Open Question 1 resolution: fallback is sufficient; no backfill of legacy
   contract WPs — see Notes.)**
3. **Resolve Scenarios.** Union of `find_scenarios_verifying(req)` over the
   seam's requirements. **Empty set → short-circuit to `blocked`** with the
   ADR-005 no-coverage reason ("this seam has no end-to-end check — nothing
   drove the real data across it"), **before** calling `gate_decision`.
4. **Once-fired guard.** For each covering Scenario, if
   `find_passing_testresults_for_scenario` already returns a pass, treat the
   seam as already-driven and **do not** re-invoke `run_scenario` (Open
   Question 2 resolution). If every covering Scenario is already green →
   `observed` without re-driving.
5. **Drive + fold.** For each not-yet-green covering Scenario, call
   `run_scenario(scenario_id)` (default: invoke `sulis-verify-acceptance
   --scenario <id> --target local --repo-root <root> --json`, read `verdict`).
   Build `AcceptanceResult`s, fold through
   `gate_decision(results, require_observed=not allow_deferred)`.
   `decision.verdict == "pass"` → `observed`; else `blocked`.
6. **Founder-English.** `reason` built via `format_gate_message` (reused) for
   the driven case; bespoke distinct strings for the no-coverage and
   couldn't-evaluate cases. **Strip all `dna:` / `WP-` ids** from `reason`;
   name the seam by the contract WP **title**.

## Definition of Done

### Red — Failing tests written
- [ ] WP-001 already authored `test_seam_close_gate.py` (the Red is inherited). Confirm it is present and currently failing at import before starting.

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/scripts/_seam_close_gate.py` created implementing `evaluate` + `SeamCloseResult` per the contract above.
- [ ] All 6 AC tests pass: `test_seam_undriven_scenario_blocks`, `test_seam_equality_verdict_passes`, `test_seam_property_verdict_passes`, `test_seam_deferred_blocks`, `test_seam_no_covering_scenario_blocks`, `test_seam_allow_deferred_escape_records`.
- [ ] All 6 supporting tests pass: noop, both detection signals, fires-once, malformed-index, gate_decision-reuse parity.
- [ ] `gate_decision` is **imported and called**, not reimplemented (the parity test enforces this).
- [ ] `find_scenarios_verifying` / `find_scenarios_for_journey` / `find_passing_testresults_for_scenario` are the **only** brain-read primitives used (no new traversal).

### Blue — Refactor complete
- [ ] Module docstring states the observed-or-blocked discipline, the ADR-005 no-coverage-distinct-from-deferred rule, and the **Open Question 2 known degradation**: "under `--no-emit-evidence` the once-fired signal is absent, so a settled seam may re-drive — wasteful, never wrong; no bespoke marker is kept (the brain evidence is the single source)."
- [ ] No I/O beyond the read seams + the injected `run_scenario`; the function is pure over its inputs (the property WP-001's parity/fixture tests rely on).
- [ ] Founder-English helper that strips operator vocabulary is a single named function, reused for every `reason` path.
- [ ] Stdlib + the four reused modules only; Python 3.11-safe; no third-party imports.

## Sequence
- **dependsOn:** WP-001 (its failing tests are the spec this module satisfies)
- **blocks:** WP-003 (the hook that calls `evaluate`), WP-004 (skill docs describe this module's behaviour)
- **Parallelisable with:** WP-005, WP-006 once WP-001 has landed (disjoint files)

## Estimated Token Cost
- **Input:** ~9k (WP-001's tests, the four reused modules' signatures, the TDD detection + resolution sections, ADR-004/005)
- **Output:** ~7k (≈ 200–260 LOC pure module + docstring)
- **Total:** ~16k

## Notes
- **Open Question 1 (backfill `implements:` vs fallback) — resolved to fallback.** This module reads `implements:` when present and falls back to journey-filtered Scenario intersection otherwise (ADR-004). It does **not** require existing contract WPs to be backfilled — backfilling every prior decomposition's contract WPs is an unbounded cross-repo side-quest (EP-04 scope) out of this change's surface. The `implements:` field is the clean forward path WP-006's standard amendment makes `/sulis:plan-work` populate going forward; the fallback keeps legacy decompositions correct now.
- **Open Question 2 (once-only under `--no-emit-evidence`) — resolved to brain-evidence signal, no bespoke marker.** Step 4 uses `find_passing_testresults_for_scenario` (the same source `_verify_scenario_coverage` uses) as the already-driven marker. A separate per-seam marker would be a second source of truth competing with the brain evidence (boring-code: no parallel state). The `--no-emit-evidence` re-fire is logged in the docstring and asserted-around by `test_seam_close_fires_once` (which seeds evidence and asserts no re-drive).
- **Why pure (no subprocess in the module):** keeps the gate unit-testable over fixtures exactly as `_acceptance_gate` is. The subprocess invocation of `sulis-verify-acceptance` is the **default** `run_scenario`, injectable so tests stub it — the seam between decision and I/O.

## Verification Plan
- **Adapter:** `methodology` (pure-function pytest).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_seam_close_gate.py` (authored by WP-001; this WP turns it green).
- **What this WP's verification proves:** the gate's decision logic — detection (both signals), the requirement→Scenario bridge with fallback, observed-or-blocked folding via reused `gate_decision`, the ADR-005 no-coverage block, the once-fired guard, and degrade-open-on-detection — all behave per the 12 encoded cases. Grounded in those tests passing.
