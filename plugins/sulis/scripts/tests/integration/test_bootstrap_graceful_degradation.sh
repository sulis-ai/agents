#!/usr/bin/env bash
# verifies: plugins/sulis/scripts/drift_check.sh
#
# test_bootstrap_graceful_degradation.sh — bootstrap-from-zero
# degradation guard (WP-009; TDD §9.3, WP-007 graceful degradation).
#
# A fresh consumer at the shipping plugin version may have a shim
# installed but NO prior releases — and crucially may have a repo whose
# `origin` exists but has no `main` branch yet (the very first release
# has not happened). The drift check must degrade gracefully in that
# state: it must NOT hard-crash with a stack trace or an unhandled git
# error. drift_check.sh's contract is "exit 0 (clean) or exit 1 (drift
# / fetch-or-tool failure, with a human-readable message on stderr)".
# A bootstrap repo with no origin/main is a "cannot verify" case → it
# must exit 1 with a `drift_check:`-prefixed message, never a raw git
# error or a non-{0,1} exit code that would make /sulis:change start
# fail in an undebuggable way.
#
# This test builds a throwaway local bare "origin" that has dev but NO
# main, points a working clone at it, and runs drift_check.sh. It
# asserts:
#   - the exit code is exactly 1 (controlled failure), never >1 or a
#     crash;
#   - stderr carries a `drift_check:`-prefixed message (graceful,
#     attributable);
#   - the script does not emit a raw unhandled git traceback / "fatal:"
#     as its ONLY output (it wraps the failure in its own message).

set -u
set -o pipefail

. "$(dirname "$0")/../lib/abm_canonical.sh"

[ -x "$ABM_DRIFT_CHECK" ] || abm_fail "drift_check.sh missing or not executable at $ABM_DRIFT_CHECK"

TMP="$(mktemp -d -t abm-bootstrap-XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# Build a bare "origin" with a dev branch but NO main branch — the
# fresh-consumer pre-first-release state.
REMOTE="$TMP/origin.git"
git init --bare --initial-branch=dev "$REMOTE" >/dev/null

WORK="$TMP/work"
git clone --quiet "$REMOTE" "$WORK"
(
    cd "$WORK"
    git config user.email "test@example.com"
    git config user.name "Test"
    git checkout -b dev 2>/dev/null || git checkout dev
    echo "bootstrap" > seed.txt
    git add seed.txt
    git commit --quiet -m "first dev commit (no release yet)"
    git push --quiet origin dev
)

# Run drift_check.sh inside the working clone. origin/main does not
# exist → the ancestor check cannot resolve origin/main.
STDERR_FILE="$TMP/stderr.txt"
STDOUT_FILE="$TMP/stdout.txt"
( cd "$WORK" && "$ABM_DRIFT_CHECK" ) > "$STDOUT_FILE" 2> "$STDERR_FILE"
RC=$?

# --- Assertion 1: controlled exit code (exactly 1, the documented
#     failure code — never a crash / signal / >1). ---
if [ "$RC" -ne 1 ]; then
    echo "--- stdout ---" >&2; cat "$STDOUT_FILE" >&2
    echo "--- stderr ---" >&2; cat "$STDERR_FILE" >&2
    abm_fail "drift_check.sh on a no-origin/main bootstrap repo exited $RC; expected the controlled exit 1 (graceful degradation)"
fi

# --- Assertion 2: stderr carries the script's own attributable
#     message, not just a raw git error. ---
if ! grep -q '^drift_check:' "$STDERR_FILE"; then
    echo "--- stderr ---" >&2; cat "$STDERR_FILE" >&2
    abm_fail "drift_check.sh did not emit a 'drift_check:'-prefixed message on the bootstrap (no-origin/main) path"
fi

abm_pass "drift_check.sh degrades gracefully on a fresh consumer with no origin/main (controlled exit 1 + attributable stderr; no crash)"
