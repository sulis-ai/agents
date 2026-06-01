---
id: WP-007
title: Implement Verify phase — drift invoke scoped to entity + roll-back on failure
status: pending
kind: backend
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-007
dependsOn: [WP-001]
blocks: [WP-008]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Armor §Cross-tenant drift semantics; FR-008 (post-mint drift verification); MUC-005
adrs: []
---

## Context

Implements the Verify phase per TDD §Armor §Cross-tenant drift
semantics + FR-008. The Step `run-drift-detector-on-mint` (Step ULID
`01KT1WDSST09RUNDRIFTDET`, per TDD §Canonical Identifiers) invokes the
existing blocking drift detector (commit `7d666df extend:
tighten-drift-gate`) scoped to the just-minted entity, and rolls back
the mint on failure (MUC-005).

The verifier reuses the drift-detector Tool declared in WP-001's
`tools.jsonld` (no new Tool ULID). It passes the
`--cross-tenant-refs-allowed-for=release_workflow_ref,belongs_to_product_ref`
flag introduced by WP-009 — without this flag, every consumer mint
would FAIL drift because the Project's `release_workflow_ref` crosses
to the marketplace tenant.

Roll-back is `target_path.unlink(missing_ok=False)` — the just-written
file is deleted; the operator sees the structured failure message
from the drift detector.

## Contract

### Files created

```
plugins/sulis/scripts/_discovery/
└── verifier.py                   # run_drift_check_on_entity + roll-back helper
plugins/sulis/scripts/tests/unit/
└── test_discovery_verifier.py    # drift-success + drift-failure + roll-back tests
```

2 files.

### Module shape

```python
# plugins/sulis/scripts/_discovery/verifier.py
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DriftVerifyResult:
    ok: bool
    exit_code: int
    stderr: str         # the drift detector's structured failure message (founder-readable)


class DriftVerifyFailed(Exception):
    """Raised when the drift detector exits non-zero AFTER roll-back has executed.
    Carries the drift detector's stderr so the skill prose can surface it.
    """
    def __init__(self, result: DriftVerifyResult, rolled_back_path: Path):
        self.result = result
        self.rolled_back_path = rolled_back_path
        super().__init__(
            f"Drift verification failed (exit {result.exit_code}). "
            f"Mint at {rolled_back_path} has been rolled back."
        )


def run_drift_check_on_entity(
    entity_path: Path,
    *,
    cross_tenant_refs_allowed: list[str] | None = None,
    drift_detector_path: Path = Path("plugins/sulis/scripts/check-canonical-drift.py"),
) -> DriftVerifyResult:
    """Invoke the drift detector scoped to one entity.

    Default cross_tenant_refs_allowed = ['release_workflow_ref', 'belongs_to_product_ref']
    per TDD §Armor §Cross-tenant drift semantics.

    Returns DriftVerifyResult; does NOT roll back on failure (that's the
    composition root's call).
    """


def verify_and_roll_back_on_failure(
    entity_path: Path,
    **kwargs,
) -> DriftVerifyResult:
    """Convenience: run_drift_check_on_entity + entity_path.unlink() on failure.

    Raises DriftVerifyFailed after roll-back so the caller can surface
    the structured stderr to the operator (MUC-005 system response).
    """
```

### Drift detector invocation

The detector is invoked via `subprocess.run(...)` with:

- `--scope <entity_path>` — limits validation to one entity (not the
  whole `.sulis/projects/` tree)
- `--cross-tenant-refs-allowed-for release_workflow_ref,belongs_to_product_ref`
  — the WP-009 flag

If WP-009's flag is not yet merged (parallel-dispatch race), the
verifier MUST fail with a clear "drift detector extension not yet
deployed" error rather than silently passing without cross-tenant
allowance. This is the n=2-dogfood-failure case from TDD §Trade-offs.

## Definition of Done

### Red — Failing tests written

- [ ] `test_discovery_verifier.py::test_drift_pass_returns_ok_True` — mock the drift detector via a fixture entity that's valid; assert `DriftVerifyResult(ok=True, exit_code=0, ...)`
- [ ] `test_discovery_verifier.py::test_drift_fail_returns_ok_False_with_stderr` — fixture entity with a bogus `release_workflow_ref`; assert `ok=False`, `exit_code != 0`, `stderr` non-empty
- [ ] `test_discovery_verifier.py::test_verify_and_roll_back_deletes_entity_on_failure` — write a fixture entity to a tmp path, run `verify_and_roll_back_on_failure`, assert (a) `DriftVerifyFailed` raised, (b) `entity_path.exists() == False` afterward
- [ ] `test_discovery_verifier.py::test_verify_and_roll_back_preserves_entity_on_success` — assert `entity_path.exists() == True` after a successful verify
- [ ] `test_discovery_verifier.py::test_cross_tenant_flag_passed_to_detector` — instrument `subprocess.run` via `monkeypatch`; assert the `argv` contains `--cross-tenant-refs-allowed-for release_workflow_ref,belongs_to_product_ref`
- [ ] `test_discovery_verifier.py::test_scope_arg_passed_to_detector` — assert `argv` contains `--scope <entity_path>`
- [ ] `test_discovery_verifier.py::test_DriftVerifyFailed_carries_rolled_back_path` — exception's `rolled_back_path` attribute equals the entity path that was deleted
- [ ] `test_discovery_verifier.py::test_DriftVerifyFailed_carries_stderr_for_operator_surface` — `exc.result.stderr` contains the detector's structured failure message (so WP-008 can surface it verbatim)
- [ ] `test_discovery_verifier.py::test_detector_missing_raises_clear_error` — simulate WP-009 flag-unsupported scenario (mock `subprocess.run` returning exit code 2 + a "unknown flag" stderr); assert the verifier raises a `DriftDetectorExtensionMissingError` with a hint pointing at WP-009

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/scripts/_discovery/verifier.py` authored per Contract
- [ ] All 9 Red tests pass
- [ ] Coverage on `verifier.py` ≥ 90%
- [ ] Cross-tenant defaults match TDD §Armor §Cross-tenant drift semantics verbatim

### Blue — Refactor complete

- [ ] One internal helper for `subprocess.run` invocation; `run_drift_check_on_entity` + `verify_and_roll_back_on_failure` compose it
- [ ] No silent swallowing of stderr — every failure path either returns `DriftVerifyResult(ok=False, ...)` or raises with stderr attached
- [ ] Roll-back is `target.unlink(missing_ok=False)` — explicit; raising if the file is already gone (a more-serious problem than the drift failure)
- [ ] Function docstring quotes the MUC-005 system response verbatim so operators surfacing the error to consumers can copy it directly

## Sequence

- **dependsOn:** WP-001 (the Step entity for `run-drift-detector-on-mint` is authored there; this WP backs it with code)
- **blocks:** WP-008 (skill prose imports `verify_and_roll_back_on_failure`)
- **Parallelisable with:** WP-002, WP-003, WP-004, WP-005, WP-006, WP-009

**Soft dependency on WP-009.** Verifier passes a flag that only WP-009
teaches the drift detector to recognise. The Red test
`test_detector_missing_raises_clear_error` covers the race condition
(WP-007 lands but WP-009 hasn't yet) by asserting a typed error. The
hard cross-WP dependency is captured at WP-008 (the skill won't
function end-to-end until both have merged); WP-007 itself is
parallelisable because the test suite mocks the detector behaviour
both ways.

## Estimated Token Cost

- **Input:** ~3k (TDD §Armor §Cross-tenant + FR-008 + MUC-005 + WP-001's drift-detector Tool spec)
- **Output:** ~3k (`verifier.py` ≈ 120 LOC + test file ≈ 180 LOC)
- **Total:** ~6k

## Performance

- Drift detector is local Python; one entity scope completes in <500ms on a typical laptop.
- Roll-back is one `unlink` call (<10ms). The combined Verify-phase time is well within NFR-001's 5-minute wall-time budget for the whole discovery run.

## Notes

- The `--scope <entity_path>` flag scopes the detector to one file rather than the whole `.sulis/projects/` tree. This keeps verify-time bounded as a consumer's Project count grows.
- The cross-tenant-allowed list defaults to `['release_workflow_ref', 'belongs_to_product_ref']` per TDD §Armor §Cross-tenant drift semantics. These are the two ref types known to cross from consumer-tenant to marketplace-tenant. New cross-tenant refs (post-v1) would require both WP-001's canonical AND this default list to be updated.
- `belongs_to_product_ref` is included as a forward-compatibility hook even though v1 doesn't use it — the foundation Project schema may grow `belongs_to_product_ref` in a later release; the list is small enough that pre-allowing both is cheaper than re-rolling the verifier.
