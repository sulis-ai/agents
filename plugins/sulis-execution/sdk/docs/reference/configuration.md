# Configuration reference

**Applies to:** sulis-execution v0.1.0

| Setting | Python | TypeScript | Default | Description |
|---|---|---|---|---|
| Repo root | `repo_root='/path'` | `repoRoot: '/path'` | `'.'` | Project repository root; resolves `.architecture/<project>/` paths |
| Project slug | `project='x'` | `project: 'x'` | — (required) | Used by every non-change operation |
| Timeout | `timeout_seconds=N` | `timeoutSeconds: N` | `5400` (90 min) | Per-call timeout; matches wpx-pipeline default |
| Binary lookup dir | `wpx_dir='/path'` | `wpxDir: '/path'` | `WPX_DIR` env, then PATH | Where to find wpx-* binaries |

## Env vars (read at runtime by the transport)

| Var | Effect |
|---|---|
| `WPX_DIR` | Binary lookup directory; overridden by `wpx_dir` / `wpxDir` config |
| `GITHUB_REPOSITORY` | Default `--repo` value for wpx-train / wpx-pipeline ops |
| `GITHUB_TOKEN` | Optional OAuth fallback for git clone (wpx-train only) |

## Env vars (read by the MCP server at startup)

| Var | Effect |
|---|---|
| `SULIS_EXECUTION_OPENAPI_SPEC` | Path to the OpenAPI YAML (default: sdk/sulis-execution.openapi.yaml) |
| `SULIS_EXECUTION_REPO_ROOT` | Repo root for the MCP server's transport (default: `.`) |
| `SULIS_EXECUTION_PROJECT` | Project slug for the MCP server (default: `default`) |
| `WPX_DIR` | Binary lookup directory |

## See also

- [How to configure the client](../how-to/configure-client.md) — usage
- [MCP Claude Desktop tutorial](../tutorials/mcp/with-claude-desktop.md) — how the env vars get set
