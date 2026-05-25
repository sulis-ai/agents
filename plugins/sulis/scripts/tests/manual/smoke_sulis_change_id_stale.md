# Manual smoke — `SULIS_CHANGE_ID` is stale (resolves to null)

> WP-007. Not run in CI. Run by hand to verify the stale-env honesty path.

## Goal

Confirm that when `SULIS_CHANGE_ID` is set but no matching change branch
exists, the Sulis agent surfaces the mismatch honestly and offers the three
documented options (continue change-less / start new / list in-flight).

## Pre-conditions

- The `sulis` plugin is installed.
- No change branch matches the ULID you will export. A syntactically valid
  but non-existent ULID is ideal:
  ```
  01HYQC7100000000000000ZZZZ
  ```

## Procedure

```bash
export SULIS_CHANGE_ID=01HYQC7100000000000000ZZZZ
claude --agent sulis "Hi"
```

## Expected

The first response:

1. States that the shell has `SULIS_CHANGE_ID={value}` but no matching
   change branch was found.
2. Offers three options:
   - Continue in change-less mode (normal session)
   - Start a new change with `/sulis:change start`
   - List in-flight changes with `/sulis:changes`
3. Does NOT fabricate a change identity or guess.

## Fail signals

- The agent invents change details → it ignored the `null` result.
- The agent errors out or stalls → the verification snippet raised instead
  of returning `null`.
