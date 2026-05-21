# Changelog

All notable changes to the sulis-execution SDK packages.

Format per [Keep a Changelog](https://keepachangelog.com/).
Versioning per [SemVer](https://semver.org/).

## [0.1.0] — 2026-05-21

### Added

- Initial release of `sulis-execution` (Python), `@sulis-ai/execution`
  (TypeScript), and `sulis-execution-mcp` (MCP server).
- 38 operations across 10 resources (pipeline, train, index, journal,
  blocker, findings, wp, worktree, step12, change).
- Outcome-category error model (ProtocolError / ExpectedError /
  InternalError) with wpx-domain extensions (BinaryNotFoundError,
  InvalidArgumentError, UnexpectedOutputError).
- Subprocess transport for Python (sync + async via httpx-style API)
  and TypeScript (sync via spawnSync, async via spawn wrapper).
- MCP server reads OpenAPI spec at startup, registers 38 tools, maps
  wpx exit codes to MCP's two-channel error model.
- Documentation per Diátaxis quadrants.

### Schema source

`sulis-execution.openapi.yaml` v0.1.0 (38 operations).

### Spec compliance

- agent-consumable-sdk-spec.md v0.2.0
- agent-consumable-sdk-wpx-mapping.md v0.2.0
- agent-consumable-sdk-docs-spec.md v0.1.0
