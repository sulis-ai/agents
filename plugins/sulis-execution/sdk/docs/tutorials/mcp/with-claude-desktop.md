# Using sulis-execution-mcp with Claude Desktop

**Applies to:** sulis-execution-mcp v0.2.0
**Time:** ~5 minutes

> **If you're using the sulis-execution Claude Code plugin (v0.15.0+),
> the MCP server auto-loads.** You only need section 1 below
> (install the server). The plugin's `.mcp.json` declares the server
> with sensible env-var defaults — `/reload-plugins` or restart your
> session and you're done. Sections 2-4 below are for non-plugin
> setups (Claude Desktop, Cursor, custom JSON-RPC clients).

## What you'll do

Configure Claude Desktop so the model can discover and invoke the 38
wpx tools directly via MCP. (For Claude Code with the plugin
installed, this happens automatically — see the note above.)

## Prerequisites

- Claude Desktop installed
- Python 3.10+
- `sulis-execution-mcp` installable from the marketplace checkout

## 1. Install the server

```bash
pip install -e plugins/sulis-execution/sdk/mcp-server/
```

Verify:

```bash
sulis-execution-mcp --help  # the server is also callable as a script
which sulis-execution-mcp
```

## 2. Edit `claude_desktop_config.json`

Location:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add an entry:

```json
{
  "mcpServers": {
    "sulis-execution": {
      "command": "sulis-execution-mcp",
      "env": {
        "SULIS_EXECUTION_REPO_ROOT": "/Users/me/Documents/repos/agents",
        "SULIS_EXECUTION_PROJECT": "kinds-and-tools",
        "WPX_DIR": "/Users/me/Documents/repos/agents/plugins/sulis-execution/scripts"
      }
    }
  }
}
```

Adjust `SULIS_EXECUTION_REPO_ROOT`, `SULIS_EXECUTION_PROJECT`, and
`WPX_DIR` to match your machine.

## 3. Restart Claude Desktop

Fully quit and reopen. The MCP server starts up automatically when
Claude Desktop launches.

## 4. Verify tool discovery

In a Claude chat, type something like:

> What tools do you have available from the sulis-execution server?

Claude should list 38 tools across pipeline, train, index, journal,
blocker, findings, work_package, worktree, lifecycle, and change.

## 5. Try a call

> Use the sulis-execution train_status tool to check eligibility.

Claude will invoke the tool, parse the JSON result, and summarise it
in plain English.

## Failure modes

| Symptom | Likely cause |
|---|---|
| Tools don't appear in Claude | Server didn't start. Check Claude Desktop logs (`~/Library/Logs/Claude/`). |
| Server starts but tool calls fail with BinaryNotFoundError | `WPX_DIR` is wrong or the wpx-* binaries aren't executable. |
| Tools appear but invoke with wrong project | `SULIS_EXECUTION_PROJECT` env var doesn't match the project you want. |

See [`docs/troubleshooting/`](../../troubleshooting/) for more.

## What's next

- [Using with Cursor](with-cursor.md) — the same shape for Cursor
- [MCP tool reference](../../reference/mcp-tools.md) — all 38 tools listed
- [Error categories](../../explanation/error-categories.md) — how the
  MCP server maps wpx errors to MCP's two error channels
