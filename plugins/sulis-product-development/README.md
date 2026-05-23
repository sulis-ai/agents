# sulis-product-development

Product development studio for the Outcome-First Methodology. Covers the
full delivery lifecycle from design through implementation to completion,
following Working Backwards / RGB principles.

## What's in here

| Phase | Skill | Purpose |
|---|---|---|
| Design | `design` | Solution-design outcome (Working Backwards methodology). |
| Design | `design-validator` | Validates design artifacts against quality bar. |
| Plan | `plan` | Creates implementation plans + machine-readable task specs. |
| Plan | `task-decomposition` | Decomposes feature designs into atomic tasks. |
| Plan | `implementation-context` | Implementation context assessment via OFM. |
| Implement | `implement` | Executes autonomous implementation following TASKS.yaml (RGB cycle). |
| Implement | `backend-development` | Backend patterns (handlers / ports / adapters / actions / routers). |
| Implement | `frontend-development` | Frontend patterns (design system + components + a11y). |
| Implement | `test-scenarios` | Translates design specs to dual-mode adapter test scenarios. |
| Implement | `sub-agents` | Sub-agent orchestration. |
| Complete | `complete` | Production-quality outcome + release logistics. |
| Complete | `production-guardian` | Production-readiness check. |
| Complete | `completion-validator` | Validates the feature is genuinely complete. |
| Complete | `completeness-spiral` | Multi-perspective completeness verification. |
| Cross-cutting | `feature-lifecycle` | End-to-end feature lifecycle orchestrator. |
| Cross-cutting | `journey` | Journey-state orchestration. |
| Cross-cutting | `ivs-authoring` | Information visualisation system authoring. |

| Surface | Purpose |
|---|---|
| `product` agent | Coordinates across the phases above. |

## When to use

- Shipping a feature end-to-end (design → plan → implement → complete)
- Validating completeness at any phase
- Running autonomous implementation following a task plan
- Onboarding into the OFM delivery cadence

## How to invoke

```
claude --agent product
```

The agent dispatches to the right phase based on your context (have you
designed yet? planned? implementing now?).

## Related plugins

- `sulis-design` — upstream design system + brand work
- `sulis-strategy` — upstream strategic foundation
- `sulis-execution` — orchestrates autonomous WP execution (Step 11
  security review + Step 12 bookkeeping)
- `sea` — architecture audit + Hardening Deltas
- `srd` — requirements specification

This studio is the workhorse of the delivery pipeline.
