#!/usr/bin/env bash
# abm_canonical.sh — shared canonical-string sourcing for the
# auto-back-merge test suite (WP-009).
#
# The whole suite's discipline (WP-009 DoD Blue): NO canonical string
# is hand-written into a test. Every reference to `back-integrate`, the
# title prefix, `dev`, `main`, or the `dev-sha-at-open` pin token is
# sourced from its single declaration — `drift_check.sh`'s constants
# (LABEL / TITLE_PREFIX / BASE_BRANCH / HEAD_BRANCH) for the four
# strings, and the canonical pin regex declared here once (it lives in
# the workflow YAML + ADR-006; this is the one place the test suite
# repeats it, so a single edit moves all consumers).
#
# Source this from any test:
#   . "$(dirname "$0")/../lib/abm_canonical.sh"
# then read $ABM_LABEL, $ABM_TITLE_PREFIX, $ABM_BASE, $ABM_HEAD,
# $ABM_PIN_REGEX, and the path helpers $ABM_REPO_ROOT / $ABM_DRIFT_CHECK
# / $ABM_REUSABLE_WORKFLOW / $ABM_RELEASE_TRAIN_SKILL / $ABM_GIT12_DOC /
# $ABM_BRANCH_CI.
#
# bash-3.2-safe (macOS /bin/bash): no associative arrays, no mapfile.

# ---------------------------------------------------------------------
# Resolve the repo root from this lib file's location.
#   tests/lib/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
# ---------------------------------------------------------------------
_ABM_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ABM_REPO_ROOT="$(cd "$_ABM_LIB_DIR/../../../../.." && pwd)"

# Canonical-source file paths. Every test references production code
# through these — a path drift surfaces as a missing-file failure.
ABM_REUSABLE_WORKFLOW="$ABM_REPO_ROOT/plugins/sulis/templates/workflows/release-on-merge.yml"
ABM_SHIM_TEMPLATE="$ABM_REPO_ROOT/plugins/sulis/templates/shims/release-on-merge.yml"
ABM_MARKETPLACE_SHIM="$ABM_REPO_ROOT/.github/workflows/release-on-merge.yml"
ABM_RELEASE_TRAIN_SKILL="$ABM_REPO_ROOT/plugins/sulis/skills/release-train/SKILL.md"
ABM_GIT12_DOC="$ABM_REPO_ROOT/plugins/sulis/references/git-workflow-standard.md"
ABM_BRANCH_CI="$ABM_REPO_ROOT/.github/workflows/branch-ci.yml"

# (Removed with the trunk cutover: `abm_source_canonical_strings` +
# the dev/main/back-integrate constants + the `dev-sha-at-open` pin regex.
# Those served the two-branch dev→main drift gate (drift_check.sh) and the
# GIT-12 auto-back-merge invariant, both decommissioned — there is no `dev`
# to fall behind on a trunk. The path helpers above + the generic
# helpers below remain for the kept canonical-drift / reusable-workflow /
# loop-guard tests.)

# Convenience: print a PASS line and exit 0 (tests call at the end).
abm_pass() {
    echo "PASS: $(basename "${0:-test}")${1:+ — $1}"
    exit 0
}

# Convenience: print a FAIL line to stderr and exit 1.
abm_fail() {
    echo "FAIL: $1" >&2
    exit 1
}

# ---------------------------------------------------------------------
# Chaos-test shared harness (used by ≥2 consumers — test_race_window.sh
# and test_missing_pin_falls_through.sh — so it lives here per EP-03 /
# RGB-Blue 2-consumer extraction).
# ---------------------------------------------------------------------

# abm_extract_step_body <workflow_yaml> <step_id> <out_file>
# Write the `run:` body of the workflow step whose `id:` matches
# <step_id> to <out_file>. The test then executes <out_file> under
# stubs — so the chaos test exercises the ACTUAL shipped step, never a
# re-typed copy. Returns non-zero (and writes nothing useful) if the
# step is absent or has no run body.
abm_extract_step_body() {
    _abm_wf="$1"; _abm_id="$2"; _abm_out="$3"
    python3 - "$_abm_wf" "$_abm_id" > "$_abm_out" <<'PY'
import sys
import yaml
with open(sys.argv[1]) as f:
    wf = yaml.safe_load(f)
want = sys.argv[2]
for s in (wf.get("jobs", {}).get("release", {}).get("steps") or []):
    if isinstance(s, dict) and s.get("id") == want:
        sys.stdout.write(s.get("run", ""))
        break
else:
    sys.stderr.write(f"step (id: {want}) not found in workflow\n")
    sys.exit(2)
PY
    [ -s "$_abm_out" ]
}

# abm_build_recording_stubs <bin_dir> <call_log> <current_dev_sha>
# Materialise stub `git` and `gh` binaries under <bin_dir>. Each logs
# its full argv to <call_log>; `git ls-remote` returns <current_dev_sha>
# on refs/heads/dev. `gh pr create` returns a fake PR URL. Put <bin_dir>
# first on PATH to use them. The push stub SUCCEEDS so a wrongful
# clean-path push is recorded (visible) rather than hidden behind a
# fall-through to the PR path.
abm_build_recording_stubs() {
    _abm_bin="$1"; _abm_log="$2"; _abm_dev="$3"
    mkdir -p "$_abm_bin"

    cat > "$_abm_bin/git" <<EOF
#!/usr/bin/env bash
echo "git \$*" >> "$_abm_log"
case "\$1" in
  fetch) exit 0 ;;
  ls-remote) echo "$_abm_dev	refs/heads/dev"; exit 0 ;;
  push) exit 0 ;;
  *) exit 0 ;;
esac
EOF

    cat > "$_abm_bin/gh" <<EOF
#!/usr/bin/env bash
echo "gh \$*" >> "$_abm_log"
case "\$1 \$2" in
  "pr create") echo "https://github.com/sulis-ai/agents/pull/4242"; exit 0 ;;
  "pr merge") exit 0 ;;
  "pr list") echo ""; exit 0 ;;
  *) exit 0 ;;
esac
EOF

    chmod +x "$_abm_bin/git" "$_abm_bin/gh"
}
