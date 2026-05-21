# Error catalogue

**Applies to:** sulis-execution v0.1.0

## The hierarchy

```
SulisExecutionError (base)
├── ProtocolError              (category='protocol')
│   └── BinaryNotFoundError
├── ExpectedError              (category='expected')
│   └── InvalidArgumentError
└── InternalError              (category='internal')
    └── UnexpectedOutputError
```

Class names are identical across Python and TypeScript per the SDK
spec's parity contract.

## Fields on every error

| Field | Type | Source |
|---|---|---|
| `message` | string | Human-readable error message |
| `category` | `'protocol' | 'expected' | 'internal'` | Set by the class |
| `transport_code` (Py) / `transportCode` (TS) | int or string | Exit code or sentinel ('exec_failure', 'timeout') |
| `correlation_id` (Py) / `correlationId` (TS) | string | PID + timestamp |
| `body` | dict / `Record<string, unknown>` | Parsed JSON envelope (when present) |
| `code` | string | Domain code from `context.code` (when present) |
| `context` | dict / `Record<string, unknown>` | Optional structured context |

## ProtocolError subclasses

### `BinaryNotFoundError`

Raised when the CLI binary (`wpx-pipeline`, `wpx-train`, `sulis-change`,
etc.) can't be located.

**Lookup order:**
1. `wpx_dir` / `wpxDir` config on the client
2. `WPX_DIR` env var
3. `$PATH`

**Recovery:** install the sulis-execution plugin so the binaries are on
PATH, or set `WPX_DIR` to point at the scripts directory.

## ExpectedError subclasses

### `InvalidArgumentError`

Raised when an argument fails validation (e.g., bad WP ID format,
missing required field that argparse caught).

**Recovery:** fix the input.

## InternalError subclasses

### `UnexpectedOutputError`

Raised when the CLI produced output that couldn't be parsed as the
expected JSON shape.

**Recovery:** likely a bug in the underlying CLI; check that the SDK
version and CLI version match. Log + escalate.

## Common `error.code` values

These come from the underlying CLI's `context.code` field.

| Code | Source op | Meaning |
|---|---|---|
| `wp_not_found` | most ops | WP isn't in INDEX.md |
| `status_mismatch` | index.flip_status | `expected` arg didn't match actual status |
| `blocker_already_exists` | blocker.write | File exists; use `force=True` to overwrite |
| `invalid_severity` | findings.register | Severity not in (CRITICAL, CONCERN, ADVISORY) |
| `branch_already_exists` | change.start | A change branch with that slug already exists |
| `worktree_already_exists` | worktree.create | Worktree path already exists |

This list grows over time as new domain errors are added. The full list
lives in the CLI's source.

## See also

- [Error categories explained](../explanation/error-categories.md)
- [Blocker is not an exception](../explanation/blocker-not-exception.md)
- [How to handle errors](../how-to/handle-errors.md)
