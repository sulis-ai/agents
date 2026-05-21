# Reference

**Applies to:** sulis-execution v0.1.0

The complete inventory of operations, types, errors, and transport
bindings. Dry, authoritative, fact-shaped.

## Source of truth

Everything in this reference traces back to
[`sulis-execution.openapi.yaml`](../../sulis-execution.openapi.yaml) (the schema)
and [`sulis-execution-sdk.yml`](../../sulis-execution-sdk.yml) (the codegen config).

If you're hand-writing this kind of detail, you're doing it wrong —
generate it from the schema.

## Sections

| Section | What's there |
|---|---|
| [Operation catalogue](operations.md) | All 38 operations, grouped by resource, with required/optional fields per request and the shape of each result |
| [Type catalogue](types.md) | All ~75 schemas |
| [Error catalogue](errors.md) | All error classes + their fields |
| [Transport bindings](transport-bindings.md) | Subprocess (current); MCP-over-stdio (current); HTTP / gRPC (deferred) |
| [Configuration](configuration.md) | All client constructor params |
| [MCP tool reference](mcp-tools.md) | All 38 MCP tool names with input/output schemas |

## Auto-generation

In v0.1.0, the operation, type, and MCP tool references are kept
in-sync with the source schema manually. A future revision will
generate them automatically (per the docs spec's MUST rule on
generated reference).

In the meantime, the Python and TypeScript clients themselves are the
authoritative reference for their language:

- Python: `from sulis_execution import *` + your IDE's autocomplete
- TypeScript: import the package + your IDE's TypeScript intellisense

The OpenAPI spec is the language-agnostic reference.

## See also

- [Mental model](../explanation/mental-model.md) — the design behind the
  operation catalogue
