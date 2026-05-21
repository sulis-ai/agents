# Using sulis-execution-mcp with Cursor

**Applies to:** sulis-execution-mcp v0.1.0
**Time:** ~5 minutes

## What you'll do

Configure Cursor so its agent can discover and invoke the 38 wpx-*
tools directly via MCP.

## Prerequisites

- Cursor installed
- Python 3.10+
- `sulis-execution-mcp` installed (see [Claude Desktop tutorial](with-claude-desktop.md) section 1)

## 1. Locate Cursor's MCP config

Cursor reads MCP servers from `~/.cursor/mcp.json` (or via the Cursor
Settings UI).

## 2. Add the server

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

## 3. Restart Cursor

Restart Cursor or use Cursor's "Reload MCP Servers" command.

## 4. Use in a chat

In a Cursor chat with agent mode enabled:

> List eligible WPs for the train using sulis-execution.

The agent picks the right tool (train_queue_list) and invokes it.

## Failure modes

Same as Claude Desktop — see that tutorial's failure modes table.

## What's next

- [MCP tool reference](../../reference/mcp-tools.md)
- [Troubleshooting](../../troubleshooting/)
