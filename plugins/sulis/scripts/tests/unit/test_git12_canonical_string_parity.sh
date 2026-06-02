#!/usr/bin/env bash
# Asserts the four canonical strings used by the auto-back-merge mechanism
# appear inside the GIT-12 section, byte-for-byte:
#
#   1. dev-sha-at-open                — the pin token in the release PR body
#   2. back-integrate                 — the PR label
#   3. chore: back-integrate main → dev — the PR title prefix (UTF-8 →)
#   4. base=dev / head=main           — the PR base+head
#
# WP-009 will cross-check these against drift_check.sh and the reusable
# workflow YAML. This WP-008 test verifies the strings are PRESENT in
# GIT-12 (the parity-vs-code check is WP-009's job).
#
# WP-008 — TDD §3 Canonical Identifiers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
STANDARD="$REPO_ROOT/plugins/sulis/references/git-workflow-standard.md"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$STANDARD" ] || fail "standard file missing at $STANDARD"

# Slice GIT-12 only.
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
    fail "GIT-12 missing canonical string '$label': expected to find '$needle'"
  fi
}

assert_contains "dev-sha-at-open"                   "pin token"
assert_contains "back-integrate"                    "PR label"
assert_contains "chore: back-integrate main → dev"  "PR title prefix"
assert_contains "base: dev"                         "PR base"
assert_contains "head: main"                        "PR head"

echo "PASS: all four canonical strings present in GIT-12 byte-for-byte"
