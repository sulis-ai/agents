# Sulis Execution — DEPRECATED

**The executor moved to the `sulis` plugin at v0.30.0 (2026-05-25).**

See `CLAUDE.md` in this directory for the full migration table.

## New commands

```bash
/sulis:run-wp WP-NNN              # was /sulis-execution:run-wp
/sulis:run-all                    # was /sulis-execution:run-all
/sulis:retry WP-NNN               # was /sulis-execution:retry
/sulis:wp-status                  # was /sulis-execution:status (renamed)
/sulis:backfill-code-review       # was /sulis-execution:backfill-code-review
/sulis:backfill-gates             # was /sulis-execution:backfill-gates
```

## Why this plugin still exists

The SDK packages still live here with their stable published names:

- `sdk/python/` → `sulis-execution` on PyPI
- `sdk/typescript/` → `@sulis-ai/execution` on npm
- `sdk/mcp-server/` → `sulis-execution-mcp` on PyPI

These are published, versioned independently, and have external
consumers. Moving them would be SemVer-breaking. They may move to a
dedicated repo (`sulis-ai/sulis-execution-sdk`) later — separate
decision from the plugin consolidation.

## Plugin retirement

Remove this entry from the marketplace when:
1. The SDK packages move to their own repo, OR
2. You're comfortable orphaning the SDK package names (forcing
   consumers to migrate)

Until then: plugin shell remains as the SDK distribution point + a
clear deprecation marker.
