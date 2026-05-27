---
id: HD-012
title: SDK lags wpx-train CLI — no mark_gates_complete; run() missing enable_gate_handoff; TrainRunResult.outcome Literal missing awaiting_gates
status: proposed
severity: HIGH
pillar: form
source: code-review:PR-batch5-2026-05-23T124318Z
lens: architecture
created: 2026-05-23
notes: |
  The orchestrator already flagged this as a known gap to address before
  commit; this delta captures the specific surface gaps and the
  contract-drift implications so the fix is bounded.
---

## Context

Batch 5 (HD-007) added two new CLI surfaces to `scripts/wpx-train`:

1. `--enable-gate-handoff` flag on the `run` subcommand
   (`wpx-train:2077-2086`).
2. `mark-gates-complete` subcommand
   (`wpx-train:2088-2108`, handler `cmd_mark_gates_complete` line 1802).

And a new outcome literal `awaiting_gates` on the structured exit
envelope from `cmd_run` via `_finalise_awaiting_gates`
(`wpx-train:1648-1671`).

The SDK at `sdk/python/sulis_execution/resources/train.py` exposes
the CLI as a typed Python interface. As of HEAD it does NOT carry the
HD-007 additions:

```python
# sdk/python/sulis_execution/resources/train.py:152-179 (HEAD)
def run(
    self,
    *,
    deploy_workflow: str,
    force: bool = False,
    staging_url: Optional[str] = None,
    health_path: Optional[str] = None,
    smoke_cmd: Optional[str] = None,
    ci_poll_interval: Optional[int] = None,
    deploy_poll_interval: Optional[int] = None,
    max_batch_size: int = 5,
    base_branch: Optional[str] = None,
    repo: Optional[str] = None,
) -> TrainRunResult:
    ...
```

No `enable_gate_handoff` parameter.

```python
# sdk/python/sulis_execution/types.py:203-216 (HEAD)
class TrainRunResult(_Base):
    train_id: str
    outcome: Literal[
        "success", "not_triggered", "nothing_to_pack", "blocker", "error"
    ]
    ...
```

No `awaiting_gates` in the Literal. No `gate_handoff` field. (`paused`
is also missing — separate pre-existing gap.)

No `mark_gates_complete` method on either `TrainResource` or
`AsyncTrainResource`.

## Why it matters

Any SDK consumer that wants to use HD-007's path cannot:

1. **Cannot opt in.** No way to pass `--enable-gate-handoff` through
   the SDK.
2. **Pydantic validation will fail** if a consumer somehow does manage
   to invoke the CLI with the flag (e.g. via `repo` env munging or
   bypass) — the `TrainRunResult.outcome` Literal rejects
   `awaiting_gates`. The SDK transport will raise on response parse.
3. **No way to finalise.** Even if the train pauses at the gate
   boundary, the SDK has no `mark_gates_complete()` method to call.

This is the classic CLI-vs-SDK contract-drift smell:
the CLI ships a feature; the SDK isn't co-evolved; the SDK becomes a
strict subset of the CLI. Once that pattern entrenches, every CLI feature
becomes a two-step (ship CLI, ship SDK retrofit), and SDK consumers
end up shelling out around the SDK.

## Severity

**HIGH.** Not blocking the batch — the only SDK consumer of `train.run`
today is the internal MCP server, which doesn't yet drive the gate-handoff
path either. But:

- `run-all/SKILL.md` documents `--enable-gate-handoff` as recommended.
  The skill shells out to the binary directly, not via the SDK. The
  moment another tool wants to drive a train programmatically, the SDK
  gap blocks them.
- Once `awaiting_gates` appears in production train YAML records, the
  SDK's `TrainRunResult` will silently fail to validate them, even on
  read-only `inspect` calls if those reuse the same type.

## Verification — failing test (RED)

```python
def test_train_run_result_outcome_literal_includes_awaiting_gates():
    """HD-012 RED — TrainRunResult must accept the awaiting_gates outcome
    introduced by HD-007 (Batch 5)."""
    from sulis_execution.types import TrainRunResult
    # Pydantic-validate a synthetic awaiting_gates envelope
    result = TrainRunResult.model_validate({
        "train_id": "train-test",
        "outcome": "awaiting_gates",
        "wps_shipped": ["WP-001"],
        "deploy_url": "https://x.example.com",
        "final_merge_sha": "abc1234",
    })
    assert result.outcome == "awaiting_gates"


def test_train_resource_has_mark_gates_complete():
    """HD-012 RED — TrainResource and AsyncTrainResource expose
    mark_gates_complete corresponding to the wpx-train CLI subcommand."""
    from sulis_execution.resources.train import (
        TrainResource, AsyncTrainResource,
    )
    assert hasattr(TrainResource, "mark_gates_complete"), (
        "HD-012: TrainResource missing mark_gates_complete; "
        "SDK lags HD-007 CLI surface"
    )
    assert hasattr(AsyncTrainResource, "mark_gates_complete"), (
        "HD-012: AsyncTrainResource missing mark_gates_complete"
    )


def test_train_resource_run_accepts_enable_gate_handoff():
    """HD-012 RED — TrainResource.run accepts enable_gate_handoff per HD-007."""
    import inspect
    from sulis_execution.resources.train import TrainResource
    sig = inspect.signature(TrainResource.run)
    assert "enable_gate_handoff" in sig.parameters, (
        "HD-012: TrainResource.run missing enable_gate_handoff kwarg"
    )
```

## Recommendation

Sync the SDK with the CLI surface in the same commit as Batch 5
(or as an immediately-following Batch-5.1 commit before any consumer
adopts the flag):

1. **`TrainResource.run` + `AsyncTrainResource.run`:** add
   `enable_gate_handoff: bool = False` kwarg; pass through to params.
2. **`TrainRunResult.outcome` Literal:** add `"awaiting_gates"` and
   `"paused"` (the second is pre-existing drift but worth doing
   together).
3. **`TrainRunResult`:** add `gate_handoff: Optional[GateHandoff] = None`
   field with a typed shape mirroring the JSON envelope's `gate_handoff`
   block (batch_start_sha / batch_end_sha / diff_range / wps /
   next_action).
4. **New methods on both resources:** `mark_gates_complete(*, train_id,
   gate_findings=None, critical_found=False, repo=None)`.
5. **New result type:** `TrainMarkGatesCompleteResult(_Base)` with
   `train_id`, `outcome: Literal["success", "gate_blocker"]`, `phase:
   Literal["success", "failed"]`, `record_path`.

## ADDED / MODIFIED / REMOVED

### MODIFIED

- `sdk/python/sulis_execution/resources/train.py`:
  - `TrainResource.run` + `AsyncTrainResource.run`: add `enable_gate_handoff`
    kwarg.
  - Both resources: add `mark_gates_complete` method.
- `sdk/python/sulis_execution/types.py`:
  - `TrainRunResult.outcome`: extend Literal to include `awaiting_gates`,
    `paused`.
  - `TrainRunResult`: add `gate_handoff: Optional[GateHandoff] = None`.

### ADDED

- `sdk/python/sulis_execution/types.py`:
  - `GateHandoff(_Base)` type.
  - `TrainMarkGatesCompleteResult(_Base)` type.
- `sdk/python/tests/test_resources_smoke.py`:
  - Smoke test for `mark_gates_complete` (uses `make_fake_binary` pattern).
- `sdk/python/tests/`: three RED tests above.

## Sequence

Either in the same commit as Batch 5 or immediately after. Must land
before any SDK consumer tries to use the gate-handoff path. The
orchestrator (founder) has already flagged this as a pre-commit
remediation item — this delta documents the specific gaps so the fix
is bounded.
