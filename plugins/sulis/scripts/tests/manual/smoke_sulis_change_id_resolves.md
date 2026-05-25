# Manual smoke — `SULIS_CHANGE_ID` resolves to a live change

> WP-007. Not run in CI (needs an interactive Sulis session). Run by hand
> on macOS or Linux when verifying the change-context greeting path.

## Goal

Confirm that when `SULIS_CHANGE_ID` is set to a **valid, existing** change
ULID, the Sulis agent greets in change-context mode — surfacing the change
identity and the recon's suggested next step.

## Pre-conditions

- The `sulis` plugin is installed (or run via `claude --plugin-dir`).
- A change exists. Create one if needed:
  ```bash
  python3 plugins/sulis/scripts/sulis-change start \
    --slug introduce-payments --primitive create \
    --intent "add subscription billing"
  ```
  Note the `change_id` from the JSON output (26-char Crockford ULID).
- The recon file exists at `~/.sulis/changes/{change_id}/CONTEXT.md`
  (written automatically by `sulis-change start`). Confirm:
  ```bash
  cat ~/.sulis/changes/{change_id}/CONTEXT.md
  ```

## Procedure

```bash
export SULIS_CHANGE_ID={the-valid-ulid}
claude --agent sulis "Hi"
```

## Expected

The first response:

1. Mentions the change handle (e.g. `CH-01HYQC`) and the intent.
2. States the primitive (e.g. "a create").
3. Surfaces the suggested next step from `CONTEXT.md` (for a `create`
   primitive: `/sulis:specify`).
4. Hands the floor back to the founder (no permission-theater closure).

## Fail signals

- Default greeting with no mention of the change → the agent did not run
  the `resolve_current_change` verification (WP-007 section missing or not
  triggering).
- Greeting references a different change → stale env var; check the export.
