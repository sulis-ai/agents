#!/usr/bin/env bash
# verifies: plugins/sulis/templates/workflows/release-on-merge.yml
#
# test_race_window.sh — the load-bearing chaos test for MUC-001
# (WP-009; TDD §6.3).
#
# A real-world race (dev advancing during the release window) is hard to
# provoke on demand. This chaos test simulates it: it extracts the
# reusable workflow's decide+act step body, runs it under a stub `git`
# and stub `gh` that record every call, with the environment rigged so
# that the current dev SHA differs from the pin. Assertions:
#
#   - The decide+act logic takes the RACED path (pin != current dev).
#   - `gh pr create --base dev --head main --label back-integrate` IS
#     invoked (verified via the stub's recorded call log).
#   - `git push origin main:dev` is NEVER invoked.
#   - NO `--force` / `--force-with-lease` flag appears in ANY recorded
#     call — even at runtime, not just in the static YAML.
#
# How the step body is obtained: rather than re-typing the logic (which
# would let the test pass while the workflow drifts), we extract the
# `run:` block of the 'Fast-forward dev to main...' step straight from
# the live YAML via PyYAML and execute it. The test therefore exercises
# the ACTUAL shipped code path.

set -u
set -o pipefail

. "$(dirname "$0")/../lib/abm_canonical.sh"

[ -f "$ABM_REUSABLE_WORKFLOW" ] || abm_fail "reusable workflow missing at $ABM_REUSABLE_WORKFLOW"

TMP="$(mktemp -d -t abm-race-XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

CALL_LOG="$TMP/calls.log"
: > "$CALL_LOG"

# ---------------------------------------------------------------------
# Extract the decide+act step's run: body from the live workflow YAML
# (id: backmerge) and build the recording git/gh stubs. Both come from
# the shared lib so test_race_window.sh and test_missing_pin_falls_
# through.sh use one harness (EP-03 2-consumer extraction).
# ---------------------------------------------------------------------
STEP_BODY="$TMP/backmerge_step.sh"
abm_extract_step_body "$ABM_REUSABLE_WORKFLOW" "backmerge" "$STEP_BODY" \
    || abm_fail "could not extract the decide+act (id: backmerge) step body from the workflow"

# Rigged values: current dev SHA differs from the pin → raced path.
CURRENT_DEV_SHA="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
STUB_BIN="$TMP/bin"
abm_build_recording_stubs "$STUB_BIN" "$CALL_LOG" "$CURRENT_DEV_SHA"

# ---------------------------------------------------------------------
# Run the extracted step body with:
#   - the stubs first on PATH,
#   - DEV_SHA_PIN set to a value DIFFERENT from CURRENT_DEV_SHA (race!),
#   - the GitHub-Actions output sink redirected to a temp file,
#   - NEW_META set so the PR title can be composed.
# ---------------------------------------------------------------------
DEV_SHA_PIN="cafebabecafebabecafebabecafebabecafebabe"  # != CURRENT_DEV_SHA
export DEV_SHA_PIN
export NEW_META="9.9.9"
export GITHUB_OUTPUT="$TMP/gh_output"
: > "$GITHUB_OUTPUT"

# The step body uses `set -uo pipefail` and `exit 0` on the clean path;
# run it in a subshell so its exit doesn't terminate this test. The
# step's own exit code is irrelevant to these assertions — we assert on
# the recorded CALL LOG (what calls it made), not on how it exited — so
# we don't capture $? here.
(
    PATH="$STUB_BIN:$PATH"
    export PATH
    bash "$STEP_BODY"
) > "$TMP/step_stdout" 2>&1 || true

# ---------------------------------------------------------------------
# Assertions.
# ---------------------------------------------------------------------

# 1. The raced path must have run `gh pr create` with the canonical
#    label / base / head (sourced from drift_check.sh).
abm_source_canonical_strings || abm_fail "could not source canonical strings"

if ! grep -q "gh pr create" "$CALL_LOG"; then
    echo "--- call log ---" >&2; cat "$CALL_LOG" >&2
    echo "--- step stdout ---" >&2; cat "$TMP/step_stdout" >&2
    abm_fail "raced path did NOT invoke 'gh pr create' (pin != current dev should open a ${ABM_LABEL} PR)"
fi
if ! grep -qE "gh pr create.*--base ${ABM_BASE}.*--head ${ABM_HEAD}" "$CALL_LOG"; then
    cat "$CALL_LOG" >&2
    abm_fail "'gh pr create' did not use '--base ${ABM_BASE} --head ${ABM_HEAD}'"
fi
if ! grep -qE "gh pr create.*--label ${ABM_LABEL}" "$CALL_LOG"; then
    cat "$CALL_LOG" >&2
    abm_fail "'gh pr create' did not use '--label ${ABM_LABEL}'"
fi

# 2. `git push origin main:dev` must NEVER have been invoked — the raced
#    path opens a PR; it does not push dev.
if grep -qE "git push .*main:dev" "$CALL_LOG"; then
    cat "$CALL_LOG" >&2
    abm_fail "raced path invoked 'git push ... main:dev' — it must open a PR, never push dev"
fi

# 3. NO force flag in ANY recorded call (runtime no-force invariant).
if grep -qE "(--force|--force-with-lease|\+main:dev)" "$CALL_LOG"; then
    cat "$CALL_LOG" >&2
    abm_fail "a force-push flag (or +main:dev refspec) appeared in a runtime call — NFR-002 violated"
fi

abm_pass "raced path opens a ${ABM_LABEL} PR (--base ${ABM_BASE} --head ${ABM_HEAD} --label ${ABM_LABEL}); never pushes dev; no force flag at runtime"
