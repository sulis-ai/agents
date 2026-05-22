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

Three common causes, in order of likelihood:

### 1. The `sulis-execution-mcp` package isn't installed

The plugin's `.mcp.json` references `sulis-execution-mcp` as a console
script. If the Python package isn't installed, the command isn't on
PATH and the MCP server can't start.

```bash
pip install -e /path/to/agents/plugins/sulis-execution/sdk/mcp-server/
which sulis-execution-mcp   # should print a path
```

After install, restart your Claude session or run `/reload-plugins`.

### 2. PATH issue (pyenv, multi-Python setups)

If you installed via `pip install -e ...` but the binary still isn't
on PATH, your shell's PATH may not include the right Python's
`bin/` directory.

```bash
pip show sulis-execution-mcp     # confirms install
pyenv which sulis-execution-mcp  # finds the binary via pyenv
# add the printed directory to PATH if missing
```

### 3. Env vars not resolving

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
