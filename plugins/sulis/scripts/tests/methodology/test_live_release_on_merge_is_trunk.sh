#!/usr/bin/env bash
# Read-through characterisation — WP-001 (CH-01KT4K, simplify-release-robot).
#
# The LIVE release workflow at .github/workflows/release-on-merge.yml is
# INVISIBLE to the drift gate (the gate's --yaml-path points at the annotated
# template, not the live file). Its correctness under the trunk model is by
# read-through only. This test is that read-through, frozen as a guard so a
# future edit cannot silently re-introduce dev->main promotion / back-merge /
# ancestry logic into the live robot.
#
# Baseline (verified at WP-001 author time): the live workflow is ALREADY a
# clean trunk-style bump+tag+push with no back-merge block — so this assertion
# passes at baseline. Its job is forward-looking: it FAILS if any of the
# promotion tokens below ever reappear as reachable logic in the live file.
#
# Tokens scanned (the load-bearing promotion/back-merge markers):
#   back-integrate     — the raced-path PR label / title
#   main:dev           — the fast-forward refspec that pushed main onto dev
#   dev-sha-at-open    — the ADR-005/006 pin read back at merge time
#   gh pr create       — opening a (release or back-merge) PR
#   gh pr merge        — squash/auto-merging a PR
#
# bash-3.2-safe (macOS /bin/bash). Exit 0 iff the live file is trunk-clean.

set -u
set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../../../.." && pwd)"
LIVE="$REPO_ROOT/.github/workflows/release-on-merge.yml"

if [ ! -f "$LIVE" ]; then
  echo "FAIL: live release workflow not present at $LIVE" >&2
  exit 1
fi

# Strip full-line comments (leading-whitespace then '#') before scanning, so a
# cautionary comment that NAMES a token (e.g. "no back-integrate here") doesn't
# trip the guard. We only care about REACHABLE logic, i.e. non-comment lines.
NONCOMMENT="$(grep -vE '^[[:space:]]*#' "$LIVE" || true)"

FAIL=0
for tok in 'back-integrate' 'main:dev' 'dev-sha-at-open' 'gh pr create' 'gh pr merge'; do
  if printf '%s\n' "$NONCOMMENT" | grep -qF "$tok"; then
    echo "FAIL: live release workflow contains reachable promotion token: '$tok'" >&2
    echo "      The live robot must perform the 10-step trunk flow (bump + tag" >&2
    echo "      + push on main) with NO dev->main promotion / back-merge logic." >&2
    FAIL=1
  fi
done

# Positive shape: the trigger must be push-to-main, not a PR-merge event.
if ! grep -qE 'branches:[[:space:]]*\[[[:space:]]*main[[:space:]]*\]' "$LIVE"; then
  echo "FAIL: live release workflow trigger is not 'push: branches: [main]'" >&2
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi

echo "OK: live .github/workflows/release-on-merge.yml is trunk-clean — no reachable"
echo "    promotion/back-merge/ancestry logic; trigger is push to main."
exit 0
