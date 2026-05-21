# Troubleshooting

**Applies to:** sulis-execution v0.1.0

Symptom-first navigation. Find the message or behaviour you're seeing
and the doc takes you to the cause.

## Quick index

| Symptom | Likely cause |
|---|---|
| `BinaryNotFoundError: Could not find binary 'wpx-...'` | [Binary not on PATH](binary-not-found.md) |
| `ExpectedError: status was 'X', expected 'Y'` | [Status mismatch on flip-status](index-status-mismatch.md) |
| MCP tools don't appear in Claude / Cursor | [MCP server didn't start](mcp-server-not-found.md) |
| `result.outcome == 'blocker'` after a clean-looking run | [Pipeline blocker](pipeline-blocker.md) |
| Tests fail with module-name collision (`tests.test_server`) | [pytest rootdir](pytest-rootdir.md) |
| TypeScript build emits errors about Record types | [Run `npm install` first](ts-build-errors.md) |

If your problem isn't here, please open an issue with:
- The error message verbatim
- What you tried
- The Python or TypeScript version
- The sulis-execution plugin version + SDK version

## See also

- [How to handle errors](../how-to/handle-errors.md)
- [Error catalogue](../reference/errors.md)
