---
id: HD-002
slug: runall-preflight-dev-clean-blocker
title: Pre-flight dev-clean check on /sulis:run-all — one up-front blocker on red dev
status: proposed
severity: medium
pillar: armor
gap_type: observability
source: srd:lesson-52
change: CH-01KSQB
primitive: Create
group: expand
depends_on: [HD-001]
blocks: []
files:
  - plugins/sulis/scripts/wpx-preflight
  - plugins/sulis/scripts/tests/unit/test_wpx_preflight.py
  - plugins/sulis/skills/run-all/SKILL.md
---

## Gap

The `/sulis:run-all` parallel loop (run-all/SKILL.md, "The parallel loop",
beginning ~line 124) reads the INDEX and dispatches a wave (Steps 1-8) **before**
any check that `dev` HEAD is CI-green. When pre-existing red sits on `dev`
(landed via a manual/non-train merge on an unprotected repo — the #52 incident),
every branch cut off `dev` inherits it, so every WP's branch-ci rediscovers the
*same* red per-branch. The founder sees N identical failures instead of one
up-front "dev is red — fix it first".

## Why it matters

This is the primary fix surface in lesson #52. Even with the train already
pausing on bundled-tip red (the merge path is safe — non-goal #1), a wave still
wastes a full executor batch rediscovering pre-existing drift the founder can't
attribute to their own WP. One up-front blocker, naming the count, is the
difference between "fix one thing on dev" and "debug N red branches".

## Design: a thin script entrypoint, invoked by the skill (skill↔script split)

The repo's convention is that deterministic logic lives in a `wpx-*` script with
unit tests, and skills orchestrate by invoking it (cf. `wpx-arrival-check`,
`wpx-train`). A pre-flight verdict that MUST faithfully reproduce CI's
conclusion is deterministic logic — it belongs in a script, not narrated inline
in the skill body, so it can be **tested**. New entrypoint `wpx-preflight` wraps
HD-001's `_preflight_ci_conclusion` and emits the run-all `ok`/`errors` JSON the
skill already knows how to parse (same `_Report`-style envelope as
`wpx-arrival-check`).

This keeps the faithful-reproduction guarantee in tested Python (HD-001 +
this script) and reduces the skill change to "invoke, parse, stop-or-proceed".

## Failing test (Red)

`plugins/sulis/scripts/tests/unit/test_wpx_preflight.py`, using `run_tool` +
`mock_gh` (subprocess style, matching `test_wpx_arrival_check.py`). The
`wpx-preflight` entrypoint does not yet exist → tests fail.

```python
def test_preflight_red_dev_emits_blocker_with_count(tmp_path, run_tool, mock_gh):
    mock_gh([{"match": "commits/dev/check-runs", "stdout": json.dumps({
        "check_runs": [
            {"name": "branch-ci", "status": "completed", "conclusion": "success"},
            {"name": "web",       "status": "completed", "conclusion": "failure"},
        ]})}])
    result = run_tool("wpx-preflight", "dev-clean",
                      "--repo", "sulis-ai/agents", "--branch", "dev")
    assert result.json["ok"] is False
    assert result.returncode == 2
    blocker = next(e for e in result.json["errors"] if e["rule"] == "PRE-01")
    assert "1" in blocker["actual"]                 # names the count
    assert "web" in (blocker.get("detail","") + blocker.get("actual",""))

def test_preflight_green_dev_is_ok(tmp_path, run_tool, mock_gh):
    mock_gh([{"match": "commits/dev/check-runs", "stdout": json.dumps({
        "check_runs": [
            {"name": "branch-ci", "status": "completed", "conclusion": "success"},
        ]})}])
    result = run_tool("wpx-preflight", "dev-clean",
                      "--repo", "sulis-ai/agents", "--branch", "dev")
    assert result.json["ok"] is True
    assert result.returncode == 0

def test_preflight_reads_conclusion_explicitly(tmp_path, run_tool, mock_gh):
    # status completed + conclusion failure → red (lesson #59 guard)
    mock_gh([{"match": "commits/dev/check-runs", "stdout": json.dumps({
        "check_runs": [{"name": "web", "status": "completed", "conclusion": "failure"}]})}])
    result = run_tool("wpx-preflight", "dev-clean",
                      "--repo", "sulis-ai/agents", "--branch", "dev")
    assert result.json["ok"] is False
```

## Changes

**ADDED** — `plugins/sulis/scripts/wpx-preflight`, a small CLI:

```python
#!/usr/bin/env python3
"""Pre-flight checks for run-all. Today: dev-clean (is base branch CI-green?)."""
# imports _wpxlib._preflight_ci_conclusion (HD-001)
# subcommand: dev-clean --repo <org/repo> --branch <branch> (default dev)
#   verdict, failed = _preflight_ci_conclusion(repo, branch)
#   green/unknown  -> {"ok": true,  "errors": [], "warnings": [...]}, exit 0
#   pending        -> ok:true + warning "CI still running on <branch>" (don't block on in-flight)
#   failed         -> {"ok": false, "errors": [{"rule":"PRE-01",
#                        "check":"dev HEAD CI-green before wave dispatch",
#                        "actual": f"{len(failed)} pre-existing CI failures: {failed}",
#                        "expected":"green"}]}, exit 2
```

Verdict mapping rationale (decided-by-default in spec — honoured):
- `failed` → hard blocker (no override), exit 2 — matches the train pausing on red.
- `green` → ok.
- `unknown` (no runs recorded yet) → ok with advisory warning ("no CI recorded
  for dev HEAD yet") — absence of evidence is not red; do not false-block.
- `pending` (runs in-flight) → ok with advisory warning — the pre-flight does
  not poll; an in-flight run is not a recorded red.

**MODIFIED** — `run-all/SKILL.md`, in "The parallel loop", a new **Step 0**
before Step 1 (read INDEX). Resolve `$WPX_DIR` (already done at session start),
determine the base branch (the existing CW-04 detection at Step 12 already
computes `change/*` vs `dev` — reuse it here), then:

```bash
PREFLIGHT=$("$WPX_DIR/wpx-preflight" dev-clean --repo <org/repo> --branch "$BASE_BRANCH")
# if ok:false → STOP. Surface ONE founder-English blocker, do NOT dispatch:
#   "<BASE_BRANCH> has N pre-existing CI failures — fix these first, then
#    re-run. (Failing checks: <names>.) Nothing was dispatched."
# if ok:true → proceed to Step 1 as today.
```

The blocker is plain-English (founder_facing flows through run-all even though
this change is internal tooling) and names the count + check names. No
"proceed anyway" path (spec decided-by-default).

## Definition of Done

- **Red:** the three `wpx-preflight` tests exist and fail.
- **Green:** `wpx-preflight dev-clean` added; tests pass. run-all/SKILL.md Step 0
  documents the invoke→stop-or-proceed gate before wave dispatch.
- **Blue:** confirm the green path is unchanged (no regression — spec acceptance
  "when dev IS green, run proceeds exactly as today"); confirm the verdict
  mapping is documented inline in the script; reuse the CW-04 base-branch
  detection rather than duplicating it.

## Boring-code notes

- The script emits the **same JSON envelope shape** (`{ok, errors, warnings}` +
  exit 0/2) as `wpx-arrival-check`, so the skill parses it with the pattern it
  already uses — no new contract for the skill to learn.
- Faithful reproduction is inherited from HD-001 (recorded conclusion, build
  order included) — this script adds no CI-reading logic of its own.

## Honest note for the orchestrator

The skill-body change (Step 0) is markdown, not executable, so it is not
unit-testable directly. The testable guarantee lives in `wpx-preflight` + HD-001.
The skill change is reviewed for: (a) gate placed BEFORE wave dispatch, (b) hard
stop on `ok:false`, (c) plain-English single blocker, (d) base-branch reuse. A
`/sulis:verify-architecture` pass should `verify` the run-all surface by driving
the skill against a mocked-red dev (or asserting the script gate at minimum).
