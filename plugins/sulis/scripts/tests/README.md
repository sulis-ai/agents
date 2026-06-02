# sulis-execution test suite

Pytest-based integration tests for the wpx-* CLI tools. Mirrors the
established pattern at `plugins/sulis/skills/analyse-codebase/tests/`.

## Layout

```
tests/
├── conftest.py        # Shared fixtures: tmp_project, run_tool, mock_gh, local_git_repo
├── unit/              # Direct imports of _wpxlib helpers; no subprocess
├── integration/       # wpx-* invoked via subprocess; cross-tool flows
├── e2e/               # Full calling-session Step 8-12 simulation (future)
└── fixtures/          # INDEX.md / WP.md / journal templates + gh response JSON
```

## Running

```bash
# From the marketplace repo root
pip install pytest
pytest plugins/sulis-execution/scripts/tests/ -v
```

Python 3.11+ recommended (matches the wpx-* tools' target).

## What's covered

- **Unit tests** for `_wpxlib`: `parse_frontmatter`, `MdTable / parse_md_table`,
  `find_section / replace_section`, `read_frontmatter`.
- **Integration tests** per tool, invoking each via subprocess to match
  the real-user surface (same code path as the agent uses):
  - `test_wpx_index.py` — flip-status, list-ready, add-wp, sync-auto-drafts,
    propagate-blocked. **Locks down v0.10.5 Bug 2** (multi-table INDEX parsing).
  - `test_wpx_journal.py` — init, step-trace round-trip, seed-plan,
    mark-plan-item atomic check, read --field plan.
  - `test_wpx_pipeline.py` — auto-skip CI when no branch CI; explicit
    `--skip-ci-poll`; emit_ok exit_code paths (v0.10.4 regression).
    **Locks down v0.10.5 Bug 1** (already-merged branch detection).
  - `test_wpx_step12.py` — happy path, multi-line JSON parse, ok:false
    propagation, --repo-root propagation (v0.10.2 regressions).

## Mocking strategy

- **gh CLI:** mocked via the `mock_gh` fixture, which installs a fake
  `gh` binary at the front of `PATH`. Tests configure a substring-match
  dispatch table of canned JSON responses (see `conftest.py`).
- **git:** NOT mocked. Tests that need git operations use the
  `local_git_repo` fixture, which initialises a real local repo + dev
  branch + an `origin` bare remote. Git is fast and deterministic;
  mocking would be more fragile than using it.
- **HTTP / curl:** Not currently exercised; future tests for the health
  check step can mock curl the same way as gh.

## Regression locks

Two tests serve as explicit regression locks for v0.10.5:

- `test_wpx_pipeline.py::test_already_merged_branch_skips_merge_step` —
  fails pre-fix when re-running the pipeline on an already-squash-merged
  branch (GitHub's POST /merges returns 409 → _gh_merge raises
  RuntimeError → outcome=error). Post-fix, `_gh_branch_already_merged`
  detects via the compare API and skips the merge step.
- `test_wpx_index.py::test_flip_status_finds_wp_table_after_primitive_summary` —
  fails pre-fix when INDEX.md has a `| ID |`-headed table preceding the
  canonical WP table (e.g., a primitive-summary table); `_find_wp_table`
  matches the wrong table. Post-fix, the heading-anchored + column-aware
  finder picks the correct WP table.

If either test fails, do NOT ship — a known production bug has
regressed.

## Adding tests

1. Identify the integration boundary (cross-tool dispatch, gh API,
   git state).
2. Add a fixture file if needed under `fixtures/` (INDEX.md / WP.md /
   journal / gh response JSON).
3. Write the test under `integration/`.
4. Use `run_tool(...)` for any wpx-* invocation. Use `mock_gh(...)` for
   gh API responses. Use `local_git_repo` for git operations.
5. Run `pytest plugins/sulis-execution/scripts/tests/ -v` and confirm
   green before commit.

---

# Auto-back-merge shell suite (WP-009)

Alongside the pytest suite above, a **bash** test suite proves the
auto-back-merge-on-release mechanism (the reusable workflow + shim +
pin + drift gate + GIT-12). It is bash because the subjects are bash
(`drift_check.sh`), YAML (the workflow), and SKILL.md prose — there is
nothing Python to import, and the assertions are over file content +
extracted workflow step bodies.

## Layout

```
tests/
├── run.sh                  # shell-test orchestrator (unit/integration/chaos/methodology)
├── bootstrap_from_zero.sh  # fresh-consumer end-to-end (gated by BOOTSTRAP_ENABLED=1)
├── DOGFOOD_ACCEPTANCE.md   # the n=1 post-ship observable (manual, not CI-executable)
├── lib/
│   └── abm_canonical.sh    # shared helper: sources canonical strings + chaos harness
├── unit/                   # sub-second static + parity checks
├── integration/            # local git-remote / shim-indirection / bootstrap-degradation
├── chaos/                  # race-window simulation (decide+act under stubs)
├── methodology/            # WP-002 move characterisation (reconciled in WP-009)
└── fixtures/
    ├── drift_check/        # setup.sh rebuilds repo-clean/ + repo-drifted/ remotes; gh-stubs/
    └── release-on-merge/   # pre-move-snapshot.yml + release-pr-body-with-pin.txt
```

## Running

```bash
# All shell tests (exit 0 iff every test passes):
bash plugins/sulis/scripts/tests/run.sh

# A single test:
bash plugins/sulis/scripts/tests/unit/test_canonical_strings_parity.sh

# The fresh-consumer end-to-end (needs gh auth + sandbox-repo perms):
BOOTSTRAP_ENABLED=1 SHIPPING_VERSION=0.3.0 \
  bash plugins/sulis/scripts/tests/bootstrap_from_zero.sh
```

CI reads `run.sh`'s exit code, nothing else. Tests are bash-3.2-safe
(they run on macOS `/bin/bash`).

## The canonical-string discipline (the most important rule)

The design's correctness rests on **four strings being identical
across four files** — the `back-integrate` label, the
`chore: back-integrate main → dev` title prefix, and the back-merge
PR's `dev` base / `main` head — plus the `dev-sha-at-open` pin token.
A one-character drift (e.g. `back_integrate` vs `back-integrate`)
breaks the mechanism silently.

So: **no test hand-writes a canonical string.** Every test sources the
four strings from their single declaration — `drift_check.sh`'s
`LABEL` / `TITLE_PREFIX` / `BASE_BRANCH` / `HEAD_BRANCH` constants —
via `lib/abm_canonical.sh`:

```bash
. "$(dirname "$0")/../lib/abm_canonical.sh"
abm_source_canonical_strings   # exports $ABM_LABEL, $ABM_TITLE_PREFIX, $ABM_BASE, $ABM_HEAD
```

`unit/test_canonical_strings_parity.sh` is the load-bearing enforcer:
it asserts the four strings agree across `drift_check.sh`, the reusable
workflow YAML, the release-train SKILL.md, and GIT-12. If a future WP
edits one source without the others, that test fails loudly.

## The load-bearing tests

| Test | What it proves |
|---|---|
| `unit/test_canonical_strings_parity.sh` | The four canonical strings + pin token agree across all four sources (P8). |
| `unit/test_pin_write_read_parity.sh` | The pin format `/sulis:release-train` writes round-trips through the workflow's read regex (the cross-WP seam). |
| `unit/test_drift_detector_points_at_reusable.sh` | branch-ci's `--yaml-path` **argument** targets the annotated reusable workflow, not a comment substring and not the annotation-free shim. |
| `integration/test_loop_guard_survives_indirection.sh` | The loop-guard `if:` lives in the reusable workflow and the shim forwards the push context + secrets through the `workflow_call` indirection. |
| `integration/test_bootstrap_graceful_degradation.sh` | `drift_check.sh` degrades gracefully (controlled exit 1 + attributable message) on a fresh consumer with no `origin/main`. |
| `chaos/test_race_window.sh` | When current dev ≠ pin, the **actual** decide+act step opens a `back-integrate` PR and never pushes dev / never uses `--force` at runtime (MUC-001). |
| `chaos/test_missing_pin_falls_through.sh` | Absent/malformed pin → raced PR path (the safe default). |
| `methodology/test_release_on_merge_yaml_unchanged_behaviour.sh` | The WP-002 move is faithful (moved block byte-equivalent to snapshot) and the back-merge block is exactly the three intended appended steps. |

The chaos tests **execute the workflow's real step body** (extracted
from the live YAML via `abm_extract_step_body`) under recording git/gh
stubs (`abm_build_recording_stubs`) — so they exercise shipped code,
not a re-typed copy.

## Adding a shell test

1. Put it under `unit/`, `integration/`, `chaos/`, or `methodology/`
   as `test_*.sh`; `run.sh` discovers it automatically.
2. Source `lib/abm_canonical.sh`; never inline a canonical string.
3. Add a `# verifies: <production-file>` header naming what it pins.
4. Do NOT use `set -e` — the tests check exit codes themselves; use
   `set -u` + `set -o pipefail` and explicit `abm_fail` / `abm_pass`.
5. Keep it bash-3.2-safe (no `mapfile`, no associative arrays).
6. Run `bash plugins/sulis/scripts/tests/run.sh` and confirm green.
