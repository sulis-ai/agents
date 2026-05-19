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

## See also

- `../agents/executor.md` — executor agent prompt; describes which tools the executor invokes at each step.
- `../references/lifecycle.md` — 12-step lifecycle with tool-invocation patterns.
- `../skills/run-all/SKILL.md` — calling-session orchestration; describes which tools the skill invokes.
