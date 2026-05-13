# Sulis AI Standards

A Claude Code plugin marketplace for the Outcome-First Methodology, requirements analysis, and facilitation tools.

## Plugins

| Plugin | Description |
|--------|-------------|
| **[srd](plugins/srd/)** | Requirements Analyst — facilitates building Software Requirements Documents through guided conversation |
| **[sulis-strategy](plugins/sulis-strategy/)** | Business strategy studio — vision, strategy, principles, commercial, GTM, roadmap, and domain-specific research |
| **[sulis-product-development](plugins/sulis-product-development/)** | Product development studio — design, plan, implement, complete, feature lifecycle, validation |
| **[sulis-design](plugins/sulis-design/)** | Design studio — design language, tokens, visual identity, customer experience, coherence verification |
| **[sulis-builder](plugins/sulis-builder/)** | Studio builder — create new domain expertise packages (7-file studio bundles) |
| **[sulis-platform-sdk](plugins/sulis-platform-sdk/)** | Platform SDK — build production-ready SaaS backends with auth, billing, multi-tenancy |

## Quick Start

### Install from marketplace

```bash
# Add the marketplace (one-time)
/plugin marketplace add sulis-ai/agents

# Install whichever plugins you need
/plugin install srd@sulis-ai-agents
/plugin install sulis-strategy@sulis-ai-agents
/plugin install sulis-product-development@sulis-ai-agents
/plugin install sulis-design@sulis-ai-agents
/plugin install sulis-builder@sulis-ai-agents
/plugin install sulis-platform-sdk@sulis-ai-agents
```

Or add to your settings.json:

```json
{
  "extraKnownMarketplaces": ["sulis-ai/agents"]
}
```

### Install from local clone

```bash
git clone https://github.com/sulis-ai/agents.git
claude --plugin-dir ./standards/plugins/sulis-strategy
```

## Architecture

The studio plugins are thin skill/agent wrappers. Methodology content (outcomes, studios, sequences, standards) lives in the platform repo and is fetched at runtime via GitHub MCP:

```
sulis-ai/agents          <- plugins (this repo, small, fast clone)
sulis-ai/platform           <- methodology content (fetched on demand)
```

Users pin a methodology version in their project's `ofm-bindings.yaml`:

```yaml
methodology:
  repo: sulis-ai/platform
  ref: v1.0.0
```

## Repo Structure

```
standards/
├── .claude-plugin/
│   └── marketplace.json       # Plugin registry (Claude Code reads from here)
├── docs/                      # Marketplace-level documentation
├── plugins/
│   ├── srd/                   # Requirements Analyst
│   ├── sulis-strategy/ # Business strategy studio
│   ├── sulis-design/    # Design studio
│   ├── sulis-product-development/ # Product delivery studio
│   ├── sulis-builder/  # Studio creation
│   └── sulis-platform-sdk/    # Platform SDK
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add skills, add plugins, and the release process.

## License

MIT License. See [LICENSE](LICENSE) for full text.
