---
id: HD-001
slug: preflight-ci-conclusion-helper
title: Add a non-polling pre-flight CI-conclusion read returning (verdict, failed_check_names)
status: proposed
severity: medium
pillar: armor
gap_type: observability
source: srd:lesson-52
change: CH-01KSQB
primitive: Create
group: expand
depends_on: []
blocks: [HD-002]
files:
  - plugins/sulis/scripts/_wpxlib.py
  - plugins/sulis/scripts/tests/unit/test_wpxlib_preflight_ci.py
---

## Gap

`_poll_ci(repo, branch, interval, cap)` (`_wpxlib.py:1196`) is the only path that
reads CI for a branch HEAD. It serves the train's needs — **wait** for in-flight
runs to complete, then return a single verdict string `'green'|'failed'|'timeout'`.
Two properties make it the wrong tool for a pre-flight read:

1. **It polls.** A pre-flight wants the *current* recorded conclusion of the
   latest completed run for `dev` HEAD, with no wait. `_poll_ci` enters a
   `time.sleep(interval)` loop bounded by `cap` (up to `CI_DEFAULT_CAP`).
2. **It discards the failed set.** At `_wpxlib.py:1212` it computes
   `failed = [s for s in statuses if s[2] not in (...)]`, logs it, and then
   returns only the verdict string. The pre-flight blocker needs the **count
   and names** to say "dev has N pre-existing CI failures — fix these first".

The CI reader underneath (`_gh_check_runs` → `GHClient.check_runs`,
`_wpxlib.py:1120` / `:996`) is correct and faithful: GitHub already ran the real
workflow (build/prepare order and all), and it reads each run's `conclusion`
**explicitly** (satisfies lesson #59 — never a chained exit code). The gap is a
missing thin helper over that reader, not a new CI-reading mechanism.

## Why it matters (faithful reproduction, build order included)

The spec's hardest constraint: the pre-flight verdict MUST match CI's actual
conclusion for `dev` HEAD — no false-green when CI is red even after a
build/prepare step (the #52 sharpening's web-job case), no false-red when green.
Reading the **recorded** conclusion is the only faithful path: GitHub ran the
genuine pipeline, so the build-order fidelity is inherited for free. Any local
re-run would have to replicate CI's full build/prepare order — the fragile path
the sharpening warns against. This delta reuses the recorded-conclusion reader;
it does NOT re-run anything locally.

## Failing characterisation test (Red)

`plugins/sulis/scripts/tests/unit/test_wpxlib_preflight_ci.py` — imports `_wpxlib`
directly (unit style, matching `test_wpxlib_tables.py`) and injects a
`FakeGHClient`-style double via the existing `GHClient` Protocol (or a minimal
in-test stub implementing `check_runs`). The helper under test does NOT yet
exist, so these fail at import/attribute resolution:

```python
def test_preflight_red_dev_returns_failed_with_names(fake_gh_red):
    # fake_gh.check_runs returns completed runs, one of which has
    # conclusion="failure" (name="web"), the rest success.
    verdict, failed = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_red)
    assert verdict == "failed"
    assert failed == ["web"]            # count == len(failed) == 1

def test_preflight_green_dev_returns_green_empty(fake_gh_green):
    verdict, failed = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_green)
    assert verdict == "green"
    assert failed == []

def test_preflight_does_not_poll_when_runs_in_flight(fake_gh_in_flight, monkeypatch):
    # If any run is status != "completed", the pre-flight does NOT sleep —
    # it returns a distinct verdict immediately (no wait). Assert time.sleep
    # is never called.
    slept = []
    monkeypatch.setattr(_wpxlib.time, "sleep", lambda s: slept.append(s))
    verdict, failed = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_in_flight)
    assert slept == []                  # never polled
    assert verdict == "pending"         # latest run not yet conclusive

def test_preflight_reads_conclusion_explicitly_not_status(fake_gh_red):
    # Regression guard for lesson #59: a run with status="completed" and
    # conclusion="failure" is failed even though status alone looks "done".
    verdict, _ = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_red)
    assert verdict == "failed"
```

The `fake_gh_*` fixtures build a stub `GHClient` whose `check_runs` returns a
`{"check_runs": [...]}` envelope shaped exactly like
`RealGHClient.check_runs` output (`_wpxlib.py:996`), matching the shape
`_poll_ci` already consumes at `:1201`.

## Changes

**ADDED** — `_wpxlib.py`, a new module-level helper near `_poll_ci`:

```python
def _preflight_ci_conclusion(
    repo: str, branch: str, *, gh: GHClient | None = None,
) -> tuple[str, list[str]]:
    """Read branch HEAD's CURRENT recorded CI conclusion. No polling.

    Returns (verdict, failed_check_names):
      - "green",   []                 — all completed runs succeeded/neutral/skipped
      - "failed",  [name, ...]        — >=1 completed run not in the pass set
      - "pending", []                 — runs exist but not all completed (no wait)
      - "unknown", []                 — no check-runs recorded for this HEAD yet

    Faithful by construction: reads GitHub's recorded conclusion for the
    workflow GitHub actually ran (build/prepare order included). Reads
    `conclusion` EXPLICITLY (lesson #59) — never a chained exit code.

    Reuses _gh_check_runs (GHClient.check_runs) — does not re-read CI.
    """
    runs = _gh_check_runs(repo, branch, gh=gh)["check_runs"]
    if not runs:
        return "unknown", []
    statuses = [(r["name"], r["status"], r["conclusion"]) for r in runs]
    if not all(s[1] == "completed" for s in statuses):
        return "pending", []
    _PASS = ("success", "neutral", "skipped")
    failed = [s[0] for s in statuses if s[2] not in _PASS]
    return ("green", []) if not failed else ("failed", failed)
```

**NOT MODIFIED** — `_poll_ci` stays exactly as-is. The train still uses it for
its wait-then-verdict semantics. The two helpers share `_gh_check_runs`; the
pass-set predicate is duplicated by intent (the train's and the pre-flight's
verdicts are independently calibrated and must be free to diverge). If a third
caller appears, the REFACTOR step extracts a shared `_classify_check_runs`
private — not now (two callers, intentional independence).

## Definition of Done

- **Red:** the four tests above exist and fail (helper undefined).
- **Green:** the helper is added; all four pass. `_poll_ci` untouched; its
  existing tests (`test_wpx_train_*`) still pass.
- **Blue:** confirm no shared-predicate extraction is warranted yet (two callers,
  documented intentional divergence); the helper has a docstring naming the
  faithfulness + lesson-#59 rationale; no `time` import added (already present).

## Boring-code notes

- Returns an explicit `tuple[str, list[str]]` — no magic, no exceptions for
  control flow. The four verdict strings are a closed set documented in the
  docstring.
- Injects `gh` via the existing keyword seam — no monkeypatching of internals
  required by callers or tests.
