# MCP tool reference

**Applies to:** sulis-execution-mcp v0.1.0

The MCP server registers one tool per OpenAPI operation. Tool names
follow `snake_case` per the MCP convention; descriptions are the
OpenAPI `description` field verbatim (already authored for the LLM
audience).

For full input/output schemas per tool, the canonical place is the
running server's `tools/list` response. Run:

```bash
# Show registered tools in JSON
python -c "
from pathlib import Path
from sulis_execution_mcp.server import load_openapi_spec, build_tool_registry
import json
spec = load_openapi_spec(Path('plugins/sulis-execution/sdk/sulis-execution.openapi.yaml'))
registry = build_tool_registry(spec)
print(json.dumps(
    [{'name': k, 'description': v['tool'].description[:120], 'binary': v['binary']}
     for k, v in sorted(registry.items())],
    indent=2,
))
"
```

## All 38 tools

| Tool name | Underlying binary | Resource |
|---|---|---|
| `blocker_archive` | wpx-blocker | blocker |
| `blocker_write` | wpx-blocker | blocker |
| `change_adopt` | sulis-change | change |
| `change_finish` | sulis-change | change |
| `change_list` | sulis-change | change |
| `change_start` | sulis-change | change |
| `change_status` | sulis-change | change |
| `findings_draft_remediation` | wpx-findings | findings |
| `findings_register` | wpx-findings | findings |
| `index_add` | wpx-index | index |
| `index_flip_status` | wpx-index | index |
| `index_list_ready` | wpx-index | index |
| `index_mark_downstream_blocked` | wpx-index | index |
| `index_read_config` | wpx-index | index |
| `index_set_status` | wpx-index | index |
| `index_register_pending_drafts` | wpx-index | index |
| `journal_add_plan_item` | wpx-journal | journal |
| `journal_complete_step` | wpx-journal | journal |
| `journal_init` | wpx-journal | journal |
| `journal_update_plan_item` | wpx-journal | journal |
| `journal_read` | wpx-journal | journal |
| `journal_record_attempt` | wpx-journal | journal |
| `journal_record_security_verdict` | wpx-journal | journal |
| `journal_record_preflight` | wpx-journal | journal |
| `journal_create_plan` | wpx-journal | journal |
| `journal_start_step` | wpx-journal | journal |
| `pipeline_run` | wpx-pipeline | pipeline |
| `lifecycle_complete` | wpx-step12 | lifecycle |
| `train_doctor` | wpx-train | train |
| `train_queue_add` | wpx-train | train |
| `train_queue_list` | wpx-train | train |
| `train_queue_remove` | wpx-train | train |
| `train_run` | wpx-train | train |
| `train_status` | wpx-train | train |
| `worktree_create` | wpx-worktree | worktree |
| `worktree_remove` | wpx-worktree | worktree |
| `work_package_append_evidence` | wpx-wp | work_package |
| `work_package_read_metadata` | wpx-wp | work_package |

## Tool descriptions

Each tool's description is the LLM-facing prompt. Examples:

### `pipeline_run`

> Polls CI for the WP's branch, rebases if the base branch has
> advanced, squash-merges to the base branch, polls the deploy
> workflow, runs health + smoke. Returns a structured result with
> outcome (success / blocker / error) and per-step verdicts.

### `change_start`

> Creates `change/{primitive}-{slug}` branched off base (default
> dev), provisions a sibling worktree, writes
> .changes/{primitive}-{slug}.yaml metadata.

### `train_run`

> Per ADR-212: rebases each eligible WP onto previous, runs
> bundled-tip CI, squash-merges sequentially, runs ONE deploy +
> health + smoke for the whole batch.

Full descriptions live in [`sulis-execution.openapi.yaml`](../../sulis-execution.openapi.yaml).

## See also

- [Operation catalogue](operations.md)
- [Transport bindings](transport-bindings.md)
- [MCP Claude Desktop tutorial](../tutorials/mcp/with-claude-desktop.md)
