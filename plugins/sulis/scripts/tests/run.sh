#!/usr/bin/env bash
# run.sh — shell-test orchestrator for the Sulis scripts test suite,
# including the auto-back-merge suite (WP-009).
#
# Runs every test_*.sh under unit/, integration/, chaos/, and
# methodology/ in alphabetical order. Exits 0 iff ALL pass; non-zero
# with a FAILED list otherwise. CI reads the exit code, nothing else
# (WP-009 DoD Blue).
#
# The Python pytest suite under this directory has its own runner
# (`uv run pytest`); this orchestrator is only for the shell tests.
# The shared sourcing helper lib/abm_canonical.sh is sourced by tests,
# never run as a test — it lives under lib/, which is not scanned.
#
# bash-3.2-safe (macOS /bin/bash): no associative arrays, no mapfile.
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PASS=0
FAIL=0
FAILED_TESTS=""

run_directory() {
    dir="$1"
    [ -d "$dir" ] || return 0
    for t in "$dir"/test_*.sh; do
        [ -f "$t" ] || continue
        if bash "$t" >/dev/null 2>&1; then
            PASS=$((PASS + 1))
        else
            FAIL=$((FAIL + 1))
            FAILED_TESTS="${FAILED_TESTS}\n  ${t}"
        fi
    done
}

echo "=== unit ==="
run_directory "$SCRIPT_DIR/unit"
echo "=== integration ==="
run_directory "$SCRIPT_DIR/integration"
echo "=== chaos ==="
run_directory "$SCRIPT_DIR/chaos"
echo "=== methodology ==="
run_directory "$SCRIPT_DIR/methodology"

echo
echo "PASS: $PASS"
echo "FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    printf 'FAILED:%b\n' "$FAILED_TESTS" >&2
    exit 1
fi
exit 0
