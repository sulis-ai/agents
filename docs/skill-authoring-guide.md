# Skill Authoring Guide

Best practices for writing effective Claude Code skills.

## Skill Categories

Before writing a skill, identify which category it falls into:

| Category | What it does | Examples |
|---|---|---|
| **Library & API Reference** | Explains how to correctly use a library, CLI, or SDK — edge cases, footguns, reference snippets | `billing-lib`, `internal-cli` |
| **Product Verification** | Describes how to test or verify code is working | `signup-flow-driver`, `checkout-verifier` |
| **Data Fetching & Analysis** | Connects to data/monitoring stacks with credentials, dashboard IDs, and common query patterns | `funnel-query`, `grafana` |
| **Business Process & Team Automation** | Automates repetitive workflows into one command | `standup-post`, `create-ticket` |
| **Code Scaffolding & Templates** | Generates framework boilerplate for a specific function in the codebase | `new-migration`, `create-app` |
| **Code Quality & Review** | Enforces code quality, reviews code — can include deterministic scripts | `adversarial-review`, `critical-thinking` |
| **Runbooks** | Takes a symptom and walks through investigation to produce a report | `service-debugging`, `oncall-runner` |

## Writing the Skill

### A skill is a folder, not just a markdown file

`SKILL.md` is the entrypoint, but the skill directory can contain scripts, assets, reference docs, templates, and data. Think of the entire file system as context engineering.

```
plugins/sulis/skills/your-skill/
├── SKILL.md              # Entrypoint — the prompt
├── references/           # API docs, standards, usage examples
│   └── standard.md
├── scripts/              # Helper scripts Claude can execute
│   └── fetch-data.sh
└── examples/             # Example outputs for Claude to learn from
    └── good-output.md
```

### Wrap existing standards and documents

If you already have a standard, style guide, or runbook, place the original in `references/` and write a `SKILL.md` that tells Claude how to *apply* it. The reference provides the knowledge; the skill provides the workflow.

### Don't state the obvious

Focus on information that pushes Claude out of its normal way of thinking — your specific conventions, non-obvious domain knowledge, internal quirks.

### Build a gotchas section

The highest-signal content in any skill is the **Gotchas** section. Build it from actual failure points. Update it over time.

```markdown
## Gotchas

- The `billing_id` field is NOT the same as `user_id` — always join through `accounts` table
- Never call `api.sync()` inside a transaction — it deadlocks in production
```

### Use progressive disclosure

Don't dump everything into `SKILL.md`. Point Claude to supplementary files and it will read them when relevant.

```markdown
For detailed API signatures and usage examples, see `references/api.md`.
```

### Avoid railroading Claude

Be specific about *what* matters (constraints, gotchas, required outputs) but loose about *how* Claude gets there.

### Design for multiple depths

A single skill can serve different levels of effort if you define explicit modes:

```markdown
## Adapting Depth

- **Quick** (e.g. "sanity check this"): Focus on X and Y. 1-2 pages.
- **Full** (e.g. "analyse whether we should..."): Apply all phases. Multiple searches.
- **Audit** (e.g. "what are we assuming?"): Focus on Z. Surface and classify every item.
```

### Write the description for the model

The `description` field in `SKILL.md` frontmatter is what Claude scans to decide whether to trigger a skill. Write it as a trigger condition, not a summary.

**Weak:** `"Generates landing pages"`
**Strong:** `"Use when the user wants to create, optimise, or A/B test a landing page"`

## Quality Checklist

Before submitting a skill PR, verify:

- [ ] Fits cleanly into one skill category
- [ ] `SKILL.md` focuses on non-obvious information (not things Claude already knows)
- [ ] Has a **Gotchas** section (even if short initially)
- [ ] Description field is written as a trigger condition
- [ ] Uses progressive disclosure — supplementary files for detailed references
- [ ] Doesn't railroad Claude into rigid step-by-step instructions
- [ ] Tool requirements are declared if the skill depends on web access, MCP servers, or specific CLIs
- [ ] If wrapping an existing standard/document, the original is in `references/` and `SKILL.md` focuses on workflow
- [ ] Tested locally against a real use case
