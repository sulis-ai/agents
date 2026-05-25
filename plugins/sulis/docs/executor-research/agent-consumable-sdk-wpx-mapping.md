# Applying the Agent-Consumable SDK Spec to wpx-*

**Version:** 0.2.0 (aligned with SDK spec v0.2.0 — universal restructure)
**Date:** 2026-05-21
**Status:** Research + recommendation
**Reads:** [`agent-consumable-sdk-spec.md`](agent-consumable-sdk-spec.md) (the generic spec)

---

## TL;DR

The generic spec at `agent-consumable-sdk-spec.md` (v0.2.0) defines the
established convention for agent-consumable SDKs using two axes: a
**schema layer** (operations + types + outcome-category errors) and a
**transport binding** (HTTP, MCP, subprocess, library, …). This document
transposes both axes onto the wpx-* tools in
`plugins/sulis-execution/scripts/`.

wpx already has the right primitives:
- Structured JSON output (success/error envelope; pipeline-result wrapper)
- Exit-code discipline (0/1/2) that maps cleanly onto the three outcome
  categories (Protocol / Expected / Internal — see v0.2.0 Part 3)
- Typed Python dataclasses in `_wpxlib.py` (`WPRow`, `TrainOverrides`,
  `EligibilityResult`, `WpxPaths`, `MdTable`)
- A shared input contract (`--project`, `--repo-root`,
  `$GITHUB_REPOSITORY`)

What's missing is the *schema layer* that would let us generate typed
Python + TS clients mechanically.

**Proposal:**

1. **Author an OpenAPI 3.1 spec** at
   `plugins/sulis-execution/scripts/wpx-sdk.openapi.yaml` describing
   every wpx subcommand as an RPC-shaped operation.
2. **Choose transport binding(s).** wpx today is **Subprocess + JSON-on-stdout**
   (v0.2.0 Part 4.3) — the wpx-* tools are explicitly named as that
   binding's reference implementation. The agent-facing layer adds
   **JSON-RPC over stdio (MCP)** (v0.2.0 Part 4.2) so LLMs can call
   wpx tools directly.
3. **Generate per-language clients** (v0.2.0 Part 5): `sulis_wpx`
   (Python, Pydantic v2) and `@sulis-ai/wpx` (TypeScript, typed interfaces).
4. **Generate** an MCP server so LLMs can call wpx tools directly via
   `tools/list` + `tools/call`.

The schema layer (OpenAPI 3.1 file) is shared across both transport
bindings — same operations, same types, same error categories, two
different invocation mechanisms.

---

## Part 1 — What wpx already has (primitives map per v0.2.0)

| Generic spec axis / requirement | wpx today | Source file |
|---|---|---|
| **Schema axis (Part 2 of v0.2.0)** | | |
| Schema language | Implicit — Python dataclasses in `_wpxlib.py` + CLI argument tables | `_wpxlib.py` |
| Operation surface | `wpx-{tool} {subcommand}` cleanly maps to `client.{tool}.{subcommand}` | All wpx-* tools |
| Type definitions | `WPRow`, `TrainOverrides`, `EligibilityResult`, `WpxPaths`, `MdTable` dataclasses | `_wpxlib.py` |
| Required-field discipline | argparse `required=True`; dataclass non-Optional fields | All wpx-* tools |
| **Error model (Part 3 of v0.2.0)** | | |
| Three universal categories supported | Exit code 0/1/2 maps to success / Expected / Internal naturally | All wpx-* tools |
| `ProtocolError` mapping | Exec failure: binary missing, permission denied (no exit code captured) | OS level |
| `ExpectedError` mapping | Exit code 1 + `{ok: false, error: "...", context: {...}}` JSON | `emit_error` in `_wpxlib.py` |
| `InternalError` mapping | Exit code 2 + traceback on stderr | `emit_internal_error` in `_wpxlib.py` |
| **Transport axis (Part 4 of v0.2.0)** | | |
| Subprocess + JSON-on-stdout binding (4.3) | Native — this is exactly what wpx-* tools do | All wpx-* tools (reference impl) |
| MCP-over-stdio binding (4.2) | Not yet — would be the agent-facing front | (proposed) |
| HTTP binding (4.1) | Not applicable — no HTTP server | N/A |
| **Operational concerns** | | |
| Structured pipeline-result wrapper | `emit_result(record, exit_code)` wraps result in `{"data": {"result": {...}}}` | `_wpxlib.py` |
| Shared input contract | `--project`, `--repo-root`, `$GITHUB_REPOSITORY` env fallback | `add_common_args` |
| Idempotent guards | `wpx-index flip-status --expected <current>` (CAS-style) | `wpx-index` |
| Atomic chained operations | `wpx-step12 wrap` chains evidence + flip + cleanup (fail-fast) | `wpx-step12` |

### Coverage assessment

Nearly every primitive from the generic spec has a wpx implementation
today. The three universal outcome categories already align with wpx's
existing 0/1/2 exit-code discipline — no semantic gymnastics needed
to map them.

The Subprocess + JSON-on-stdout binding (v0.2.0 Part 4.3) calls out the
wpx-* tools as its reference implementation. The wpx codebase isn't
adopting a new convention; it's already the canonical example of one.

### What's NOT in wpx today (the gap)

| Generic spec requirement | wpx today | What's needed |
|---|---|---|
| **Explicit schema document** (OpenAPI 3.1 or similar) | None | Author `wpx-sdk.openapi.yaml` |
| **Codegen configuration** | None | Author `wpx-sdk.yml` |
| **Generated Python client** | None (callers shell out via subprocess) | Generate `sulis_wpx` |
| **Generated TypeScript client** | None | Generate `@sulis-ai/wpx` |
| **MCP server (Part 4.2 binding)** | None (CLI-only; agents shell out and parse JSON) | Hand-author using MCP Python SDK |
| **Per-language error class hierarchy** | Exit codes carry the category but no class hierarchy exists in Python/TS | Generate `ProtocolError` / `ExpectedError` / `InternalError` hierarchy (per v0.2.0 Part 3.3) plus wpx-domain extensions |
| **Auto-pagination** | N/A (no paginated endpoints today; volumes are small) | Skip until needed |
| **Streaming** | N/A (no streaming endpoints today) | Skip until needed |

---

## Part 2 — Tool surface inventory

The OpenAPI spec needs to model every wpx subcommand. Inventory:

| Tool | Subcommands | Purpose |
|---|---|---|
| `wpx-pipeline` | `run` | Steps 8-10 per-WP pipeline |
| `wpx-train` | `queue-list`, `queue-add`, `queue-remove`, `status`, `doctor`, `run` | Batched merge queue + eligibility discovery |
| `wpx-index` | `flip-status`, `set-status`, `list-ready`, `read-config`, `propagate-blocked`, `add-wp`, `sync-auto-drafts` | INDEX.md management |
| `wpx-journal` | `init`, `start-step`, `complete-step`, `record-attempt`, `record-preflight`, `record-postdeploy`, `seed-plan`, `mark-plan-item`, `add-plan-item`, `read` | Per-WP executor journal |
| `wpx-blocker` | `write`, `archive` | EL-08 BLOCKER record management |
| `wpx-findings` | `register`, `auto-draft-wp` | Security findings register |
| `wpx-wp` | `read-frontmatter`, `append-evidence` | WP file operations |
| `wpx-worktree` | `create`, `remove` | Git worktree lifecycle |
| `wpx-step12` | `wrap` | Atomic Step 12 (evidence + flip + cleanup) |
| `sulis-change` | `start`, `adopt`, `finish`, `list`, `status` | Change branch + worktree management (CW-01..CW-08) |

**Total: ~38 subcommands across 10 tools.**

Per the generic spec's "Resource tree" convention (v0.2.0 Part 5),
these become:

```
client.pipeline.run(...)
client.train.queue_list(...)
client.train.queue_add(...)
client.train.run(...)
client.index.flip_status(...)
client.index.list_ready(...)
client.journal.start_step(...)
client.journal.complete_step(...)
client.blocker.write(...)
client.findings.register(...)
client.wp.read_frontmatter(...)
client.worktree.create(...)
client.step12.wrap(...)
client.change.start(...)
client.change.finish(...)
```

Resources are nouns (pipeline, train, index, journal, blocker, findings,
wp, worktree, step12, change). Methods are verbs (run, flip_status, write).

---

## Part 3 — Schema layer for wpx

Per v0.2.0 Part 2, we choose a schema language matching the transport
goals. For wpx:

**Choice: OpenAPI 3.1.** Rationale:

- The schema layer is transport-agnostic in v0.2.0; OpenAPI 3.1's
  HTTP-bias doesn't bind us (we use it as a schema container, not for
  its HTTP semantics).
- Open-source codegen exists for both Python (`openapi-python-client`)
  and TypeScript (`openapi-typescript`).
- The MCP server target can read OpenAPI directly and register tools
  from operations (each `operationId` → MCP tool name; `requestBody.schema`
  → `inputSchema`; `responses.200.schema` → `outputSchema`).
- Smithy would also work and would be more transport-neutral, but
  OpenAPI's per-language codegen ecosystem is more mature today.

**Note on the OpenAPI HTTP-bias:** OpenAPI 3.1 was designed for HTTP
APIs. The paths/verbs/status codes in OpenAPI files map to HTTP
mechanics. For wpx (which is subprocess-shaped), we use the paths as
operation IDs only (e.g., `/pipeline/run` becomes `operationId:
pipelineRun`) and the responses 200/4xx/5xx as schema-container
shapes only (the actual transport binding in Part 5 of this document
maps wpx's 0/1/2 exit codes onto outcome categories, ignoring HTTP).

This works but is slightly off-label use of OpenAPI. A future revision
could move to Smithy or a custom schema container if the off-label use
proves friction-heavy.

### Worked example: `wpx-pipeline run`

This is the canonical example. Every other tool follows the same shape.

#### Operation

```yaml
paths:
  /pipeline/run:
    post:
      operationId: pipelineRun
      summary: Run the per-WP Steps 8-10 pipeline
      description: |
        Polls CI for the WP's branch, rebases if the base branch has
        advanced, squash-merges to the base branch, polls the deploy
        workflow, runs health + smoke. Returns a structured result
        with outcome (success / blocker / error) and per-step verdicts.

        Use this for hotfix / solo-ship paths. For batched shipping,
        use `train.run`.

        Failure modes (returned as successful operations with
        `outcome: blocker`; the SDK does NOT raise an exception):
        - CI poll timeout or red → outcome: blocker, blocker_reason set
        - Rebase conflict → outcome: blocker
        - Deploy workflow timeout or red → outcome: blocker
        - Health check unhealthy → outcome: blocker
        - Smoke test fail → outcome: blocker

        Errors (the SDK raises):
        - Invalid arguments → ExpectedError
        - Tool crash → InternalError
        - Tool not found / permission denied → ProtocolError
      x-sulis-snippets:
        - language: python
          code: |
            client.pipeline.run(
                wp="WP-001",
                branch="feat/wp-001-introduce-payments",
                project="my-project",
                dev_sha_at_creation="abc123def",
                deploy_workflow="Deploy to Dev",
                staging_url="https://staging.example.com",
                smoke_cmd="curl -sf https://staging.example.com/health",
            )
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PipelineRunRequest'
      responses:
        '200':
          description: Pipeline completed (outcome may be success or blocker — both are normal results)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PipelineRunResult'
        '400':
          $ref: '#/components/responses/ExpectedError'
        '500':
          $ref: '#/components/responses/InternalError'
```

#### Request schema

```yaml
components:
  schemas:
    PipelineRunRequest:
      type: object
      required:
        - wp
        - branch
        - project
        - dev_sha_at_creation
        - deploy_workflow
      properties:
        wp:
          type: string
          pattern: '^WP-[A-Z0-9-]+$'
          description: Work Package ID (e.g. WP-001)
        branch:
          type: string
          pattern: '^feat/wp-.+$'
          description: Feature branch name
        project:
          type: string
          description: Project slug (resolves .architecture/<project>/ paths)
        repo_root:
          type: string
          default: '.'
          description: Repository root directory
        repo:
          type: string
          description: GitHub repo (org/name); defaults to $GITHUB_REPOSITORY env var
        worktree_path:
          type: string
          description: Path to executor worktree (defaults to repo root)
        dev_sha_at_creation:
          type: string
          pattern: '^[0-9a-f]{7,40}$'
          description: origin/dev SHA captured at worktree creation
        deploy_workflow:
          type: string
          description: Deploy workflow name (e.g. "Deploy to Dev Environment")
        staging_url:
          type: string
          format: uri
          description: Staging URL (optional; triggers health check if set)
        health_path:
          type: string
          default: ''
          description: HTTP path for health check (auto-detected from smoke_cmd if empty)
        smoke_cmd:
          type: string
          default: ''
          description: Smoke test shell command
        ci_poll_interval:
          type: integer
          minimum: 30
          default: 300
        deploy_poll_interval:
          type: integer
          minimum: 30
          default: 300
        skip_ci_poll:
          type: boolean
          default: false
        base_branch:
          type: string
          default: 'dev'
          description: |
            Base ref for rebase + merge (CW-04). When invoked inside a
            change worktree, callers pass the change branch name so
            WPs ship to the change branch rather than directly to dev.
```

#### Response schema (success-shape; blockers are also "success" at the SDK layer)

```yaml
    PipelineRunResult:
      type: object
      required: [ok, data]
      properties:
        ok:
          type: boolean
        data:
          type: object
          required: [result]
          properties:
            result:
              $ref: '#/components/schemas/PipelineResult'

    PipelineResult:
      type: object
      required: [wp, outcome, completed_at]
      properties:
        wp:
          type: string
        outcome:
          type: string
          enum: [success, blocker, error]
          description: |
            success = pipeline completed cleanly.
            blocker = pipeline ran but reported a deterministic failure
                      (CI red, deploy timed out, smoke failed). Inspect
                      blocker_reason; this is NOT an exception — the SDK
                      returns this result and the caller decides.
            error = unexpected internal state (rare; bug in the pipeline
                    itself). The SDK MAY raise InternalError instead.
        merge_sha:
          type: string
          nullable: true
        deploy_url:
          type: string
          nullable: true
        deploy_workflow_run:
          type: string
          nullable: true
        health_status:
          type: string
          enum: [healthy, unhealthy, skipped]
          nullable: true
        health_url:
          type: string
          nullable: true
        smoke_verdict:
          type: string
          nullable: true
        blocker_reason:
          type: string
          nullable: true
        ci_poll_skipped:
          type: boolean
          default: false
        merge_already_complete:
          type: boolean
          default: false
        started_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
```

#### Error schema

```yaml
    Error:
      type: object
      required: [ok, error]
      properties:
        ok:
          type: boolean
          enum: [false]
        error:
          type: string
          description: Human-readable error message
        context:
          type: object
          additionalProperties: true
          description: Optional structured context

  responses:
    ExpectedError:
      description: Expected failure — invalid input, file not found, etc.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    InternalError:
      description: Internal crash (bug)
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
```

The same pattern repeats for all ~38 operations. Each gets:
- An `operationId` in camelCase (e.g. `pipelineRun`)
- A description written for an LLM audience
- A `requestBody` schema with required fields explicit
- A `200` response schema with the typed result (which may include
  `outcome: blocker`)
- Shared `400` / `500` error responses (the SDK maps these to
  `ExpectedError` and `InternalError` exceptions per Part 4)

---

## Part 4 — Error model mapping per v0.2.0 Part 3

This is the load-bearing alignment with v0.2.0. The generic spec
defines three universal outcome categories; this section maps wpx's
exit codes + JSON envelope shape onto them.

### The mapping

| wpx native | v0.2.0 category | Python client behaviour |
|---|---|---|
| **Exec failure** (binary not found, permission denied) | `ProtocolError` | SDK raises `ProtocolError` subclass |
| **Exit 0, ok:true** | Successful operation | SDK returns the typed result |
| **Exit 1, ok:true, outcome=blocker** | Successful operation (the operation succeeded; the result happens to be a deterministic blocker) | SDK returns the typed result with `outcome=blocker`; caller inspects `blocker_reason` |
| **Exit 1, ok:false, error="..."** | `ExpectedError` | SDK raises `ExpectedError` (or domain subclass — e.g., the `--expected` mismatch in `wpx-index flip-status` raises `ConflictError`) |
| **Exit 2 + traceback on stderr** | `InternalError` | SDK raises `InternalError` with the traceback in `body` |

### Why "blocker" is NOT an exception

This is the most important deviation from a naive HTTP-shaped mapping.
In wpx, a "blocker" outcome means the operation ran successfully — the
pipeline executed all its steps and reported what happened. The fact
that one of those steps failed (CI was red, deploy timed out) is part
of the operation's *result*, not the operation's *failure*.

Treating "blocker" as an exception would conflate two semantically
distinct things:
- "I couldn't run the operation" (raise an exception)
- "I ran the operation, and the result is that things didn't go well"
  (return a typed result that includes the bad news)

The generic spec (v0.2.0 Part 3.5) supports this distinction via the
`outcome` field on the result. Exceptions are reserved for the cases
where the SDK couldn't return a meaningful result at all.

### Domain extensions

Per v0.2.0 Part 3.4, domain errors extend the canonical hierarchy. For wpx:

```python
# wpx-specific extensions of the canonical hierarchy
class IndexStatusMismatchError(ConflictError):
    """Raised when `wpx-index flip-status --expected X` finds the
    actual status was not X. The caller's assumption about the
    INDEX state was wrong; refresh and retry."""

class BlockerAlreadyExistsError(ConflictError):
    """Raised when `wpx-blocker write` finds a BLOCKER file already
    exists for the WP. Use --force to overwrite or call archive
    first."""

class WorkPackageNotFoundError(NotFoundError):
    """Raised when a wpx command references a WP that isn't in
    INDEX.md and has no WP-NNN.md file."""
```

These all extend the canonical subtypes (per v0.2.0 Part 3.4 —
`ConflictError`, `NotFoundError`). The agent's mental model of "catch
`ConflictError` for retry-after-refresh logic" works across all wpx
operations.

### Error fields (per v0.2.0 Part 3.5)

Every wpx error exposes:

| Field | Source |
|---|---|
| `message` | `error` field from the JSON envelope |
| `category` | One of `protocol` / `expected` / `internal` |
| `transport_code` | Exit code (0/1/2) + the `context` object if present |
| `correlation_id` | Process PID + start timestamp (constructed by the SDK) |
| `body` | The full JSON envelope from stdout (when present) |
| `code` | Domain-specific code if `context.code` is set |

---

## Part 5 — Transport binding choice

Per v0.2.0 Part 4, the SDK chooses a transport binding. For wpx:

### Primary transport: Subprocess + JSON-on-stdout (v0.2.0 Part 4.3)

This is what the wpx-* tools already do natively. The Python and
TypeScript clients spawn the wpx CLI as a subprocess, write argv,
read stdout JSON, parse, and raise/return per Part 4.

Per v0.2.0 Part 4.3, this binding's conventions:

| Concern | Wpx implementation |
|---|---|
| Invocation | argv + env vars; reads stdout for JSON result; exits 0/1/2 |
| ProtocolError | Exec failed (binary missing, permission denied) |
| ExpectedError | Exit 1 + `{ok: false, error: "..."}` JSON |
| InternalError | Exit 2 + traceback on stderr |
| Retries | Disabled (local ops; no transient transport failures) |
| Telemetry | stderr stream; structured log lines (`[ISO-8601] msg`); PID + timestamp form correlation ID |
| Authentication | Inherited from process (parent process trusted); short-lived tokens via env var or argv |
| Streaming | Line-delimited JSON on stdout (NDJSON) — used by `wpx-pipeline` for in-progress events |

### Secondary transport: JSON-RPC over stdio (MCP) (v0.2.0 Part 4.2)

The agent-facing layer. For LLMs calling wpx tools directly (via Claude
Desktop, Cursor, or any MCP-compatible client), MCP is the canonical
transport.

A small MCP server hand-authored using the MCP Python SDK:
- Reads the `wpx-sdk.openapi.yaml` at startup
- Registers each operation as an MCP tool via `tools/list`
- On `tools/call`, dispatches to the corresponding wpx CLI subcommand
  (the subprocess transport beneath)
- Returns the JSON result via MCP's result envelope; maps wpx exit
  codes onto MCP's two error channels per v0.2.0 Part 4.2

### The shared schema is the source of truth

Both transport bindings consume the same `wpx-sdk.openapi.yaml` file.
The schema layer doesn't change; only the wire mechanism does.

This is the v0.2.0 Part 1 separation working in practice: schema
is one primitive; transport is another; you can pick one or both
without rewriting either.

---

## Part 6 — Per-language generation (v0.2.0 Part 5)

The generated Python client uses Pydantic v2; the generated TypeScript
client uses typed interfaces. Both adhere to the parity contract
(v0.2.0 Part 6).

### 6.1 Generated Python client

```python
# Caller code
from sulis_wpx import (
    Wpx, AsyncWpx,
    ExpectedError, InternalError, ProtocolError,
    ConflictError, NotFoundError,  # canonical hierarchy from v0.2.0
    IndexStatusMismatchError,        # wpx domain extension
)

client = Wpx(repo_root=".", project="my-project")

# Direct resource access (mirror of wpx CLI subcommands)
result = client.pipeline.run(
    wp="WP-001",
    branch="feat/wp-001-introduce-payments",
    dev_sha_at_creation="abc123def",
    deploy_workflow="Deploy to Dev",
    staging_url="https://staging.example.com",
    smoke_cmd="curl -sf https://staging.example.com/health",
)
# result is a Pydantic model
assert result.outcome in {"success", "blocker", "error"}

# A blocker is a returned result, NOT an exception
if result.outcome == "blocker":
    print(f"Blocker: {result.blocker_reason}")
    # Caller decides what to do — write a BLOCKER file, retry later, etc.

# Exceptions are for cases where the operation couldn't return a result
try:
    client.index.flip_status(wp="WP-001", to="done", expected="in_progress")
except IndexStatusMismatchError as e:
    # Status was not the expected "in_progress" — refresh and retry
    print(f"Conflict: {e.message}; current status: {e.context.get('actual')}")
except ExpectedError as e:
    # Other expected failures (e.g., WP doesn't exist)
    print(f"Cannot flip: {e.message}")
```

#### Sync vs async

```python
# Sync client
client = Wpx(...)
result = client.pipeline.run(...)

# Async client (same shape; awaitable methods)
async_client = AsyncWpx(...)
result = await async_client.pipeline.run(...)
```

#### Typed return models

```python
from sulis_wpx.types import PipelineResult

result: PipelineResult = client.pipeline.run(...)

# Pydantic v2 conveniences
result.model_dump()       # dict
result.model_dump_json()  # JSON string
result.model_copy(update={"outcome": "success"})  # immutable update
```

### 6.2 Generated TypeScript client

```typescript
import {
  Wpx,
  ExpectedError, InternalError, ProtocolError,
  ConflictError, NotFoundError,
  IndexStatusMismatchError,
} from '@sulis-ai/wpx';

const client = new Wpx({ repoRoot: '.', project: 'my-project' });

const result = await client.pipeline.run({
  wp: 'WP-001',
  branch: 'feat/wp-001-introduce-payments',
  dev_sha_at_creation: 'abc123def',         // snake_case preserved from wire
  deploy_workflow: 'Deploy to Dev',
  staging_url: 'https://staging.example.com',
  smoke_cmd: 'curl -sf https://staging.example.com/health',
});

if (result.outcome === 'blocker') {
  console.log(`Blocker: ${result.blocker_reason}`);
}

try {
  await client.index.flipStatus({ wp: 'WP-001', to: 'done', expected: 'in_progress' });
} catch (err) {
  if (err instanceof IndexStatusMismatchError) {
    console.log(`Conflict: ${err.message}`);
  } else if (err instanceof ExpectedError) {
    console.log(`Cannot flip: ${err.message}`);
  }
}
```

#### Notes per v0.2.0 Part 6 parity contract

- `client.pipeline.run` and `client.index.flipStatus` — methods are
  camelCase (TS idiom); resources match Python single-word resources
  (`pipeline`, `index`).
- Request body fields are `snake_case` — preserved from the wire format.
  This is the parity rule from v0.2.0 Part 6 for JSON-wire transports.
- Async-only (Promise-returning). No sync client in TS per v0.2.0
  convention.
- Error class names (`ExpectedError`, `ConflictError`,
  `IndexStatusMismatchError`) are identical across Python and
  TypeScript per v0.2.0 Part 6.

---

## Part 7 — The MCP transport in detail (v0.2.0 Part 4.2)

When the LLM calls wpx tools directly (via MCP), the same OpenAPI spec
generates the MCP tool listing.

### Tool naming

| OpenAPI `operationId` | MCP tool `name` (snake_case per v0.2.0 Part 4.2) |
|---|---|
| `pipelineRun` | `pipeline_run` |
| `trainQueueList` | `train_queue_list` |
| `indexFlipStatus` | `index_flip_status` |
| `changeStart` | `change_start` |

### Tool description (the LLM-facing prompt)

For each operation, the MCP server uses the OpenAPI `description`
field verbatim as the LLM-facing tool description. Write descriptions
for the LLM as the audience: lead with intent, list required inputs,
name common outcomes, mention failure modes.

Example for `pipeline_run`:

```
Run the per-WP Steps 8-10 pipeline. Polls CI for the WP's branch,
rebases if the base branch has advanced, squash-merges to the base
branch, polls the deploy workflow, runs health + smoke. Returns a
structured result with outcome (success / blocker / error) and
per-step verdicts.

Use this for hotfix / solo-ship paths. For batched shipping, use
train_run.

Required: wp, branch, project, dev_sha_at_creation, deploy_workflow.

Outcomes (returned as normal results — not errors):
- success: WP merged to base branch, deploy + health + smoke all green
- blocker: deterministic failure with blocker_reason set
- error: internal crash; check stderr

Errors (returned as JSON-RPC errors):
- Invalid arguments → JSON-RPC code -32602
- Tool not found / permission denied → ProtocolError
- Internal crash → JSON-RPC code -32603
```

### Tool I/O

- `inputSchema` = the OpenAPI `requestBody` schema
- `outputSchema` = the OpenAPI `200` response schema (the
  `PipelineResult` shape including `outcome: blocker` as a normal value)
- Per v0.2.0 Part 4.2 two-channel error model:
  - **Tool-execution outcomes** (success, blocker) returned as normal
    results — so the LLM can see them and decide what to do next.
  - **Protocol errors** (validation failures, missing tool, internal
    crash) raised as JSON-RPC errors.

The two-channel model maps cleanly:
- exit 0 / exit 1 with `ok:true` (success or blocker) → normal result
- exit 1 with `ok:false` → JSON-RPC -32602 (invalid params / expected
  error)
- exit 2 → JSON-RPC -32603 (server error)
- exec failure → JSON-RPC transport error (-32700 / connection drop)

---

## Part 8 — Why these specific bindings

Per v0.2.0 Part 4, transport choice is a deliberate decision.

### Why Subprocess + JSON-on-stdout (Part 4.3) as primary

1. **It's what wpx already is.** No change to the existing tools.
2. **The wpx-* tools are explicitly named** as v0.2.0 Part 4.3's
   reference implementation. We're already the canonical example.
3. **Local-only ops don't need a network.** Filesystem and git ops
   don't have network failure modes; the subprocess binding's
   "no-retry, no-network-telemetry" defaults match wpx's reality.
4. **JSON-on-stdout is debuggable.** When something goes wrong,
   `wpx-pipeline run ... | jq` gives you the structured output
   without an SDK layer in between.

### Why JSON-RPC over stdio / MCP (Part 4.2) as agent-facing

1. **LLMs are the primary consumer.** The marketplace's existing
   agents (concierge, executor, code-review, etc.) invoke wpx tools.
   MCP is the LLM-native protocol for that.
2. **MCP runs over stdio natively.** Matches today's subprocess model
   (each tool invocation is a process; returns JSON). No new HTTP
   server to manage.
3. **Anthropic's MCP SDKs (Python + TypeScript) ship the server
   primitives.** We don't roll our own protocol layer.
4. **OpenAPI → MCP is a thin transformation.** Operations become
   tools; descriptions become LLM prompts; request schemas become
   `inputSchema`; response schemas become `outputSchema`.

### Why not HTTP / REST (Part 4.1)

The wpx tools are local-only. There's no HTTP server. Standing one
up adds a new process to manage, a port to allocate, an auth story to
design, all for a benefit (network reach) that wpx doesn't need.

If a future use case requires HTTP (e.g., a remote orchestrator
invoking wpx on a cloud worker), the OpenAPI spec stays the same; a
new HTTP server target binds to it. The schema layer doesn't change.

### Why not gRPC / Protobuf (Part 4.5)

Protobuf's wire-level advantages (binary; small payloads; bidirectional
streams) don't matter for wpx's scale. The operations run in seconds-
to-minutes; payloads are kilobytes; nothing streams continuously. The
gRPC tooling overhead doesn't pay back.

### Why not library / in-process (Part 4.4)

wpx tools shell out to `git` and `gh` CLIs. Pulling them into the
host process would mean replacing those CLI invocations with
in-process libraries (`pygit2`, `PyGithub`) — a much larger change
than just generating a typed client around the existing CLI surface.

The library-binding option remains open for the future; not v0.1 of
the SDK.

---

## Part 9 — Migration strategy

The existing wpx tools don't change. The migration is **additive**:

### Phase 1: Author the spec
- New file: `plugins/sulis-execution/scripts/wpx-sdk.openapi.yaml`
- New file: `plugins/sulis-execution/scripts/wpx-sdk.yml` (codegen config)
- Describe every existing subcommand (~38 operations)

### Phase 2: Generate the clients
- Python: `openapi-python-client generate --path wpx-sdk.openapi.yaml`
  → produces `sulis_wpx` (Pydantic v2 + httpx, but here we override
  the transport with subprocess)
- TypeScript: `openapi-typescript wpx-sdk.openapi.yaml --output types.ts`
  + a hand-written 50-line `client.ts` wrapper that invokes the
  subprocess and maps the response
- Each client's transport layer is the Part 4.3 subprocess binding —
  spawn the wpx CLI; write argv; read stdout; map exit code + JSON
  to outcome/exception per Part 4 above

### Phase 3: Generate the MCP server
- Hand-author using MCP Python SDK
- Reads the OpenAPI spec at startup
- Registers each operation as an MCP tool via `tools/list`
- On `tools/call`, dispatches to the corresponding wpx CLI subcommand
- Maps wpx exit codes + JSON envelope onto MCP's two error channels
  (per Part 7 above; per v0.2.0 Part 4.2)

### Phase 4: Pilot a new tool spec-first
- Pick the next tool we'd build (e.g. a `sulis-change-train` that
  ships multiple changes as a single train)
- Define its OpenAPI operations + schemas BEFORE writing the
  implementation
- Generate Python + TS clients + MCP tools
- The implementation then becomes a CLI subcommand that conforms to
  the spec — but the spec is authored first

### Phase 5 (later): Migrate existing tools to spec-first
- Treat the current `_wpxlib.py` types as the implementation; the
  OpenAPI spec is the public contract
- When a tool gains a new flag or returns a new field, the OpenAPI
  spec is updated alongside the code (or before, in spec-first mode)

---

## Part 10 — Concrete first deliverable

To make this real, the smallest useful first deliverable is:

**One OpenAPI spec file + one codegen config + one generated Python client + one generated TypeScript client, all describing `wpx-pipeline run` only.**

Effort estimate:
- ~2 hours to author the spec for `wpx-pipeline run` alone
- ~1 hour to write the codegen config
- Free: codegen produces both clients
- ~1 hour to test the generated clients against the actual CLI
- ~1 hour to wire the transport layer (subprocess spawn + JSON parse)
- **Total: ~5 hours for the pilot**

After that proof-of-concept, the remaining ~37 operations are mechanical
schema authoring (~2-3 hours total). The hard part is the first operation;
subsequent ones follow the pattern.

---

## Part 11 — Where this stops short

- **Concrete OpenAPI spec for every wpx-* subcommand.** This document
  defines the shape and shows one worked example (`pipeline.run`).
  Producing the full ~38-operation OpenAPI file is the next step.
- **Migration plan for the existing tools.** The Phase 1-5 plan above
  is high-level; each phase needs concrete tasks.
- **Backward-compatibility versioning.** OpenAPI has versioning
  conventions (path-based: `/v1/...`, `/v2/...`); the SDK package
  version (sulis-wpx `0.1.0` initially) is the package-level version.
- **Subprocess transport plumbing.** The codegen tools listed are
  HTTP-shaped by default. We'd override the generated `httpx` client
  in the Python SDK with a thin `subprocess` wrapper. This is custom
  code; not generated; but it's a small wrapper.
- **The companion docs spec** (see
  [`agent-consumable-sdk-docs-spec.md`](agent-consumable-sdk-docs-spec.md))
  describes what docs accompany the generated SDK. The wpx SDK
  produces: Tutorials (Python getting-started + TypeScript getting-started
  + MCP-with-Claude-Desktop), How-tos (error handling, common
  patterns), Reference (auto-generated per language + MCP tool
  reference), Explanation (why subprocess + MCP transports; how
  "blocker" is not an exception). All four Diátaxis quadrants apply.

---

## Sources

For the generic spec sources, see
[`agent-consumable-sdk-spec.md`](agent-consumable-sdk-spec.md). The
wpx-specific sources:

**wpx code references** (all in `/Users/iain/Documents/repos/agents/plugins/sulis-execution/scripts/`):

- `_wpxlib.py` — shared helpers; `emit_ok` / `emit_error` /
  `emit_result` at lines 107-148; dataclasses `WPRow`,
  `TrainOverrides`, `EligibilityResult`, `WpxPaths`, `MdTable`
- `wpx-pipeline` — per-WP Steps 8-10 pipeline
- `wpx-train` — batched merge queue (ADR-212)
- `wpx-index` — INDEX.md management
- `wpx-journal` — per-WP executor journal
- `wpx-blocker` — EL-08 BLOCKER records
- `wpx-findings` — security findings register + auto-draft WPs
- `wpx-wp` — WP file operations (frontmatter, evidence)
- `wpx-worktree` — git worktree lifecycle
- `wpx-step12` — atomic Step 12 (evidence + flip + cleanup)
- `sulis-change` — change branch + worktree management (CW-01..CW-08)
- `wpx` — Bash dispatcher

**Related marketplace standards:**

- [`plugins/sulis/references/convention-preference-standard.md`](../../../sulis/references/convention-preference-standard.md)
  — CP-01 (recommend established conventions)
- [`plugins/sulis/references/change-work-standard.md`](../../../sulis/references/change-work-standard.md)
  — CW-01..CW-08 (the change-bounded workflow that wpx now supports)
- [`plugins/sulis/references/lifecycle.md`](../../references/lifecycle.md)
  — the Step 1-12 executor lifecycle (Steps 8-10 ship via wpx-pipeline
  or wpx-train depending on path)

---

## Version history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-21 | Initial mapping. Used v0.1.0 SDK spec section numbers; treated MCP as a codegen target; bespoke `WpxBlockerError` exception class for blocker outcomes. |
| 0.2.0 | 2026-05-21 | Aligned to SDK spec v0.2.0: schema/transport split made explicit; outcome-category error model adopted (Protocol / Expected / Internal); "blocker" reframed as a successful operation outcome (NOT an exception); MCP elevated to transport binding (v0.2.0 Part 4.2) alongside Subprocess + JSON-on-stdout (v0.2.0 Part 4.3); section numbers refreshed to point at v0.2.0 structure. |
