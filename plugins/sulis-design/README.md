# sulis-design

Design studio for the Outcome-First Methodology. Translates brand into a
production-ready design system through a sequenced set of skills that
each address a specific design discipline.

## What's in here

| Surface | Purpose |
|---|---|
| `design` agent | Coordinates the design workflow across the seven skills below. |
| `design-foundation` | Foundational design principles + design tokens. |
| `visual-identity` | Visual identity work (logos, colour, typography, spacing). |
| `identity-articulation` | Articulating who the brand is + voice / tone. |
| `customer-experience` | CX-focused design (journey mapping, touchpoint design). |
| `design-coherence` | Ensuring design choices cohere across surfaces. |
| `design-compliance` | Compliance against the design system / brand standards. |
| `implementation-system` | Translating design system into implementation patterns. |

## When to use

- Building or evolving a design system
- Bridging brand identity into design tokens + components
- Validating design choices against the system

## How to invoke

```
claude --agent design
```

The agent dispatches to the right skill based on the phase you're in.

## Related plugins

- `sulis-strategy` — upstream strategic foundation (vision / brand)
- `sulis-product-development` — downstream delivery (design → plan → implement)
- `sulis-builder` — meta-pattern for creating new studios

The design system sits between strategy (what to build) and product
development (how to ship it).
