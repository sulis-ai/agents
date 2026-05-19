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
| `wpx-index` | Manage INDEX.md (status flips, ready set, config) | Calling session + executor |
| `wpx-wp` | Read WP frontmatter; append acceptance evidence | Calling session + executor |
| `wpx-blocker` | Write BLOCKER-WP-NNN.md per EL-08 format | Executor agent |
| `wpx-findings` | Findings register + SF files + auto-draft WPs | Calling session |
| `wpx-worktree` | Create/remove worktrees; record dev SHA | Executor + calling session |
| `wpx-pipeline` | Steps 8-10: CI poll + merge + deploy + health + smoke | Calling session (via background Bash) |
| `wpx-step12` | Step 12 bookkeeping wrap (atomic) | Calling session |

## Common conventions

All tools share these conventions:

- **First positional arg**: subcommand (`init`, `start-step`, etc).
- **Flags**: `--kebab-case`, `--project <slug>` for project-relative paths.
- **JSON output**: structured to stdout when a result is returned.
- **Errors**: human-readable to stderr.
- **Exit codes**: `0` success, `1` user/data error (bad args, file not found, expected failure), `2` internal error (bug, unexpected).

## Installation

The tools are plain Python 3 files with `#!/usr/bin/env python3` shebang. They are invoked via their full path:

```bash
python3 plugins/sulis-execution/scripts/wpx-journal init --wp WP-7
```

Or directly (if executable bit set):

```bash
./plugins/sulis-execution/scripts/wpx-journal init --wp WP-7
```

Dependencies: **stdlib only**. No `click`, no `pyyaml` required — frontmatter is parsed with a tiny inline parser sufficient for the executor's needs.

## Path resolution

By default the tools resolve paths relative to the current working directory + the `--project` flag value:

```
.architecture/<project>/work-packages/WP-NNN-*.md
.architecture/<project>/work-packages/INDEX.md
.architecture/<project>/work-packages/.executor-WP-NNN.md
.architecture/<project>/work-packages/BLOCKER-WP-NNN.md
.security/<project>/findings-register.md
.security/<project>/findings/SF-NNN-*.md
```

Override with `--repo-root <path>` if invoked from a different cwd.

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
