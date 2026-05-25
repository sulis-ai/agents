# Agent Shape Conventions

The conventions for what an `agent.md` file looks like in the Sulis marketplace. This is the equivalent of `add-skill/references/kinds-and-tools-learnings.md` — provenance + shape reference, consulted at Gate 3 (Generate).

## Anatomy of an agent.md

```markdown
---
name: <kebab-case>
description: <one or two sentences — the dispatch contract>
user_invocable: true  # optional; false default per Claude Code
model: sonnet         # optional; haiku / sonnet / opus / omit
tools: [Read, Edit, Bash, Agent]  # optional; * default (inherit)
standards:            # required for v0.1.0+ standards-grounded agents
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
  output: [CRITICAL_THINKING_STANDARD, TONE_STANDARD, COACHING_STANDARD]
verification_spiral:  # required for v0.1.0+
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  custom_dimensions: []
related_skills:       # required if agent dispatches skills/agents
  - relationship: depends_on
    skill: <path>
    notes: <semantic context>
register:             # required if Audience is founder-facing or both
  founder_mode: default
  technical_mode:
    shape: <json_envelope | markdown_with_paths | diff | raw_tool_output | structured_summary>
    triggers: [intent, --raw, /sulis:jargon]
---

# Agent Name (Title Case)

## Role

<One paragraph: what you are. Lead with the conclusion per PP-01.>

## Required reading

<Optional list of standards / references the agent must consume on dispatch.>

## Workflow / Main loop / When dispatched

<Step-by-step what the agent does.>

## Output shape / Output contract

<What the agent produces. For dual-register: founder-mode shape AND technical-mode shape with examples of each.>

## Gotchas

<Optional — top 3-5 things the agent must avoid.>

## Vocabulary

<Optional — domain terms the agent introduces.>
```

## Frontmatter fields explained

### `name` (required)

Kebab-case identifier. Becomes the `subagent_type` when dispatched via `Agent(subagent_type=<name>)`. Must be unique across the marketplace.

Convention: short (1-3 words), descriptive, ends with the agent's role-noun:

- `executor`, `orchestrator`, `concierge` (single role-nouns — concise + memorable)
- `requirements-analyst`, `engineering-architect`, `security-reviewer` (role descriptions — when the single noun would be ambiguous)
- `context-cartographer` (role + domain — when needed for disambiguation)

Avoid:

- Verbs (`run-executor`, `dispatch-orchestrator`) — agents are nouns, not verbs
- Plurals (`executors`, `analysts`) — a single agent represents one role
- Internal jargon (`wp-executor`, `srd-analyst`) — the name should be founder-readable for user_invocable agents

### `description` (required)

The dispatch trigger. One or two sentences. The parent agent (Sulis, orchestrators, the user-facing CLI) scans this to decide whether to route. Failure modes:

- **Too vague** ("Helps with engineering work") → parent agent routes inappropriately
- **Too specific** ("Runs WP-101 schema migrations") → parent agent doesn't route when it should
- **Mechanism-focused** ("Uses Semgrep + Gitleaks + Trivy to scan") → parent agent doesn't know what semantic work the agent does

Good descriptions name:

1. The role (what kind of work the agent owns)
2. The conditions under which to dispatch (when it should be routed to)
3. (Optional) Hard constraints (what it doesn't own)

Examples from existing agents:

- `executor`: *"Work Package Executor — takes one WP, writes failing tests, makes them pass with minimum code, refactors, updates docs, lints, commits, pushes. Returns when the branch is on remote."* — names role + condition + return contract
- `orchestrator`: *"Walks the Work Package INDEX, picks the next ready WP, dispatches the executor."* — names workflow shape + dispatch target

### `user_invocable` (optional; default `false`)

Set `true` if the founder can invoke the agent directly via `claude --agent <name>`. Sulis, executor, orchestrator are all `user_invocable: true`. Agent-internal agents (only dispatched by other agents) leave this `false` or omit.

### `model` (optional; default `inherit`)

`haiku` / `sonnet` / `opus`. Per-cost-and-latency profile:

- **haiku** — fast cheap; pure classifiers, simple routers, mechanical agents (a depth-mode classifier, a status-formatter)
- **sonnet** — default for most specialist agents (requirements-analyst, engineering-architect, security-reviewer)
- **opus** — coordinator agents with long-context conversational work (Sulis); agents producing complex multi-file artifacts (engineering-architect when synthesising TDDs)
- **omit** — inherits the parent agent's model; surprises possible

### `tools` (optional; default `*`)

Per principle of least privilege, declare only what the agent needs:

- Coordinator agents (Sulis, orchestrator) — typically `*` or `[Read, Write, Edit, Bash, Agent, TaskCreate, TaskUpdate]`
- Specialist agents — narrow lists (e.g., requirements-analyst: `[Read, Write, AskUserQuestion]`)
- Mechanical agents — even narrower (a classifier: `[Read]`)

Tools available include: `Read`, `Write`, `Edit`, `Bash`, `Agent`, `AskUserQuestion`, `TaskCreate`, `TaskUpdate`, `TaskList`, `WebFetch`, `WebSearch`, plus MCP tools and plugin-specific tools. See Claude Code docs for the full list.

### `standards` (required v0.1.0+)

Per STANDARDS_RUBRIC phase classification. Defaults by audience:

- Operator-facing or agent-internal:
  ```yaml
  standards:
    input: [REFERENTIAL_INTEGRITY_STANDARD]
    processing: [CRITICAL_THINKING_STANDARD]
    output: [CRITICAL_THINKING_STANDARD]
  ```

- Founder-facing or both:
  ```yaml
  standards:
    input: [REFERENTIAL_INTEGRITY_STANDARD]
    processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
    output: [CRITICAL_THINKING_STANDARD, TONE_STANDARD, COACHING_STANDARD]
  ```

Adjust based on the agent's role — coordinator agents often need DECOMPOSITION_PROCEDURE; analysis agents always need it.

### `verification_spiral` (required v0.1.0+)

The tier the agent is verified at:

- **LIGHT** — pure-classifier agents only; justification required
- **STANDARD** — most specialist agents (requirements-analyst, engineering-architect, security-reviewer)
- **HEAVY** — coordinator + founder-facing agents (Sulis); any agent where misleading the founder carries high trust cost

Heavy tier adds Outcome-Specific Rigor (Dispatch Trigger Precision + Tool Completeness + Output-Shape Verification) and Independence Check.

### `related_skills` (required if agent dispatches anything)

Forward-only declarations of what the agent depends on / optionally uses / relates to. Same vocabulary as `add-skill`'s `related_skills:` (four relationship types: depends_on / optional_input / related_to / supersedes).

Include both skills AND other agents in this block — the relationship semantics are the same.

### `register` (required if Audience is founder-facing or both)

```yaml
register:
  founder_mode: default
  technical_mode:
    shape: <one of: json_envelope | markdown_with_paths | diff | raw_tool_output | structured_summary>
    triggers: [intent, --raw, /sulis:jargon]
```

If technical_mode is declared, Gate 4 Register Switch Correctness perspective verifies the switch mechanics work. If only one register, declare just that one:

```yaml
register:
  technical_mode: default  # operator-only agents
```

## Body shape: the standard sections

### `# Agent Name` (required)

H1 with the agent's display name in Title Case. Convention: matches the `name:` field in Title Case form (`requirements-analyst` → `Requirements Analyst`).

### `## Role` (required, lead with this)

Per Pyramid Principle PP-01: lead with the conclusion. The role section answers "what are you?" in one paragraph. Examples:

- *"You are the **Senior Engineer**. You take one Work Package and write the code..."* (executor)
- *"You are the **Tech Lead**. You don't write code. You walk the Work Package INDEX..."* (orchestrator)

The role-noun in bold serves as the dispatched-agent's mental anchor for the duration of the session.

### `## Required reading` (optional)

If the agent must consume standards or references on dispatch, list them in priority order. Each item is a relative or absolute path with a one-sentence reason.

Convention: keep to ≤ 5 items (per PD-02 fan-out). If more are needed, structure into sub-categories or move some to `## References` deeper in the body.

### `## Workflow` / `## Main loop` / `## When dispatched` (required)

The agent's behaviour, step-by-step. Choose ONE heading per agent:

- `## Workflow` — for procedural agents (executor, requirements-analyst)
- `## Main loop` — for loop-shaped agents (orchestrator)
- `## When dispatched` — for event-driven agents (security-reviewer triggered on commit)

Use numbered steps, sub-headings, or a fenced code-block pseudo-code (orchestrator.md uses this pattern). Choose what fits the agent's complexity.

### `## Output shape` / `## Output contract` (required)

What the agent produces. For founder-facing or both agents (declaring dual register), include separate sub-sections for each mode with examples:

```markdown
### Founder-mode output (default)

> "Recon done. Found 3 apps in this monorepo (api, web, worker). Branching: dev/main with merge-queue on dev. CI: 6 workflows wired, all green at HEAD. One gap: deploy-staging fires but no smoke check runs after it. Ready to specify when you are."

### Technical-mode output (--raw / after /sulis:jargon on)

```json
{
  "apps": ["api", "web", "worker"],
  "branching": {"model": "dev/main", "merge_queue": "dev"},
  "ci": {"workflows": [...], "status": "green"},
  "gaps": [{"id": "smoke-missing", "where": "deploy-staging → ?", "severity": "advisory"}]
}
```
```

These examples become the agent's behavioural anchors — Gate 4's Coaching Delivery + Tone Conformance perspectives score against them.

### `## Gotchas` (optional but encouraged)

Top 3-5 things the agent must avoid. Each gotcha must trace to a concrete prior-failure source (per add-skill methodology).

### `## Vocabulary` (optional)

Domain terms the agent introduces. Reserved for terms not already in the founder-tone stack lexicon.

## Examples to study

When authoring a new agent, read the existing agents whose role most closely matches:

| New agent shape | Read first |
|---|---|
| Coordinator / front-door | `plugins/sulis/agents/concierge.md` (1526 LOC — the canonical coordinator) |
| Specialist procedural | `plugins/sulis/agents/executor.md` |
| Specialist loop | `plugins/sulis/agents/orchestrator.md` |
| Specialist facilitator | `plugins/sulis/agents/requirements-analyst.md` |
| Specialist analytical | `plugins/sulis/agents/engineering-architect.md` |
| Specialist auditor | `plugins/sulis-security/agents/security-reviewer.md` |

## Conventions for naming the verification report

```
plugins/<plugin>/agents/<agent>.VERIFICATION_REPORT.md       # first iteration
plugins/<plugin>/agents/iterations/<agent>/{N}/VERIFICATION_REPORT.md  # deepening iterations
```

The first form sits next to the agent for easy discovery. The second form preserves history when the agent gets upsurged. Both pass the single filesystem check.

## What's not in the agent.md

These belong elsewhere, not inside the agent file:

- **Skills the agent dispatches** — live at `plugins/<plugin>/skills/<skill-name>/` (use `add-skill`)
- **Templates the agent uses** — live at `plugins/<plugin>/templates/` (plugin-level)
- **Scripts the agent runs** — live at `plugins/<plugin>/scripts/` (plugin-level)
- **References the agent cites** — live at `plugins/<plugin>/references/` (plugin-level)
- **Standards the agent cites** — live at `plugins/sulis/references/standards/` (sulis-canonical)

The agent body cites these via relative or absolute paths. It does not inline them. Progressive disclosure.
