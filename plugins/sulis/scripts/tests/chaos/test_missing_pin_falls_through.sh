#!/usr/bin/env bash
# verifies: plugins/sulis/templates/workflows/release-on-merge.yml
#
# test_missing_pin_falls_through.sh — safe-default chaos test (WP-009;
# TDD §5.6 pin tampering / safe defaults).
#
# When the pin is absent or malformed, the regex extracts nothing and
# DEV_SHA_PIN is empty. The decide+act step must treat empty-pin as the
# RACED path (open a back-integrate PR) — the safe default. It must NOT
# fast-forward dev (a force-equivalent risk) on a missing pin.
#
# Same harness shape as test_race_window.sh: extract the live decide+act
# step body, run it under stub git/gh with DEV_SHA_PIN="" (empty), and
# assert the PR-open path fires and dev is never pushed.

set -u
set -o pipefail

. "$(dirname "$0")/../lib/abm_canonical.sh"

[ -f "$ABM_REUSABLE_WORKFLOW" ] || abm_fail "reusable workflow missing at $ABM_REUSABLE_WORKFLOW"

TMP="$(mktemp -d -t abm-nopin-XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

CALL_LOG="$TMP/calls.log"
: > "$CALL_LOG"

# Extract the live decide+act step + build the recording stubs via the
# shared lib harness (same harness test_race_window.sh uses).
STEP_BODY="$TMP/backmerge_step.sh"
abm_extract_step_body "$ABM_REUSABLE_WORKFLOW" "backmerge" "$STEP_BODY" \
    || abm_fail "could not extract the decide+act (id: backmerge) step body"

CURRENT_DEV_SHA="0000111122223333444455556666777788889999"
STUB_BIN="$TMP/bin"
abm_build_recording_stubs "$STUB_BIN" "$CALL_LOG" "$CURRENT_DEV_SHA"

# Empty pin — the safe-default trigger.
export DEV_SHA_PIN=""
export NEW_META="1.2.3"
export GITHUB_OUTPUT="$TMP/gh_output"
: > "$GITHUB_OUTPUT"

(
    PATH="$STUB_BIN:$PATH"
    export PATH
    bash "$STEP_BODY"
) > "$TMP/step_stdout" 2>&1 || true

abm_source_canonical_strings || abm_fail "could not source canonical strings"

# Empty pin → raced path → gh pr create must fire.
if ! grep -q "gh pr create" "$CALL_LOG"; then
    echo "--- call log ---" >&2; cat "$CALL_LOG" >&2
    echo "--- step stdout ---" >&2; cat "$TMP/step_stdout" >&2
    abm_fail "empty pin did NOT fall through to the PR-open path (safe default broken)"
fi

# dev must never be pushed on the safe-default path.
if grep -qE "git push .*main:dev" "$CALL_LOG"; then
    cat "$CALL_LOG" >&2
    abm_fail "empty pin path pushed dev — must open a PR, never fast-forward on a missing pin"
fi

# No force flag at runtime.
if grep -qE "(--force|--force-with-lease|\+main:dev)" "$CALL_LOG"; then
    cat "$CALL_LOG" >&2
    abm_fail "force flag appeared at runtime on the empty-pin path — NFR-002 violated"
fi

abm_pass "absent/empty pin falls through to the ${ABM_LABEL} PR path (safe default); never pushes dev; no force flag"
