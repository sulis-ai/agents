#!/usr/bin/env bash
# Asserts plugins/sulis/references/git-workflow-standard.md contains a
# section `## GIT-12: Auto-back-merge on release (MUST)` AFTER the
# existing `## GIT-11` section (textual ordering check).
#
# WP-008 — GIT-12 rule append. ADR-004 records the placement decision
# (append after GIT-11; no doc re-versioning to existing GIT-NN rules).

set -euo pipefail

# Locate the standard relative to this test file (repo-root-anchored).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
STANDARD="$REPO_ROOT/plugins/sulis/references/git-workflow-standard.md"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$STANDARD" ] || fail "standard file missing at $STANDARD"

# Find line numbers of the two headings.
git11_line=$(grep -n '^## GIT-11:' "$STANDARD" | head -1 | cut -d: -f1)
git12_line=$(grep -n '^## GIT-12: Auto-back-merge on release (MUST)$' "$STANDARD" | head -1 | cut -d: -f1)

[ -n "$git11_line" ] || fail "GIT-11 heading not found in standard"
[ -n "$git12_line" ] || fail "GIT-12 heading not found in standard (expected '## GIT-12: Auto-back-merge on release (MUST)')"

if [ "$git12_line" -le "$git11_line" ]; then
  fail "GIT-12 (line $git12_line) must appear AFTER GIT-11 (line $git11_line)"
fi

echo "PASS: GIT-12 section heading present at line $git12_line, after GIT-11 at line $git11_line"
