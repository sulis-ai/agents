# Why snake_case in TypeScript?

**Applies to:** sulis-execution v0.1.0

Most TypeScript codebases use `camelCase` for everything. The
sulis-execution TypeScript SDK uses `camelCase` for methods + class
names but **`snake_case` for response fields**. Here's why.

## The parity contract

Per agent-consumable SDK spec v0.2.0 Part 6 — the Python ↔ TypeScript
parity contract:

> Preserve wire-format field case. Don't auto-camelCase JSON in
> TypeScript. The agent's mental model is "this is what comes off the
> wire" — same field names, same nesting, same JSON-Schema-derived
> shape. Differences live in methods and async-shape, not in fields.

## What this looks like

**Wire (JSON from `wpx-pipeline run`):**
```json
{
  "ok": true,
  "data": {
    "result": {
      "wp": "WP-001",
      "outcome": "success",
      "merge_sha": "abc123",
      "deploy_url": "https://staging.example.com",
      "ci_poll_skipped": false,
      "started_at": "2026-05-21T12:00:00Z"
    }
  }
}
```

**Python (snake_case throughout):**
```python
result.wp                 # str
result.outcome            # 'success' | 'blocker' | ...
result.merge_sha          # str | None
result.deploy_url         # str | None
result.ci_poll_skipped    # bool
result.started_at         # datetime
```

**TypeScript (snake_case fields, camelCase methods):**
```typescript
result.wp                 // string
result.outcome            // 'success' | 'blocker' | ...
result.merge_sha          // string | null   ← snake_case preserved
result.deploy_url         // string | null   ← snake_case preserved
result.ci_poll_skipped    // boolean         ← snake_case preserved
result.started_at         // string          ← snake_case preserved

client.pipeline.run({...})       // method is camelCase
client.train.queueList()          // queueList vs queue_list
client.index.flipStatus({...})    // flipStatus vs flip_status
```

## Why not auto-camelCase TypeScript fields?

Three reasons.

**1. The mental model ports across languages.** A developer working in
Python sees `merge_sha`; switching to TypeScript, they see `merge_sha`.
No translation needed. They can read the OpenAPI spec and know the
field name in any language.

**2. The wire is the wire.** When debugging, the developer pastes the
JSON output of `wpx-pipeline run` into a viewer. They see
`merge_sha`. The TypeScript code uses `merge_sha`. The Python code
uses `merge_sha`. No mental case-conversion to keep straight.

**3. Anthropic + OpenAI SDKs converge on this.** Both vendors' TypeScript
SDKs preserve wire-format field case. The convention is established at
scale.

## What IS camelCase in TypeScript?

- **Method names**: `queueList`, `flipStatus`, `recordPostdeploy`
- **Class names**: `SulisExecution`, `AsyncSulisExecution`, `ExpectedError`
- **Internal SDK properties** (not wire fields): `transportCode`,
  `correlationId`, `repoRoot`, `wpxDir`

## When you'd notice

ESLint might complain about snake_case fields if your config is strict.
You can:
- Disable the rule for files that destructure SDK responses
- Use bracket access: `result['merge_sha']` (TypeScript still types it)
- Accept the lint and document why

The cost is small; the consistency gain across languages is worth it.

## See also

- [Mental model](mental-model.md)
- [Getting started with TypeScript](../tutorials/typescript/getting-started.md)
