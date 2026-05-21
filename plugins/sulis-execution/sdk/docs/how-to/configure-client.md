# How to configure the client

**Applies to:** sulis-execution v0.1.0

## All configuration knobs

| Option | Python kwarg | TypeScript option | Default |
|---|---|---|---|
| Repo root | `repo_root` | `repoRoot` | `'.'` |
| Project slug | `project` | `project` | (required) |
| Timeout (seconds) | `timeout_seconds` | `timeoutSeconds` | `5400` (90 min) |
| Binary lookup dir | `wpx_dir` | `wpxDir` | env: `WPX_DIR`, then `PATH` |

## Python example

```python
from sulis_execution import SulisExecution

client = SulisExecution(
    repo_root='/Users/me/Documents/repos/my-project',
    project='payments',
    timeout_seconds=3600,                  # 1 hour cap
    wpx_dir='/Users/me/wpx-scripts',       # override binary lookup
)
```

## TypeScript example

```typescript
import { SulisExecution } from '@sulis-ai/execution';

const client = new SulisExecution({
  repoRoot: '/Users/me/Documents/repos/my-project',
  project: 'payments',
  timeoutSeconds: 3600,
  wpxDir: '/Users/me/wpx-scripts',
});
```

## Environment-variable overrides

The transport also respects `WPX_DIR` from the env when `wpx_dir` isn't
set on the client:

```bash
export WPX_DIR=/Users/me/Documents/repos/agents/plugins/sulis-execution/scripts
```

This is handy for CI / Claude Desktop / MCP-server contexts where you
want to configure once.

## Why default timeout is 90 minutes

Matches `wpx-pipeline`'s default — a real deploy + health + smoke run
can legitimately take that long. Override for shorter operations:

```python
quick = SulisExecution(repo_root='.', project='x', timeout_seconds=60)
quick.index.list_ready()  # 60s cap is fine for read-only ops
```

## What you can't configure (yet)

- Retries (intentionally disabled for local subprocess; per v0.2.0 Part 4.3)
- Telemetry (not exposed as a knob; uses PID + timestamp correlation by default)
- Custom transport (subprocess is the only binding for v0.1.0)

See [Retry strategy explained](../explanation/retry-strategy.md) for
the rationale on retries being disabled.
