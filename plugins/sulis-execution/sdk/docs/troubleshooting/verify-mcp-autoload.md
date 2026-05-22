# Verify MCP auto-load is working

**Applies to:** sulis-execution v0.15.0+

After installing the sulis-execution plugin, the MCP server
(`sulis-execution-mcp`) should load automatically per the plugin's
`.mcp.json`. This page tells you how to verify that — and how to fix
the common failure modes.

## In a Claude Code session

The fastest check:

```
/mcp
```

You should see `sulis-execution-mcp` in the server list with an
indicator that it came from a plugin. If it's there, you're done —
the 38 tools are addressable as `mcp__sulis-execution-mcp__<tool_name>`.

If it's missing, see "If /mcp doesn't show it" below.

## Outside a Claude Code session (smoke test)

You can verify the server works without Claude by sending it a
JSON-RPC `tools/list` request over stdio:

```bash
python3 - << 'EOF'
import json
import os
import subprocess

env = os.environ.copy()
env["SULIS_EXECUTION_OPENAPI_SPEC"] = (
    "/path/to/agents/plugins/sulis-execution/sdk/sulis-execution.openapi.yaml"
)
env["SULIS_EXECUTION_REPO_ROOT"] = "."
env["SULIS_EXECUTION_PROJECT"] = "smoke-test"
env["WPX_DIR"] = "/path/to/agents/plugins/sulis-execution/scripts"

proc = subprocess.Popen(
    ["sulis-execution-mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    env=env, text=True,
)
requests = (
    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18",
                           "capabilities": {}, "clientInfo":
                           {"name": "smoke", "version": "0"}}}) + "\n" +
    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized",
                "params": {}}) + "\n" +
    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list",
                "params": {}}) + "\n"
)
stdout, _ = proc.communicate(input=requests, timeout=15)
tools = next(json.loads(l)["result"]["tools"]
             for l in stdout.splitlines()
             if l.strip() and json.loads(l).get("id") == 2)
print(f"✓ {len(tools)} tools registered")
EOF
```

Expected: `✓ 38 tools registered`.

## If `/mcp` doesn't show it

Four common causes, in order of likelihood:

### 1. The `sulis-execution-mcp` package isn't installed

The plugin uses a launcher script that tries multiple Python
interpreters to find the install. If no Python has the package
importable, the launcher emits a clear "could not find" error.

```bash
pip install -e /path/to/agents/plugins/sulis-execution/sdk/mcp-server/
pip show sulis-execution-mcp     # should print the version
```

After install, run `/reload-plugins`.

### 2. PATH issue (Claude Code launched from GUI vs terminal — fixed in v0.19.1)

On macOS, Claude Code launched from Finder / Spotlight / Launchpad
inherits `launchctl`'s minimal PATH (`/usr/bin:/bin:/usr/sbin:/sbin`)
and cannot see pyenv shims or user-local `bin/` directories. Versions
of the plugin before v0.19.1 used `command: sulis-execution-mcp` in
`.mcp.json`, which relies on shell PATH to find the console script.
If your PATH didn't include the Python install's bin/, the MCP
server failed to spawn with "1 error during load."

v0.19.1+ ships `sdk/mcp-server/bin/sulis-execution-mcp-launcher` — a
small shell wrapper that tries multiple Python interpreters
(`python3`, `python3.12`, `~/.pyenv/shims/python3`, `~/.pyenv/versions/3.X/bin/python3`,
`/usr/local/bin/python3`, `/opt/homebrew/bin/python3`, `/usr/bin/python3`)
and execs the first one that can import `sulis_execution_mcp`. The
`.mcp.json` references the launcher by absolute path via
`${CLAUDE_PLUGIN_ROOT}`, so it works regardless of shell PATH.

If you're on v0.19.1+ and still see the error, run the launcher
directly to diagnose:

```bash
PLUGIN_ROOT=$(ls -td ~/.claude/plugins/cache/sulis-ai-agents/sulis-execution/*/ | head -1)
"$PLUGIN_ROOT/sdk/mcp-server/bin/sulis-execution-mcp-launcher" < /dev/null
# Exit 0 = launcher found a working Python (server is up; press Ctrl-C to quit)
# Exit 1 = launcher reports which Pythons it tried; install missing
```

If the launcher exits 1, install the package into one of the
candidate Pythons:

```bash
~/.pyenv/shims/python3 -m pip install -e \
  "$PLUGIN_ROOT/sdk/mcp-server/"
```

### 3. The cached plugin is stale (older version than the marketplace has)

`/reload-plugins` reconnects MCP servers using the currently-cached
plugin. If the marketplace has a newer version, you may need to
re-install the plugin to get the new manifest + spec. Check:

```bash
ls -lt ~/.claude/plugins/cache/sulis-ai-agents/sulis-execution/ | head -3
# Most recent dir = current cached version
```

If the cache is missing the latest version, re-install from
Claude Code's plugin UI / command (depends on Claude Code version).

### 4. Env vars not resolving

The `.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}` for default WPX_DIR + OpenAPI
spec paths. `CLAUDE_PLUGIN_ROOT` is set by Claude Code per its plugin
spec. If you're running the MCP server outside a Claude Code session,
set the env vars explicitly:

```bash
export WPX_DIR=/path/to/agents/plugins/sulis-execution/scripts
export SULIS_EXECUTION_OPENAPI_SPEC=/path/to/agents/plugins/sulis-execution/sdk/sulis-execution.openapi.yaml
export SULIS_EXECUTION_REPO_ROOT=.
export SULIS_EXECUTION_PROJECT=<your-project-slug>
```

## What success looks like

In Claude Code:

```
/mcp
> sulis-execution-mcp (plugin)
>   38 tools available
```

In a smoke test: `✓ 38 tools registered`.

In your skills: when you invoke `mcp__sulis-execution-mcp__train_status`,
the call dispatches to `wpx-train status` under the hood and returns a
typed `TrainStatusResult`.

## See also

- [MCP tool reference](../reference/mcp-tools.md) — all 38 tools
- [With Claude Desktop](../tutorials/mcp/with-claude-desktop.md) —
  non-plugin manual setup
- [Troubleshooting / binary-not-found](binary-not-found.md) — adjacent
  issue (the wpx-* binaries themselves not on PATH)
