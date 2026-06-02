#!/usr/bin/env bash
# verifies: plugins/sulis/skills/release-train/SKILL.md
# verifies: plugins/sulis/templates/workflows/release-on-merge.yml
#
# test_pin_write_read_parity.sh — the load-bearing cross-WP seam
# (WP-009; TDD §3 / ADR-005 write / ADR-006 read).
#
# The pin is the ONLY piece of state the workflow needs at robot-run
# time to distinguish "clean" from "raced". It is written by
# /sulis:release-train (WP-006) and read by the reusable workflow's
# pin-read step (WP-003). The two sides were authored by different WPs;
# if their formats drift by one byte, the reader silently extracts an
# empty pin and the workflow always takes the raced path. This test
# proves the seam holds:
#
#   1. Reconstruct the EXACT write format from SKILL.md's printf line.
#   2. Reconstruct the EXACT read regex from the workflow's grep line.
#   3. Synthesise a release-PR body using the writer's format with a
#      known 40-hex SHA.
#   4. Apply the reader's regex to that body.
#   5. Assert the extracted SHA byte-equals the SHA the writer embedded.
#
# This asserts against the canonical sources (the live SKILL.md and the
# live workflow), not against two independently hand-copied formats.

set -u
set -o pipefail

. "$(dirname "$0")/../lib/abm_canonical.sh"

[ -f "$ABM_RELEASE_TRAIN_SKILL" ] || abm_fail "release-train SKILL.md missing"
[ -f "$ABM_REUSABLE_WORKFLOW" ]   || abm_fail "reusable workflow missing"

# ---------------------------------------------------------------------
# 1. Extract the writer's printf format from SKILL.md.
#    Expected line (WP-006):
#      printf '\n\n<!-- dev-sha-at-open: %s -->\n' "$DEV_SHA"
#    We assert the format string contains the HTML-comment-wrapped pin
#    token with a %s placeholder.
# ---------------------------------------------------------------------
WRITER_LINE="$(grep -F -- "<!-- ${ABM_PIN_TOKEN}:" "$ABM_RELEASE_TRAIN_SKILL" | grep -F 'printf' | head -n1)"
if [ -z "$WRITER_LINE" ]; then
    abm_fail "could not find the pin-writer printf line in SKILL.md (expected an HTML comment '<!-- ${ABM_PIN_TOKEN}: %s -->')"
fi
# The writer must wrap the SHA in an HTML comment with the exact token.
case "$WRITER_LINE" in
    *"<!-- ${ABM_PIN_TOKEN}: %s -->"*) : ;;  # ok
    *) abm_fail "pin-writer format is not '<!-- ${ABM_PIN_TOKEN}: %s -->'; got: $WRITER_LINE" ;;
esac

# ---------------------------------------------------------------------
# 2. Extract the reader's regex from the workflow's grep line.
#    Expected (WP-003): grep -oE 'dev-sha-at-open: ([a-f0-9]{40})'
#    We assert the live workflow uses exactly ABM_PIN_REGEX.
# ---------------------------------------------------------------------
if ! grep -qF -- "$ABM_PIN_REGEX" "$ABM_REUSABLE_WORKFLOW"; then
    abm_fail "reusable workflow pin-read does not use the canonical regex '$ABM_PIN_REGEX'"
fi

# ---------------------------------------------------------------------
# 3. Synthesise a release-PR body using the writer's format. A known
#    40-hex SHA (deterministic; not inlined from any canonical source —
#    it is test data, not a contract string).
# ---------------------------------------------------------------------
KNOWN_SHA="0123456789abcdef0123456789abcdef01234567"
TMP_BODY="$(mktemp -t abm-pin-body-XXXXXX)"
trap 'rm -f "$TMP_BODY"' EXIT
{
    printf 'Release notes for v9.9.9\n\n'
    printf '%s\n' '- did a thing'
    # Reproduce the writer's exact format (HTML comment, token, SHA).
    printf '\n\n<!-- %s: %s -->\n' "$ABM_PIN_TOKEN" "$KNOWN_SHA"
} > "$TMP_BODY"

# ---------------------------------------------------------------------
# 4. Apply the reader's extraction pipeline (the SAME pipeline the
#    workflow uses: grep -oE <regex> | head -n1 | awk '{print $2}').
# ---------------------------------------------------------------------
EXTRACTED="$(grep -oE "$ABM_PIN_REGEX" "$TMP_BODY" | head -n1 | awk '{print $2}')"

# ---------------------------------------------------------------------
# 5. Assert parity.
# ---------------------------------------------------------------------
if [ "$EXTRACTED" != "$KNOWN_SHA" ]; then
    abm_fail "pin round-trip broke: writer embedded '$KNOWN_SHA', reader extracted '${EXTRACTED:-<empty>}'"
fi

# Negative control: a body WITHOUT the pin must extract empty (the
# safe-default raced path; TDD §5.6).
TMP_NOPIN="$(mktemp -t abm-pin-nopin-XXXXXX)"
printf 'Release notes, no pin here\n' > "$TMP_NOPIN"
NOPIN="$(grep -oE "$ABM_PIN_REGEX" "$TMP_NOPIN" | head -n1 | awk '{print $2}')"
rm -f "$TMP_NOPIN"
if [ -n "$NOPIN" ]; then
    abm_fail "reader extracted a pin from a body that has none: '$NOPIN' (raced-path safe default broken)"
fi

abm_pass "writer format and reader regex round-trip the same 40-hex SHA; absent pin extracts empty (safe default)"
