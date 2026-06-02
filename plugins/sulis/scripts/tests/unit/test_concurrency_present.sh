#!/usr/bin/env bash
# WP-002 unit test — TDD §6.1 (test_concurrency_present).
#
# Asserts that the plugin-side reusable workflow YAML preserves the
# `concurrency:` block from the source workflow:
#
#   concurrency:
#     group: release-on-merge
#     cancel-in-progress: false
#
# FR-004 / MUC-005: two release PRs merged in quick succession must
# serialise — `cancel-in-progress: false` is the load-bearing flag
# that prevents the second from cancelling the first. WP-009's full
# suite carries this forward; WP-002 ships it early because the file
# is created here.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../../../.." && pwd)"

REUSABLE="$REPO_ROOT/plugins/sulis/templates/workflows/release-on-merge.yml"

if [ ! -f "$REUSABLE" ]; then
  echo "FAIL: reusable workflow not present at $REUSABLE" >&2
  exit 1
fi

# Top-level concurrency block — match the two child keys, allowing
# any whitespace ordering / extra blank lines between them.
if ! grep -qE '^concurrency:' "$REUSABLE"; then
  echo "FAIL: top-level 'concurrency:' key missing from $REUSABLE" >&2
  exit 1
fi

if ! grep -qE '^[[:space:]]+group:[[:space:]]+release-on-merge[[:space:]]*$' "$REUSABLE"; then
  echo "FAIL: 'group: release-on-merge' missing under concurrency: in $REUSABLE" >&2
  exit 1
fi

if ! grep -qE '^[[:space:]]+cancel-in-progress:[[:space:]]+false[[:space:]]*$' "$REUSABLE"; then
  echo "FAIL: 'cancel-in-progress: false' missing under concurrency: in $REUSABLE" >&2
  exit 1
fi

echo "OK: concurrency block present with group=release-on-merge cancel-in-progress=false"
