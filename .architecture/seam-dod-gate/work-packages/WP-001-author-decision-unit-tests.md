---
# Identity (WP-01)
id: WP-001
title: Author the failing decision-unit tests for the seam-close gate (6 acceptance criteria + correctness cases)
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
sequence_id: WP-001
dependsOn: []
blocks: [WP-002]
foundation: true

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 8k
  output: 6k
tdd_section: §Proof (decision-unit layer); §Test surface File 1
adrs: [ADR-001, ADR-004, ADR-005]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_seam_close_gate.py

rollback: |
  Delete plugins/sulis/scripts/tests/unit/test_seam_close_gate.py.
  No production code touched; pure test-authoring WP.
---

# Author the failing decision-unit tests for the seam-close gate

## Context

TDD §Proof (Verification protocol), **Test surface — File 1**. This is the
**test-first (MUST)** WP for the change: it authors the six SPEC acceptance
criteria — plus the named correctness cases — as failing pure-function tests
over `_seam_close_gate.evaluate(...)` **before** the gate module exists
(WP-002). The tests fail at Red because the module they import is not yet
written; WP-002 turns them green.

This mirrors the established pattern at
`plugins/sulis/scripts/tests/unit/test_ship_acceptance_gate_wiring.py` and the
decision-unit style of `test_acceptance_gate.py`. All stdlib + pytest,
Python 3.11-safe, no subprocess (the runner is stubbed/monkeypatched so the
decision logic is exercised in isolation).

The tests define the gate's **contract by example**: each test fixes one input
shape (a fixture INDEX graph + a fixture brain store or monkeypatched
`_brain_query` + a stubbed runner verdict) and asserts the resulting verdict
(`observed`/`blocked`/`not-closed`) and the founder-English message. WP-002
implements the module to satisfy exactly these assertions — the tests are the
spec it codes against.

## Contract

This WP's contract is the **public shape of `_seam_close_gate.evaluate(...)`**
that the tests pin down. WP-002 MUST satisfy this signature:

### Module under test (created by WP-002; imported by these tests)

```
plugins/sulis/scripts/_seam_close_gate.py
```

### Public function the tests call

```python
def evaluate(
    just_done_wp: str,                 # WP id that just flipped to done
    *,
    index_path: Path,                  # INDEX.md to read the seam graph from
    brain_base_dir: Path,              # brain store for requirement→scenario resolution
    repo_root: Path,                   # passed to the runner
    allow_deferred: bool = False,      # the --allow-deferred escape (default OFF)
    run_scenario=...,                  # injected runner callable (seam for stubbing,
                                       #   default = invoke sulis-verify-acceptance)
) -> SeamCloseResult:
    ...
```

### Result dataclass the tests assert against

```python
@dataclass
class SeamCloseResult:
    verdict: str           # "observed" | "blocked" | "not-closed"
    seam_title: str        # contract WP title (founder-facing seam name); "" when not-closed
    reason: str            # founder-English message (empty when observed/not-closed-silent)
    blocking: list         # [{scenario, why}] — folded from gate_decision when driven
    deferred_needs: list   # recorded needs (non-blocking under allow_deferred)
    drove_scenarios: list  # scenario ids driven this evaluation (for the once-fired record)
```

### Files this WP creates

```
plugins/sulis/scripts/tests/unit/test_seam_close_gate.py   (CREATE — the only file)
```

The test file owns its own fixtures (an in-file INDEX.md writer helper, a
fixture brain-store writer or a `monkeypatch` of `_brain_query` functions, and
a `FakeRunner` that returns canned `gate`/`verdict` envelopes). No shared
fixture module is created (avoids a peer-collision surface with future WPs;
rubric P6).

### The six acceptance-criteria tests (SPEC §Acceptance 1–6)

| Test | AC | Asserts |
|---|---|---|
| `test_seam_undriven_scenario_blocks` | AC-1 | Seam closes; a covering Scenario exists but was never driven green → `verdict == "blocked"`. (The bug being fixed: today it passes silently until ship.) |
| `test_seam_equality_verdict_passes` | AC-2 | Covering Scenario drove green, **equality** verdict → `verdict == "observed"`. |
| `test_seam_property_verdict_passes` | AC-3 | Covering Scenario drove green, **property** verdict → `verdict == "observed"`. |
| `test_seam_deferred_blocks` | AC-4 | Deferred/blocked Scenario → `verdict == "blocked"`; `reason` names the seam (by contract-WP **title**) and what wasn't driven; **no** `dna:` / `WP-` ids leak into `reason` (assert via regex). |
| `test_seam_no_covering_scenario_blocks` | AC-5 | Closing seam with **no** covering Scenario → `verdict == "blocked"`; `reason` distinguishes "no end-to-end check" from "couldn't run" (ADR-005 distinct wording). |
| `test_seam_allow_deferred_escape_records` | AC-6 | `allow_deferred=True` on a knowingly-deferred seam → `verdict == "observed"` (proceeds) **and** the deferral is recorded (`deferred_needs` non-empty / a recorded note present). |

### Supporting correctness tests (not numbered ACs; required for correctness)

- `test_unrelated_wp_done_is_noop` — a just-`done` WP in no seam → `verdict == "not-closed"`, `reason == ""` (silent). The common single-kind case — **this change's own WPs hit this path** (CF exemption).
- `test_integration_wp_completion_detects_seam_close` — detection signal (1): an integration / `kind: composite` WP reaching `done` closes its rooted seam.
- `test_contract_fanout_all_done_detects_seam_close` — detection signal (2): contract WP + all `dependsOn`-children `done`, no explicit integration WP.
- `test_seam_close_fires_once` — a settled seam (its covering Scenarios already have passing TestResults in the fixture brain) is **not** re-driven by a later unrelated WP `done`. Resolves Open Question 2 (once-only via brain evidence). Asserts `run_scenario` is **not** called when evidence already present.
- `test_malformed_index_does_not_fabricate_green` — Armor: an undeterminable detection (malformed INDEX / missing WP row) → `verdict == "not-closed"` with a "couldn't evaluate" `reason`; **never** fabricates `observed`.
- `test_gate_decision_is_reused_not_reimplemented` — behaviour-parity: fold the same fixture verdicts through both `_acceptance_gate.gate_decision` directly and through `evaluate`; assert identical `blocked`/`pass` outcome (so the two gates can't drift on observed-or-blocked).

## Definition of Done

### Red — Failing tests written
- [ ] `plugins/sulis/scripts/tests/unit/test_seam_close_gate.py` authored with all 6 AC tests + 6 supporting tests above.
- [ ] Running `pytest plugins/sulis/scripts/tests/unit/test_seam_close_gate.py` **fails at collection/import** (`ModuleNotFoundError: _seam_close_gate` or `ImportError` on `evaluate`/`SeamCloseResult`) — proving the tests precede the implementation (test-first MUST).
- [ ] Each test's assertion block is concrete (exact verdict string + message regex), not a `pytest.skip` or `xfail` placeholder.

### Green — Implementation makes tests pass
- [ ] N/A for this WP — Green is owned by WP-002. This WP's "implementation" is the test bodies + fixtures; they are complete when the assertions encode the contract above and fail only because the module is absent.
- [ ] The FakeRunner returns the same JSON envelope shape `sulis-verify-acceptance --json` emits (`{"scenario", "verdict", "gate"}`), so WP-002 codes against the real contract.

### Blue — Refactor complete
- [ ] Fixtures factored to in-file helpers (`_write_index(...)`, `_seed_brain(...)`, `FakeRunner`) — no copy-paste across the 12 tests.
- [ ] Founder-English assertions test the **absence** of operator vocabulary (`dna:`, `WP-`, `dna:scenario:`) in `reason`, per the SPEC plain-English constraint, not just presence of the seam title.
- [ ] No mock of `_acceptance_gate.gate_decision` — the parity test exercises the **real** `gate_decision` so the reuse is genuine (MEA-09: no mock of the unit we assert reuse of).

## Sequence
- **dependsOn:** — (foundation; starts at t=0)
- **blocks:** WP-002 (the module that turns these Red tests Green)
- **Parallelisable with:** WP-005, WP-006 (standards WPs — disjoint files)

## Estimated Token Cost
- **Input:** ~8k (the TDD test-surface table, `_acceptance_gate.py`, `_brain_query.py` signatures, `sulis-verify-acceptance` envelope, the ship-wiring test pattern)
- **Output:** ~6k (≈ 12 tests + fixtures, ~250 LOC)
- **Total:** ~14k

## Notes
- **Why test-first as its own WP rather than folded into WP-002:** the SPEC makes test-first a MUST and the blueprint mirrors `test_ship_acceptance_gate_wiring.py`. Separating the failing-test authoring from the implementation makes the Red gate observable in the dependency graph (WP-002 cannot start until WP-001's tests exist and fail) and keeps each WP single-responsibility (rubric P2).
- **Open Question 2 resolution lands here:** `test_seam_close_fires_once` pins the once-only behaviour to the brain-evidence signal (`find_passing_testresults_for_scenario`) — the same source `_verify_scenario_coverage` uses. No separate per-seam marker file (would be a second source of truth). The `--no-emit-evidence` degradation (a settled seam may re-fire) is documented in WP-002's module docstring, not guarded by a bespoke marker.

## Verification Plan
- **Adapter:** `methodology` (pure-function pytest, no subprocess).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_seam_close_gate.py`.
- **What this WP's verification proves:** the six SPEC acceptance criteria + the correctness cases are encoded as executable assertions that fail in the absence of the gate module and pass once WP-002 implements `evaluate` to the contract above. This is the change's primary blocking gate (TDD: "the tests are the teeth"), grounded in the tests passing — not advisory branch-CI (RC-02: `main` unprotected).
