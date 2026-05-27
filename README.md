# Sulis AI

A Claude Code plugin marketplace for **building products end-to-end** — from idea to deployed, secure software — and **preparing investor pitches** when fundraising.

Two focused plugins, one engineering team and one pitch coach.

## Start Here

```bash
# 1. (Optional) Install the tools sulis uses across its skills
#    (clone first, then run — safer than curl|bash)
git clone https://github.com/sulis-ai/agents.git /tmp/sulis-agents
bash /tmp/sulis-agents/plugins/sulis/scripts/install-sulis.sh --check
bash /tmp/sulis-agents/plugins/sulis/scripts/install-sulis.sh
#   Flags:
#     --check               audit what's installed; no changes
#     --core-only           just git, gh, python3, pipx
#     --with-code-health    everything, including the 7-tier scanners
#                           (hadolint, trivy, gitleaks, semgrep, …)

# 2. Add the marketplace
/plugin marketplace add sulis-ai/agents

# 3. Install whichever plugin matches what you're trying to do
/plugin install sulis@sulis-ai-agents             # build your product
/plugin install investor-coach@sulis-ai-agents    # prepare your pitch deck

# 4. Launch
claude --agent sulis              # AI engineering team
claude --agent investor-coach     # Sequoia-style pitch coach
```

**Tool install is optional.** The sulis plugin gracefully degrades — each
code-health tier checks if its tool is on `PATH` and emits `NOT_ASSESSED`
if missing. So you can install the plugin first, then run `install-sulis.sh`
only when you want to enable the tiers it covers.

## The two plugins

### `sulis` — your AI engineering team

Talk through what you want to build, and Sulis takes it end-to-end:

- **Discover** what's already in your codebase
- **Specify** what the system should do (requirements + use cases + NFRs)
- **Design** the architecture (TDD, ADRs, work packages)
- **Build** the code with tests, atomically (Red-Green-Blue, ship per work package)
- **Verify** that the shipped code matches the design
- **Secure** the codebase against business-risk findings
- **Capture lessons** as durable GitHub issues so nothing evaporates
- **Send feedback** to the maintainers (with personal context scrubbed)

The full skill catalogue is at [plugins/sulis/](plugins/sulis/).

### `investor-coach` — Sequoia-style pitch deck coach

Guided, stage-aware (angel through Series B) conversation that produces:

- A grounded narrative on the Sequoia spine
- Tiered, traced market research (sources → proof-points → claims)
- A financial model in Excel + a branded HTML dashboard
- An adversarial investor-objection review
- A branded `.pptx` + reveal.js HTML deck
- A live rehearsal drill against the 5/15/30 arc

The full skill catalogue is at [plugins/investor-coach/](plugins/investor-coach/).

## Install from a local clone (development)

```bash
git clone https://github.com/sulis-ai/agents.git
claude --plugin-dir ./agents/plugins/sulis
claude --plugin-dir ./agents/plugins/investor-coach
```

Or point your Claude Code settings at the clone via `extraKnownMarketplaces`:

```json
{ "extraKnownMarketplaces": ["/path/to/agents"] }
```

## Repo structure

```
agents/
├── .claude-plugin/
│   └── marketplace.json       # Plugin registry (Claude Code reads this)
├── docs/                       # Marketplace-level documentation
└── plugins/
    ├── sulis/                  # AI engineering team
    └── investor-coach/         # Pitch deck coach
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add skills, modify the plugins, and the release process.

## License

MIT License. See [LICENSE](LICENSE) for full text.
