#!/usr/bin/env bash
# test_drift_check_help_message.sh
#
# Smoke: drift_check.sh --help prints a synopsis that names the
# "dev-behind-main drift" purpose so callers can self-document.
#
# WP-001 Definition of Done — Red item 1 of 3.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="$SCRIPT_DIR/../../drift_check.sh"

if [[ ! -x "$HELPER" ]]; then
    echo "FAIL: $HELPER missing or not executable" >&2
    exit 1
fi

OUTPUT="$("$HELPER" --help 2>&1)"
RC=$?

if [[ $RC -ne 0 ]]; then
    echo "FAIL: --help exited $RC (expected 0)" >&2
    echo "$OUTPUT" >&2
    exit 1
fi

if ! grep -q 'dev-behind-main drift' <<<"$OUTPUT"; then
    echo "FAIL: --help output does not contain 'dev-behind-main drift'" >&2
    echo "--- output ---" >&2
    echo "$OUTPUT" >&2
    exit 1
fi

# WP-001 DoD Green: synopsis names exit codes 0 and 1.
if ! grep -q 'exit 0' <<<"$OUTPUT" || ! grep -q 'exit 1' <<<"$OUTPUT"; then
    echo "FAIL: --help synopsis does not name both exit codes 0 and 1" >&2
    echo "--- output ---" >&2
    echo "$OUTPUT" >&2
    exit 1
fi

echo "PASS: $(basename "$0")"
exit 0
