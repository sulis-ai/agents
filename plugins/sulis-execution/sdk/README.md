# sulis-execution SDK

**Version:** 0.1.0
**Status:** Initial release

Typed Python + TypeScript SDK + MCP server for the sulis-execution
plugin's CLI tools — wpx-pipeline, wpx-train, wpx-index, wpx-journal,
wpx-blocker, wpx-findings, wpx-wp, wpx-worktree, wpx-step12, and
sulis-change.

**38 operations across 10 resources, available in Python, TypeScript,
and as an MCP server.**

> **A note on the `wpx-` prefix.** The underlying CLI tools have names
> like `wpx-pipeline`, `wpx-train`, `wpx-index` (where `wpx` is short
> for "Work Package eXecutor" — an internal-jargon prefix from the
> plugin's earlier history). The SDK wraps these under cleaner public
> names: `client.pipeline`, `client.train`, `client.index`, etc.
> Most callers never need to touch the `wpx-*` names directly. The
> only place they surface is in `BinaryNotFoundError` messages
> (which name the underlying binary that couldn't be located) and
> in the `wpx_dir` / `WPX_DIR` configuration.

---

## What this is for

An agent or developer using the sulis-execution plugin today calls
the CLI via subprocess and parses JSON. That works but it isn't typed,
isn't tested at the call site, and the LLM-facing surface doesn't get
discovered cleanly via MCP.

This SDK fixes that. Same underlying tools, three new shapes:

| Surface | Use when |
|---|---|
| **Python client** (`sulis_execution`) | You're writing Python code that calls wpx-* operations. Typed inputs, Pydantic v2 outputs, both sync + async. |
| **TypeScript client** (`@sulis-ai/execution`) | You're writing Node.js / TypeScript code that calls wpx-* operations. Typed interfaces, async-only. |
| **MCP server** (`sulis-execution-mcp`) | You want an LLM (Claude, Cursor, etc.) to discover and invoke wpx-* operations directly. JSON-RPC over stdio per MCP. |

---

## Quick start

### Python

```bash
pip install -e ./python/
```

```python
from sulis_execution import SulisExecution

client = SulisExecution(repo_root='.', project='my-project')
result = client.pipeline.run(
    wp='WP-001',
    branch='feat/wp-001-introduce-payments',
    dev_sha_at_creation='abc123def',
    deploy_workflow='Deploy to Dev',
)
if result.outcome == 'blocker':
    print(f'Blocker: {result.blocker_reason}')
```

See: [`docs/tutorials/python/getting-started.md`](docs/tutorials/python/getting-started.md)

### TypeScript

```bash
cd ./typescript && npm install && npm run build
```

```typescript
import { SulisExecution } from '@sulis-ai/execution';

const client = new SulisExecution({ repoRoot: '.', project: 'my-project' });
const result = await client.pipeline.run({
  wp: 'WP-001',
  branch: 'feat/wp-001-introduce-payments',
  dev_sha_at_creation: 'abc123def',
  deploy_workflow: 'Deploy to Dev',
});
```

See: [`docs/tutorials/typescript/getting-started.md`](docs/tutorials/typescript/getting-started.md)

### MCP server

```bash
pip install -e ./mcp-server/
sulis-execution-mcp  # runs over stdio
```

Configure your MCP client (Claude Desktop, Cursor, etc.) per:
- [`docs/tutorials/mcp/with-claude-desktop.md`](docs/tutorials/mcp/with-claude-desktop.md)
- [`docs/tutorials/mcp/with-cursor.md`](docs/tutorials/mcp/with-cursor.md)

---

## Documentation

Organised per [Diátaxis](https://diataxis.fr/):

| Quadrant | What's there | When you need it |
|---|---|---|
| **[Tutorials](docs/tutorials/)** | Getting-started per language + per transport setup | First time using the SDK |
| **[How-to guides](docs/how-to/)** | Recipes for specific tasks (error handling, raw response, mocking, etc.) | You know what you want; need the steps |
| **[Reference](docs/reference/)** | Operation catalogue per resource; transport bindings; configuration | Looking up a specific thing |
| **[Explanation](docs/explanation/)** | Mental model; error categories; "blocker is not an exception"; quirks | Want to understand the design |
| **[Recipes](docs/recipes/)** | End-to-end worked examples | Want to see complete tasks |
| **[Troubleshooting](docs/troubleshooting/)** | Symptom-first navigation | Something's broken |
| **[Migrations](docs/migrations/)** | Per-release change notes | Upgrading |

---

## Specifications this SDK implements

| Spec | What it governs |
|---|---|
| [`agent-consumable-sdk-spec.md`](../docs/research/agent-consumable-sdk-spec.md) v0.2.0 | Universal SDK conventions — schema/transport split, outcome-category errors, per-transport bindings |
| [`agent-consumable-sdk-wpx-mapping.md`](../docs/research/agent-consumable-sdk-wpx-mapping.md) v0.2.0 | wpx-specific application of the above |
| [`agent-consumable-sdk-docs-spec.md`](../docs/research/agent-consumable-sdk-docs-spec.md) v0.1.0 | Diátaxis structure for these docs |
| [`sdk-implementation-validation-rubric.md`](../docs/research/sdk-implementation-validation-rubric.md) v0.1.0 | Used in Phase 6 to validate this implementation |

---

## Source-of-truth schema

The SDK is generated from `sulis-execution.openapi.yaml` (OpenAPI 3.1).
Every typed interface, every method signature, every MCP tool definition
traces back to this file. Don't hand-edit the generated clients without
updating the schema.

The codegen config sits in `sulis-execution-sdk.yml` (resource tree,
error mapping, target languages).

---

## Versioning

| Package | Initial version |
|---|---|
| `sulis-execution` (Python) | 0.1.0 |
| `@sulis-ai/execution` (TypeScript) | 0.1.0 |
| `sulis-execution-mcp` | 0.1.0 |

Per [SemVer](https://semver.org/): bumping the SDK schema in
non-backwards-compatible ways requires a major version bump. Adding
operations (additive change) requires a minor bump. Bug fixes get
patch.

See [`CHANGELOG.md`](CHANGELOG.md) for full release history.

---

## License

MIT. See the marketplace root `LICENSE` file.
