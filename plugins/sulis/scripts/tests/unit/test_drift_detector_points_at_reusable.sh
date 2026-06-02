#!/usr/bin/env bash
# verifies: .github/workflows/branch-ci.yml
#
# test_drift_detector_points_at_reusable.sh — path-drift regression
# guard (WP-009).
#
# The canonical drift detector (check-canonical-drift.py) reads the
# annotated release workflow and compares it against the release-train
# entity instance. When WP-002 moved the annotated workflow into the
# plugin (templates/workflows/release-on-merge.yml) and WP-005 turned
# the marketplace's .github/workflows/release-on-merge.yml into a thin
# annotation-free shim, branch-ci.yml's `--yaml-path` had to follow the
# annotations to the plugin path. The fix landed during WP-005's CI.
#
# THE REGRESSION THIS GUARDS: the existing Python test
# (test_branch_ci_has_drift_check.py) asserts the path fragment
# '.github/workflows/release-on-merge.yml' appears *somewhere* in
# branch-ci.yml — and it does, but only inside a COMMENT explaining the
# move. That is a false positive: the assertion would still pass even if
# the actual `--yaml-path` argument pointed at the wrong file. This test
# closes that gap by inspecting the ARGUMENT VALUE the script is invoked
# with, not raw text anywhere in the file.
#
# Assertions:
#   1. The `canonical-drift-check` job's run: block invokes
#      check-canonical-drift.py with `--yaml-path` pointing at the
#      reusable workflow (plugins/.../templates/workflows/release-on-merge.yml).
#   2. The `--yaml-path` argument does NOT point at the marketplace shim
#      (.github/workflows/release-on-merge.yml) — the shim has no
#      canonical:step annotations, so pointing there would make the
#      detector trivially "clean" and blind to real drift.
#
# Structural assertion over the parsed YAML run: block (PyYAML), with an
# argument-aware extraction so comments and prose can never satisfy it.

set -u
set -o pipefail

. "$(dirname "$0")/../lib/abm_canonical.sh"

[ -f "$ABM_BRANCH_CI" ] || abm_fail "branch-ci.yml missing at $ABM_BRANCH_CI"

if python3 - "$ABM_BRANCH_CI" <<'PY'
import re
import sys
import yaml

branch_ci_path = sys.argv[1]
with open(branch_ci_path) as f:
    doc = yaml.safe_load(f)


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


jobs = doc.get("jobs") or {}
job = jobs.get("canonical-drift-check")
if job is None:
    fail("branch-ci.yml has no 'canonical-drift-check' job")

# Concatenate every step's run: block — the script invocation lives in
# one of them. PyYAML strips YAML comments during parse, so anything we
# see here is REAL run-script content, never a YAML comment. (That alone
# eliminates the comment false-positive that the existing Python test
# falls into, but we go further and parse the actual argument value.)
steps = job.get("steps") or []
run_text = "\n".join(
    s.get("run", "") for s in steps if isinstance(s, dict)
)

if "check-canonical-drift.py" not in run_text:
    fail("canonical-drift-check job does not invoke check-canonical-drift.py")

# Extract the VALUE passed to --yaml-path. Tolerate quoting and the
# $GITHUB_WORKSPACE-absolute prefix; capture up to the next whitespace
# or closing quote.
m = re.search(r'--yaml-path[=\s]+"?([^"\s]+)"?', run_text)
if not m:
    fail("could not find a --yaml-path argument in the drift-check run: block")
yaml_path_value = m.group(1)

# --- Assertion 1: argument points at the reusable workflow. ---
REUSABLE_FRAGMENT = "plugins/sulis/templates/workflows/release-on-merge.yml"
if REUSABLE_FRAGMENT not in yaml_path_value:
    fail(
        "--yaml-path ARGUMENT does not point at the reusable workflow.\n"
        f"  expected to contain: {REUSABLE_FRAGMENT}\n"
        f"  actual argument:     {yaml_path_value}"
    )

# --- Assertion 2: argument does NOT point at the marketplace shim. ---
# The shim path ends in '.github/workflows/release-on-merge.yml'. The
# reusable path does not contain '.github/workflows/', so a correct
# argument fails this substring check; a regressed one (pointing back at
# the shim) trips it.
SHIM_FRAGMENT = ".github/workflows/release-on-merge.yml"
if SHIM_FRAGMENT in yaml_path_value:
    fail(
        "--yaml-path ARGUMENT points at the annotation-free marketplace "
        "shim, which would blind the drift detector.\n"
        f"  actual argument: {yaml_path_value}"
    )

print(
    "OK: --yaml-path argument targets the reusable workflow "
    f"({yaml_path_value}); not the annotation-free shim"
)
PY
then
    abm_pass "drift detector --yaml-path argument points at the reusable workflow (not a comment, not the shim)"
else
    abm_fail "drift-path assertion failed (see message above)"
fi
