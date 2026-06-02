#!/usr/bin/env bash
# Characterisation test for WP-002 (REORGANISE-Move primitive).
#
# Asserts that the plugin-side reusable workflow's `jobs.release.steps`
# block is byte-identical to the captured snapshot of the marketplace's
# pre-move .github/workflows/release-on-merge.yml — modulo the two
# structural adjustments listed in TDD §4.2 (the `on:` block shape and
# the job-level `permissions:` re-declaration).
#
# This is the load-bearing test for the move: byte-equivalent steps
# prove no silent reformatting / no behaviour change snuck in under the
# guise of a path change.

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

# Use python3 + PyYAML to load both files and compare the
# jobs.release.steps node. Steps are a YAML sequence of maps; equality
# under yaml.safe_load is structural — semantically identical to
# byte-equivalence at the step level (ignoring whitespace and key
# ordering, which is the right granularity for "no behaviour change").
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

if reusable_steps != snapshot_steps:
    # Find the first difference, for an actionable error message.
    msg = ["FAIL: jobs.release.steps differs between reusable workflow and pre-move snapshot."]
    n = max(len(reusable_steps), len(snapshot_steps))
    for i in range(n):
        r = reusable_steps[i] if i < len(reusable_steps) else None
        s = snapshot_steps[i] if i < len(snapshot_steps) else None
        if r != s:
            msg.append(f"  step #{i}:")
            msg.append(f"    reusable: {r!r}")
            msg.append(f"    snapshot: {s!r}")
            break
    print("\n".join(msg), file=sys.stderr)
    sys.exit(1)

# Also assert the `if:` job-level guard is preserved (loop-guard for
# the bot's own release commits — TDD §5.1 / FR-004 adjacent).
reusable_if = reusable["jobs"]["release"].get("if")
snapshot_if = snapshot["jobs"]["release"].get("if")
if reusable_if != snapshot_if:
    print(f"FAIL: jobs.release.if differs: reusable={reusable_if!r} snapshot={snapshot_if!r}", file=sys.stderr)
    sys.exit(1)

print("OK: jobs.release.steps and jobs.release.if are byte-equivalent (modulo on:/permissions:/name:/concurrency:)")
PY
