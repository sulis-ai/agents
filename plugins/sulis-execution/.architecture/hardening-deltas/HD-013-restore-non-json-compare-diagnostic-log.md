---
id: HD-013
title: Restore lost diagnostic log for non-JSON / empty `gh compare` output
status: implemented
severity: MEDIUM
pillar: armor
source: code-review:PR-batch4-retro-2026-05-23T132739Z
lens: architecture + quality
sources:
  - Batch 4 retroactive code-review (2026-05-23) — behaviour-preservation regression in HD-005
created: 2026-05-23
implemented: 2026-05-23
implemented_in: v0.23.1 (same commit as the HD-013 draft import)
---

## Context

HD-005's `RealGHClient.compare()` consolidated the `gh api repos/{repo}/compare/{base}...{head}` shell-out from two sites (`_gh_branch_already_merged` and `is_sha_on_branch`). The HD's stated contract is "byte-for-byte identical behaviour" — and for the return-value path that holds. But the **observability path lost two diagnostic log messages** that existed pre-HD-005.

`is_sha_on_branch` (pre-HD-005), `scripts/_wpxlib.py`:

```python
try:
    data = json.loads(out)
except json.JSONDecodeError:
    _log(f"is_sha_on_branch: compare API returned non-JSON. out: {out!r}")
    return False
```

`_gh_branch_already_merged` (pre-HD-005), `scripts/_wpxlib.py`:

```python
try:
    data = json.loads(out)
except json.JSONDecodeError:
    _log(f"compare API returned non-JSON; falling through. out: {out!r}")
    return False, ""
```

Both logged the raw `out` on non-JSON, giving operators a clue when GitHub returned something unparseable (auth-expired HTML, rate-limit page, empty body, etc.).

Post-HD-005, `RealGHClient.compare()` at `scripts/_wpxlib.py:645-660` silently catches `JSONDecodeError` and the empty-output case and returns `{}`:

```python
if not out.strip():
    return {}
try:
    return json.loads(out)
except json.JSONDecodeError:
    # Defensive: pre-HD-005 callers ... handled non-JSON output by logging and
    # falling through. Preserve that shape so they keep working.
    return {}
```

The comment claims preservation, but only of the *return value*. The diagnostic log is gone. Callers receive an empty dict and reach `status.get("status", "") in (...)` which evaluates false — same downstream behaviour, but **no operator-visible trace of why**.

This matters because the original log was load-bearing for production debugging. The compare API is rare to fail with non-JSON, but when it does (token expiration during a long-running train, GitHub's outage HTML page, etc.), production logs now show `is_sha_on_branch returning False conservatively` for the `rc != 0` path and **nothing at all** for the non-JSON / empty path — meaning the operator sees `is_sha_on_branch == False` with no signal whether the API was unreachable, returned garbage, or returned a real "ahead" status.

The legacy `_gh_branch_already_merged` log message also lost the `(rc={rc})` exit-code annotation when its log was relocated into the wrapper's `RuntimeError` handler (the `RuntimeError` carries `err` but not `rc`).

## Decision

Restore the two lost log messages by adding `_log` calls inside `RealGHClient.compare()` for the empty-output and JSONDecodeError branches, with enough context (operation name + raw output preview) that operators can diagnose unparseable GitHub responses. Keep the return shape unchanged (`{}` for both cases).

## Verification

### Characterisation test

Add a test at `scripts/tests/unit/test_ghclient_protocol.py` that:

1. Constructs a `RealGHClient` instance.
2. Monkey-patches `_wpxlib._run` to return `(0, "not-json-content", "")`.
3. Captures `_log` calls via monkeypatch.
4. Asserts that calling `client.compare("owner/repo", "main", "branch")` returns `{}` AND emits a log entry containing `"compare API returned non-JSON"` and the offending output.

A parallel test for the empty-output case (`_run` returns `(0, "", "")`).

Both tests fail pre-delta (no log emitted) and pass post-delta.

## ADDED

- One `_log(...)` call in `RealGHClient.compare()` for the empty-output branch.
- One `_log(...)` call in `RealGHClient.compare()` for the `JSONDecodeError` branch, preserving the raw `out!r` preview.
- One restored `(rc=...)` annotation in the `_gh_branch_already_merged` log message (achievable by having `RealGHClient.compare()`'s `RuntimeError` carry the rc in its message, or by adding a separate `compare_with_rc` accessor; lowest-impact: include `rc` in the RuntimeError message string).

## MODIFIED

- `scripts/_wpxlib.py`: `RealGHClient.compare()` — three `_log` calls added, one RuntimeError message enriched.
- `scripts/tests/unit/test_ghclient_protocol.py`: two new tests for diagnostic log emission.

## REMOVED

- Nothing.

## Trade-offs

- **+** Restores observability lost in HD-005. Production debugging of compare-API anomalies recovers parity with pre-HD-005.
- **+** Tests pin the diagnostic-log contract, so future refactors can't silently drop it again.
- **−** Tiny LOC addition (~6 lines). Two extra `_log` calls per compare invocation in degenerate paths; negligible cost.
- **−** None substantive.

## Rationale (boring-code check)

`_log` is the existing module-level helper. No new abstractions, no metaprogramming, no dynamic dispatch. The fix is additive and surgical — restore three log statements that were dropped during the protocol extraction.
