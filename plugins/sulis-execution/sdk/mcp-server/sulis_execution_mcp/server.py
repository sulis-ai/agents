"""MCP server for the sulis-execution CLI surface.

Per agent-consumable SDK spec v0.2.0 Part 4.2.

Behaviour:
1. Reads sulis-execution.openapi.yaml at startup
2. Registers each operation as an MCP tool (tools/list)
3. On tools/call, dispatches to the corresponding CLI subprocess
4. Maps wpx exit codes to MCP's two error channels:
   - Tool-execution outcomes (success, blocker, etc.) → normal results
   - Protocol errors (validation, missing tool, crash) → JSON-RPC errors

Run via: python -m sulis_execution_mcp
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import yaml
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from sulis_execution.errors import (
    ExpectedError,
    InternalError,
    ProtocolError,
    SulisExecutionError,
)
from sulis_execution.transport import SubprocessTransport, TransportConfig

# Resource → CLI binary mapping (mirrors sulis-execution-sdk.yml's
# binary_per_resource block).
RESOURCE_BINARIES = {
    "pipeline": "wpx-pipeline",
    "train": "wpx-train",
    "index": "wpx-index",
    "journal": "wpx-journal",
    "blocker": "wpx-blocker",
    "findings": "wpx-findings",
    "work-package": "wpx-wp",        # SDK resource `work_package`; URL path `work-package`
    "worktree": "wpx-worktree",
    "lifecycle": "wpx-step12",       # SDK resource `lifecycle`; CLI keeps wpx-step12
    "change": "sulis-change",
}


def _operation_to_tool_name(operation_id: str) -> str:
    """Convert camelCase operationId to snake_case MCP tool name.

    Per v0.2.0 Part 4.2 (MCP naming convention): pipelineRun → pipeline_run;
    trainQueueList → train_queue_list; indexFlipStatus → index_flip_status.
    """
    result: list[str] = []
    for i, ch in enumerate(operation_id):
        if ch.isupper() and i > 0:
            result.append("_")
        result.append(ch.lower())
    return "".join(result)


def _operation_to_resource_subcommand(
    operation_id: str,
    path: str,
    operation: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    """Resolve an operationId + path to (binary, subcommand, resource_name).

    Path like /pipeline/run → ('wpx-pipeline', 'run', 'pipeline').
    Path like /train/queue-list → ('wpx-train', 'queue-list', 'train').

    If the operation declares `x-cli-subcommand`, that overrides the
    path-derived subcommand. This is needed when the SDK method name
    differs from the underlying CLI subcommand (e.g. SDK
    `lifecycle.complete` calls CLI `wpx-step12 wrap`).
    """
    parts = path.strip("/").split("/")
    resource = parts[0]
    path_derived_subcommand = parts[1] if len(parts) > 1 else ""
    binary = RESOURCE_BINARIES.get(resource)
    if not binary:
        raise ValueError(f"Unknown resource: {resource}")
    # `x-cli-subcommand` extension overrides the path-derived subcommand
    if operation and "x-cli-subcommand" in operation:
        subcommand = operation["x-cli-subcommand"]
    else:
        subcommand = path_derived_subcommand
    return binary, subcommand, resource


def load_openapi_spec(spec_path: Path) -> dict[str, Any]:
    """Load and parse the OpenAPI YAML spec."""
    with spec_path.open() as f:
        return yaml.safe_load(f)


def _resolve_schema(
    schema_or_ref: dict[str, Any], components: dict[str, Any]
) -> dict[str, Any]:
    """Resolve $ref pointers; flatten allOf into a single schema."""
    if "$ref" in schema_or_ref:
        ref = schema_or_ref["$ref"]
        if ref.startswith("#/components/schemas/"):
            name = ref.split("/")[-1]
            return _resolve_schema(components.get(name, {}), components)
        return {}

    if "allOf" in schema_or_ref:
        merged: dict[str, Any] = {
            "type": "object", "properties": {}, "required": []
        }
        for sub in schema_or_ref["allOf"]:
            resolved = _resolve_schema(sub, components)
            if resolved.get("type") == "object":
                merged["properties"].update(resolved.get("properties", {}))
                merged["required"].extend(resolved.get("required", []))
        merged["required"] = list(set(merged["required"]))
        return merged

    return schema_or_ref


def build_tool_from_operation(
    operation_id: str,
    path: str,
    operation: dict[str, Any],
    components: dict[str, Any],
) -> Tool:
    """Map an OpenAPI operation to an MCP Tool definition."""
    tool_name = _operation_to_tool_name(operation_id)
    description = operation.get("description") or operation.get("summary", "")

    request_schema: dict[str, Any] = {"type": "object", "properties": {}}
    request_body = operation.get("requestBody") or {}
    if request_body:
        content = request_body.get("content", {}).get("application/json", {})
        schema = content.get("schema", {})
        request_schema = _resolve_schema(schema, components)

    return Tool(
        name=tool_name,
        description=description,
        inputSchema=request_schema,
    )


def build_tool_registry(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Walk the OpenAPI spec and build a registry of MCP tools.

    Returns: {tool_name: {tool: Tool, binary, subcommand, resource}}
    """
    components = spec.get("components", {}).get("schemas", {})
    registry: dict[str, dict[str, Any]] = {}

    for path, methods in spec.get("paths", {}).items():
        for verb, operation in methods.items():
            if "operationId" not in operation:
                continue
            try:
                binary, subcommand, resource = _operation_to_resource_subcommand(
                    operation["operationId"], path, operation,
                )
            except ValueError:
                continue
            tool = build_tool_from_operation(
                operation["operationId"], path, operation, components
            )
            registry[tool.name] = {
                "tool": tool,
                "binary": binary,
                "subcommand": subcommand,
                "resource": resource,
            }
    return registry


def _format_error_result(err: SulisExecutionError) -> list[TextContent]:
    """Format a SulisExecutionError as an MCP `isError: true` result."""
    payload = {
        "error": err.message,
        "category": err.category,
        "transport_code": err.transport_code,
        "correlation_id": err.correlation_id,
        "code": err.code,
    }
    return [
        TextContent(
            type="text", text=json.dumps(payload, indent=2, default=str)
        )
    ]


def create_server(
    *,
    spec_path: Path,
    repo_root: Path,
    project: str,
    wpx_dir: Path | None = None,
) -> Server:
    """Create the MCP server with all tools registered."""
    spec = load_openapi_spec(spec_path)
    registry = build_tool_registry(spec)

    config = TransportConfig(
        repo_root=repo_root,
        project=project,
        wpx_dir=wpx_dir,
    )
    transport = SubprocessTransport(config)

    server = Server("sulis-execution-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [entry["tool"] for entry in registry.values()]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        entry = registry.get(name)
        if not entry:
            raise ValueError(f"Unknown tool: {name}")

        # Inject project + repo_root if not provided by the caller
        params = dict(arguments)
        params.setdefault("project", config.project)
        params.setdefault("repo_root", str(config.repo_root))

        try:
            envelope = transport.invoke(
                entry["binary"], entry["subcommand"], params
            )
        except SulisExecutionError as err:
            # Map to MCP's tool-execution error channel — return as
            # `isError: true` result content so the LLM can see it.
            return _format_error_result(err)

        # Success — return the JSON envelope as text content
        return [
            TextContent(type="text", text=json.dumps(envelope, indent=2, default=str))
        ]

    return server


async def _run_stdio_server(server: Server) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entrypoint: configure from env vars, run over stdio."""
    spec_path_env = os.environ.get("SULIS_EXECUTION_OPENAPI_SPEC")
    if spec_path_env:
        spec_path = Path(spec_path_env)
    else:
        spec_path = (
            Path(__file__).resolve().parent.parent.parent / "sulis-execution.openapi.yaml"
        )
    repo_root = Path(os.environ.get("SULIS_EXECUTION_REPO_ROOT", ".")).resolve()
    project = os.environ.get("SULIS_EXECUTION_PROJECT", "default")
    wpx_dir_env = os.environ.get("WPX_DIR")
    wpx_dir = Path(wpx_dir_env).resolve() if wpx_dir_env else None

    server = create_server(
        spec_path=spec_path,
        repo_root=repo_root,
        project=project,
        wpx_dir=wpx_dir,
    )
    asyncio.run(_run_stdio_server(server))


if __name__ == "__main__":
    main()
