# Versioning policy

**Applies to:** sulis-execution v0.1.0+

The SDK packages (Python, TypeScript, MCP server) follow [SemVer](https://semver.org/).

## What counts as a breaking change

| Change | Breaking? |
|---|---|
| Remove an operation | Yes (major) |
| Remove a required field from an operation's input | Yes (major) |
| Add a required field to an operation's input | Yes (major — existing callers break) |
| Remove a field from a result | Yes (major) |
| Change a field's type in a result | Yes (major) |
| Rename an operation, field, or class | Yes (major) |
| Tighten a string enum | Yes (major — old values become invalid) |
| Change error class hierarchy (move parent class) | Yes (major) |
| Add a new operation | No (minor) |
| Add an optional field to a request | No (minor) |
| Add a new field to a result | No (minor — `extra=allow` shapes tolerate) |
| Add a new error subclass extending existing class | No (minor) |
| Loosen a string enum (add new values) | No (minor) |
| Fix a bug without changing the public surface | No (patch) |
| Improve a description (no semantic change) | No (patch) |

## Schema versioning

The OpenAPI spec (`sulis-execution.openapi.yaml`) has its own
`info.version`. SDK packages may release multiple versions against the
same schema version (e.g., a doc-only patch). Schema and package
versions track separately.

When the schema changes, bump it in lockstep with the highest-affected
package version.

## Deprecation timeline

- **Deprecate** in version N: mark the operation/field with a
  deprecation message in the OpenAPI spec; SDK methods emit a
  DeprecationWarning (Python) or console warning (TypeScript) at
  call time.
- **Continue supporting** for at least one major version.
- **Remove** no earlier than version N+2 major.

Example: if `wpx-pipeline run`'s `--skip-ci-poll` were deprecated in
v0.2.0, it would still work in v0.x, and could only be removed in v2.0.0
at the earliest.

## Pre-1.0 versioning (where we are now)

The SDK is at v0.1.0. Per SemVer, **anything goes during 0.x**: minor
versions may include breaking changes. We commit to:

- Documenting breaking changes in CHANGELOG.md
- Posting migration notes in `docs/migrations/v0.X-to-v0.Y.md`
- Trying to avoid them where possible

Once we hit v1.0.0, the breakage rules above apply strictly.

## When you'll need to migrate

| Change category | Migration size |
|---|---|
| Patch (0.1.0 → 0.1.1) | Nothing |
| Minor (0.1.0 → 0.2.0) | Read migration note; usually nothing |
| Major (0.x → 1.0) | Read migration note; possibly small code changes |
| Major (1.0 → 2.0) | Read migration note; likely real code changes |

## See also

- [`CHANGELOG.md`](../../CHANGELOG.md)
- [`docs/migrations/`](../migrations/) (per-release migration notes)
