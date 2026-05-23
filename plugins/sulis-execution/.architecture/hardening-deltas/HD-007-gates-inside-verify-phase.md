---
id: HD-007
title: Fold Step 10.5 + Step 11 into the train's verify phase (gate handoff)
status: implemented
severity: MEDIUM
pillar: form
sources:
  - SEA audit report 2026-05-23 (Pattern G — Step 10.5 and Step 11 dispatch lives in run-all/SKILL.md as post-train follow-on; conceptually they are part of the train's transaction but architecturally they fire after the train declares success, blurring the train's "done" semantics)
  - HD-001 (this delta extends `_verify_phase` with the gate-handoff boundary; it depends on HD-001's phase split landing first)
created: 2026-05-23
implemented: 2026-05-23
---

## Context

After `wpx-train run` returns `outcome: success`, the calling LLM session
(today: `run-all/SKILL.md` Steps 13 and 14 — the "Step 10.5 (per-batch
code-review)" and "Step 11 (per-batch security review)" dispatches) runs
two more verification primitives over the batch that just shipped:

1. **Step 10.5** — `/sea:code-review` against the batch diff range,
   surfacing cross-WP composition issues that only appear when sibling
   WPs compose (N+1 across siblings, contract drift between
   interdependent WPs).
2. **Step 11** — per-WP `sulis-security:security-reviewer` Agent calls
   over `wps_shipped`, with findings registered + remediation WPs
   auto-drafted.

These primitives complete the train's transaction in the conceptual sense:
the batch isn't really "shipped" until both code-review and security review
have run. But today the train declares `outcome: success` *before* the
gates run, and the run-all skill chases after with the gate dispatch as a
post-train follow-on. The semantic gap: a downstream consumer reading
the train YAML record sees `outcome: success` and concludes the batch is
fully verified, when in fact two more steps are still pending.

The architectural cost:

- **Transaction boundary is wrong.** The train's notion of "success" should
  include the gates the user requires before considering a batch shipped.
  Putting them outside the train means `outcome: success` is a lie of
  omission.
- **The calling session can't tell when the train is "really done".**
  A future orchestrator that wants to chain a follow-on action after a
  train completes (e.g. tag a release, notify a channel, kick off a
  next-stage pipeline) has no clean signal — it has to peek at the
  run-all skill's downstream output rather than the train's exit envelope.
- **State machine doesn't model the in-progress-but-merges-landed window.**
  Between `verifying` (deploy/health/smoke) completing and the gates
  finishing, the train's state is ambiguous: deploys landed, merges are
  live, but verification isn't complete. `inspect` shows `verifying →
  success` with no intermediate state — there's nowhere to record gate
  outcomes.

### The tension (and why we choose option (b))

A Python CLI (`wpx-train`) can't directly spawn LLM Agents (the Step 10.5
+ Step 11 dispatch). SEA's audit Pattern G called this out: the train
*can't* run the gates itself. Two architectures resolve this:

- **(a) Pause-then-resume.** `_verify_phase` writes a structured "needs
  gate" pause record; cmd_run exits paused; calling session dispatches
  gates; cmd_run is re-invoked via `wpx-train resume <id>` which continues
  `_verify_phase` from where it left off. Reuses the existing resume
  machinery. *Cost*: cmd_resume gains a new branch (post-verify-pre-gates
  resume), adding complexity to the resume state machine which today
  already special-cases pre-merge vs post-merge.

- **(b) Stop-at-boundary with explicit gate-complete signal.** cmd_run
  reaches the gate boundary, writes state to a new `verifying_gates`
  phase, emits a new outcome `awaiting_gates`. Calling session reads the
  state, dispatches the gates inline (today's run-all code, factored
  cleanly), then signals completion via a new tiny subcommand
  `wpx-train mark-gates-complete --train-id <id> [--gate-findings <path>]`
  which finalises the train to terminal `success`. *Cost*: one new
  subcommand; one new phase in the state machine. *Benefit*: cmd_resume
  doesn't change at all (resume continues to refuse post-merge resumes);
  the gate-completion path is a separate, narrow code path that's easy
  to reason about.

**Decision: (b).** Three reasons:

1. cmd_resume's existing pre-merge-vs-post-merge logic is already nuanced;
   adding a third "post-verify-pre-gates" case is a bigger code change
   than adding a fresh single-purpose subcommand.
2. The gate dispatch *needs* to stay in the calling LLM session anyway
   (the Python CLI can't spawn Agents). Option (b) makes that boundary
   explicit; option (a) hides it behind the resume machinery.
3. Backwards compatibility: the new behaviour is gated behind
   `--enable-gate-handoff` (default False initially) so today's callers
   see no change. The 9 existing failure-path tests pass without
   modification.

## Decision

### State-machine extension

Add one new phase between `verifying` and the terminal phases:

```python
PHASES = (
    "pending", "rebasing", "ci_running", "merging", "deploying", "verifying",
    "verifying_gates",        # NEW — deploy/health/smoke done; gates pending
    "success", "failed", "paused", "aborted",
)
```

`verifying_gates` is **not** terminal — it sits between `verifying` and
`success`. A train in `verifying_gates` has all merges live + deploy
verified + health + smoke green, and is waiting for the calling session
to dispatch Step 10.5 + Step 11 and signal completion.

### New cmd_run exit shape (only when `--enable-gate-handoff` is set)

When `_verify_phase` returns `ready_for_gates=True` (i.e., the new
behaviour flag is on AND deploy/health/smoke all came back green), cmd_run
transitions the state to `verifying_gates` and emits a NEW outcome:

```json
{
  "train_id": "train-2026-05-23T...",
  "outcome": "awaiting_gates",
  "phase": "verifying_gates",
  "wps_shipped": ["WP-001", "WP-002", "WP-003"],
  "deploy_url": "...",
  "final_merge_sha": "abcd1234",
  "record_path": "...",
  "gate_handoff": {
    "batch_start_sha": "...pre_train_sha of first bundle entry...",
    "batch_end_sha": "...final_merge_sha...",
    "diff_range": "<batch_start>..<batch_end>",
    "wps": ["WP-001", "WP-002", "WP-003"],
    "next_action": "calling session: dispatch Step 10.5 (sea:code-review against diff_range) + Step 11 (per-WP security review); then run `wpx-train mark-gates-complete --train-id <id>` to finalise."
  }
}
```

Exit code: **0** (this is success-pending-gates, not failure). The
calling session is expected to inspect this envelope, run the gates, then
call mark-gates-complete.

### New subcommand: `mark-gates-complete`

```
wpx-train mark-gates-complete --train-id <id> \
  [--gate-findings <path>] \
  [--critical-found] \
  [--repo <org/repo>]
```

Reads the train state at `<id>.state.json`. Required phase:
`verifying_gates` (errors otherwise).

Effects:

- If `--critical-found` was set, transition to phase `failed` with
  `pause_reason: "Gate found CRITICAL finding(s); see <gate-findings>"`,
  write the final YAML record with `outcome: gate_blocker`. *Does not*
  invoke the ADR-212 revert — the calling session already wrote BLOCKERs
  per Step 10.5 / 11's existing CRITICAL handling; the train's job is
  just to record the outcome.
- Otherwise: transition to phase `success` (the existing terminal
  success path), write the YAML record with `outcome: success`,
  optionally include `gate_findings_path` in the record. Clean up the
  state file.

This subcommand is intentionally tiny — it's just a state-machine
transition + record write. No git operations, no shell-outs, no agent
dispatch.

### `cmd_resume` semantics

Unchanged. A train paused at `verifying_gates` is treated like other
post-merge pauses — `wpx-train resume` errors out with the existing
"post-merge resume isn't available" message pointing the founder at
`mark-gates-complete` (or `abort` for the rollback path).

### Backwards compatibility

- **Default behaviour unchanged.** Without `--enable-gate-handoff`, the
  flag defaults to False. `_verify_phase` returns `ready_for_gates=False`,
  cmd_run transitions to terminal `success` exactly as today.
- **All 9 integration tests pass unmodified.** None of them set
  `--enable-gate-handoff`, so they exercise the legacy path.
- **`wpx-train resume <id>` semantics unchanged.** Post-merge resume
  refusal already covers `verifying_gates`; the error message gains the
  `mark-gates-complete` suggestion.

### Migration plan for the run-all skill

`skills/run-all/SKILL.md` Steps 13 (Step 10.5) and 14 (Step 11) gain a
preamble:

> Pre-flight: pass `--enable-gate-handoff` when invoking `wpx-train run`.
> The train will return with `outcome: awaiting_gates` (exit 0) instead
> of `outcome: success` once deploy/health/smoke are green. The
> `gate_handoff` block in the envelope carries the batch diff range +
> wps_shipped — use it to drive Step 10.5 and Step 11. After both gates
> complete, invoke `wpx-train mark-gates-complete --train-id <id>` to
> finalise the train.

The Step 10.5 and Step 11 dispatch code in the skill stays put — that's
the LLM-Agent dispatch the Python CLI can't do. What changes is the
*ordering signal*: instead of "after the train returns success, run the
gates", it becomes "the train pauses before declaring success; the gates
are the train's gate, and `mark-gates-complete` is what flips it".

The legacy code path (run gates after `outcome: success`) is preserved
in the skill text for a deprecation cycle so projects mid-migration
don't break.

### What the change-primitives catalogue says

- **Primitive: `expand-create` (EXPAND).** New phase, new subcommand, new
  outcome value — all additive. Existing behaviour unchanged.
- **Characterisation tests:** existing 9 failure-path tests are the
  baseline. Two new tests added (REDs below) cover the new boundary
  semantics.
- **No wrap rot:** the `mark-gates-complete` subcommand isn't a wrapper —
  it's a new state-machine transition with no equivalent counterpart in
  the codebase today.

## Verification

### Characterisation tests (existing — must all still pass)

- `scripts/tests/integration/test_train_failure_paths.py` — 9 tests pass
  unmodified. The `make_args()` default does not set
  `enable_gate_handoff`, so these all exercise the legacy path.
- `scripts/tests/integration/test_wpx_train_partial_merge_failure.py` —
  5 tests pass unmodified.

### Failing tests (REDs that prove the gap exists today)

```python
def test_verify_phase_pauses_at_gate_boundary_when_handoff_enabled(train_testbed):
    """HD-007 RED — with --enable-gate-handoff, train stops at verifying_gates
    instead of going to terminal success."""
    _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args(enable_gate_handoff=True)
    record, exit_code = train_testbed.run_train(args)
    assert exit_code == 0, f"Gate handoff is success-pending, not failure"
    assert record.get("outcome") == "awaiting_gates", (
        f"Expected outcome=awaiting_gates; got {record.get('outcome')}"
    )
    # All merges still landed
    train_testbed.assert_merged_on_dev("WP-001")
    train_testbed.assert_merged_on_dev("WP-002")
    train_testbed.assert_merged_on_dev("WP-003")


def test_mark_gates_complete_finalises_train_to_success(train_testbed):
    """HD-007 RED — mark-gates-complete promotes verifying_gates → success."""
    _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args(enable_gate_handoff=True)
    record, exit_code = train_testbed.run_train(args)
    train_id = record["train_id"]
    # Invoke the new subcommand
    from types import SimpleNamespace
    wpx = _load_wpx_train_module()
    mark_args = SimpleNamespace(
        project=train_testbed.project,
        repo_root=str(train_testbed.workspace),
        repo="acme/test-repo",
        train_id=train_id,
        gate_findings=None,
        critical_found=False,
    )
    try:
        wpx.cmd_mark_gates_complete(mark_args)
    except SystemExit:
        pass
    final = train_testbed.read_latest_train_record()
    assert final.get("outcome") == "success"
```

Both fail pre-HD-007 (the `verifying_gates` phase doesn't exist, the
`mark-gates-complete` subcommand doesn't exist, and `_verify_phase` doesn't
honour `enable_gate_handoff`). Both pass post-HD-007.

## ADDED / MODIFIED / REMOVED

### ADDED

- `scripts/_wpxlib.py`:
  - New phase `"verifying_gates"` in `PHASES`.
  - `VerifyResult.ready_for_gates: bool` field (added by HD-001's dataclass;
    HD-007 wires it).

- `scripts/wpx-train`:
  - New `_verify_phase` branch: when `args.enable_gate_handoff` is True
    AND deploy/health/smoke all green, transition phase to
    `verifying_gates` and emit `outcome: awaiting_gates` with the
    `gate_handoff` envelope block.
  - New `cmd_mark_gates_complete` function (~50 LOC).
  - New `--enable-gate-handoff` argument on `p_run`.
  - New `mark-gates-complete` subparser + handler registration.

- `scripts/tests/integration/test_train_failure_paths.py`:
  - Two new tests: `test_verify_phase_pauses_at_gate_boundary_when_handoff_enabled`
    and `test_mark_gates_complete_finalises_train_to_success`.

- `scripts/tests/integration/testbed.py`:
  - `TrainTestbed.make_args()` accepts `enable_gate_handoff` override
    (defaults to False — preserves all 9 existing tests).

- `references/lifecycle.md`:
  - New section: "Step 10.5 + Step 11 as the train's verify-phase gates"
    documenting `verifying_gates` phase + `mark-gates-complete`
    subcommand + the calling-session dispatch pattern.

### MODIFIED

- `skills/run-all/SKILL.md`:
  - Step 12 (the `wpx-train run` invocation): add
    `--enable-gate-handoff` flag.
  - Step 13 (Step 10.5): updated preamble — train returns
    `outcome: awaiting_gates`, not `success`. Parse `gate_handoff` block
    from envelope. Dispatch unchanged otherwise.
  - Step 14 (Step 11): same preamble updated. After all per-WP reviews
    complete, invoke `wpx-train mark-gates-complete --train-id <id>`.
  - Legacy code paths preserved as fallback documentation for a
    deprecation cycle.

### REMOVED

Nothing removed. HD-007 is additive — the boundary moves conceptually,
the dispatch stays where the LLM Agents live.

## Sequence

This delta SHIPS IN THE SAME BATCH 5 COMMIT AS HD-001. HD-001 introduces
the `_verify_phase` function and `VerifyResult` dataclass; HD-007 extends
both. They share state-machine modifications. Splitting them across
commits would force an awkward interim where `_verify_phase` exists but
doesn't yet honour the gate-handoff flag.

The `wpx-train mark-gates-complete` subcommand is the minimum-surface
addition needed to close HD-007 without dragging cmd_resume into the
change. If a future need arises to actually re-enter `_verify_phase`
from a pause (e.g., re-poll deploy after a flaky deploy timeout that
eventually went green), that's a separate delta — HD-007 doesn't preempt
that design.
