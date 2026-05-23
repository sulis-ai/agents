---
id: HD-001
title: Split cmd_run into plan / commit / verify phases with explicit transaction boundaries
status: implemented
severity: HIGH
pillar: form
sources:
  - SEA audit report 2026-05-23 (Pattern A — `cmd_run` is a ~415 LOC monolith with implicit phase transitions; no transaction boundary between read-only planning and origin-mutating commits)
  - merge-queue-spike-2026-05.md F11 (PARTIAL recommendation — the cmd_run split is a *better* refactor under MQ; commit phase becomes a strategy dispatcher; HD-001 ships the split now, MQ strategy lands later)
  - HD-005 (GHClient protocol shipped v0.22.0 — supplies the injection seam that makes phase functions testable)
  - HD-002 (TrainTestbed fixture shipped v0.22.0 — supplies the end-to-end harness the refactor verifies against)
created: 2026-05-23
implemented: 2026-05-23
---

## Context

`scripts/wpx-train`'s `cmd_run` is a single function spanning lines 1169–1600
(~415 LOC). It orchestrates the entire batched-merge-queue lifecycle in one
linear flow: trigger evaluation, eligibility computation, batch packing, temp
clone, sequential rebase chain, bundled-tip CI poll, sequential squash-merge,
deploy poll, health, smoke, and either terminal success or one of two failure
paths (pre-merge `_pause_train_state`, post-merge `_handle_post_merge_failure`).

The architectural cost:

- **No transaction boundary.** Read-only operations (clone, rebase in temp,
  CI poll) and origin-mutating operations (force-push rebased branches,
  squash-merge to base) are interleaved with no visible seam. A reader has to
  track *which side of the bundled-tip-CI gate* a given line lives on to
  reason about its blast radius.
- **Mutable orchestration state pervades the function.** `record`, `bundle`,
  `clone_dir`, `final_merge_sha`, `deploy_url` are all module-level locals
  threaded through every step. The HD-003 mid-loop revert path proved this
  is fragile: getting the partial bundle to `_handle_post_merge_failure`
  with the right `merge_sha_on_dev` population required line-by-line
  reasoning about which `record["bundle"] = bundle` assignment was the
  current snapshot.
- **Phase functions aren't testable in isolation.** TrainTestbed (HD-002)
  exercises cmd_run end-to-end; it can't ask "given a known PlanResult, does
  the commit phase do the right thing on per-merge failure?" without
  re-driving the whole train. Coverage of the failure cross-product (six
  failure modes × any deploy verdict × any health verdict × any smoke
  verdict) is hard to keep tractable.
- **The MQ strategy switch has nowhere to live.** Per the merge-queue spike's
  PARTIAL recommendation, the commit phase becomes a strategy dispatcher
  (`_commit_via_merge_queue` for MQ-eligible repos, `_commit_via_rebase_loop`
  for the fallback). Today there's no callable named "the commit phase" to
  dispatch from.

This refactor is the structural-Form delta the merge-queue spike's F11 calls
out: "Today the equivalent split fights against the inline rebase+merge
logic." The MQ adoption itself ships in a later batch; HD-001 establishes
the seam.

## Decision

Split `cmd_run` into three phase functions with explicit dataclass-typed
return values that flow between them:

### `_plan_phase(state: PlanContext) -> PlanResult`

**Read-only against origin.** What's it allowed to do:

- Clone the repo into the per-train temp directory
- Read SHAs from origin via the GHClient
- Sequential rebase of bundle WPs in the temp clone (force-push of rebased
  branches happens here — this *is* origin-mutating, but only to feature
  branches the train owns; the *base branch* is never touched in plan phase)
- Poll bundled-tip CI to a verdict
- Build the bundle list (with `pre_train_sha`, `rebased_to_sha` populated)

What it returns: `PlanResult(bundle, base_branch, bundle_tip_branch, clone_dir,
ci_verdict, rebase_failures)`.

What it does on failure: calls the existing `_pause_train_state` (for
CI-red/timeout — non-fatal pre-merge) or emits an early "all branches failed
rebase" blocker. Both paths terminate the process via `emit_result()`. The
caller (cmd_run) never sees a None return — either the function returned a
successful `PlanResult` or the process exited.

### `_commit_phase(state: CommitContext) -> CommitResult`

**Only phase that mutates the base branch.** What's it allowed to do:

- Sequential squash-merge into the base branch (calls `_merge_squash` per
  bundle entry)
- Per-entry try/except wrapping the merge call — HD-003's partial-failure
  handling is preserved verbatim
- Updates `merge_sha_on_dev` on each bundle entry as merges land

**Strategy dispatcher**: this is where MQ-vs-legacy will eventually branch.
For HD-001's scope, we implement only `_commit_via_rebase_loop` — today's
sequential squash-merge logic factored as a private function. The dispatcher
in `_commit_phase` is a single-arm `if`/`else` (always `legacy` today;
follow-up adds `mq`):

```python
def _commit_phase(ctx: CommitContext) -> CommitResult:
    strategy = ctx.commit_strategy  # "legacy" today; "mq" in follow-up
    if strategy == "legacy":
        return _commit_via_rebase_loop(ctx)
    raise RuntimeError(f"Unknown commit strategy {strategy!r}")
```

What it returns: `CommitResult(merge_shas: dict[wp -> sha], final_merge_sha:
str)`.

What it does on failure: the HD-003 path — partial bundle handed to
`_handle_post_merge_failure`, which terminates the process. Same exit
contract as plan phase.

### `_verify_phase(state: VerifyContext) -> VerifyResult`

**Post-merge verification.** What's it allowed to do:

- Poll deploy workflow to a verdict
- Run health check (when staging URL provided)
- Run smoke command (when smoke_cmd provided)
- Per HD-007: report a `gates_pending` boundary when `--enable-gate-handoff`
  is set (calling LLM session dispatches Step 10.5 + Step 11)

What it returns: `VerifyResult(deploy_url, deploy_verdict, health_status,
smoke_verdict, ready_for_gates)`.

What it does on failure: `_handle_post_merge_failure` (ADR-212 revert) on
deploy/health/smoke fail; `_pause_train_state` on deploy timeout.

### `cmd_run` becomes orchestration only

```python
def cmd_run(args):
    paths = paths_from_args(args)
    repo = _resolve_repo(args)
    # ... eligibility, trigger check, batch packing (kept inline — small)
    plan_ctx = _build_plan_context(...)
    init_train_state(...)
    clone_dir = Path(tempfile.mkdtemp(...))
    try:
        plan = _plan_phase(plan_ctx._replace(clone_dir=clone_dir))
        commit = _commit_phase(_build_commit_context(plan_ctx, plan))
        verify = _verify_phase(_build_verify_context(plan_ctx, plan, commit))
        _finalise_success(plan_ctx, plan, commit, verify)
    except SystemExit:
        raise  # phase functions own their failure-path exits
    except Exception as exc:
        emit_internal_error(exc)
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)
```

### Dataclass shapes

Defined in `_wpxlib.py` (so future MQ commit strategy can live alongside the
legacy one without circular imports):

```python
@dataclass
class PlanResult:
    bundle: list[dict]          # entries with pre_train_sha + rebased_to_sha
    base_branch: str
    bundle_tip_branch: str
    ci_verdict: str              # "green" (paused on non-green)
    rebase_failures: list[dict]  # non-fatal per-WP failures

@dataclass
class CommitResult:
    merge_shas: dict[str, str]      # wp_id → squash-merge SHA
    final_merge_sha: str

@dataclass
class VerifyResult:
    deploy_url: str
    deploy_verdict: str
    health_status: str
    smoke_verdict: str
    ready_for_gates: bool        # HD-007 — see below
```

Phase context objects (`PlanContext`, `CommitContext`, `VerifyContext`) are
also dataclasses, constructed by small `_build_*_context()` helpers in
wpx-train. They carry the args namespace + paths + repo + train_id + clone_dir
so each phase function takes one argument.

### What the change-primitives catalogue says

- **Primitive: `decompose` (REORGANISE).** A single function is being
  decomposed into three.
- **Characterisation test (MUST):** the existing 9 integration tests in
  `test_train_failure_paths.py` (HD-002) plus the 5 partial-merge tests in
  `test_wpx_train_partial_merge_failure.py` are the characterisation set.
  Every one must continue to pass without modification — the behaviour
  contract is preserved.
- **No band-aid wrappers:** `_plan_phase` / `_commit_phase` / `_verify_phase`
  are not wrappers over `cmd_run`'s body; `cmd_run` itself shrinks. They
  are the *result* of decomposition.

## Verification

### Characterisation tests (no new tests for HD-001 alone — the existing suite IS the characterisation)

- `scripts/tests/integration/test_train_failure_paths.py` — all 9 tests pass
  unchanged. These cover: happy path, rebase conflict, CI red, CI timeout,
  mid-batch merge failure, deploy timeout, deploy failure, health
  unhealthy, smoke FAIL.
- `scripts/tests/integration/test_wpx_train_partial_merge_failure.py` —
  all 5 partial-failure tests pass unchanged. These cover the HD-003
  semantics specifically (partial bundle handed to the revert path).
- `scripts/tests/` full sweep — 288 tests passing pre-refactor; 288 (+ any
  HD-007 additions) post-refactor.

### Failing test (the RED that proves the gap exists today)

Pre-refactor: `_commit_phase` does not exist; importing it fails:

```python
def test_commit_phase_is_an_importable_function():
    """HD-001 RED — phase functions don't exist yet."""
    wpx = _load_wpx_train_module()
    assert hasattr(wpx, "_plan_phase"), "HD-001: _plan_phase not extracted"
    assert hasattr(wpx, "_commit_phase"), "HD-001: _commit_phase not extracted"
    assert hasattr(wpx, "_verify_phase"), "HD-001: _verify_phase not extracted"
    assert callable(wpx._plan_phase)
    assert callable(wpx._commit_phase)
    assert callable(wpx._verify_phase)
```

This test fails before HD-001, passes after. Added to
`scripts/tests/integration/test_train_failure_paths.py`.

### Sizing assertion (the second RED — proves the decomposition is real)

```python
def test_cmd_run_is_under_120_loc_after_refactor():
    """HD-001 RED — cmd_run is a thin orchestrator post-refactor, not the monolith."""
    import inspect
    wpx = _load_wpx_train_module()
    src = inspect.getsource(wpx.cmd_run)
    loc = sum(1 for ln in src.splitlines()
              if ln.strip() and not ln.strip().startswith("#"))
    assert loc < 120, (
        f"cmd_run is {loc} non-blank non-comment LOC; expected <120 "
        f"post-HD-001. Most logic should now live in _plan_phase / "
        f"_commit_phase / _verify_phase."
    )
```

This test fails before HD-001 (cmd_run ~330 LOC of body), passes after
(cmd_run ~80-100 LOC of orchestration).

## ADDED / MODIFIED / REMOVED

### MODIFIED

- `scripts/wpx-train`:
  - `cmd_run` shrinks from ~415 LOC (lines 1169-1600) to ~80-100 LOC of
    orchestration.
  - Three new module-level functions inserted: `_plan_phase`,
    `_commit_phase`, `_verify_phase`, plus one strategy implementation
    `_commit_via_rebase_loop`.
  - Three small helpers: `_build_plan_context`, `_build_commit_context`,
    `_build_verify_context`. (Or equivalent inline construction in cmd_run.)
  - `_finalise_success` extracted from cmd_run's tail (writes record,
    cleans up state file, emits the success JSON envelope).

- `scripts/_wpxlib.py`:
  - Three new dataclasses added: `PlanResult`, `CommitResult`,
    `VerifyResult` (plus context classes if exposed).
  - Exported via the import block at top of `scripts/wpx-train`.

### ADDED

- `scripts/tests/integration/test_train_failure_paths.py`:
  - Two new tests added (the REDs above): `test_phase_functions_exist`,
    `test_cmd_run_is_under_120_loc_after_refactor`.

### REMOVED

- The inline orchestration in old `cmd_run` body (lines 1257-1584) is
  fully replaced by `_plan_phase` / `_commit_phase` / `_verify_phase` calls.

## Sequence

This delta SHIPS BEFORE HD-007 in the same Batch 5 commit. HD-007 builds
on top of `_verify_phase` (adds the `verifying_gates` boundary). Both share
the new `VerifyContext` / `VerifyResult` shapes.

The MQ strategy implementation (`_commit_via_merge_queue` + eligibility
detection) is **deferred to a separate follow-up delta** per the spike's
recommendation; HD-001 ships only the single-strategy dispatcher with
`_commit_via_rebase_loop` as the one strategy. The dispatcher's
`raise RuntimeError(f"Unknown commit strategy {strategy!r}")` is the
seam for the follow-up.
