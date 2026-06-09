# Glossary — Comprehensive Spec & Two-Surface Journey Walk

**Change:** CH-CQRWWR (`01KTPWDWJ7CQRWWRGPQEQ22P1M`) · primitive `harden` · slug `comprehensive-spec-and-journey-walk`
**Status:** locked (Phase 3.5 disambiguation sweep complete)

This glossary is the authoritative vocabulary for every artifact in this
specification. Every recurring noun used in `SRD.md`, `NFR.md`,
`MISUSE_CASES.md`, the diagrams, and the scenarios file reconciles against it.

---

## Summary

The "product" being specified here is **the Sulis specify/design process itself** —
a methodology change, not a software feature. Terms below distinguish the two
*actors* of that process (founder, agent), the two *surfaces* a system can be
walked along (UI, tool), the *artifacts* the process produces, and the *gates*
that block a change from advancing.

---

## Preferred Terms

| Term | Definition |
|------|------------|
| **Comprehensive design document** | The single, always-produced design artifact that carries — regardless of intake depth — an executive summary, problem discovery, stakeholders/personas, full requirements (functional, non-functional with measurable targets, constraints, assumptions+risk, dependencies, STRIDE threat model), scope, use cases with main + alternate + exception flows, and solution design with architecture-at-levels. Modelled on the canonical `features/entity-crud/DESIGN.md`. In Sulis this is the restructured `DESIGN.md` (formerly `TDD.md`). |
| **Depth** | The size of the *context-gathering interview* a change runs at specify/design time. One of `lite`, `standard`, `deep`. Post-change, depth sizes ONLY how much context is gathered — never which documents exist. |
| **Intake** | The act of gathering context from the founder at specify/design time. Its size is governed by depth. |
| **Doc-existence** | Whether a given document section (use cases, NFR, threat model, personas) is present in the produced design document. Post-change this is always "present" — decoupled from depth. |
| **Founder** | The (typically non-technical) human running `/sulis:specify` and `/sulis:design`. The primary actor of the methodology. |
| **Agent** | The Sulis AI executing the specify/design stages — gathering context, producing the comprehensive design document, walking the journeys, deriving scenarios, and running the gates. The secondary actor. |
| **Surface** | A consumer-facing seam through which a system is exercised. This change recognises exactly two: the UI surface and the tool surface. |
| **UI surface** | The human-facing consumer path — screens, pages, components a human clicks through. The surface the existing journey walk already covers. |
| **Tool surface** | The machine-facing consumer path — the API / SDK / MCP tool operations an agent or SDK calls end-to-end. The second surface this change adds to the journey walk. |
| **Journey walk** | The outside-in, hop-by-hop pass over a consumer's path through a surface, where each hop is classified `EXISTS` / `planned-WP` / `GAP`, and the walk is a hard gate before the design completes. |
| **Two-surface journey walk** | A journey walk performed over BOTH the UI surface AND the tool surface for a behavioural change, so the machine consumer's path receives the same outside-in proof the human consumer's path receives. |
| **Hop** | One step in a journey — a single consumer action and the component that handles it (e.g. "click sign-in → redirect" on UI; "agent calls `create_entity` → handler → persistence" on tool). |
| **EXISTS** | A hop classification meaning the handling component is present in the codebase, cited by file + function. For a tool-surface hop, EXISTS additionally requires the tool/handler AND its ServiceSpec binding to both be cited (the "looks-built-but-isn't-wired" bar). |
| **planned-WP** | A hop classification meaning no handling component exists yet, but a Work Package is planned to build it. |
| **GAP** | A hop classification meaning the hop is neither built nor planned. A bare GAP blocks design completion. |
| **ServiceSpec binding** | The declaration that wires an exposed tool/operation to its concrete handler. A tool that serves an interface but has no ServiceSpec binding is the canonical "looks-built-but-isn't-wired" failure. |
| **Use case** | A specification of an actor achieving a goal through the system, carrying Actor, Trigger, Preconditions, Main Flow, Alternate Flows, and Exception Flows. Numbered UC-NN. |
| **Flow** | A numbered sequence of steps within a use case. One of: main flow (the happy path), alternate flow (a valid variation, numbered e.g. 3a), or exception flow (an error path, numbered e.g. 6a). |
| **Verifiable scenario** | A drivable, observable check derived from a use-case flow. It names a journey, a surface, the operation it drives, and the observable pass condition. Observed-or-blocked when driven. |
| **UC-flow-coverage gate** | The gate that blocks a change from shipping if any main/alternate/exception flow of any in-scope use case has no covering scenario. Companion to the scenario-required gate (#103) and the journey-coverage gate (#86). |
| **Scenario-required gate** | The existing gate (#103) requiring a behavioural change to define at least one verifiable scenario. |
| **Journey-coverage gate** | The existing gate (#86) requiring every hop of every in-scope journey scenario to be EXISTS or planned-WP. |
| **STRIDE threat model** | The always-produced security section of the comprehensive design document — Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege — with trust boundaries and attack surface, modelled on entity-crud §4.6. |
| **Architecture-at-levels** | The C4-style hierarchy of architecture diagrams: context (system in its environment), container (deployable units), component (internals of a unit). Sulis currently has 5 flat Mermaid types and no levels. |
| **ADR** | Architecture Decision Record — a record of a *technical* decision, its context, and consequences. Sulis already produces these. |
| **BDR** | Business Decision Record — a record of a *business/product* decision (scope cut, pricing, sequencing), its context, and consequences. The canonical has ADR + BDR; Sulis has ADR only. |
| **Verification substrate** | The #98 mechanism that drives scenarios — scripted `http_call` / `subprocess` drivers plus agent-step tiers — already capable of driving tool calls end-to-end. |
| **Bypass** | A way a change can advance while skipping the discipline this change enforces — e.g. skipping use cases, walking only one surface, or writing happy-path-only scenarios. The misuse cases enumerate the bypasses the change must close. |

---

## Also Known As (synonym resolutions)

| Preferred Term | Also Known As (deprecated / avoid) |
|----------------|-----------------------------------|
| Comprehensive design document | "the full doc", "DESIGN.md", "TDD.md", "the deep doc" |
| Depth | "mode", "tier" (when referring to specify/design size) |
| Tool surface | "API surface", "SDK surface", "MCP surface", "machine surface" |
| UI surface | "screen journey", "human surface", "front-end journey" |
| EXISTS | "built", "wired", "present" |
| planned-WP | "planned", "WP-to-be" |
| Verifiable scenario | "scenario", "drivable check", "acceptance scenario" |

When a single artifact must reference one of the deprecated forms for precision
(e.g. the literal filename `DESIGN.md`), it does so as a code-span, not as prose.

---

## NOT the Same As (disambiguation)

| Term A | Term B | Distinction |
|--------|--------|-------------|
| **Depth** | **Doc-existence** | Depth sizes the interview. Doc-existence is whether a doc section is present. The whole point of this change is to DECOUPLE them: post-change, depth varies, doc-existence does not. |
| **UI surface** | **Tool surface** | Same system, two consumers. UI = human clicks; tool = agent/SDK calls. A behavioural change must walk BOTH. |
| **Journey walk** | **Verifiable scenario** | The walk is the *design-time classification* (EXISTS/planned/GAP) over a surface. A scenario is the *drivable artifact* derived from a flow. The walk proves the path is built-or-planned; the scenario proves it actually works when driven. |
| **ADR** | **BDR** | ADR records a technical decision; BDR records a business/product decision. Both are decision records; they differ in subject. |
| **UC-flow-coverage gate** | **Scenario-required gate** | Scenario-required (#103) demands ≥1 scenario exists. UC-flow-coverage demands EVERY flow (main/alternate/exception) of every in-scope use case has a covering scenario. The former is a floor; the latter is completeness. |
| **UC-flow-coverage gate** | **Journey-coverage gate** | Journey-coverage (#86) checks every *hop of a scenario's journey* is built-or-planned. UC-flow-coverage checks every *use-case flow* has a scenario at all. One checks hops within scenarios; the other checks scenarios exist per flow. |
| **EXISTS (UI hop)** | **EXISTS (tool hop)** | For a UI hop, EXISTS = component cited by file+function. For a tool hop, EXISTS additionally requires the ServiceSpec binding cited — a serving interface without a binding is a GAP, not EXISTS. |
