# Sulis AI

A Claude Code plugin marketplace for building products end-to-end — from idea to deployed, secure software — via the **Outcome-First Methodology**.

## Start Here (Most Founders)

```bash
# 1. Add the marketplace
/plugin marketplace add sulis-ai/agents

# 2. Install the entry-point plugin (the only one you need to start)
/plugin install sulis-concierge@sulis-ai-agents

# 3. Launch the concierge — your VP of Engineering
claude --agent sulis-concierge:concierge
```

**That's it.** The concierge interviews you about your goal, then routes you to the right specialist plugin (and installs it for you when needed). You don't need to know which plugin to use first — that's the concierge's job.

If you skip this step and try `/sulis-execution:run-all` directly, you'll hit "blocked: missing SRD" / "blocked: missing blueprint" errors. That's the **specifications-first** flow working as designed — the executor refuses to ship code without an approved spec + architecture. The concierge walks you through those phases in order.

## The Journey (How the Plugins Fit Together)

The concierge walks you through these phases. Each phase produces an artifact that the next phase reads:

| Phase | What you produce | Plugin |
|---|---|---|
| **0. Discover** | `.context/{project}/INDEX.md` — what exists in this codebase | `sulis-context` |
| **1. Specify** | `.specifications/{project}/SRD.md` — what the system should do | `srd` |
| **2. Design** | `.architecture/{project}/TDD.md` + Work Packages | `sea` |
| **3. Build** | Code + tests, shipped per Work Package | `sulis-execution` |
| **4. Verify** | Architecture audit + test coverage | `sea` |
| **5. Secure** | `.security/{project}/viability-report.md` — 25-primitive review | `sulis-security` |
| **6. Pitch (optional)** | Sequoia-style deck for fundraising | `idc` |

Each plugin is described in detail below. **You don't install them all upfront** — the concierge installs each one when its phase arrives.

## Plugins (Reference)

The concierge knows which to invoke when. You shouldn't normally need to choose manually — but here's the full catalogue:

### Entry point

| Plugin | What it does |
|---|---|
| **[sulis-concierge](plugins/sulis-concierge/)** | The VP-of-Engineering entry point. Owns the 7-phase journey; installs + dispatches specialists as needed. |

### Core build flow

| Plugin | What it does |
|---|---|
| **[sulis-context](plugins/sulis-context/) [DEPRECATED]** | Consolidated into `sulis` at v0.35.0. Discovery now lives at `/sulis:discover-context`; refresh at `/sulis:refresh-context`; show at `/sulis:show-context`. Plugin shell preserved for marketplace compatibility |
| **[srd](plugins/srd/) [DEPRECATED]** | Consolidated into `sulis` at v0.37.0. Requirements facilitation now lives at the requirements-analyst agent + `/sulis:codebase-mapping`, `/sulis:critical-thinking`, `/sulis:requirements-validation`, `/sulis:index-specifications`, `/sulis:requirements-templates`, `/sulis:map-architecture`. Marketplace-wide standards (AAF, FE, repository-contract, pr-hygiene, change-work, convention-preference, engineering-principles, executor-loop, git-workflow, security, cognitive-load, content-quality, coaching-without-conflict) now at plugins/sulis/references/. Plugin shell preserved for compatibility |
| **[sea](plugins/sea/) [DEPRECATED]** | Consolidated into `sulis` at v0.38.0. Architecture skills now live at `/sulis:draft-architecture`, `/sulis:plan-work`, `/sulis:harden-codebase`, `/sulis:analyse-codebase`, `/sulis:verify-architecture`, `/sulis:code-review`, `/sulis:codebase-audit`, `/sulis:suggest-split`. Engineering architect agent + 11 references (boring-code, MECE-3, Red-Green-Blue, change-primitives, code-review-standard, etc.) at plugins/sulis/. Shell preserved for compatibility |
| **[sulis-execution](plugins/sulis-execution/)** | Work Package Executor + Train — ships code from Work Packages: RGB → commit → CI → merge → deploy → review |
| **[sulis-security](plugins/sulis-security/) [DEPRECATED]** | Consolidated into `sulis` at v0.40.0. Security-reviewer agent + viability-framework reference moved to plugins/sulis/. `codebase-assess` skill (already DEPRECATED in favour of `/sulis:code-health`) preserved at `/sulis:codebase-assess` through its deprecation window. Plugin shell preserved for compatibility |

### Specialist studios (the concierge routes you here when needed)

| Plugin | When the concierge sends you here |
|---|---|
| **[sulis-strategy](plugins/sulis-strategy/)** | "I need to nail down the business strategy / pricing / GTM" |
| **[sulis-design](plugins/sulis-design/)** | "I need a design language, visual identity, or brand foundation" |
| **[sulis-product-development](plugins/sulis-product-development/)** | "I'm running an OFM product-development cycle (design → plan → implement → complete)" |
| **[idc](plugins/idc/)** | "I'm preparing an investor pitch deck" |

## "Help! The executor is blocking me on missing files"

This is the most common confusion (thanks Sib for surfacing it). If `/sulis-execution:run-all` or `/sulis-execution:run-wp` tells you a Work Package can't proceed because some `.md` file doesn't exist, here's what's happening and how to recover:

**Why it happens.** The executor only ships work that has a complete spec chain behind it. It needs:

- `.specifications/{project}/SRD.md` — produced by `claude --agent requirements-analyst`
- `.architecture/{project}/TDD.md` + Work Packages — produced by `/sulis:draft-architecture`

If any of those are missing, the executor refuses to fabricate them. That's a feature: building without specs is how you get expensive rewrites.

**How to recover.** Stop the executor. Run the concierge instead:

```bash
claude --agent sulis-concierge:concierge
```

Tell it: "I started in the executor and got blocked on missing files; help me back up to where I should have started." It will walk you through Phases 0–2 (discover → specify → design) to produce the artifacts the executor needs, then hand back to the executor when ready.

If you'd prefer to skip the concierge and run the phases manually, in order:

```bash
/sulis:discover-context <project-slug>
claude --agent requirements-analyst <project-slug>
/sulis:draft-architecture <project-slug>
/sulis-execution:run-all
```

But honestly, the concierge is easier — it remembers state, suggests next steps, and gives you progress checkpoints.

## Quick Start (Manual install of all plugins)

If you'd rather have everything installed up front:

```bash
/plugin marketplace add sulis-ai/agents

# Or in settings.json:
{ "extraKnownMarketplaces": ["sulis-ai/agents"] }

# Install all (the concierge auto-installs as needed, so this is optional)
for p in sulis-concierge sulis-context srd sea sulis-execution \
         sulis-security sulis-strategy sulis-design sulis-product-development idc; do
  /plugin install $p@sulis-ai-agents
done
```

### Install from local clone (development)

```bash
git clone https://github.com/sulis-ai/agents.git
claude --plugin-dir ./agents/plugins/sulis-concierge
```

## Architecture

The studio plugins are thin skill/agent wrappers. Methodology content (outcomes, studios, sequences, standards) lives in a separate repo and is fetched at runtime via GitHub MCP:

```
sulis-ai/agents      <- plugins (this repo; small, fast clone)
sulis-ai/platform    <- methodology content (fetched on demand)
```

Projects pin a methodology version in `ofm-bindings.yaml`:

```yaml
methodology:
  repo: sulis-ai/platform
  ref: v1.0.0
```

## Repo Structure

```
agents/
├── .claude-plugin/
│   └── marketplace.json       # Plugin registry (Claude Code reads from here)
├── docs/                      # Marketplace-level documentation
├── plugins/
│   ├── sulis-concierge/       # Entry point (START HERE)
│   ├── sulis-context/         # Phase 0: discover
│   ├── srd/                   # Phase 1: specify
│   ├── sea/                   # Phase 2: design + Phase 4: verify
│   ├── sulis-execution/       # Phase 3: build
│   ├── sulis-security/        # Phase 5: secure
│   ├── sulis-strategy/        # Specialist studio
│   ├── sulis-design/          # Specialist studio
│   ├── sulis-product-development/  # Specialist studio
│   └── idc/                   # Specialist studio (pitch deck)
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add skills, add plugins, and the release process.

## License

MIT License. See [LICENSE](LICENSE) for full text.
