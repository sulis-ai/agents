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
