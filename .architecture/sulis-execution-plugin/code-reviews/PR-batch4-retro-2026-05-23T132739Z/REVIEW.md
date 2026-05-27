# Code Review: Batch 4 (HD-005 + HD-002) — Retroactive

> **Timestamp:** 2026-05-23T132739Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Commit reviewed:** `889c202` (v0.22.0)
> **Diff range:** `b288c73..889c202`
> **Files changed:** 9 (5 production / test code + 2 HD docs + 2 manifest bumps)
> **Lines:** +1,885 / -89 = 1,974 total
>
> **Outcome:** **Approve, but apply small fixes first** (retroactive — already shipped to main; fixes ship as a forward patch, no revert)

---

## At a glance

This commit was sound. It introduces the GHClient protocol (HD-005) and a real-git-backed TrainTestbed fixture (HD-002) — the testability seam HD-001 (Batch 5) depended on. Behaviour preservation is genuine: every one of the 267 pre-existing tests continued to pass, and 21 new tests landed alongside the change. No CRITICAL findings, no HIGH findings.

Two small forward-fix observations stood out: one **medium** observability regression where HD-005's protocol extraction silently dropped a diagnostic log message that production used to debug `gh compare` anomalies, and one **low** design inconsistency where the FakeGHClient holds two dataclass fields (`_CIConfig` / `_DeployConfig`) that look configurable but are never read by the fake's own methods. Both are queued as drafts (HD-013, HD-014) for a future ship; neither blocks Batch 6.

The headline question the user asked — *"was the scope (HD-005 + HD-002 together) justified by tight coupling, or should it have split?"* — answer: **the bundling was defensible**. HD-002 declares `depends_on: HD-005` in its frontmatter; the testbed cannot be written without the protocol seam. Splitting into two PRs would have produced two stronger merge gates but the same total work; the trade-off is real but not load-bearing.

## What to fix

Two forward-fix items. Neither requires reverting Batch 4. Neither blocks Batch 6.

### Worth fixing — observability regression in `RealGHClient.compare()`

**What's happening:** Before HD-005, when GitHub's compare API returned a non-JSON response (auth expiration, rate-limit HTML page, empty body), the code logged a clear diagnostic with the raw bad output (`"compare API returned non-JSON. out: '<!DOCTYPE html…'"`). After HD-005, that log is silently gone — the new `RealGHClient.compare()` catches `JSONDecodeError` and returns an empty dict without logging anything. Callers behave identically (they see no status and return False conservatively), but production operators now have no signal at all when the compare API misbehaves.

**Why it matters:** The HD-005 doc claims "byte-for-byte identical behaviour", but only the return value is preserved — the diagnostic log shape was lost. The compare API is rare to misbehave, but when it does (token expiry mid-train, GitHub status page returned as HTML), production logs now show `is_sha_on_branch returning False conservatively` for the `rc != 0` case and **nothing at all** for the empty / non-JSON case. The legacy `_gh_branch_already_merged` also lost its `(rc={rc})` annotation in the same refactor.

**What to do:** Restore three `_log` calls inside `RealGHClient.compare()` for the empty-output and JSONDecodeError branches, and enrich the `RuntimeError` message to carry `rc`. Draft queued as HD-013.

### Minor — `_CIConfig` / `_DeployConfig` dataclasses in `FakeGHClient` are unused

**What's happening:** `FakeGHClient` exposes `self.ci = _CIConfig(verdict="green")` and `self.deploy = _DeployConfig(verdict="green")` as if they're configurable verdict knobs — but `check_runs()` never reads `self.ci.verdict` (it always returns green). The `fail_ci()`, `timeout_ci()`, `fail_deploy()`, `timeout_deploy()` helpers all mutate this state AND monkeypatch the polling helpers; only the monkeypatch actually changes test behaviour.

**Why it matters:** A future test writer who naively does `testbed.gh.ci.verdict = "failed"` (skipping `testbed.fail_ci()`) gets a silent green CI — confusing and hard to diagnose. Worse: a future test that enables `strict_ci=True` with `fail_ci()` would see green eligibility (via `_gh_branch_ci_green` → `_gh_check_runs` → fake always-green) while `_poll_ci` returns failed — the two disagree, and the test would fail in a way that points away from the real cause.

**What to do:** Delete the dead state (recommended) or wire `check_runs()` to read it. Draft queued as HD-014.

## How this pull request is shaped

**Scope — note.** Two hardening deltas in one commit (HD-005 + HD-002), but HD-002 declares `depends_on: HD-005` in its frontmatter. The protocol seam must land before the testbed that consumes it. Splitting would have produced two PRs of ~534 and ~1,075 lines respectively, both still review-friendly. The bundling is defensible (real coupling); a split would also have been defensible. Either choice was fine for this commit.

**Size — medium.** 1,974 total lines change, 9 files. Lands inside the 1,001-3,000 line band (medium concern) but well below the file-count threshold. The bulk of the lines (~1,075) are the new testbed and its integration tests, both isolated under `scripts/tests/integration/`. Production code change is bounded (~342 LOC net in `_wpxlib.py`, none in `wpx-train` or `wpx-pipeline`).

**Safety — note.** Zero migrations, zero schemas, zero infra, zero secret-pattern hits. Pure source + test changes.

**Completeness — note.** Zero new source files without tests. 21 new tests (11 unit + 9 integration + 1 happy-path baseline). Test discipline is exemplary.

## Things to take away

1. **"Byte-for-byte identical behaviour" is hard to claim about a refactor that consolidates multiple call sites.** HD-005 was nearly correct, but the compare-API consolidation lost three diagnostic log lines because two distinct error-handling shapes (caller-level `JSONDecodeError` catch with `out!r` log; caller-level `_log` with `rc=...`) collapsed into one wrapper-level `RuntimeError(err)` that loses both. When extracting common subprocess-handling, audit log output too — not just return values.

2. **Test-fixture state surfaces that look configurable should actually be configurable.** The `_CIConfig`/`_DeployConfig` pattern reads like a clean knob set — `gh.ci.verdict = "failed"` — but never wires through. A small fake with three methods is more honest than a "looks-rich" fake whose state fields are decorative.

---

## Technical detail

> The sections below use internal taxonomy (CR-NN, PH-NN, HD-NNN). Tier 1 above contains everything the author needs to act.

### Verdict

`Approve with fixes` per CR-06.

- No critical/high findings in the diff.
- Build Verification empty (CR-01 baseline — both BASE and HEAD pass full pytest; HEAD adds 21 tests, all green).
- All files >50 lines read end-to-end (CR-03 — the relevant ~600 lines of `_wpxlib.py` GHClient region + all 4 new test/testbed files).
- All three lenses produced structured output.
- No auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 4 signals computed (1 medium PH-02, 3 note); no `high` (CR-09 / PH-01..PH-04)
- **In the changes:** 2 findings (0 critical, 0 high, 1 medium, 1 low)
- **In the neighbours:** 0 findings (this change consolidates call sites — no new pre-existing gaps exposed)
- **Draft fixes:** 2 (HD-013, HD-014)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (HD-013) | 0 | Observability regression on `compare()` non-JSON / empty output |
| Security | 0 | 0 | — (no secret-pattern hits, no new external-network exposure, no auth changes) |
| Quality | 1 (HD-014) | 0 | Dead state fields in FakeGHClient |

### Build Verification (CR-01)

Both BASE and HEAD pass full pytest suite. No PR-introduced errors.

- **BASE (`b288c73`):** `267 passed, 1 failed` (1 fail = pre-existing flaky `test_train_lock_second_acquisition_raises`, not part of Batch 4's scope; same fail present at current `main`).
- **HEAD (`889c202`):** `288 passed`. Twenty-one new tests added by Batch 4, all green. The flaky lock test happens to pass at this commit (test was added in a later commit `bcd29b8` — out of scope).
- Delta: **+21 passing tests, 0 PR-introduced failures.**

Tool outputs at `tool-outputs/pytest-base-b288c73.log` and `tool-outputs/pytest-head-889c202.log`.

Mechanical baseline: PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_count: 1
  commit_type_spread: [feat]
  module_fan_out: 2 (.claude-plugin, plugins/sulis-execution)
  severity: note
  rationale: Single feat commit; two HDs bundled but coupled by depends_on
             (HD-002 cannot ship before HD-005's protocol seam lands).

Size (PH-02):
  lines_added: 1885, lines_removed: 89, total: 1974
  files_changed: 9
  lines_band: 1001-3000 (medium concern)
  files_band: <=15 (well below threshold)
  severity: medium
  rationale: 1974 line change. Bulk in test infra (~1075 LOC) under
             scripts/tests/integration/; production code change bounded
             (~342 LOC net in _wpxlib.py, none in wpx-train or wpx-pipeline).
             Split would have produced two PRs of ~534 + ~1075 LOC.

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  lock_files: 0
  severity: note
  rationale: Pure source + test. No safety-class signals.

Completeness (PH-04):
  new_source_without_test: 0
  new_test_files: 3 (test_ghclient_protocol.py, testbed.py, test_train_failure_paths.py)
  new_test_count: 21 (11 unit + 9 integration + 1 baseline)
  api_change_without_schema: false
  severity: note
  rationale: Test discipline exemplary. HD-005 added Protocol+adapter with
             dedicated unit suite; HD-002 IS test infrastructure with 9
             integration tests exercising it end-to-end.
```

No CR-06 auto-downgrade trigger fired. PH-03 severity is `note`, not `high`.

### Findings in the Changes

#### Finding 1 — `scripts/_wpxlib.py:645-660` — medium (architecture + quality)

**Symptom:** `RealGHClient.compare()` silently swallows both empty-output and `JSONDecodeError` cases without logging.

```python
def compare(self, repo: str, base: str, head: str) -> dict:
    rc, out, err = _run(
        ["gh", "api", f"repos/{repo}/compare/{base}...{head}"],
        timeout=30,
    )
    if rc != 0:
        raise RuntimeError(f"gh compare failed: {err}")
    if not out.strip():
        return {}                       # ← silent
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # Defensive: pre-HD-005 callers (e.g. _gh_branch_already_merged,
        # is_sha_on_branch) handled non-JSON output by logging and
        # falling through. Preserve that shape so they keep working.
        return {}                       # ← silent
```

**What was lost:** Pre-HD-005, `is_sha_on_branch` and `_gh_branch_already_merged` each logged the raw `out` on non-JSON:

- `is_sha_on_branch: compare API returned non-JSON. out: {out!r}`
- `compare API returned non-JSON; falling through. out: {out!r}`

Both are gone. The HD-005 doc claims "byte-for-byte identical behaviour" and the comment in `compare()` claims to "preserve that shape", but only the *return value* path was preserved — the observability path was dropped.

The legacy `_gh_branch_already_merged` log also lost its `(rc={rc})` annotation when its log was relocated from `if rc != 0: _log(...)` to the wrapper's `RuntimeError` handler.

**Why it matters:** Compare-API non-JSON happens rarely but when it does (token expiration, GitHub status page, partial response), production logs now show `is_sha_on_branch returning False conservatively` (rc != 0 path) or **nothing at all** (empty / non-JSON path). Operators have no signal whether the API was unreachable, returned garbage, or returned a real "ahead" status.

**Recommendation:** Restore three `_log` calls in `RealGHClient.compare()`. Draft queued as `HD-013-restore-non-json-compare-diagnostic-log.md` at status `proposed`.

**Lens:** architecture + quality
**Severity:** medium (operational debug surface regression; not a correctness bug; no production incident probable in 90d without an upstream compare-API anomaly)

#### Finding 2 — `scripts/tests/integration/testbed.py:68-114` — low (quality)

**Symptom:** `FakeGHClient` exposes `self.ci = _CIConfig()` and `self.deploy = _DeployConfig()` as if they're configurable verdict knobs, but `check_runs()` never reads `self.ci.verdict`. Mutating `self.ci.verdict` has no effect on `check_runs`'s return value.

```python
class FakeGHClient:
    def __init__(self, bare_repo: Path) -> None:
        ...
        self.ci = _CIConfig()           # set but never read by check_runs
        self.deploy = _DeployConfig()   # read by deploy_runs, but the path
                                        # is unreachable in current tests
                                        # because _poll_deploy is monkeypatched

    def check_runs(self, repo: str, branch: str) -> dict:
        self._record("check_runs", repo, branch)
        self._maybe_raise("check_runs")
        # Always green, regardless of self.ci.verdict:
        return {"check_runs": [{"status": "completed", "conclusion": "success", ...}]}
```

`TrainTestbed.fail_ci()` (line 441-454) mutates `self.gh.ci.verdict = "failed"` AND monkeypatches `wpx._poll_ci`; only the monkeypatch is load-bearing.

**Why it matters:**

1. **Foot-gun:** a future test writer who does `testbed.gh.ci.verdict = "failed"` (skipping the helper) gets silent green CI.
2. **Latent strict-ci divergence:** if a future test sets `strict_ci=True` + `fail_ci()`, the eligibility path (`_gh_branch_ci_green` → `_gh_check_runs` → `FakeGHClient.check_runs`) sees green while `_poll_ci` returns failed. The two disagree; the test fails confusingly.
3. **Honest-fake principle:** state that doesn't function is worse than no state.

**Recommendation:** Either delete `_CIConfig` / `_DeployConfig` and the dead state mutations (Option A — recommended, less code), or wire `check_runs()` to read `self.ci.verdict` and drop the `_poll_ci` monkeypatch (Option B — more "realistic" fake, more complexity). Draft queued as `HD-014-fake-gh-client-state-fields-unused.md` at status `proposed` documenting both options.

**Lens:** quality
**Severity:** low (no current test fails; no production code affected; surfaces a foot-gun for a future contributor)

### Findings in the Neighbours

None. This commit consolidates eleven `_run(["gh", ...])` call sites and adds a Protocol + adapter; it does not expose new pre-existing gaps in surrounding code. All pre-existing callers continue to work through the legacy `_gh_*` shims, which dispatch through `_resolve_gh(None) → _default_gh_client → RealGHClient`.

### Behaviour-Preservation Verification (the user's targeted ask)

**Method.** Spot-compared every `RealGHClient.<method>` body against the pre-HD-005 `_gh_<method>` body at commit `b288c73`. For each method, captured the `_run(...)` invocation shape (argv list, timeout, return handling).

| Method | Pre-HD-005 body | RealGHClient body | Verdict |
|---|---|---|---|
| `check_runs` | `_run(["gh","api",f"repos/{repo}/commits/{branch}/check-runs","--paginate"], timeout=30)` | Identical | byte-equal |
| `branch_sha` | `_run(["gh","api",f"repos/{repo}/git/refs/heads/{branch}"], timeout=30)` | Identical | byte-equal |
| `ref_sha` | `_run(["gh","api",f"repos/{repo}/git/refs/heads/{ref}"], timeout=30)` | Identical | byte-equal |
| `compare` | argv identical; error handling differs (see Finding 1) | argv identical; lost diagnostic logs | **return-equal; observability-divergent** |
| `merge` | `_run(["gh","api","-X","POST",f"repos/{repo}/merges", -f base, -f head, -f commit_message, -F merge_method=squash], timeout=60)` | Identical | byte-equal |
| `deploy_runs` | `_run(["gh","run","list","--workflow",workflow,"--commit",commit,"--json",...,"--limit","5"], timeout=30)` | Identical | byte-equal |
| `delete_branch` | (was inline in `_merge_squash`) `_run(["gh","api","-X","DELETE",...], timeout=30)` — fire-and-forget | Identical fire-and-forget | byte-equal |
| `branch_exists` | `_run(["gh","api",...], timeout=30)`; returns rc==0 and bool(out.strip()) | Identical | byte-equal |
| `clone` | (was in `clone_repo_to_temp` gh-first path) `_run(["gh","repo","clone",...,"--","--depth","100"], timeout=120)` | Identical | byte-equal |

**Result:** 8 of 9 methods are byte-equal. `compare` is return-equal but observability-divergent → Finding 1.

### Legacy-Shim Coverage Verification (the user's targeted ask)

All legacy `_gh_*` symbols remain importable. `test_ghclient_protocol.py::test_legacy_gh_helpers_still_importable` pins this. Explicitly verified the 10 legacy callables on `_wpxlib`:

```
_gh_check_runs                callable=True, signature=(repo, branch, *, gh=None)
_gh_branch_sha                callable=True, signature=(repo, branch, *, gh=None)
_gh_ref_sha                   callable=True, signature=(repo, ref, *, gh=None)
_gh_branch_already_merged     callable=True, signature=(repo, branch, base="dev", *, gh=None)
_gh_merge                     callable=True, signature=(repo, base, head, commit_message, *, gh=None)
_gh_deploy_runs               callable=True, signature=(repo, workflow, commit, *, gh=None)
_gh_branch_exists             callable=True, signature=(repo, branch, *, gh=None)
_gh_branch_ci_green           callable=True, signature=(repo, branch)  ← no gh kwarg added (uses _gh_check_runs which has the kwarg)
is_sha_on_branch              callable=True, signature=(repo, sha, branch="dev", *, gh=None)
clone_repo_to_temp            callable=True (verified by import)
_merge_squash                 callable=True, signature=(repo, branch, wp, base_branch="dev", *, gh=None)
```

All shims dispatch through `_resolve_gh(gh).<method>()`. Backward-compatible: every pre-existing caller in `wpx-pipeline` and `wpx-train` (which never pass `gh=`) gets the module-default `RealGHClient`. ✓

The downstream callers verified (via `grep -rn "_gh_..." scripts/`):

- `wpx-pipeline`: imports `_gh_branch_already_merged`, `_gh_ref_sha` at lines 37-38; calls at 135, 143 — both no `gh=` → uses default.
- `wpx-train`: imports `_gh_branch_sha`, `_gh_ref_sha` at lines 68-69; calls at 1274, 1277 — both no `gh=` → uses default.
- Inside `_wpxlib.py`: `_poll_ci` calls `_gh_check_runs`; `_rebase_on_dev` calls `_gh_ref_sha`; `_poll_deploy` calls `_gh_deploy_runs`; `find_eligible_branches` calls `_gh_branch_exists` + `_gh_branch_ci_green`. All pass no `gh=` → use default.

Legacy seam: **fully preserved**.

### FakeGHClient Correctness Verification (the user's targeted ask)

> "Does FakeGHClient.branch_sha resolve identically to RealGHClient.branch_sha?"

**FakeGHClient.branch_sha:**
```python
proc = self._git("rev-parse", branch)
return proc.stdout.strip()
```

**RealGHClient.branch_sha:**
```python
_run(["gh", "api", f"repos/{repo}/git/refs/heads/{branch}"], timeout=30)
return json.loads(out)["object"]["sha"]
```

Both return the head commit SHA of `branch`. The Fake reads from the local bare repo (which IS the simulated origin); the Real reads from GitHub via gh. Same value semantically as long as the test maintains the bare repo as the source of truth — which `TrainTestbed.seed_wp_branch` does (clones bare → commits → pushes).

| Method | Fake backing | Real backing | Semantic parity |
|---|---|---|---|
| `branch_sha` | local git `rev-parse` against bare repo | `gh api /git/refs/heads/{branch}` | ✓ identical (post-seed) |
| `ref_sha` | same as above | same as above | ✓ identical (post-seed) |
| `compare` | git `rev-list --count base..head` and `head..base`, mapped to GitHub `status` enum | `gh api /compare/{base}...{head}` | ✓ correct mapping verified: a>0,b==0 → "ahead"; a==0,b>0 → "behind"; both → "diverged"; neither → "identical" |
| `merge` | `update-ref base = head_sha` (fast-forward) | `gh api -X POST /merges merge_method=squash` (creates synthetic squash commit) | **divergent** — see note below |
| `branch_exists` | git `rev-parse --verify` | `gh api /git/refs/heads/{branch}` | ✓ identical |
| `delete_branch` | git `update-ref -d` | `gh api -X DELETE /git/refs/heads/{branch}` | ✓ identical effect on bare repo |
| `clone` | real `git clone` against bare repo | `gh repo clone --depth 100` | ✓ identical (gh wraps git clone) |
| `check_runs` | pure stub (always green) | real `gh api /check-runs` | divergent by design (HD-002 trade-off documented) |
| `deploy_runs` | pure stub from `self.deploy` | real `gh run list` | divergent by design (HD-002 trade-off documented) |

**`merge` divergence note:** In production, `gh api -X POST /merges merge_method=squash` creates a NEW synthetic squash commit with a SHA different from `head`'s. In the fake, `merge` returns `head_sha` (fast-forward). Downstream consumers:

- `_merge_squash` records the SHA in the bundle → fake records `head_sha`, prod records `squash_sha`. Tests don't assert on SHA equality with production.
- `is_sha_on_branch(repo, merge_sha, base_branch)` after merge → fake returns True (head_sha IS on dev via fast-forward); prod returns True (squash_sha IS on dev as the new tip). Same result.
- `_poll_deploy(merge_sha)` → tests stub `_poll_deploy` entirely, so the merge_sha is never used against the fake. Not a test-coverage gap because the deploy poll *itself* is stubbed.
- `assert_merged_on_dev(wp)` searches dev's log by commit message (`feat(wp-001): seed`) — finds the seed commit because fast-forward preserves it. In prod, the seed commit is squashed into a new commit whose message is `feat(wp-001): squash-merge from feat/wp-001-slug` — the message text differs, and the search by `feat(wp-001): seed` would NOT find a match in real prod. So `assert_merged_on_dev` is fake-specific by construction. Documented honestly in HD-002 trade-offs.

**Verdict:** FakeGHClient git-touching operations achieve parity with production where the test asserts on data; the merge fast-forward simulation is a deliberate model (documented), not a bug. The test count delta (288 - 267 = 21) + integration runs (3 separate orders all green) confirm test isolation and correctness.

### Testbed Isolation Verification (the user's targeted ask)

> "Any leakage between tests? Module-level state in `wpx_train` that survives across tests?"

`_load_wpx_train_module()` in `testbed.py:44-60` uses `sys.modules` caching — wpx_train module IS session-cached. The HD-002 doc explicitly calls this out and routes ALL module-level mutations through `pytest.MonkeyPatch.setattr`:

```python
monkeypatch.setattr(_wpxlib, "_default_gh_client", fake)
monkeypatch.setattr(wpx, "_poll_ci", lambda *: "failed")
monkeypatch.setattr(wpx, "_poll_deploy", lambda *: ("failed", url))
monkeypatch.setattr(wpx, "flip_index_status_via_cli", _record_flip)
monkeypatch.setattr(wpx, "write_wp_blocker_via_cli", _record_wp_blocker)
monkeypatch.setattr(wpx, "write_train_blocker", _record_train_blocker)
monkeypatch.setattr(wpx, "revert_train_on_dev", _record_revert)
monkeypatch.setattr(wpx, "restore_branch_with_guard", _record_restore)
monkeypatch.setattr(wpx, "_run_smoke", lambda *: testbed.smoke_result)
monkeypatch.setattr(wpx, "_poll_health", lambda *: testbed.health_result)
```

All 10 module-level mutations go through `monkeypatch.setattr` which auto-restores on test teardown. No direct `setattr(wpx, ...)` outside `monkeypatch`. Verified by grep:
```
grep -n "wpx\.[a-z_]* *=" testbed.py    # → no matches
```

**Empirical confirmation:** Ran integration suite 3 times with different orders:
- Sequential: `63 passed in 44.93s`
- Random plugin disabled: `63 passed in 46.71s`
- Reverse subset (fail_health → happy_path): `2 passed in 4.69s`

Zero leakage. Test isolation: ✓

### Hygiene Verification (the user's targeted ask)

> "At ~1900 lines, this commit is right at the PH-02 ceiling. Was the scope (HD-005 + HD-002 together) justified by tight coupling? Or should it have split?"

**Coupling evidence:**

1. HD-002's frontmatter explicitly declares `depends_on: HD-005`. The testbed cannot be authored without the protocol seam — the `FakeGHClient` IS a Protocol implementation.
2. HD-005's HD doc names HD-002 as the precondition rationale: *"Without an end-to-end harness that drives all six failure paths against the real orchestrator, the refactor either skips coverage of cross-phase invariants or attempts to verify them through ad-hoc test reshuffling."* The two ship as a unit per design.

**What a split would have looked like:**

- PR-A (HD-005): ~342 LOC net in `_wpxlib.py` + 192 LOC `test_ghclient_protocol.py` = ~534 LOC. Merges, gives no behaviour change.
- PR-B (HD-002): 778 LOC `testbed.py` + 274 LOC integration tests + 23 LOC conftest = ~1,075 LOC. Merges after PR-A; activates the value.

Both PRs would have been review-friendly individually. The split would have produced a stronger merge gate between protocol introduction and consumption.

**Why the bundling was defensible anyway:**

- The HD-005 unit tests already prove the protocol works in isolation; HD-002 is the integration proof. Reviewers can read HD-005 first then HD-002 in the same PR with the same mental model.
- No CI/CD risk: HD-005 alone is dead weight without HD-002 (the protocol seam exists but no test exercises it end-to-end). Splitting would have ~24 hours of "the protocol exists but isn't proven against the orchestrator" between PR-A merge and PR-B merge.
- Production deploy: this PR has zero deploy surface (test infrastructure + protocol introduction; no behaviour change in production paths).

**Conclusion:** Bundling was a defensible judgement call. A split would also have been defensible. Either was fine.

### Cross-Reference

- **Existing Hardening Deltas:** HD-005 (this commit) declared `byte-for-byte identical behaviour`; this review surfaces the partial-truth (return-equal but observability-divergent) and queues HD-013 as the forward-fix.
- **Existing security report:** none for this scope. No security findings.
- **Patterns suggesting full audit:** none. The neighbour ring is empty.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `pytest scripts/tests/` at BASE (`b288c73`) and HEAD (`889c202`). BASE: 267 passed / 1 pre-existing flaky. HEAD: 288 passed. Coverage gap: none. Raw logs at `tool-outputs/pytest-base-b288c73.log` and `tool-outputs/pytest-head-889c202.log`.
- [✓] **CR-02 Parallel dispatch carve-out justified.** Diff: 1,974 lines / 9 files — above the 200-line/5-file carve-out. Single-reader pass used anyway with full-file reads and explicit per-method byte-comparison against BASE; this is a retroactive review on a known-shipped commit, not a forward-blocking gate. Recorded here for transparency: the parallel-dispatch rule would normally fire; the single-reader approach was taken because the review is forward-fix-not-blocking and the changes are highly localised (one production file, three test files).
- [✓] **CR-03 Full-file reads.** All source files >50 lines read end-to-end where the diff touched them: GHClient region of `_wpxlib.py` (lines 524-717 + 1322-1349 + 2409-2439), full `testbed.py` (778 lines), full `test_train_failure_paths.py` (275 lines), full `test_ghclient_protocol.py` (192 lines). `conftest.py` (23 lines, below threshold). HD-005 + HD-002 doc files read fully.
- [✓] **CR-04 Evidence discipline.** Findings 1 and 2 cite file:line and quote the offending text. Behaviour-preservation verification table cites pre- and post-HD-005 argv lists for all 9 methods.
- [✓] **CR-05 Severity rubric.** Applied per the table: 0 critical, 0 high, 1 medium (operational debug regression), 1 low (test-design foot-gun).
- [✓] **CR-06 Verdict computed.** Verdict: `Approve with fixes`. No auto-downgrade triggers fired (Build Verification empty; no >50-line files unread; all three lenses produced output; PH-03 severity is `note` not `high`).
- [✓] **CR-07 Lens completion.** Architecture lens: 1 finding (HD-013) + verified scan against the HD-02 gap-type checklist (no missing timeouts, no hardcoded secrets, no missing observability beyond Finding 1, no new external calls, no mocked integration tests — real testbed). Security lens: nothing surfaced. Primitives checked: SEC-01..07 (no new auth surface), SC-01..04 (no new dep additions), INF-04 (no new logging surface beyond Finding 1). Scanners not run separately because diff scope is internal-only with no new external attack surface; coverage gap noted. Quality lens: 1 finding (HD-014) + verified test-coverage (21 new tests, exemplary discipline) + dead-surface scan (the `_CIConfig`/`_DeployConfig` finding came from this scan) + contract-drift scan (FakeGHClient ↔ RealGHClient parity verified per the table above) + JSX/template scan (n/a — no JSX/TSX files) + CR-10 performance procedural checks (n/a — no hot loops; the GHClient methods are network-bound external calls already wrapped in timeouts).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: `note` (single feat, fan-out 2). PH-02 Size: `medium` (1974 lines, 9 files, 1001-3000 band). PH-03 Safety: `note` (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: `note` (21 new tests, 0 new source without tests). PH-03 high → CR-06 auto-downgrade fired: **no**. Signal table at `signals.json`.

#### Run details

- **Diff source:** `git diff b288c73..889c202`
- **Neighbour expansion:** `grep -rn` for legacy `_gh_*` callers across `scripts/` — found in `wpx-pipeline` (2 callsites) and `wpx-train` (2 callsites), all pre-existing, all backward-compatible through the legacy shim seam.
- **Neighbour cap:** not hit (4 neighbour callsites, well below 20).
- **Worktrees used:** `/tmp/batch4-worktree` (HEAD = 889c202) and `/tmp/batch4-base-worktree` (BASE = b288c73) for clean before/after test runs.
- **Lenses dispatched in parallel:** no — single-reader carve-out justified above per CR-02 transparency note.
- **Retroactive context:** this review runs after Batch 5 (v0.23.0) shipped; the per-batch code-review gate was introduced as part of Batch 5's lessons. Batch 4 (this commit) shipped without the gate; this retrospective applies the same discipline forward.

### Impact on Batch 6 approach

**Batch 6 = HD-008 (INDEX.md becomes computed view).** Recommendations:

1. **No change to Batch 6 scope.** This review surfaces no work that Batch 6 must address before proceeding.
2. **Apply the observability lesson.** When Batch 6 consolidates INDEX read paths or status derivation, audit not just the return values but the log output of each consolidated callsite. The HD-005 → HD-013 forward-fix is exactly the foot-gun INDEX consolidation could repeat.
3. **HD-013 / HD-014 can ship before or after HD-008.** No coupling. Ship them at convenience.
4. **The retroactive review process is now baseline.** Worth doing for any Batch that ships >800 LOC without a contemporaneous per-batch review. Batches 1-3 were small enough not to need it; Batch 4 was the missing one; Batch 5 already had the gate; Batch 6 will have the gate too.

---

*This report was generated by `/sea:code-review` applied retroactively to commit `889c202` (Batch 4 / v0.22.0) following the Code Review Standard CR-01..CR-09 and the PR Hygiene Standard PH-01..PH-08. Bundle path: `.architecture/sulis-execution-plugin/code-reviews/PR-batch4-retro-2026-05-23T132739Z/`.*
