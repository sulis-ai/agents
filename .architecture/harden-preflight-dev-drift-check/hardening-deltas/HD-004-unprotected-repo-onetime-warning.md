---
id: HD-004
slug: unprotected-repo-onetime-warning
title: One-time unprotected-repo warning on /sulis:run-all and /sulis:change ship
status: proposed
severity: medium
pillar: armor
gap_type: observability
source: srd:lesson-52
change: CH-01KSQB
primitive: Create
group: expand
depends_on: [HD-003]
blocks: []
files:
  - plugins/sulis/scripts/wpx-preflight
  - plugins/sulis/scripts/tests/unit/test_wpx_preflight.py
  - plugins/sulis/skills/run-all/SKILL.md
  - plugins/sulis/skills/change/SKILL.md
---

## Gap

When a repo is private on the free GitHub plan, branch protection is unavailable,
so `branch-ci` runs but cannot gate merges. Only Sulis-routed (train) merges are
CI-gated; a manual `gh pr merge` or a direct push can land red on `dev`. Neither
`/sulis:run-all` nor `/sulis:change ship` tells the founder this. The git-workflow
standard's assumption that branch-ci gates merges (GIT-01..GIT-10) silently
breaks for the common founder case. This is the awareness half of lesson #52.

## Why it matters

The founder needs to know that on their plan, the safety net only covers the
Sulis train — not their own manual merges. Informational, not a blocker (spec
non-goal #4): it raises awareness so the founder either routes merges through
Sulis or upgrades/makes-public; it never stops `run-all` or `ship`.

## Design: detection in the script, "warn once per invocation" in the skill

HD-003 already produces the free-plan distinction inside `wpx-arrival-check`'s
`_check_rc02_protections`. HD-004 surfaces the *same distinction* through a
`wpx-preflight protection-status` subcommand (so both skills share one tested
detection path rather than each shelling out to `gh` and re-parsing the 403),
and the **skills own the "warn once per invocation"** semantics:

- "Warn once" = once per `run-all` run / once per `ship` (spec decided-by-default
  — not persisted-once-ever). The skill emits the warning at most once in its
  own turn flow; nothing is written to disk to silence future invocations.

## Failing test (Red)

Add to `plugins/sulis/scripts/tests/unit/test_wpx_preflight.py`:

```python
def test_protection_status_freeplan_403_reports_unprotected(tmp_path, run_tool, mock_gh):
    mock_gh([{"match": "branches/dev/protection", "exit_code": 1,
        "stderr": ("gh: Upgrade to GitHub Pro or make this repository public "
                   "to enable this feature. (HTTP 403)")}])
    result = run_tool("wpx-preflight", "protection-status",
                      "--repo", "sulis-ai/agents", "--branch", "dev")
    assert result.json["ok"] is True            # informational, never blocks
    assert result.json["data"]["protection"] == "unavailable-free-plan"

def test_protection_status_protected_reports_protected(tmp_path, run_tool, mock_gh):
    mock_gh([{"match": "branches/dev/protection", "stdout": json.dumps({
        "required_status_checks": {"contexts": ["branch-ci"]}})}])
    result = run_tool("wpx-preflight", "protection-status",
                      "--repo", "sulis-ai/agents", "--branch", "dev")
    assert result.json["data"]["protection"] == "protected"

def test_protection_status_genuine_missing_reports_unprotected_misconfig(tmp_path, run_tool, mock_gh):
    # rc!=0 but NOT the free-plan body → capable-but-unconfigured, distinct value
    mock_gh([{"match": "branches/dev/protection", "exit_code": 1,
              "stderr": "gh: Not Found (HTTP 404)"}])
    result = run_tool("wpx-preflight", "protection-status",
                      "--repo", "sulis-ai/agents", "--branch", "dev")
    assert result.json["data"]["protection"] == "unconfigured"
```

## Changes

**ADDED** — `wpx-preflight protection-status` subcommand. Reuses HD-003's
`_is_freeplan_protection_403` predicate (import it, or move the predicate to
`_wpxlib.py` if both `wpx-arrival-check` and `wpx-preflight` consume it — see
Blue). Returns:

```json
{"ok": true, "data": {"protection": "protected | unavailable-free-plan | unconfigured"}}
```

Always `ok:true` — protection status is never a blocker on this surface.

**MODIFIED** — `run-all/SKILL.md`: in Step 0 (alongside HD-002's dev-clean gate),
after the dev-clean check, call `wpx-preflight protection-status`. If
`unavailable-free-plan`, emit the one-time warning (founder-English), then
proceed regardless:

```
"Heads-up: branch protection isn't available on your plan (private repo on
 the free GitHub plan), so the automated checks can't block a merge. Only
 merges I route through Sulis are checked before landing — a manual merge or
 a direct push to dev is not. If you merge by hand, the checks won't stop a
 broken change from landing."
```

**MODIFIED** — `change/SKILL.md`, `ship` flow: at step 4 (where it waits for
`branch-ci`), before/alongside the wait, call `wpx-preflight protection-status`
for the base branch. If `unavailable-free-plan`, emit the same one-time warning
once per ship. The ship still proceeds (the PR + branch-ci wait + review gate are
unchanged); the warning is purely informational and does not gate the merge.

## Definition of Done

- **Red:** the three `protection-status` tests exist and fail.
- **Green:** `wpx-preflight protection-status` added; tests pass. Both skills
  document the one-time warning + proceed-regardless behaviour. Public/protected
  repos emit no warning (spec acceptance — behaviour unchanged).
- **Blue:** if both `wpx-arrival-check` and `wpx-preflight` now consume
  `_is_freeplan_protection_403`, extract it to `_wpxlib.py` (shared primitive —
  CLAUDE.md #2: two callers of the same pattern → extract now, this PR, not
  later). If only `wpx-preflight` consumes it, leave it where HD-003 put it.
  Confirm the warning text matches the RC-02 warning wording from HD-003 (one
  voice, not two).

## Boring-code notes

- Three explicit protection states in a closed enum (`protected` /
  `unavailable-free-plan` / `unconfigured`) — no boolean that conflates
  "can't protect" with "didn't protect".
- "Warn once per invocation" is the simplest correct semantics: no persistence,
  no state file, no silencing. A founder who hasn't fixed the situation is
  reminded each run — which is the point (spec decided-by-default).

## Cross-delta note

HD-004's `protection-status` and HD-003's RC-02 refinement read the same API and
make the same distinction. HD-003 is the arrival-check surface (a one-time
repo-setup audit); HD-004 is the per-run/per-ship surface. They share the
predicate (Blue extraction). HD-003 must land first so the predicate exists and
its semantics are pinned by the characterisation test.
