---
name: design
description: |
  Invokes the solution-design outcome for Working Backwards methodology.
  Generates complete design artifacts that enable autonomous implementation by AI agents.

  TRIGGER KEYWORDS: design feature, design a feature, design system, solution design,
  working backwards, pr/faq, press release, user guide, user documentation, technical design,
  ivs, implementation spec, verification spec, nfr, non-functional requirements,
  feature design, design for, architect, architecture design, how should we build,
  design document, design doc, spec, specification, requirements, market evidence,
  ontology, traceability, service specification, servicespec.

  USE WHEN:
  - Starting a new feature that needs design
  - User says "design a feature for X"
  - User says "let's design" or "help me design"
  - Need to create complete design artifacts
  - Planning a feature before implementation

  METHODOLOGY SOURCE: methodology/delivery/product/outcomes/solution-design/OUTCOME.md

  GENERATES (via outcome):
  - MARKET_EVIDENCE.md, PR_FAQ.md, USER_GUIDE.md, UX_PROTOTYPE
  - TEST_SCENARIOS.md, DESIGN.md, ENTITY_MODEL_DELTA.md
  - IVS.md, NFR.md
  - ONTOLOGY.jsonld, TRACEABILITY.jsonld
  - SERVICE_SPECIFICATION.md, SOLUTION_SUMMARY.md
  - LIFECYCLE_STATE.json

allowed-tools: Read, Write, Edit, Glob, Grep, AskUserQuestion, Task, WebSearch, WebFetch, mcp__github__get_file_contents
---

# Design Skill

> **This skill invokes the solution-design OFM outcome.**
>
> **Methodology:** Fetch via GitHub MCP: `delivery/product/outcomes/solution-design/OUTCOME.md`
> **Triad:** Customer Advocate, Technical Architect, Operations Forecaster
>
> Fetch the outcome definition before executing:
> ```
> mcp__github__get_file_contents(owner, repo, path="methodology/delivery/product/outcomes/solution-design/OUTCOME.md", ref)
> ```
> Use `ofm-bindings.yaml` for repo config. See `skills/shared/bindings.md` for resolution pattern.
> **Process:** 4 phases, 17 activities with Working Backwards methodology

---

## When Triggered

1. Parse feature description from user input
2. Execute outcome: `solution-design`
3. Format outcome artifacts for display

---

## Invocation

```
Execute outcome: solution-design
Input: {feature description}
```

The outcome contains the complete methodology:
- **Phase 1:** Setup + Market Validation (Customer Advocate leads)
- **Phase 2:** User Value Definition (Customer Advocate leads)
- **Phase 3:** Technical Design (Technical Architect leads)
- **Phase 4:** Completion + Approval (Technical Architect leads)

---

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| feature_description | Description of the feature to design | Yes |
| --skip-product-lifecycle | Skip product lifecycle advisory check | No |
| --journey {name} | Link to journey for context | No |

---

## Output Location

All artifacts created in `features/{feature-name}/`:

```
features/{feature-name}/
├── LIFECYCLE_STATE.json
├── MARKET_EVIDENCE.md
├── PR_FAQ.md
├── USER_GUIDE.md
├── UX_PROTOTYPE.md (if UI)
├── TEST_SCENARIOS.md
├── DESIGN.md
├── ENTITY_MODEL_DELTA.md (if entities)
├── IVS.md
├── NFR.md
├── ONTOLOGY.jsonld
├── TRACEABILITY.jsonld
├── SERVICE_SPECIFICATION.md (if service)
├── SOLUTION_SUMMARY.md
└── reviews/
    └── design-validator-{YYYY-MM-DDTHHMMSSZ}.md
```

---

## Process Summary

| Phase | Lead | Key Activities |
|-------|------|----------------|
| 1: Setup + Market Validation | Customer Advocate | Classification, Market Validation |
| 2: User Value Definition | Customer Advocate | PR_FAQ, USER_GUIDE, UX_PROTOTYPE, TEST_SCENARIOS |
| 3: Technical Design | Technical Architect | DESIGN, IVS, NFR, Platform Compliance |
| 4: Completion + Approval | Technical Architect | ONTOLOGY, TRACEABILITY, SOLUTION_SUMMARY, GATE 1 |

---

## Related

| Skill/Command | Relationship |
|---------------|--------------|
| `/sulis plan` | Follows design - creates implementation plan |
| `/sulis implement` | Follows plan - executes TDD |
| design-validator | Pre-GATE 1 validation |
| research | Market evidence gathering |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-xx | Original full methodology (1,036 lines) |
| 2.0.0 | 2026-02-01 | Refactored to thin adapter per DC-09 |
