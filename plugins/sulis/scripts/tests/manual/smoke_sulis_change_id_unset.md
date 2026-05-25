# Manual smoke — `SULIS_CHANGE_ID` unset (no regression)

> WP-007. Not run in CI. Run by hand to verify the default path is
> unchanged when no change binding is present.

## Goal

Confirm that when `SULIS_CHANGE_ID` is **unset**, the Sulis agent behaves
exactly as before — default greeting + normal journey routing, no
change-context narration.

## Pre-conditions

- The `sulis` plugin is installed.
- `SULIS_CHANGE_ID` is not set in the environment.

## Procedure

```bash
unset SULIS_CHANGE_ID
claude --agent sulis "Hi"
```

## Expected

The first response is the normal Sulis greeting / journey-routing
behaviour. No mention of change bindings, no `resolve_current_change`
narration, no three-option stale prompt.

## Fail signals

- The agent narrates a change-context check or mentions `SULIS_CHANGE_ID`
  → the new section is firing when it should be inert (the unset branch is
  meant to be a no-op).
