# Manual smoke — `sulis-change start --spawn` end-to-end

> WP-004 (composes WP-003 launcher + WP-005 recon + WP-006 pre-prompt +
> WP-007 agent body). Not run in CI. Run by hand on macOS and Linux.

## Goal

Confirm the full founder UX: `sulis-change start --spawn` creates the
change, writes the recon, opens a new terminal in the worktree, and the
spawned Sulis greets in change-context mode.

## Procedure

```bash
python3 plugins/sulis/scripts/sulis-change start \
  --slug introduce-payments \
  --primitive create \
  --intent "add subscription billing" \
  --spawn
```

## Expected — JSON output (the calling shell)

```json
{
  "ok": true,
  "data": {
    "change_id": "01H...",
    "handle": "CH-01H...",
    "branch": "change/create-introduce-payments",
    "primitive": "create",
    "slug": "introduce-payments",
    "worktree_path": ".../agents-change-create-introduce-payments",
    "context_md_path": ".../.sulis/changes/01H.../CONTEXT.md",
    "spawn_result": {
      "status": "spawned",
      "pid": 1234,
      "terminal_app_used": "Terminal.app",
      "script_path": ".../.sulis/changes/01H.../launch.sh",
      "session_json_path": ".../.sulis/changes/01H.../session.json",
      "error": null
    }
  }
}
```

## Expected — new terminal window

1. Opens in the change worktree directory.
2. `echo $SULIS_CHANGE_ID` prints the ULID.
3. `claude --agent sulis` starts with the pre-prompt.
4. Sulis greets in change-context mode: names the handle + intent, states
   the primitive, surfaces the recon's suggested next step
   (`/sulis:specify` for a create primitive). Composes with WP-007.

## Expected — recon artefact

```bash
cat ~/.sulis/changes/{change_id}/CONTEXT.md
```
Shows change identity, git state at spawn, and the suggested next step.

## Failure path (honest, non-fatal)

If the spawn fails (e.g. Linux with no terminal app), `spawn_result.status`
is `"failed"` with an actionable `error`, but `ok` is still `true` and the
branch + worktree + metadata + recon are all committed. Fall back to:
```bash
cd {worktree_path} && SULIS_CHANGE_ID={change_id} claude --agent sulis
```
