#!/usr/bin/env bash
# WP-002 unit test — TDD §5.2 (static layer) + §6.1
# (test_no_force_push_static).
#
# Asserts that the plugin-side reusable workflow YAML contains none of
# the force-push patterns:
#
#   --force
#   --force-with-lease
#   +main:dev   (the git refspec form that bypasses fast-forward
#                checks)
#
# NFR-002 promotes "no force push" from an informal habit to an
# enforced invariant. This static grep is the cheapest of the three
# enforcement layers (static / runtime / recovery — see TDD §5.2). It
# passes trivially after WP-002 ships because the moved content has no
# force flags — the test exists as a guardrail for future changes.
# WP-009 carries the same test forward.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../../../.." && pwd)"

REUSABLE="$REPO_ROOT/plugins/sulis/templates/workflows/release-on-merge.yml"

if [ ! -f "$REUSABLE" ]; then
  echo "FAIL: reusable workflow not present at $REUSABLE" >&2
  exit 1
fi

# Use grep -nE; an exit status of 0 means HITS were found (bad), 1
# means none (good). Use a tolerant set:noglob to handle the literal
# `+main:dev` refspec form.
HITS=$(grep -nE '(\+main:dev|--force|--force-with-lease)' "$REUSABLE" || true)

if [ -n "$HITS" ]; then
  echo "FAIL: force-push patterns found in $REUSABLE:" >&2
  echo "$HITS" >&2
  exit 1
fi

echo "OK: no force-push patterns in $REUSABLE"
