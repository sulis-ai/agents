"""sulis-execution-mcp — MCP server for the sulis-execution CLI surface.

Per agent-consumable SDK spec v0.2.0 Part 4.2 (JSON-RPC over stdio / MCP).

Reads sulis-execution.openapi.yaml at startup, registers each operation
as an MCP tool, and dispatches tools/call to the underlying CLI subprocess
via the Python SDK's transport.
"""
__version__ = "0.2.2"
