---
id: HD-014
title: Remove dead `_CIConfig` / `_DeployConfig` state in `FakeGHClient` (or wire it up)
status: proposed
severity: LOW
pillar: proof
source: code-review:PR-batch4-retro-2026-05-23T132739Z
lens: quality
sources:
  - Batch 4 retroactive code-review (2026-05-23) — design inconsistency in FakeGHClient state surface
created: 2026-05-23
---

## Context

`scripts/tests/integration/testbed.py` defines `_CIConfig` (line 68-73) and `_DeployConfig` (line 76-81) dataclasses for the `FakeGHClient`'s CI and deploy verdict simulation. Each `FakeGHClient` instance holds `self.ci = _CIConfig()` and `self.deploy = _DeployConfig()` (line 112, 114) — these look like the configurable verdict knobs for the fake.

But:

- `FakeGHClient.check_runs()` (line 142-152) **never reads `self.ci.verdict`** — it always returns a green check-run regardless of the configured value.
- `TrainTestbed.fail_ci()` (line 441-454) sets `self.gh.ci.verdict = "failed"` AND monkeypatches `wpx._poll_ci` to return `"failed"`. The `_poll_ci` monkeypatch is what actually makes the test see CI red; the state mutation on `self.gh.ci` is dead.
- `TrainTestbed.fail_deploy()` / `timeout_deploy()` similarly set `self.gh.deploy.verdict` AND monkeypatch `wpx._poll_deploy`. The `deploy_runs` method on `FakeGHClient` *does* honour `self.deploy.verdict`, but in practice every test reaches deploy through `_poll_deploy` which is monkeypatched — so the `deploy_runs` path is unreachable in the integration tests as written.

The result: `FakeGHClient`'s public state surface (`self.ci`, `self.deploy`) advertises a configurable verdict that callers cannot actually control through the fake alone — they must additionally monkeypatch the polling helpers. This is invisible to a reader of `FakeGHClient` who, seeing `self.ci.verdict`, would reasonably expect mutating it to change what `check_runs` returns.

A second consequence: if a future test writer naively does `testbed.gh.ci.verdict = "failed"` (skipping `testbed.fail_ci()`), the test will silently see green CI — a confusing, hard-to-diagnose false positive.

A third consequence: the `strict_ci=True` eligibility path routes through `_gh_branch_ci_green` → `_gh_check_runs` → `FakeGHClient.check_runs` → **always green**. A future test that exercises `strict_ci=True` with `fail_ci()` would have eligibility see green while `_poll_ci` returns failed — the two would disagree.

## Decision

Two options. Pick one, document in HD-002 trade-offs:

**Option A (lower-effort, ship now):** Delete `_CIConfig` and `_DeployConfig` and their `self.ci` / `self.deploy` fields. Make `FakeGHClient.check_runs()` accept a `verdict` parameter on construction, or expose explicit `set_check_runs_response(verdict)` / `set_deploy_runs_response(verdict)` methods that mutate the response shape directly. Remove the dead state mutation from `fail_ci`/`fail_deploy`/`timeout_*` methods.

**Option B (higher-effort, more honest fake):** Make `FakeGHClient.check_runs()` actually read `self.ci.verdict` and return failed/empty check-runs accordingly. Remove the `_poll_ci` monkeypatch from `fail_ci`/`timeout_ci` and let the production `_poll_ci` poll the fake. The fake's `poll_count_before_resolve` field becomes meaningful (controlling how many calls before the verdict materialises). This brings the test closer to exercising real `_poll_ci` logic but adds complexity (needs to simulate poll-timing without `time.sleep`).

Recommendation: **Option A**. The pure-stub approach is faster, simpler, and matches what HD-002 actually does today; the `_CIConfig`/`_DeployConfig` machinery is aspirational state that was never wired through. Removing it makes the fake's contract honest. Option B is a separate concern (closer-to-reality fake) and deserves its own delta if pursued.

## Verification

### Characterisation test

A test in `scripts/tests/unit/test_ghclient_protocol.py` or alongside `testbed.py`:

```python
def test_fake_gh_client_check_runs_ignores_ci_verdict_state():
    """Pre-HD-014: setting self.ci.verdict="failed" has no effect on check_runs."""
    fake = FakeGHClient(bare_repo=...)
    fake.ci.verdict = "failed"
    result = fake.check_runs("owner/repo", "branch")
    # Pre-HD-014: result is green (assertion is the bug — confirms dead state).
    # Post-HD-014: either the field doesn't exist, or check_runs returns red.
    ...
```

Post-HD-014 (Option A): the test asserts `_CIConfig` is no longer importable and `FakeGHClient` has no `.ci` / `.deploy` attribute.

Post-HD-014 (Option B): the test asserts `check_runs` returns the failed verdict when `self.ci.verdict == "failed"`.

## ADDED

- None (Option A) / one `check_runs` branch reading `self.ci.verdict` (Option B).

## MODIFIED

- `scripts/tests/integration/testbed.py`: remove `_CIConfig`, `_DeployConfig`, `self.ci`, `self.deploy` (Option A) OR wire through (Option B). Update `fail_ci`, `fail_deploy`, `timeout_ci`, `timeout_deploy` to drop the dead state mutation.
- `scripts/tests/unit/test_ghclient_protocol.py`: pin the corrected contract.

## REMOVED

- `_CIConfig` and `_DeployConfig` dataclasses (Option A only).

## Trade-offs

- **+** Removes a foot-gun for future test authors who would naively mutate `testbed.gh.ci.verdict` expecting it to take effect.
- **+** Eliminates the `strict_ci=True` + `fail_ci()` divergence latent bug.
- **+** The fake's surface area matches what it actually models (Option A).
- **−** Option A makes the fake slightly less "realistic-looking" — but realism that doesn't function is worse than a smaller, honest API.
- **−** Trivial code churn (~30 lines deleted, Option A).

## Rationale (boring-code check)

Deleting dead state is the most boring possible fix. No abstractions added; no metaprogramming; the surviving FakeGHClient is a smaller, more direct mapping from method-call to fake-response. Option A in particular reduces code; Option B adds a clearly-bounded path.
