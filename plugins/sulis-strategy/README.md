# sulis-strategy

Business strategy studio for the Outcome-First Methodology. Provides the
strategic foundation work that all downstream studios (design, product,
execution) build on.

## What's in here

| Skill | Purpose |
|---|---|
| `vision` | Long-term vision (3-10 year horizon). |
| `strategy` | Strategic positioning + competitive choice. |
| `principles` | Principles that guide decision-making. |
| `commercial` | Commercial model / pricing / revenue strategy. |
| `gtm-planning` | Go-to-market planning. |
| `roadmap` | Sequenced roadmap. |
| `identity` | Brand identity (WHY / HOW / WHAT). |
| `anti-goals` | Things we explicitly will NOT do. |
| `bmc` | Business Model Canvas. |
| `brand-research` | Brand-position research. |
| `company-research` | Company research (yours or a competitor's). |
| `competitive-research` | Competitive landscape research. |
| `win-loss-analysis` | Win/loss analysis. |

| Surface | Purpose |
|---|---|
| `strategy` agent | Coordinates strategic foundation work across the skills above. |

## When to use

- Establishing or evolving strategic foundation
- Brand positioning + identity work
- GTM planning, commercial model design, roadmap sequencing
- Pre-design / pre-product-development discovery

## How to invoke

```
claude --agent strategy
```

The agent dispatches to the right skill based on which strategic
artifact you're producing.

## Related plugins

- `sulis-design` — downstream design work that translates strategy into
  design system
- `sulis-product-development` — downstream delivery
- `sulis-business-strategy` — Kind-schema variant for newer
  outcome-driven business context work
- `idc` — investor deck coach (uses strategy outputs to assemble pitches)

Strategy sits at the top of the OFM stack; everything else cascades from it.
