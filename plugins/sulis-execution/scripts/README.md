# wpx-* — Work Package Executor CLI tool library

Deterministic helper tools the executor agent + calling session invoke
via Bash for all bookkeeping operations in the v0.9.0+ executor
lifecycle.

The tools eliminate agent format-drift on repeatable operations
(journal updates, INDEX flips, BLOCKER writes, findings register,
acceptance evidence, worktree management, the long-running CI +
deploy + health + smoke pipeline, and Step 12 bookkeeping wrap).

## Why these exist

Production observations across v0.5.x–v0.8.x showed the executor
drifting on bookkeeping at depth — format-misaligning table rows,
forgetting fields, rationalising that "knowing" a verdict was as
good as persisting it. Discipline-as-policy reached its limit;
discipline-as-mechanism (these tools) is the next step.

For the architectural rationale, see
`../references/lifecycle.md` and the v0.9.0 design notes.

## Tools

| Tool | Purpose | Typical caller |
|---|---|---|
| `wpx-journal` | Manage `.executor-WP-NNN.md` per-WP journal | Executor agent |
| `wpx-index` | Manage INDEX.md: flip-status, set-status, list-ready, read-config, propagate-blocked, add-wp (v0.10.3+), sync-auto-drafts (v0.10.3+) | Calling session + executor |
| `wpx-wp` | Read WP frontmatter; append acceptance evidence | Calling session + executor |
| `wpx-blocker` | Write BLOCKER-WP-NNN.md per EL-08 format | Executor agent |
| `wpx-findings` | Findings register + SF files + auto-draft WPs | Calling session |
| `wpx-worktree` | Create/remove worktrees; record dev SHA | Executor + calling session |
| `wpx-pipeline` | Steps 8-10: CI poll + merge + deploy + health + smoke | Calling session (via background Bash) |
| `wpx-step12` | Step 12 bookkeeping wrap (atomic) | Calling session |
| `wpx` (v0.10.1+) | Dispatcher wrapper — one-time PATH install for human ad-hoc use | Humans (debug, recovery, exploration) |

## Common conventions

All tools share these conventions:

- **First positional arg**: subcommand (`init`, `start-step`, etc).
- **Flags**: `--kebab-case`, `--project <slug>` for project-relative paths.
- **JSON output**: structured to stdout when a result is returned.
- **Errors**: human-readable to stderr.
- **Exit codes**: `0` success, `1` user/data error (bad args, file not found, expected failure), `2` internal error (bug, unexpected).

## Installation

The tools are plain Python 3 files with `#!/usr/bin/env python3` shebang. Dependencies: **stdlib only**. No `click`, no `pyyaml` required — frontmatter is parsed with a tiny inline parser sufficient for the executor's needs.

When the sulis-execution plugin is installed via the Claude Code marketplace, the scripts land at:

```
~/.claude/plugins/cache/sulis-ai-agents/sulis-execution/<version>/scripts/
```

The version directory changes with each plugin upgrade, so callers cannot hard-code the path.

### Agent invocation (automatic)

The executor agent and the `run-all` / `run-wp` skills resolve the tool directory automatically at session start. The first Bash call in every session is a path-resolution preamble:

```bash
WPX_DIR=$(
  find ~/.claude/plugins/cache \
    -name wpx-journal -type f \
    -path '*/sulis-execution/*/scripts/*' \
    2>/dev/null \
  | sort -r | head -1 | xargs -I{} dirname {} 2>/dev/null
)
# Dev fallback: marketplace repo cwd
if [ -z "$WPX_DIR" ] && [ -f "plugins/sulis-execution/scripts/wpx-journal" ]; then
  WPX_DIR="$(pwd)/plugins/sulis-execution/scripts"
fi
```

All subsequent invocations use `"$WPX_DIR/wpx-NAME"`. See `agents/executor.md` and `skills/run-all/SKILL.md` for the canonical preamble text. **No setup is required for the agent path.**

### Human invocation via the `wpx` wrapper (one-time setup, opt-in)

For ad-hoc human use — manual journal reads, recovery, debugging, exploration — install the `wpx` dispatcher to your PATH:

```bash
mkdir -p ~/.local/bin
ln -sf "$(find ~/.claude/plugins/cache -name wpx -path '*/sulis-execution/*/scripts/*' -type f | sort -r | head -1)" ~/.local/bin/wpx

# Verify (should print the resolved scripts directory)
wpx resolve
```

Make sure `~/.local/bin` is on your `$PATH` (most shells include it by default; check with `echo $PATH | tr ':' '\n' | grep local`).

After install, the wrapper dispatches to any wpx-* subtool by name:

```bash
# From any project directory
wpx journal init   --wp WP-7  --project kinds-and-tools --repo-root .
wpx index list-ready          --project kinds-and-tools --repo-root .
wpx journal read   --wp WP-7  --project kinds-and-tools --repo-root . --field plan

wpx --help    # list subtools
wpx resolve   # diagnostic — print the resolved scripts directory
```

The wrapper does its own resolution at each invocation (same logic as the agent preamble), so it always dispatches to the latest installed version even when the plugin is upgraded. No re-link needed on plugin upgrade.

### Direct invocation (development from the marketplace repo)

If you are working inside the marketplace repo itself (this repository), the scripts are at their checked-in location:

```bash
./plugins/sulis-execution/scripts/wpx-journal init --wp WP-7 --project <slug>
```

The agent preamble's dev-fallback branch handles this case automatically.

## Project-relative path resolution

Once a tool is invoked, it resolves all artifact paths relative to the project root + the `--project` flag value:

```
<repo-root>/.architecture/<project>/work-packages/WP-NNN-*.md
<repo-root>/.architecture/<project>/work-packages/INDEX.md
<repo-root>/.architecture/<project>/work-packages/.executor-WP-NNN.md
<repo-root>/.architecture/<project>/work-packages/BLOCKER-WP-NNN.md
<repo-root>/.security/<project>/findings-register.md
<repo-root>/.security/<project>/findings/SF-NNN-*.md
```

`--repo-root` defaults to the current working directory. Override explicitly with `--repo-root <path>` when invoking the tools from a directory that is not the project root (e.g., the human `wpx` wrapper from `/tmp`).

This is distinct from the tool-directory resolution above: tool-directory tells you where the `wpx-*` scripts THEMSELVES live; `--repo-root` tells the script where the target project's `.architecture/` tree lives.

## Setting up branch CI

The full v0.9.0+ executor lifecycle assumes your project runs CI on
push to feature branches (Step 8 polls the branch's CI before merging
to dev). Per `plugins/srd/references/git-workflow-standard.md`
GIT-04 v0.1.3+, branch CI is the canonical safety net before squash-
merge: if your only CI runs on push-to-dev, every WP's first run on
dev is also its first CI run, and a broken WP can land before tests
ever execute.

### What `wpx-pipeline` does when branch CI is absent (v0.10.4+)

`wpx-pipeline run` detects whether your project has a branch-CI
workflow by checking `.github/workflows/*.y[a]ml` and `.gitlab-ci.yml`
for any Conventional Commits prefix (`feat/`, `fix/`, `chore/`, etc.).
If no match is found, the tool emits a `WARNING` to stderr, sets the
result's `ci_poll_skipped` flag to `true`, and proceeds directly to
rebase + squash-merge without polling CI. The pipeline still runs to
completion — you just don't get the pre-merge safety net.

You can also pass `--skip-ci-poll` explicitly to force the same
behaviour even when branch CI is present (rare; useful when you want
to bypass a known-flaky CI suite for a specific WP).

### The canonical branch-CI workflow (recommended)

Drop this into `.github/workflows/branch-ci.yml` in your project,
replacing the lint / type-check / test commands with whatever your
project uses:

```yaml
# .github/workflows/branch-ci.yml — minimal feature-branch CI per GIT-04
name: Branch CI
on:
  push:
    branches:
      - 'feat/**'
      - 'fix/**'
      - 'chore/**'
      - 'refactor/**'
      - 'docs/**'
      - 'test/**'
      - 'perf/**'
      - 'build/**'
      - 'ci/**'
      - 'style/**'
      - 'revert/**'

concurrency:
  group: branch-ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Replace these with your project's runtime setup
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -e .[dev]

      - name: Lint
        run: ruff check .

      - name: Type-check
        run: mypy .

      - name: Test
        run: pytest -x
```

After committing this workflow, the next `wpx-pipeline` run on a
feature branch will auto-detect the CI configuration and poll it
normally — no flag changes required.

### Why this matters

- **Safety net before merge.** A broken WP fails CI on the branch
  before squash-merge happens. Without branch CI, the first
  validation is post-merge on dev — which means a broken WP lands
  before tests ever run, and rolling back requires a revert PR or
  `wpx-blocker` retry.
- **Parallel dispatch.** When `run-all` dispatches N WPs in parallel,
  branch CI runs in parallel too. Without it, post-merge dev CI runs
  sequentially per merge, serialising the validation step.
- **Auto-detected by `wpx-pipeline`.** The tool's `_detect_branch_ci`
  function mirrors the Step 1 pre-flight check's heuristic — no
  manual configuration of the marketplace is required for the
  auto-skip to work. Adding branch CI flips wpx-pipeline back into
  poll-mode automatically.

## JSON output shape

When a tool returns data, the shape is:

```json
{
  "ok": true,
  "data": { ... },
  "warnings": ["..."]
}
```

Or on expected failure:

```json
{
  "ok": false,
  "error": "WP-NNN not found",
  "context": { ... }
}
```

Internal errors (exit code 2) print a traceback to stderr; stdout
may be empty.

## Versioning

Tools version-locked with the sulis-execution plugin. Tool-internal
contracts (CLI args + JSON output shape) follow SemVer:

- **Patch**: bug fixes, new commands.
- **Minor**: new subcommands, new optional flags. Old invocations remain valid.
- **Major**: breaking flag changes, output shape changes.

The plugin's version (in `plugin.json`) tracks the tools.

## Running the tests (v0.10.5+)

The wpx-* tools have a pytest suite at `tests/`. From the marketplace repo root:

```bash
pip install pytest
pytest plugins/sulis-execution/scripts/tests/ -v
```

See `tests/README.md` for what's covered, the mock conventions, and the
two regression locks (Bug 1: already-merged branch detection; Bug 2:
multi-table INDEX.md parsing). The suite runs in CI via
`.github/workflows/sulis-execution-tests.yml` on every push and PR
touching `plugins/sulis-execution/scripts/**`.

## See also

- `../agents/executor.md` — executor agent prompt; describes which tools the executor invokes at each step.
- `../references/lifecycle.md` — 12-step lifecycle with tool-invocation patterns.
- `../skills/run-all/SKILL.md` — calling-session orchestration; describes which tools the skill invokes.
- `tests/README.md` — pytest suite walkthrough (v0.10.5+).
