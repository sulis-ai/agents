#!/usr/bin/env bash
# Asserts GIT-12's body contains:
#   - the invariant statement ("append-only relative to the release robot")
#   - the four-moving-parts mechanism list
#   - all three worked examples (clean, raced, manual recovery)
#   - the three prior back-integration commit SHAs (0e85c24, 8612834, d93517c)
#     that historically demonstrated the structural gap
#
# WP-008 — TDD §4.2 + §6.6.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
STANDARD="$REPO_ROOT/plugins/sulis/references/git-workflow-standard.md"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$STANDARD" ] || fail "standard file missing at $STANDARD"

# Slice from GIT-12 heading to the next top-level heading.
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
    fail "GIT-12 body missing $label: expected to find '$needle'"
  fi
}

# Invariant statement.
assert_contains "append-only relative to the release robot" "invariant phrase"

# Four-moving-parts mechanism.
assert_contains "reusable" "moving-part 1 (reusable workflow)"
assert_contains "shim" "moving-part 2 (consumer shim)"
assert_contains "dev-sha-at-open" "moving-part 3 (pin)"
assert_contains "drift_check.sh" "moving-part 4 (drift gate)"

# Three worked examples by heading anchor.
assert_contains "Worked example 1 — clean path" "worked example 1 heading"
assert_contains "Worked example 2 — raced path" "worked example 2 heading"
assert_contains "Worked example 3 — manual recovery" "worked example 3 heading"

# The three prior back-integration commit SHAs that proved the gap exists.
assert_contains "0e85c24" "back-integration commit SHA #1"
assert_contains "8612834" "back-integration commit SHA #2"
assert_contains "d93517c" "back-integration commit SHA #3"

echo "PASS: GIT-12 invariant + mechanism + three worked examples + three historical SHAs all present"
