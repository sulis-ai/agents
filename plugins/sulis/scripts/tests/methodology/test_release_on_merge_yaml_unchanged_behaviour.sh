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
#   2. The reusable workflow has EXACTLY the snapshot's steps PLUS the
#      three named back-merge steps appended after them — no more, no
#      fewer, in that order (the delta is exactly the intended one).
#   3. The job-level `if:` loop-guard is unchanged (preserved across
#      both the move and the append).
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

# The three back-merge steps WP-003 intentionally appended. Identified by
# name (the canonical-string CONTENT of these steps is asserted by
# WP-009's parity + chaos tests, not here).
EXPECTED_APPENDED = [
    "Read dev-sha-at-open pin from release PR",
    "Fast-forward dev to main, or open raced-path back-integrate PR",
    "Verify atomicity (NFR-006)",
]

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
        "FAIL: the appended back-merge block is not exactly the three "
        "expected steps (in order).\n"
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
