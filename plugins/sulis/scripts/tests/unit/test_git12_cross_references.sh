#!/usr/bin/env bash
# Asserts GIT-12 cross-references GIT-05, GIT-06, GIT-09 by canonical ID.
# These are the three composing rules GIT-12 layers on top of:
#   - GIT-05 — Direct merge to dev on CI green (no PR ceremony)
#   - GIT-06 — dev → main promotion via the release train
#   - GIT-09 — No hook bypass / no force-push to protected branches
#
# WP-008 — TDD §4.2 + ADR-004 "GIT-12 composes with, never supersedes,
# existing GIT-NN rules".

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
STANDARD="$REPO_ROOT/plugins/sulis/references/git-workflow-standard.md"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$STANDARD" ] || fail "standard file missing at $STANDARD"

slice="$(awk '
  /^## GIT-12: Auto-back-merge on release \(MUST\)$/ { capture=1 }
  capture && /^## / && !/^## GIT-12:/ { capture=0 }
  capture { print }
' "$STANDARD")"

[ -n "$slice" ] || fail "GIT-12 section is empty or absent"

assert_contains() {
  local needle="$1"
  local label="$2"
  if ! grep -qF -- "$needle" <<<"$slice"; then
    fail "GIT-12 missing cross-reference to $label: expected to find '$needle'"
  fi
}

assert_contains "GIT-05" "GIT-05 (direct merge to dev)"
assert_contains "GIT-06" "GIT-06 (release train)"
assert_contains "GIT-09" "GIT-09 (no force-push / no hook bypass)"

echo "PASS: GIT-12 cross-references GIT-05, GIT-06, GIT-09"
