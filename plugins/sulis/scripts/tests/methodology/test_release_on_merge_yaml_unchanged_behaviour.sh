#!/usr/bin/env bash
# Characterisation test for WP-002 (REORGANISE-Move primitive),
# RECONCILED for WP-003's back-merge append by WP-009.
#
# ----------------------------------------------------------------------
# WP-009 RECONCILIATION (the flagged failure).
#
# Original contract (WP-002): the plugin-side reusable workflow's
# `jobs.release.steps` block is byte-identical to the captured snapshot
# of the marketplace's pre-move .github/workflows/release-on-merge.yml.
# That proved the MOVE introduced no silent behaviour change.
#
# WP-003 then INTENTIONALLY appended three back-merge steps to the
# reusable workflow (pin-read, decide+act, post-condition). WP-005 made
# the marketplace file a thin shim. As a result the original
# whole-list byte-equality assertion now fails — not because the move
# regressed, but because the suite grew the intended back-merge block.
#
# DECISION (WP-009): KEEP the characterisation test, don't retire it —
# but narrow its assertion to its actual purpose. The move-fidelity
# signal lives in the FIRST N steps (the moved block); the back-merge
# block is the documented, intended delta whose CONTENT is covered by
# WP-009's byte-parity tests (test_canonical_strings_parity.sh,
# test_pin_write_read_parity.sh) and behaviour by the chaos tests
# (test_race_window.sh, test_missing_pin_falls_through.sh).
#
# So this test now asserts:
#   1. The reusable workflow's first len(snapshot.steps) steps are
#      byte-equivalent to the snapshot (the MOVE is still faithful —
#      no silent reformatting of the moved bump/tag/push block).
#   2. The reusable workflow has EXACTLY the snapshot's steps and NOTHING
#      appended after them — the delta is now empty.
#   3. The job-level `if:` loop-guard is unchanged (preserved across
#      both the move and the append).
#
# ----------------------------------------------------------------------
# WP-001 RECONCILIATION (CH-01KT4K — simplify-release-robot, trunk re-model).
#
# The trunk re-model DELETED the three WP-003 back-merge steps from the
# reusable workflow: on a trunk there is no dev to back-merge main into, so
# the pin-read / fast-forward-or-raced-PR / verify-atomicity block is dead
# machinery. The intended delta over the snapshot is therefore now EMPTY —
# the reusable workflow IS exactly the 12-step moved block (the CHANGELOG
# draft step was re-annotated under write-changelog-entry, a comment-only
# change that leaves the parsed step bodies byte-identical to the snapshot).
# Assertion 2's EXPECTED_APPENDED drops to []. The byte-fidelity of the
# moved block (assertion 1) + the loop-guard preservation (assertion 3) are
# unchanged.
# ----------------------------------------------------------------------

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../../../.." && pwd)"

REUSABLE="$REPO_ROOT/plugins/sulis/templates/workflows/release-on-merge.yml"
SNAPSHOT="$REPO_ROOT/plugins/sulis/scripts/tests/fixtures/release-on-merge/pre-move-snapshot.yml"

if [ ! -f "$REUSABLE" ]; then
  echo "FAIL: reusable workflow not present at $REUSABLE" >&2
  exit 1
fi

if [ ! -f "$SNAPSHOT" ]; then
  echo "FAIL: pre-move snapshot not present at $SNAPSHOT" >&2
  exit 1
fi

python3 - "$REUSABLE" "$SNAPSHOT" <<'PY'
import sys
import yaml

reusable_path, snapshot_path = sys.argv[1], sys.argv[2]

with open(reusable_path) as f:
    reusable = yaml.safe_load(f)
with open(snapshot_path) as f:
    snapshot = yaml.safe_load(f)

reusable_steps = reusable["jobs"]["release"]["steps"]
snapshot_steps = snapshot["jobs"]["release"]["steps"]

# The trunk re-model (WP-001) DELETED the three WP-003 back-merge steps —
# they are dead machinery on a trunk (no dev to back-merge into). The
# intended delta over the snapshot is now empty.
EXPECTED_APPENDED = []

n = len(snapshot_steps)

# --- Assertion 1: the moved block (first n steps) is byte-equivalent. ---
moved_block = reusable_steps[:n]
if moved_block != snapshot_steps:
    msg = ["FAIL: the MOVED block (first %d steps) differs from the pre-move snapshot." % n]
    for i in range(n):
        r = moved_block[i] if i < len(moved_block) else None
        s = snapshot_steps[i] if i < len(snapshot_steps) else None
        if r != s:
            msg.append(f"  step #{i} ({(s or {}).get('name')!r}):")
            msg.append(f"    reusable: {r!r}")
            msg.append(f"    snapshot: {s!r}")
            break
    print("\n".join(msg), file=sys.stderr)
    sys.exit(1)

# --- Assertion 2: the delta is EXACTLY the three named back-merge steps. ---
appended = reusable_steps[n:]
appended_names = [s.get("name") for s in appended if isinstance(s, dict)]
if appended_names != EXPECTED_APPENDED:
    print(
        "FAIL: the reusable workflow has unexpected steps appended after the "
        "moved block. On the trunk (WP-001) the delta must be EMPTY — the "
        "back-merge block was deleted.\n"
        f"  expected: {EXPECTED_APPENDED}\n"
        f"  actual:   {appended_names}",
        file=sys.stderr,
    )
    sys.exit(1)

# --- Assertion 3: the job-level `if:` loop-guard is preserved. ---
reusable_if = reusable["jobs"]["release"].get("if")
snapshot_if = snapshot["jobs"]["release"].get("if")
if reusable_if != snapshot_if:
    print(
        f"FAIL: jobs.release.if differs (loop-guard drifted): "
        f"reusable={reusable_if!r} snapshot={snapshot_if!r}",
        file=sys.stderr,
    )
    sys.exit(1)

print(
    "OK: moved block (%d steps) byte-equivalent to snapshot; "
    "back-merge block is exactly the 3 intended steps; loop-guard preserved"
    % n
)
PY
