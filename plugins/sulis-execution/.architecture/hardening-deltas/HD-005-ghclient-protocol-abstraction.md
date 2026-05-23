---
id: HD-005
title: GHClient protocol abstraction over `gh` shell-outs (testability seam)
status: implemented
severity: MEDIUM
pillar: proof
sources:
  - SEA audit report 2026-05-23 (Pattern D — `gh` shell-outs scattered across the train/pipeline path; no dependency-injection seam for integration tests)
  - merge-queue-spike-2026-05.md (recommendation PARTIAL ADOPT; the MQ strategy dispatcher needs an injectable GitHub-API client to be testable without hitting real GitHub)
created: 2026-05-23
implemented: 2026-05-23
---

## Context

`scripts/_wpxlib.py` reaches GitHub through ten distinct `_run(["gh", "api", …])`
and `_run(["gh", "repo", …])` / `_run(["gh", "run", …])` callsites. Today each
is wrapped in a private module-level helper (`_gh_check_runs`,
`_gh_branch_sha`, `_gh_ref_sha`, `_gh_branch_already_merged`, `_gh_merge`,
`_gh_deploy_runs`, `_gh_branch_exists`, plus a branch-delete inside
`_merge_squash`, plus `is_sha_on_branch`, plus `clone_repo_to_temp`'s
gh-first path), and each helper subprocess-execs the `gh` binary directly.
`wpx-pipeline` and `wpx-train` import these helpers and consume them
pointwise.

The architectural consequence:

- **No injection seam.** The existing 268-test suite covers `_wpxlib.py`'s
  internals well, but at the *boundary* — where wpx-train consumes those
  helpers — tests can only monkeypatch each `_gh_*` symbol one at a time
  (see `test_wpx_train_partial_merge_failure.py` lines 164–183, which
  monkeypatches `_gh_ref_sha`, `_gh_branch_sha`, `_poll_ci`, and others
  individually). Each new failure-mode test repeats the same shape.
- **No fault-injection vocabulary.** Tests that want to model "what
  happens when the merge endpoint returns 502 on the third merge" or
  "what happens when CI never goes green" or "what happens when the deploy
  workflow returns failed" each have to recreate the gh-call sequence by
  hand. There is no place to say *"this fake GitHub fails the rebase for
  WP-B and otherwise behaves normally"*.
- **The merge-queue spike's PARTIAL recommendation needs this seam.**
  HD-001 (Batch 5) is going to introduce a strategy dispatcher in
  cmd_run's commit phase: `_commit_via_merge_queue` vs
  `_commit_via_rebase_loop`. Both strategies operate over the *same*
  GitHub API surface. Testing two strategies × six failure modes × the
  cross-product with deploy/health/smoke verdicts is intractable without
  a fake-able client at the gh boundary.

## Decision

Introduce a **`GHClient` Protocol** in `_wpxlib.py` defining the ten
operations the train + pipeline + helpers need from GitHub. Ship one real
implementation, `RealGHClient`, that delegates each method to the existing
`_run(["gh", ...])` shape — **byte-for-byte identical behaviour** to today.
Refactor every `_gh_*` shim helper to accept an optional
`gh: GHClient | None = None` parameter; when `None`, the shim uses a
module-level `_default_gh_client` (a `RealGHClient()` instance). Callsites
that don't care continue to call the shim without the parameter and get
the real client. Tests that want to inject a fake pass `gh=fake_client`.

Wrapper-rot check (per `references/change-primitives.md`'s No-Band-Aid-
Wrappers rule): this is **EXPAND-Create over an external subject** (the
`gh` CLI / GitHub API), not a wrap over internal code. `gh` is third-party;
the GHClient Protocol is the port that lets the domain depend on an
interface, not on a subprocess shape. **subject_ownership: external.** No
removal plan required.

The Ports & Adapters discriminator: whose interface is the public face?
*Mine* — `GHClient` is a Protocol owned by the train domain. `RealGHClient`
is an adapter implementing it; the `gh` CLI is *called by* the adapter.
This is the canonical adapter-for-a-domain-owned-port shape, which the
change-primitives catalogue classifies as Create (EXPAND), not Wrap.

## Verification

### Characterisation test

This delta's failing test is the negative of behaviour preservation: every
test currently in the suite continues to pass against the refactored
helpers, AND the new HD-002 integration tests (which CANNOT be written
today because the seam doesn't exist) become writable.

Concretely:

- **Pre-delta failing test:** `tests/integration/test_train_failure_paths.py`
  cannot be authored — the testbed's `FakeGHClient` has nowhere to plug in.
  Any attempt to construct a deterministic 3-WP train end-to-end test
  forces monkeypatching ten distinct helpers across two modules, and even
  then cannot represent "GitHub returns this for the merge endpoint, that
  for the compare endpoint" as a single coherent fake.
- **Post-delta passing tests:** (a) the existing 268 tests continue to
  pass without modification (behaviour preservation); (b) the new HD-002
  tests construct a `TrainTestbed(gh=FakeGHClient(...))` and drive
  `cmd_run` end-to-end through deterministic failure injections.

### Acceptance criteria

1. `GHClient` Protocol defined in `_wpxlib.py` with all methods needed by
   the helpers `_gh_check_runs`, `_gh_branch_sha`, `_gh_ref_sha`,
   `_gh_branch_already_merged`, `_gh_merge`, `_gh_deploy_runs`,
   `_gh_branch_exists`, `is_sha_on_branch`, plus `clone_repo_to_temp`'s
   gh-first path and `_merge_squash`'s remote-branch delete.
2. `RealGHClient` class implementing the Protocol; each method body is
   the existing `_run(["gh", ...])` invocation moved verbatim. No
   behaviour change.
3. Module-level `_default_gh_client: GHClient = RealGHClient()`. Existing
   helpers take `gh: GHClient | None = None`; on `None`, use the default.
4. All 268 existing tests pass without modification.
5. The `_gh_*` symbols remain importable as before (so
   `test_wpx_train_partial_merge_failure.py` style monkeypatching
   continues to work); the Protocol provides an *additional* seam, it
   doesn't replace the existing one.

## ADDED

- **`scripts/_wpxlib.py`:** new Protocol `GHClient` declaring nine
  abstract methods covering the GitHub-API surface in use; new concrete
  class `RealGHClient` implementing each method by delegating to `_run`;
  module-level singleton `_default_gh_client = RealGHClient()`.

## MODIFIED

- **`scripts/_wpxlib.py`:** every existing `_gh_*` helper plus
  `is_sha_on_branch`, `clone_repo_to_temp`, `_merge_squash` gain an
  optional `gh: GHClient | None = None` parameter. When unset, they
  delegate to `_default_gh_client`. The pre-existing positional/keyword
  signatures are preserved (extra parameter is the last keyword-only arg
  with a default), so every existing caller is source-compatible.

## REMOVED

- Nothing. Behaviour-preservation is the design constraint. No code paths
  are deleted; no callers need to change. The Protocol is purely additive.

## Trade-offs

- **+** Tests can now inject a single coherent `FakeGHClient`
  representing GitHub's behaviour for a given scenario, eliminating the
  ten-helper monkeypatch dance and enabling HD-002.
- **+** HD-001's merge-queue strategy dispatcher (Batch 5) can be unit-
  tested against a `FakeGHClient` that simulates MQ ejection, group CI
  outcomes, and per-PR `merge_commit_sha` reconciliation without GitHub
  network.
- **+** The Protocol documents in one place exactly which GitHub API
  surface the train depends on. Adding a tenth `gh api` invocation
  anywhere now goes through the Protocol — it can't be added silently.
- **−** Two seams exist for tests: the legacy per-helper monkeypatch
  (still works) and the new Protocol injection. The legacy seam is kept
  to preserve the existing 268 tests; new tests should prefer the
  Protocol. We accept the duplication as the cost of behaviour
  preservation.
- **−** `_default_gh_client` is module-level state. Tests that mutate it
  must restore it on teardown. The TrainTestbed fixture (HD-002) does
  this via pytest's `monkeypatch.setattr` which auto-restores.

## Rationale (boring-code check)

Every Protocol method takes explicit parameters; no implicit `self.repo`
or thread-locals. `RealGHClient` is stateless. The `_default_gh_client`
module variable is a singleton for convenience, not a registry; it never
mutates outside tests. No metaprogramming, no decorators, no
dynamic dispatch.
