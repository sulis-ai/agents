#!/usr/bin/env bash
# verifies: plugins/sulis/templates/workflows/release-on-merge.yml
# verifies: .github/workflows/release-on-merge.yml
#
# test_loop_guard_survives_indirection.sh — regression guard (WP-009).
#
# The loop-guard stops the release robot's own `release: sulis` push-back
# from re-triggering the release workflow infinitely. After WP-005 made
# the marketplace's `.github/workflows/release-on-merge.yml` a thin shim
# that `uses:` the reusable workflow, the guard moved one layer down:
# the job-level `if:` now lives in the REUSABLE workflow, and the shim
# must forward the `push` event context (github.event.head_commit.*,
# github.actor) through the `workflow_call` indirection so the guard
# still fires.
#
# WP-005 verified this manually; this test pins it so a future change
# to either file that breaks the indirection fails CI. Three assertions:
#
#   1. The reusable workflow has a job-level `if:` loop-guard (the guard
#      that skips the bot's own release commits).
#   2. The marketplace shim triggers on `push` to main (the event whose
#      context carries the actor/head_commit the guard inspects).
#   3. The shim invokes the reusable workflow via `uses:` and forwards
#      secrets (`secrets: inherit`) — the indirection is in place. The
#      shim must NOT carry its own copy of the loop-guard `if:` at the
#      job level (the guard belongs to the reusable workflow; a
#      duplicate would be drift).
#
# Structural assertion over the YAML (parsed with python3 + PyYAML,
# same approach as the methodology characterisation test). No GitHub
# runtime required.

set -u
set -o pipefail

. "$(dirname "$0")/../lib/abm_canonical.sh"

[ -f "$ABM_REUSABLE_WORKFLOW" ] || abm_fail "reusable workflow missing at $ABM_REUSABLE_WORKFLOW"
[ -f "$ABM_MARKETPLACE_SHIM" ]  || abm_fail "marketplace shim missing at $ABM_MARKETPLACE_SHIM"

if python3 - "$ABM_REUSABLE_WORKFLOW" "$ABM_MARKETPLACE_SHIM" <<'PY'
import sys
import yaml

reusable_path, shim_path = sys.argv[1], sys.argv[2]

with open(reusable_path) as f:
    reusable = yaml.safe_load(f)
with open(shim_path) as f:
    shim = yaml.safe_load(f)


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


# --- 1. reusable workflow has the job-level loop-guard `if:` ---
rel_job = (reusable.get("jobs") or {}).get("release")
if rel_job is None:
    fail("reusable workflow has no jobs.release")
guard = rel_job.get("if")
if not guard:
    fail("reusable workflow jobs.release has no job-level `if:` loop-guard")
# The guard must reference the bot's release commit signal — either the
# 'release: sulis' commit-message prefix or the github-actions[bot] actor.
guard_text = str(guard)
if ("release: sulis" not in guard_text) and ("github-actions" not in guard_text):
    fail(
        "reusable workflow loop-guard does not reference the bot's release "
        f"signal ('release: sulis' or github-actions[bot]); got: {guard_text!r}"
    )

# --- 2. shim triggers on push to main ---
# PyYAML parses the bare `on:` key as the boolean True in some YAML 1.1
# loaders; handle both the string 'on' and the boolean True key.
on = shim.get("on", shim.get(True))
if on is None:
    fail("shim has no `on:` trigger block")
push = (on or {}).get("push") if isinstance(on, dict) else None
if not push:
    fail("shim does not trigger on `push`")
branches = push.get("branches") if isinstance(push, dict) else None
if not branches or "main" not in branches:
    fail(f"shim `on.push.branches` does not include 'main'; got: {branches!r}")

# --- 3. shim invokes the reusable workflow via uses: + secrets: inherit ---
shim_job = (shim.get("jobs") or {}).get("release")
if shim_job is None:
    fail("shim has no jobs.release")
uses = shim_job.get("uses")
if not uses or "release-on-merge.yml" not in uses:
    fail(f"shim jobs.release does not `uses:` the reusable workflow; got: {uses!r}")
if shim_job.get("secrets") != "inherit":
    fail(
        "shim jobs.release does not forward `secrets: inherit` — the push "
        f"context the loop-guard inspects would not propagate; got: {shim_job.get('secrets')!r}"
    )

# The shim must NOT duplicate the loop-guard at its own job level — the
# guard belongs to the reusable workflow. A duplicate would be canonical
# drift (two sources of the same logic).
if shim_job.get("if") is not None:
    fail(
        "shim jobs.release carries its own job-level `if:` — the loop-guard "
        "belongs to the reusable workflow; a duplicate here is drift. "
        f"Got: {shim_job.get('if')!r}"
    )

print(
    "OK: loop-guard `if:` lives in the reusable workflow; shim forwards the "
    "push-to-main context + secrets through the workflow_call indirection; "
    "no duplicate guard in the shim"
)
PY
then
    abm_pass "loop-guard survives the shim→reusable indirection"
else
    abm_fail "loop-guard indirection assertion failed (see message above)"
fi
