# sulis-builder

Self-service studio creation for the Outcome-First Methodology. Use this
when you need to spin up a new domain-expertise package (a "studio") and
want it to follow the marketplace's conventions out of the gate.

## What's in here

| Surface | Purpose |
|---|---|
| `studio-builder` agent | Walks you through creating a new studio bundle (7-file studio package) following the studio-creation sequence. |
| `outcome-definition` skill | Phase 0 — defines well-formed outcomes using PACER + SMART before any design work begins. |
| `studio-definition` skill | Creates or migrates a studio definition using the studio-creation sequence (outcome-definition → platform integration → tail outcomes). |

## When to use

- Building a new domain expertise package that needs to slot into the
  Outcome-First Methodology
- Migrating an existing ad-hoc package into the standard 7-file shape
- Defining outcomes (PACER + SMART) for any cross-functional initiative

## How to invoke

```
claude --agent sulis-builder
```

The agent walks you through outcome definition first, then the studio
creation sequence.

## Related plugins

- `sulis-strategy` — strategic foundation studios (vision, principles, etc.)
- `sulis-design` — design studios (foundation, identity, system)
- `sulis-product-development` — product delivery studios (design, plan, implement)

All three share the Outcome-First Methodology backbone that
`sulis-builder` scaffolds.
