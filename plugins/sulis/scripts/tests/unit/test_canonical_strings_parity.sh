#!/usr/bin/env bash
# verifies: plugins/sulis/scripts/drift_check.sh
# verifies: plugins/sulis/templates/workflows/release-on-merge.yml
# verifies: plugins/sulis/skills/release-train/SKILL.md
# verifies: plugins/sulis/references/git-workflow-standard.md
#
# test_canonical_strings_parity.sh — THE load-bearing P8 enforcement
# (WP-009; TDD §3 Canonical Identifiers).
#
# The design's correctness rests on four strings being identical across
# four files. A subtle typo (e.g. `back_integrate` vs `back-integrate`)
# would break the mechanism silently: the drift gate would not find the
# open PR; the workflow would not filter the PR list correctly. This
# test catches the entire "one source drifted, the rest didn't" bug
# class.
#
# The four canonical strings (TDD §3):
#   LABEL        = back-integrate
#   TITLE_PREFIX = chore: back-integrate main → dev
#   BASE_BRANCH  = dev
#   HEAD_BRANCH  = main
#
# Four sources:
#   1. drift_check.sh                       — LABEL/TITLE_PREFIX/BASE/HEAD constants
#   2. templates/workflows/release-on-merge.yml — the workflow literals
#   3. skills/release-train/SKILL.md        — drift recovery message + pin
#   4. references/git-workflow-standard.md  — GIT-12 worked examples
#
# Method: take drift_check.sh as the single source of truth (every
# other component is contracted to match it), then assert each of the
# other three sources contains each string byte-for-byte.

set -u
set -o pipefail

. "$(dirname "$0")/../lib/abm_canonical.sh"

abm_source_canonical_strings || abm_fail "could not source canonical strings"

# Sanity: drift_check.sh declared all four.
[ -n "${ABM_LABEL:-}" ]        || abm_fail "drift_check.sh LABEL is empty"
[ -n "${ABM_TITLE_PREFIX:-}" ] || abm_fail "drift_check.sh TITLE_PREFIX is empty"
[ -n "${ABM_BASE:-}" ]         || abm_fail "drift_check.sh BASE_BRANCH is empty"
[ -n "${ABM_HEAD:-}" ]         || abm_fail "drift_check.sh HEAD_BRANCH is empty"

for f in "$ABM_REUSABLE_WORKFLOW" "$ABM_RELEASE_TRAIN_SKILL" "$ABM_GIT12_DOC"; do
    [ -f "$f" ] || abm_fail "canonical source missing: $f"
done

# ---------------------------------------------------------------------
# Assert a literal string is present in a file. Uses grep -F (fixed
# string) so the UTF-8 arrow and the colon in the title prefix are not
# treated as regex metacharacters.
# ---------------------------------------------------------------------
assert_in_file() {
    needle="$1"; file="$2"; what="$3"
    if ! grep -qF -- "$needle" "$file"; then
        abm_fail "$what '$needle' (from drift_check.sh) NOT found in $(basename "$file")"
    fi
}

# --- LABEL: back-integrate ---
# Present in the workflow (--label back-integrate), the SKILL.md drift
# message (gh pr list --label back-integrate), and GIT-12 examples.
assert_in_file "$ABM_LABEL" "$ABM_REUSABLE_WORKFLOW"     "LABEL (workflow)"
assert_in_file "$ABM_LABEL" "$ABM_RELEASE_TRAIN_SKILL"   "LABEL (release-train SKILL.md)"
assert_in_file "$ABM_LABEL" "$ABM_GIT12_DOC"             "LABEL (GIT-12)"

# --- TITLE_PREFIX: chore: back-integrate main → dev ---
# Present in the workflow (gh pr create --title) and GIT-12 examples.
# (Not required in SKILL.md — the skill writes the pin and the drift
# message, not the back-merge PR title; the workflow owns that.)
assert_in_file "$ABM_TITLE_PREFIX" "$ABM_REUSABLE_WORKFLOW" "TITLE_PREFIX (workflow)"
assert_in_file "$ABM_TITLE_PREFIX" "$ABM_GIT12_DOC"         "TITLE_PREFIX (GIT-12)"

# --- BASE_BRANCH / HEAD_BRANCH: dev / main ---
# These two are single words that appear ubiquitously; asserting raw
# presence is meaningless. Instead, assert they appear in the
# back-merge PR-create context where they are load-bearing: the
# workflow must use `--base dev --head main` and GIT-12 must document
# `base: dev` / `head: main`.
if ! grep -qE -- "--base[[:space:]]+${ABM_BASE}[[:space:]]+--head[[:space:]]+${ABM_HEAD}" "$ABM_REUSABLE_WORKFLOW"; then
    abm_fail "workflow does not use '--base ${ABM_BASE} --head ${ABM_HEAD}' in the back-merge PR-create"
fi
# GIT-12 documents base/head in its worked example (the form there is
# 'base: dev' / 'head: main').
assert_in_file "base: ${ABM_BASE}"  "$ABM_GIT12_DOC" "BASE in GIT-12 worked example"
assert_in_file "head: ${ABM_HEAD}"  "$ABM_GIT12_DOC" "HEAD in GIT-12 worked example"

# ---------------------------------------------------------------------
# Pin-token parity: the `dev-sha-at-open` token must appear in the
# SKILL.md writer, the workflow reader, and the GIT-12 docs — all from
# the single ABM_PIN_TOKEN declaration.
# ---------------------------------------------------------------------
assert_in_file "$ABM_PIN_TOKEN" "$ABM_RELEASE_TRAIN_SKILL" "pin token (writer SKILL.md)"
assert_in_file "$ABM_PIN_TOKEN" "$ABM_REUSABLE_WORKFLOW"   "pin token (reader workflow)"
assert_in_file "$ABM_PIN_TOKEN" "$ABM_GIT12_DOC"           "pin token (GIT-12)"

abm_pass "all four canonical strings + pin token agree across drift_check.sh, workflow, SKILL.md, GIT-12"
