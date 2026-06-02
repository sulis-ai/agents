#!/usr/bin/env bash
# run.sh — bash-test orchestrator for plugins/sulis/scripts/tests/unit/.
# Runs every *.sh under unit/ in alphabetical order and exits non-zero
# on the first failure. The Python pytest suite under this directory
# has its own runner; this orchestrator is only for the shell tests.
set -u
set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fail=0
for t in "$SCRIPT_DIR"/unit/test_*.sh; do
    [[ -e "$t" ]] || continue
    if ! "$t"; then
        echo "FAIL: $t" >&2
        fail=1
    fi
done
exit $fail
