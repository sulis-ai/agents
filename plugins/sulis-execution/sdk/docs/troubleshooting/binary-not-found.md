# Symptom: `BinaryNotFoundError: Could not find binary 'wpx-...'`

**Applies to:** sulis-execution v0.1.0

## What it means

The SDK tried to spawn one of the wpx-* binaries (e.g., `wpx-pipeline`,
`sulis-change`) and couldn't find it.

## Lookup order

1. `wpx_dir` / `wpxDir` set on the client
2. `WPX_DIR` env var
3. System `$PATH`

## Fix

**Option A — point at the marketplace checkout:**

```python
client = SulisExecution(
    repo_root='.',
    project='my-project',
    wpx_dir='/Users/me/Documents/repos/agents/plugins/sulis-execution/scripts',
)
```

**Option B — set the env var (recommended for shells / CI / MCP):**

```bash
export WPX_DIR=/Users/me/Documents/repos/agents/plugins/sulis-execution/scripts
```

**Option C — install the marketplace plugin so binaries are on PATH** (when
the plugin's setup adds them globally).

## Verify

```bash
ls $WPX_DIR | head     # should list wpx-pipeline, wpx-train, etc.
which wpx-pipeline      # should print a path if on PATH
```

## Why this happens

The SDK doesn't bundle the wpx-* binaries — it shells out to whichever
ones are installed locally. This keeps the SDK light and the CLI tools
the single source of truth, but it means setup has to point at them.
