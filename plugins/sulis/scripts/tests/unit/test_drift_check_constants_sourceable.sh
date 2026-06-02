#!/usr/bin/env bash
# test_drift_check_constants_sourceable.sh
#
# The four canonical-string constants (LABEL, TITLE_PREFIX, BASE_BRANCH,
# HEAD_BRANCH) must be sourceable from drift_check.sh and exact-match
# the TDD §3 canonical identifiers. WP-009 expands this to the full
# cross-component parity check (workflow + release-train SKILL.md);
# this WP locks the source-of-truth values here.
#
# WP-001 Definition of Done — Red item 2 of 3.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="$SCRIPT_DIR/../../drift_check.sh"

if [[ ! -f "$HELPER" ]]; then
    echo "FAIL: $HELPER missing" >&2
    exit 1
fi

# Source in a subshell so we don't pollute this test's environment.
# DRIFT_CHECK_SOURCED_ONLY=1 is the contract sentinel that tells the
# helper "do not run the check; just declare constants".
(
    set -u
    export DRIFT_CHECK_SOURCED_ONLY=1
    # shellcheck disable=SC1090
    source "$HELPER"

    if [[ "${LABEL:-}" != "back-integrate" ]]; then
        echo "FAIL: LABEL='${LABEL:-<unset>}' (expected 'back-integrate')" >&2
        exit 1
    fi

    if [[ "${TITLE_PREFIX:-}" != "chore: back-integrate main → dev" ]]; then
        echo "FAIL: TITLE_PREFIX='${TITLE_PREFIX:-<unset>}'" >&2
        echo "       expected 'chore: back-integrate main → dev'" >&2
        exit 1
    fi

    if [[ "${BASE_BRANCH:-}" != "dev" ]]; then
        echo "FAIL: BASE_BRANCH='${BASE_BRANCH:-<unset>}' (expected 'dev')" >&2
        exit 1
    fi

    if [[ "${HEAD_BRANCH:-}" != "main" ]]; then
        echo "FAIL: HEAD_BRANCH='${HEAD_BRANCH:-<unset>}' (expected 'main')" >&2
        exit 1
    fi

    exit 0
) || exit 1

echo "PASS: $(basename "$0")"
exit 0
