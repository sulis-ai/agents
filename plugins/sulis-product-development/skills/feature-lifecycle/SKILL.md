# Feature Lifecycle Skill

> **Purpose:** Orchestrate complete feature development from initial request through
> deployment, documentation, and sign-off with strict contract-based phase transitions.
>
> **Invocation:** `/feature-lifecycle` or automatically when feature work is detected
>
> **Framework:** Implements **The Outcome-First Methodology (OFM)**
> See: `methodology standards/GENERATIVE_FEATURE_FRAMEWORK.md`

---

## Underlying Framework: OFM

This skill operationalizes **The Outcome-First Methodology (OFM)**:

> **"Business-critical features are generated from ideas."**

**Core Principle:** Features are not built—they are **generated**. You provide an idea.
The framework transforms that idea into complete specifications (the Generative Seed).
From those specifications, the entire feature is generated automatically by AI agents.

**Three-Layer Architecture:**
- **Layer 0 (Foundation):** ARCHITECTURE.md, PLATFORM_ENTITY_MODEL.md, PLATFORM_CONVENTIONS.md
- **Layer 1 (Generative Seed):** Core IP (User Truth) + Contract (System Truth) - created in DESIGN phase
- **Layer 2 (Generation Plan):** PLAN.md, TASKS.md - derived from approved specifications

**Key Principle:** The specification IS the feature in declarative form—a generative seed
from which the complete feature grows. Core IP and Contract are two perspectives of
the same feature, created together, reviewed together, generated together.

---

## Core Principle

> **Every feature follows the same lifecycle. No shortcuts. NO DEFERRALS.**
>
> **Start with the end.** Write the press release, user guide, and test plan BEFORE
> designing the solution. If you can't write a compelling announcement or clear
> user instructions, you don't understand what you're building.
>
> **Everything planned MUST be completed.** There is no MVP vs future scope.
> There are no deferrals. All IVS requirements must be met before deployment.
>
> **ServiceSpec is the source of truth.** All features either:
> - Define a new service (with its own ServiceSpec)
> - Extend the ServiceSpec specification itself (adding capabilities to all services)
> - Enhance an existing service (adding operations to an existing ServiceSpec)

---

## TRIGGER KEYWORDS (SEO-OPTIMIZED)

This skill should be invoked for ANY feature work. Use extensive keyword matching:

### Primary Action Verbs (Creation/Addition)
add, create, build, make, develop, implement, introduce, establish, set up,
write, construct, generate, produce, spawn, instantiate, bootstrap, scaffold,
new, adding, creating, building, making, developing, implementing

### Primary Action Verbs (Modification)
change, modify, update, alter, adjust, tweak, revise, edit, amend, transform,
evolve, adapt, customize, configure, reconfigure, changing, modifying, updating

### Primary Action Verbs (Improvement)
improve, enhance, optimize, upgrade, boost, refine, polish, streamline,
strengthen, harden, extend, expand, scale, grow, enrich, augment, elevate,
improving, enhancing, optimizing, upgrading, better, make better

### Primary Action Verbs (Fixing/Repair)
fix, repair, resolve, patch, correct, debug, troubleshoot, diagnose, remedy,
address, handle, solve, mend, restore, recover, heal, fixing, repairing

### Primary Action Verbs (Refactoring/Restructuring)
refactor, restructure, reorganize, redesign, rearchitect, rewrite, rework,
rebuild, redo, overhaul, modernize, migrate, move, transfer, convert,
transition, consolidate, simplify, clean up, tidy up, refactoring

### Primary Action Verbs (Removal/Deprecation)
remove, delete, deprecate, eliminate, drop, disable, decommission, retire,
sunset, phase out, clean out, purge, strip, exclude, removing, deleting

### Primary Action Verbs (Integration/Connection)
integrate, connect, link, combine, merge, unify, join, attach, couple,
bridge, wire, hook up, plug in, sync, synchronize, integrating, connecting

### Primary Action Verbs (Replacement)
replace, swap, substitute, switch, exchange, trade, supersede, supplant,
override, replacing, swapping

### Feature/Capability Nouns
feature, capability, functionality, function, behavior, ability, capacity,
power, option, setting, preference, mode, mechanism, system, subsystem,
component, module, service, microservice, layer, tier, piece, part, element

### Problem/Issue Nouns
bug, issue, problem, defect, error, fault, glitch, flaw, weakness,
vulnerability, security hole, exploit, regression, failure, crash,
exception, incident, outage, bottleneck, blocker, impediment, obstacle,
challenge, concern, risk, threat, gap, limitation, constraint, debt,
technical debt, tech debt, smell, code smell, anti-pattern

### Requirements/Planning Nouns
requirement, specification, spec, need, request, demand, expectation,
criteria, criterion, acceptance criteria, user story, epic, ticket, task,
backlog item, work item, deliverable, milestone, goal, objective, target,
outcome, result, KPI, metric, SLA, contract, agreement

### Design/Architecture Nouns
design, solution, approach, strategy, plan, blueprint, roadmap, vision,
architecture, structure, pattern, framework, template, model, schema,
diagram, flowchart, sequence, entity, relationship, interface, contract,
API, endpoint, route, path, URL, URI, method, operation, action, command,
query, mutation, event, message, signal, hook, callback, handler, listener

### Domain-Specific Nouns (Sulis Platform)
handler, port, adapter, repository, provider, factory, service layer,
domain model, entity model, value object, aggregate, bounded context,
CRUD, HTTP, REST, GraphQL, gRPC, webhook, websocket, SSE, polling,
authentication, authorization, auth, authz, authn, permission, role,
policy, ACL, RBAC, ABAC, token, JWT, API key, OAuth, OIDC, session,
validation, sanitization, serialization, deserialization, mapping,
transformation, conversion, parsing, formatting, encoding, decoding

### Infrastructure/DevOps Nouns
deployment, infrastructure, terraform, IaC, CI/CD, pipeline, workflow,
container, docker, kubernetes, k8s, cloud, GCP, AWS, Azure, serverless,
function, lambda, cloud run, cloud function, VM, instance, cluster,
database, storage, persistence, cache, caching, redis, memcached,
queue, messaging, pub/sub, kafka, rabbitmq, SQS, event bus, stream,
logging, monitoring, observability, tracing, metrics, alerts, dashboard

### Quality/Testing Nouns
test, testing, unit test, integration test, e2e test, end-to-end,
acceptance test, regression test, smoke test, load test, stress test,
performance test, security test, penetration test, coverage, quality,
QA, validation, verification, assertion, expectation, mock, stub, fake,
fixture, snapshot, golden file, baseline

### Problem Indicator Adjectives
broken, not working, failing, crashed, down, unavailable, unreachable,
slow, laggy, timeout, unresponsive, hanging, stuck, frozen, blocked,
incorrect, wrong, unexpected, weird, strange, odd, abnormal, erratic,
inconsistent, flaky, intermittent, sporadic, random, unpredictable,
missing, absent, lacking, incomplete, partial, empty, null, undefined,
deprecated, outdated, obsolete, legacy, old, stale, expired, invalid,
insecure, vulnerable, exposed, leaking, leaky, unsafe, risky, dangerous

### Intent Phrases (Questions)
how do we, how should we, how can we, how to, how would we, how might we,
what if we, what about, what's the best way to, what's the right way to,
what approach, what strategy, what solution, what design, what pattern,
can we, could we, should we, would we, shall we, might we, may we,
is it possible to, is there a way to, any way to, able to, capable of,
why is, why does, why doesn't, why won't, why can't, why isn't,
when should, when do, when does, where should, where do, where is,
which approach, which method, which pattern, which library, which tool

### Intent Phrases (Statements)
I want to, I need to, I'd like to, I have to, I must, I should,
we want to, we need to, we'd like to, we have to, we must, we should,
let's, let me, let us, help me, help us, assist with, support for,
planning to, thinking about, considering, looking into, exploring,
working on, looking at, investigating, researching, evaluating,
trying to, attempting to, aiming to, seeking to, hoping to,
figure out, determine, decide, choose, select, pick, evaluate, assess,
need help with, assistance with, guidance on, advice on, input on,
struggling with, having trouble with, stuck on, blocked by, confused about

### Working Backwards Indicators
release notes, press release, announcement, user guide, documentation,
success metrics, KPI, measure success, how will we know, what does success look like,
customer value, user value, outcome, result, benefit, impact,
working backwards, amazon method, pr/faq, faq, frequently asked questions,
test plan, test scenarios, acceptance criteria, validation plan,
traceability, trace, link to, derived from, coverage

---

## Lifecycle Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FEATURE LIFECYCLE                                  │
│                        (4 Phases, 4 Approval Gates)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐                                                         │
│  │ CLASSIFICATION │  Auto-check (no user gate)                              │
│  └───────┬────────┘                                                         │
│          ↓                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  DESIGN (Working Backwards)                                             │ │
│  │  Creates ALL design artifacts:                                          │ │
│  │  PR_FAQ, USER_GUIDE, TEST_SCENARIOS, DESIGN, IVS, ONTOLOGY,            │ │
│  │  TRACEABILITY, SOLUTION_SUMMARY                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│          ↓                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  DESIGN VALIDATOR (Independent Agent)                                   │ │
│  │  Validates design against:                                              │ │
│  │  - features/PLATFORM_CONVENTIONS.md                                    │ │
│  │  - architecture/PLATFORM_ENTITY_MODEL.md                               │ │
│  │  - architecture/ARCHITECTURE.md                                        │ │
│  │  Decision: PASSED or BLOCKED                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│          ↓                                                                   │
│  ★ GATE 1: Design Approval ★                                                │
│  User reviews complete design package together                              │
│          ↓                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  IMPLEMENTATION                                                         │ │
│  │  Creates PLAN, TASKS, CHANGELOG + TDD implementation                    │ │
│  │  ALL IVS requirements must be implemented (NO DEFERRALS)                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│          ↓                                                                   │
│  ★ GATE 2: Implementation Complete ★                                        │
│  User confirms implementation is complete                                   │
│          ↓                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  RELEASE                                                                │ │
│  │  Production Guardian (STRICT MODE) + Deployment                         │ │
│  │  Decision: APPROVED or BLOCKED only (no CONDITIONAL, no deferrals)      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│          ↓                                                                   │
│  ★ GATE 3: Release Approval ★                                               │
│  User approves Production Guardian report + deployment                      │
│          ↓                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  COMPLETION                                                             │ │
│  │  Documentation updates, features/index.md update                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│          ↓                                                                   │
│  ★ GATE 4: User Sign-off ★                                                  │
│  Final acceptance of complete feature                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**KEY DESIGN: Approval Gate at Each Phase Transition**

- **Design Validator (Pre-GATE 1):** Automated validation against PLATFORM_CONVENTIONS.md, PLATFORM_ENTITY_MODEL.md, and ARCHITECTURE.md - must PASS before proceeding to user approval
- **GATE 1 (Design):** User reviews ALL design artifacts together (PR_FAQ, USER_GUIDE, DESIGN, IVS, ONTOLOGY, etc.) in one review - not split across multiple gates
- **GATE 2 (Implementation):** User confirms all planned work is complete, TASKS.md is 100% done
- **GATE 3 (Release):** User approves Production Guardian report and deployment
- **GATE 4 (Completion):** Final sign-off on the complete feature

---

## Phase Contracts

Each phase operates like an MCP tool with strict input/output schemas:

| Phase | Input Contract | Output Contract | Gate |
|-------|----------------|-----------------|------|
| **CLASSIFICATION** | `feature-request.json` | `classification-result.json` | Auto check |
| **DESIGN** | `classification-result.json` | `design-package.json` | **GATE 1: User Approval** |
| **IMPLEMENTATION** | `design-package.json` | `implementation-package.json` | **GATE 2: User Approval** |
| **RELEASE** | `implementation-package.json` | `release-package.json` | **GATE 3: User Approval** |
| **COMPLETION** | `release-package.json` | `completion-report.json` | **GATE 4: User Sign-off** |

Schema files: `./schema/contracts/`
Gate schemas: `./schema/gates/`

---

## Phase 0: CLASSIFICATION

### Purpose

Determine the feature's relationship to ServiceSpec BEFORE any design work begins.

### Classification Matrix

| Classification | Definition | Examples | ServiceSpec Relationship |
|----------------|------------|----------|--------------------------|
| **Service** | Has entities, operations, events, lifecycle | Notifications, Webhooks, Storage | Creates NEW ServiceSpec |
| **ServiceSpec Extension** | Adds capabilities to ALL services | Rate Limiting, Caching, Resilience | Extends SERVICE_SPECIFICATION.md |
| **Service Enhancement** | Adds operations to EXISTING service | New Platform API endpoint | Updates EXISTING ServiceSpec |
| **Infrastructure** | Pure infrastructure, no ServiceSpec impact | CI/CD, Deployment | No ServiceSpec changes |

### Classification Questions Checklist

1. **Entity Test:**
   - [ ] Does this feature define new entities with lifecycle?
   - [ ] Do these entities have CRUD operations?
   - [ ] Do these entities have state machines?

2. **Cross-Cutting Test:**
   - [ ] Does this capability apply to ALL services equally?
   - [ ] Would every operation potentially have this metadata?
   - [ ] Is this more like "configuration on operations" than "a thing with operations"?

3. **Discovery Test:**
   - [ ] How would an AI agent discover this capability via ServiceSpec?
   - [ ] What ServiceSpec query would return this information?

4. **Domain Test:**
   - [ ] Does this warrant its own bounded context?
   - [ ] Would it have its own handler, repository, events?

### Post-Classification: Parent Spec Version Check

**For `service_enhancement`, `extension_enhancement`, or `capability_enhancement` classifications:**

After classification, IMMEDIATELY verify the parent spec version:

```
1. Read parent spec from canonical location:
   - service_enhancement    → features/services/{parent}/SERVICE_SPECIFICATION.md
   - extension_enhancement  → .extensions/{parent}/EXTENSION_SPECIFICATION.md
   - capability_enhancement → .capabilities/{parent}/CAPABILITY_SPECIFICATION.md

2. Extract current version (e.g., "1.1.0")

3. Record in LIFECYCLE_STATE.json:
   {
     "classification": "service_enhancement",
     "enhances": {
       "type": "service",
       "name": "compute",
       "path": "features/services/compute/",
       "version_at_start": "1.1.0"
     }
   }

4. Create delta file with correct parent version reference
```

**Why This Matters:**
- Parent spec may change during development
- Delta must reference correct version to merge cleanly
- Validator (servicespec-delta-validator) will flag version mismatches

**If Parent Spec Changed During Development:**
```
Parent version at start: 1.1.0
Parent version now:      1.2.0

Action Required:
1. Review changes in parent spec 1.2.0
2. Update delta to reference 1.2.0
3. Verify no conflicts with new parent changes
4. Update LIFECYCLE_STATE.json with new version
```

---

## Phase 1: DESIGN (Working Backwards)

### Purpose

Transform the classified feature request into complete design artifacts using the
Working Backwards methodology. Start with the end outcome.

### Required Reading (MANDATORY)

Before creating any design artifacts:

1. **`features/PLATFORM_CONVENTIONS.md`** - Cross-cutting patterns ALL features must follow
2. **`features/index.md`** - Feature registry (find related features)
3. **`architecture/ARCHITECTURE.md`** - Core architecture principles
4. **`architecture/PLATFORM_ENTITY_MODEL.md`** - Entity relationships

### Pre-Design Analysis (REQUIRED)

#### Entity Model Analysis

| Question | Action if YES |
|----------|---------------|
| Does feature introduce NEW entities? | Plan to add to Entity Hierarchy section |
| Does feature modify entity RELATIONSHIPS? | Plan to update ERD diagrams |
| Does feature affect NAMESPACE patterns? | Plan to update Namespace Patterns section |
| Does feature resolve an existing ISSUE? | Plan to update Issue Registry |

#### Organization Optionality Check

Verify the design supports both B2B (with organizations) AND B2C (without organizations):
- [ ] Design does NOT require organization_id where it should be optional
- [ ] API endpoints support platform-level access
- [ ] Storage namespaces support `plat_{id}` pattern

### Working Backwards Steps

#### Step 1.0: Market Problem Validation (MANDATORY)

> **Critical:** Before writing ANY design artifacts, validate that the problem EXISTS
> in the market. This prevents building solutions for imaginary problems.
>
> **Reference:** See `skills/research/SKILL.md` § Market Validation Research Type

**Purpose:** Gather evidence that real users experience the pain point you're solving.

**Process:**

1. **Invoke Research Skill for Market Validation**

   ```
   Task(
       subagent_type="general-purpose",
       prompt="""
       ## Market Validation Research

       **Research Type:** Market Validation
       **Problem Hypothesis:** {description of the problem we believe exists}
       **Target Users:** {who experiences this problem}

       ## Research Protocol

       1. Search Reddit, Hacker News, Twitter for users expressing this pain
       2. Find GitHub issues on related tools showing this need
       3. Look for quantitative data (developer surveys, industry reports)
       4. Position within Agentic Engineering / Vibe Coding landscape

       ## Output Required

       Produce a MARKET_EVIDENCE.md file with:
       - Problem Validation Status (VALIDATED/WEAK/UNVALIDATED)
       - Community evidence table with exact quotes and links
       - Quantitative evidence (if available)
       - Market context (Agentic Engineering positioning)
       - Harvard-formatted references

       Save to: features/{feature}/MARKET_EVIDENCE.md
       """,
       description="Market Problem Validation"
   )
   ```

2. **Validation Decision**

   | Status | Evidence Required | Action |
   |--------|-------------------|--------|
   | **VALIDATED** | 5+ independent sources showing the problem | Proceed to Step 1.1 |
   | **WEAK** | 2-4 sources, inconsistent pattern | Discuss with user before proceeding |
   | **UNVALIDATED** | <2 sources, no clear pattern | STOP - Problem may not exist |

3. **Output Artifact**

   Create `features/{feature}/MARKET_EVIDENCE.md` containing:
   - Problem statement
   - Community evidence (Reddit, HN, Twitter, GitHub with exact quotes + links)
   - Quantitative evidence (surveys, reports with citations)
   - Market context (Agentic Engineering landscape positioning)
   - Validation status and reasoning
   - Harvard-formatted references

**Why This Step is Mandatory:**

> "The most common cause of startup failure is building something nobody wants."
> — Paul Graham (YC, 2012)

Without market validation:
- We may solve imaginary problems
- The PR_FAQ becomes fiction, not evidence-based
- We waste design and implementation effort
- We miss the real language users use to describe their pain

**Research Integrity (NON-NEGOTIABLE):**

> **NEVER fabricate, invent, or assume market evidence.**
>
> If evidence cannot be found, that IS the finding. UNVALIDATED is a valid status.

- Every quote must be real (copied from actual sources)
- Every link must be valid and verifiable
- Every engagement metric must be accurate
- "No evidence found" is MORE valuable than false evidence
- Document searches attempted even when they yield nothing

**When evidence cannot be found:**
1. Report UNVALIDATED status honestly
2. Document all search queries attempted (Appendix)
3. Present this to the user as a decision point
4. Recommend pivoting or abandoning the feature idea
5. **Do NOT proceed to PR_FAQ with fabricated evidence**

**What to Capture:**

| Evidence Type | Why It Matters | Where to Find |
|---------------|----------------|---------------|
| **Exact quotes** | Real language users use | Reddit, HN, Twitter |
| **Upvote/engagement counts** | Signal strength | All community sources |
| **GitHub issue reactions** | Concrete demand | Related tool repos |
| **Survey percentages** | Quantitative validation | Developer surveys |
| **Market size/trends** | Strategic context | Industry reports |

#### Step 1.1: Create PR/FAQ Document

> **Pre-requisite:** Step 1.0 (Market Problem Validation) must be complete with
> VALIDATED or user-approved WEAK status before proceeding.

Create `features/{feature}/PR_FAQ.md` using template.

**Press Release (< 1 page):**
- **Headline:** One-sentence value proposition
- **Subheading:** Target user + primary benefit
- **Body:** Problem → Solution → Benefits (2-4 paragraphs)

**FAQ Questions to Answer:**
1. "Who is this for?"
2. "What problem does it solve?"
3. "How do I get started?"
4. "What could go wrong?" (risks)
5. "What are the dependencies?"

**Success Metrics:**
Define 2-3 KPIs that prove this worked.

#### Step 1.2: Create User Guide

Create `features/{feature}/USER_GUIDE.md` using template.

**Required Sections:**
1. **Concepts:** What is this? Key terminology
2. **Getting Started:** Step-by-step first use
3. **Common Tasks:** How-to for typical use cases
4. **Reference:** Limits, troubleshooting, edge cases

> **Critical:** Each section drives test scenarios. If you can't describe
> how a user will use this, you don't understand it yet.

#### Step 1.3: Derive Test Scenarios (Outside-In TDD)

Create `features/{feature}/TEST_SCENARIOS.md` using template.

**Derivation Rules:**

| User Guide Section | Test Category | Test IDs |
|-------------------|---------------|----------|
| Getting Started | Happy Path | TS-01 through TS-05 |
| Common Tasks | Happy Path | TS-06 through TS-15 |
| Advanced Usage | Edge Cases | TS-16 through TS-25 |
| Troubleshooting | Error Handling | TS-26 through TS-35 |
| Reference (Limits) | Boundary Conditions | TS-36 through TS-40 |

**Integration Test Categories (Outer Loop - Written FIRST):**

| Category | ID Pattern | Source |
|----------|------------|--------|
| Happy Path | INT-HP-* | USER_GUIDE Getting Started |
| Alternate Path | INT-ALT-* | USER_GUIDE Reference, FAQ |
| Security | INT-SEC-* | PR_FAQ security questions |
| Referential Integrity | INT-RI-* | DESIGN entity relationships |
| Journey | INT-J-* | USER_GUIDE Common Tasks |

#### Step 1.4: Create Technical Design

Create `features/{feature}/DESIGN.md` using template.

**Required Sections:**
- Use cases from User Guide How-To sections
- Architecture diagrams (Mermaid)
- Entity models
- API contracts
- Component breakdown

#### Step 1.4A: Create Entity Model Delta (if adding/modifying entities)

> **When Required:** Any feature that adds new entities, modifies existing entities,
> or changes entity relationships.
>
> **Canonical Reference:** `architecture/PLATFORM_ENTITY_MODEL.md`

If this feature introduces or modifies entities, create `features/{feature}/ENTITY_MODEL_DELTA.md`:

**Required Sections:**

1. **As-Is State** - Current entities from PLATFORM_ENTITY_MODEL.md
2. **To-Be State** - Proposed entities after this feature
3. **Delta Analysis:**
   - New entities (with ID prefixes, parent relationships, tenant scope)
   - Modified entities (field changes, relationship changes)
   - New relationships (cardinality, type)
4. **Compliance Check** - Verify against R1-R6 rules:
   | Rule | Requirement |
   |------|-------------|
   | R1 | Every tenant-scoped entity MUST have `platform_id` |
   | R2 | `organization_id` is ALWAYS optional (nullable) |
   | R3 | Users belong to exactly 1 Platform, 0..N Organizations |
   | R4 | Organizations belong to exactly 1 Platform |
   | R5 | Cross-platform references are FORBIDDEN |
   | R6 | Global entities have no platform_id |
5. **Update Plan** - Sections of PLATFORM_ENTITY_MODEL.md to update

**Template:** `methodology templates/specification/ENTITY_MODEL_DELTA_TEMPLATE.md`

**Approval Gate:** Entity delta MUST be reviewed before implementation.
Non-compliant entities are BLOCKING.

#### Step 1.4B: Complete Platform Compliance Checklist (MANDATORY)

> **Purpose:** Verify compliance with platform conventions BEFORE seeking approval.
> Non-compliance will result in BLOCKED status during design validation.

Complete DESIGN.md Section 12.3 (Platform Compliance Checklist):

**Required Checks:**

| Category | Reference | What to Verify |
|----------|-----------|----------------|
| **ENT-*** | PLATFORM_ENTITY_MODEL.md | ID prefixes registered, R1-R6 rules followed |
| **WL-*** | PLATFORM_CONVENTIONS.md | No hardcoded domains, use `{platform_host}` |
| **ORG-*** | PLATFORM_ENTITY_MODEL.md | Feature works without organizations (B2C) |
| **API-*** | PLATFORM_CONVENTIONS.md | Endpoints follow `/api/v1/{service}/{resource}` |
| **SEC-*** | PLATFORM_CONVENTIONS.md | Uses SecretService pattern |
| **EVT-*** | PLATFORM_CONVENTIONS.md | CloudEvents 1.0 with platform extensions |
| **PERM-*** | PLATFORM_CONVENTIONS.md | Permission format `{domain}.{resource}:{action}` |
| **WIRE-*** | PLATFORM_CONVENTIONS.md | INT-WIRE-* requirements in IVS.md |

**Before Proceeding:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PLATFORM COMPLIANCE GATE                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ❓ Have you read PLATFORM_ENTITY_MODEL.md?                                 │
│     - Check Section 2.2 for existing ID prefixes                            │
│     - Check Section 1.2 for R1-R6 rules                                     │
│                                                                              │
│  ❓ Have you read PLATFORM_CONVENTIONS.md?                                  │
│     - Check § White-Labeling Directive                                       │
│     - Check § 1.3, 1.4 for API patterns                                     │
│     - Check § 9 for CloudEvents format                                      │
│     - Check § 9A for deployment wiring                                       │
│                                                                              │
│  ❓ Does your feature work on B2C platforms (no organizations)?             │
│     - organization_id must be OPTIONAL                                       │
│     - Add TS-B2C-* test scenarios                                            │
│                                                                              │
│  ❓ Did you complete DESIGN.md Section 12.3 with all boxes checked?         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**All compliance categories must show ✅ before proceeding to Step 1.5.**

#### Step 1.5: Create IVS (Implementation & Verification Specification)

> **IMPORTANT:** The IVS must be produced using the 8-phase process defined in
> `methodology/delivery/product/outcomes/solution-design/OUTCOME.md` § Activity 3.5.
> The standalone `ivs-authoring` skill is DEPRECATED.

Create `features/{feature}/IVS.md` using the **8-phase IVS Production Process**:

| Phase | Purpose | IVS Sections |
|-------|---------|-------------|
| 0 | C4 Architecture Model (4 levels) | §0.1-0.5 |
| 0.5 | Dependency Analysis & Abstraction Opportunities | §0.6 |
| 0.6 | Codebase-Wide Health Check | §0.7 |
| 1 | Infrastructure Analysis | §1.1-1.5 |
| 2 | Port-to-Implementation Mapping | §2.1-2.2 |
| 3 | Security Verification (SEC-*) | §4 (Security) |
| 4 | Observability Verification (OBS-*) | §4 (Observability) |
| 5 | Reliability Verification (REL-*) | §5 |
| 6 | Architecture + Ontology Verification (ARC-*, ONT-*) | §6 |
| 7 | Functional Verification (FN-*) | FN section |
| 8 | Production Guardian Checklist | §10-11 |

**ALL verification requirements are BLOCKING. NO DEFERRALS.**

Refer to `solution-design OUTCOME.md § Activity 3.5` for the full phased process
including inputs, actions, and outputs for each phase.

#### Step 1.6: Create ONTOLOGY.jsonld (MANDATORY)

Create `features/{feature}/ONTOLOGY.jsonld` using template.

**Required Sections:**
1. **Entities** - All new entities with display metadata, lifecycle
2. **Operations** - All operations with user guides, leads_to navigation
3. **Errors** - All error codes with user_action remediation
4. **Workflows** - Multi-step processes with error handling
5. **Guides** - FAQ, troubleshooting

**Ontology Derivation Rules:**

| Source Artifact | Ontology Target |
|-----------------|-----------------|
| USER_GUIDE.md → Getting Started | Operations.userGuide.whenToUse |
| USER_GUIDE.md → Common Tasks | Workflows |
| USER_GUIDE.md → Troubleshooting | Guides.troubleshooting |
| USER_GUIDE.md → Field descriptions | Properties.display.description |
| PR_FAQ.md → FAQ | Guides.faq |
| TEST_SCENARIOS.md → Error cases | Errors catalog |
| DESIGN.md → Entity models | Entities |
| DESIGN.md → API contracts | Operations |

#### Step 1.7: Create Traceability (Bidirectional)

Create `features/{feature}/TRACEABILITY.jsonld` using template.

> **Reference:** See `methodology standards/TRACEABILITY_MODEL.md` for complete traceability model.

**Required Bidirectional Links (OFM Traceability Model):**

| Core IP Element | Must Link To | Contract Element |
|-----------------|--------------|------------------|
| USER_GUIDE How-To section | `mapsToOperation` | ServiceSpec Operation (SS-OP-*) |
| USER_GUIDE Reference section | `describesEntity` | ServiceSpec Entity (SS-ENT-*) |
| USER_GUIDE Troubleshooting | `documentsErrors` | ServiceSpec Errors (SS-ERR-*) |
| Requirement (FR-*) | `serviceSpecRef` | ServiceSpec Requirement (SS-§X.Y) |
| Test Scenario (TS-*) | `serviceSpecOperation` | ServiceSpec Operation (SS-OP-*) |

**Required Contract Elements:**

```json
{
  "serviceSpecSections": [
    {"@id": "SS-§X", "implementedBy": ["T-X.*"], "mapsToUserGuide": ["UG-*"]}
  ],
  "serviceSpecOperations": [
    {"@id": "SS-OP-*", "testedBy": ["TS-*"], "mapsToUserGuide": ["UG-*"]}
  ],
  "serviceSpecEntities": [
    {"@id": "SS-ENT-*", "testedBy": ["TS-*"], "implementedBy": ["T-X.*"]}
  ],
  "serviceSpecErrors": [
    {"@id": "SS-ERR-*", "testedBy": ["TS-*"], "mapsToUserGuide": ["UG-*"]}
  ]
}
```

**Validation Rules (must pass):**
- R1: Every ServiceSpec section must have tasks
- R2: Every requirement must map to ServiceSpec
- R3: Every USER_GUIDE How-To must map to an operation
- R4: Every ServiceSpec operation must have tests

#### Step 1.8: Create ServiceSpec Artifact (MANDATORY for Services/Extensions)

**For Services:** Create `SERVICE_SPECIFICATION.md` using `methodology templates/specification/SERVICE_SPECIFICATION_TEMPLATE.md`
**For Extensions:** Create `SERVICE_SPECIFICATION_EXTENSION.md` using `methodology templates/specification/SERVICE_SPECIFICATION_EXTENSION_TEMPLATE.md`
**For Enhancements:** Update the existing service's SERVICE_SPECIFICATION.md (document changes in DESIGN.md)

> **Note:** ServiceSpec artifacts define the complete contract for AI agent discoverability.
> They include entities, operations, permissions, events, errors, and observability specs.

### Output: Design Package

All artifacts created in `features/{feature}/`:
- PR_FAQ.md
- USER_GUIDE.md
- TEST_SCENARIOS.md
- DESIGN.md
- IVS.md
- ONTOLOGY.jsonld (MANDATORY)
- TRACEABILITY.jsonld
- SOLUTION_SUMMARY.md (executive dashboard)
- SERVICE_SPECIFICATION.md (for Services) OR SERVICE_SPECIFICATION_EXTENSION.md (for Extensions)

---

## Phase 2: IMPLEMENTATION

### Purpose

Execute the design with TDD, creating production-ready code.

### Internal Processing

1. **Planning with Traceability**
   - Create PLAN.md (implementation strategy)
   - Create TASKS.md (TDD task breakdown **with explicit traceability**)
   - Initialize CHANGELOG.md

   **TASKS.md Generation Requirements:**

   > **Reference:** See `methodology standards/TRACEABILITY_MODEL.md` for complete model.

   **Task ID Convention (T-X.Y.Z):**
   ```
   T-2.1.2
   │ │ │
   │ │ └─ Task number within section
   │ └─── Section number (maps to ServiceSpec section)
   └───── Phase number
   ```

   **Each Task Entry Must Include:**
   ```markdown
   - [ ] **T-2.1.2** Implement {Entity} model
     - **ServiceSpec:** §2.1 (Entity schema with sys envelope)
     - **Requirements:** FR-01, FR-03
     - **Tests:** TS-01, TS-04
     - **UserGuide:** UG-04 (Reference - {Entity} Model)
     - **File:** `src/services/{service}/domain/models/{entity}.py`
   ```

   **TASKS.md Must Include Traceability Matrix:**
   ```markdown
   ## ServiceSpec Traceability Matrix

   | Section | Name | Tasks | Requirements | Tests | Status |
   |---------|------|-------|--------------|-------|--------|
   | §2.1 | Entity schema | T-2.1.* | FR-01, FR-03 | TS-01, TS-04 | Planned |
   | §3.2 | {action} operation | T-3.2.* | FR-01, FR-02 | TS-01, TS-02, TS-03 | Planned |
   ```

2. **Double-Loop TDD (Outside-In)**

   ```
   ┌─────────────────────────────────────────────────────────────┐
   │  OUTER LOOP: Integration Tests (write FIRST, all FAILING)   │
   │  INT-HP-*, INT-ALT-*, INT-SEC-*, INT-RI-*, INT-J-*          │
   │  Run locally with InMemoryServiceAdapter (~10ms/test)       │
   │  Same tests run via SDKServiceAdapter in CI/CD              │
   └─────────────────────────────────────────────────────────────┘
                                 ↓
   ┌─────────────────────────────────────────────────────────────┐
   │  INNER LOOP: Unit TDD (RED → GREEN → REFACTOR)              │
   │  Domain → Infrastructure → Handler → Entrypoints             │
   │  Continue until outer loop tests pass                        │
   └─────────────────────────────────────────────────────────────┘
   ```

   **Outer Loop (Integration Tests - Written FIRST):**
   - Write ALL integration tests before any implementation
   - Tests run against API/SDK endpoints
   - All tests FAIL initially (expected - nothing exists yet)
   - Use test scenario IDs from TEST_SCENARIOS.md (TS-*)

   **Inner Loop (Unit TDD - Per Task):**

   For each task in TASKS.md:

   | Phase | Action | Marker |
   |-------|--------|--------|
   | **RED** | Write failing test first | `tddPhase: "RED"` |
   | **GREEN** | Write minimum code to pass | `tddPhase: "GREEN"` |
   | **REFACTOR** | Clean up, all tests still pass | `tddPhase: "REFACTOR"` |

   **Implementation Order:**
   1. Domain models (T-2.*)
   2. Domain actions (T-2.*)
   3. Port protocols (T-2.*)
   4. Handlers with @operation (T-3.*)
   5. Infrastructure adapters (T-5.*)
   6. Entrypoints (T-4.*)
   7. Cross-cutting concerns (T-9.*, T-10.*)

   **Continue inner loop until ALL outer loop tests pass.**

3. **Verification**
   - Verify ALL SEC-* requirements met
   - Verify ALL OBS-* requirements met
   - Verify ALL REL-* requirements met
   - **Verify ALL META-* requirements met** (ServiceSpec Metadata Compliance)
   - **NO PARTIAL VERIFICATION - ALL MUST BE COMPLETE**

   **META-* Verification (CRITICAL):**

   > Reference: `skills/validators/servicespec-compliance-rules.md`

   Before completing IMPLEMENTATION phase, verify:
   - [ ] META-OP-*: @operation decorators on ALL handler methods
   - [ ] META-ENT-*: Entity display metadata in models
   - [ ] META-FORM-*: Form-drivable metadata on fields
   - [ ] META-ERR-*: Error catalog with user_action fields
   - [ ] META-DISC-*: ONTOLOGY.jsonld matches code (ops, entities, errors count)
   - [ ] META-BIND-*: SDK methods added (if user-facing)

   **Verification Command:**
   ```bash
   # Compare @operation count to ONTOLOGY operations
   ONTOLOGY_OPS=$(jq '.operations | length' features/{feature}/ONTOLOGY.jsonld)
   CODE_OPS=$(grep -r "@operation(" src/services/{service}/service_layer/handlers/ | wc -l)
   [ "$CODE_OPS" -ge "$ONTOLOGY_OPS" ] && echo "PASS" || echo "BLOCK: $CODE_OPS < $ONTOLOGY_OPS"
   ```

4. **Traceability Validation**
   - Every ServiceSpec section has at least one task
   - Every task references a ServiceSpec section
   - Every task has at least one test scenario
   - Update TRACEABILITY.jsonld `taskToServiceSpec` entries

5. **Pre-commit Checks**
   - Run `uv run nox -s pre-commit`
   - All tests pass

6. **Entity Model Canonicalization (if ENTITY_MODEL_DELTA.md exists)**

   After all implementation tasks complete, update the canonical entity model:

   ```
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │  ENTITY MODEL CANONICALIZATION                                               │
   ├─────────────────────────────────────────────────────────────────────────────┤
   │                                                                              │
   │  1. Read ENTITY_MODEL_DELTA.md Section 7 (Update Plan)                      │
   │                                                                              │
   │  2. Update architecture/PLATFORM_ENTITY_MODEL.md:                          │
   │     - Section 2.1: Add entities to hierarchy                                 │
   │     - Section 2.2: Add new ID prefixes                                       │
   │     - Section 3.X: Add/update ERD diagrams                                   │
   │     - Section 4.X: Add/update service ontology                               │
   │     - Section 5: Add cross-service relationships                             │
   │     - Section 6: Add namespace/storage patterns                              │
   │     - Section 8: Add change log entry                                        │
   │                                                                              │
   │  3. Commit: "docs: Update PLATFORM_ENTITY_MODEL.md for {feature}"           │
   │                                                                              │
   └─────────────────────────────────────────────────────────────────────────────┘
   ```

   **Task ID Convention:** T-11.1.X (Documentation & Finalization phase)

   **This step is MANDATORY if ENTITY_MODEL_DELTA.md exists.**
   Production Guardian will verify the canonical model is updated.

### Output: Implementation Package

- PLAN.md
- TASKS.md (100% complete - NO DEFERRALS, **with explicit ServiceSpec traceability**)
- CHANGELOG.md
- PLATFORM_ENTITY_MODEL.md updated (if entities were added/modified)
- Updated TRACEABILITY.jsonld (with `taskToServiceSpec` mappings)
- All code changes
- All tests passing
- All IVS requirements verified (100%)

---

## Phase 3: RELEASE

### Purpose

Deploy to production and verify deployment success.

### Internal Processing

1. **Commit & Push**
   - Create meaningful commit message
   - Push to remote branch

2. **Production Guardian Review (STRICT MODE)**
   - Invoke production-guardian skill
   - **Phase 2: ServiceSpec Compliance Scan (META-*)** - Runs FIRST
     - All 60 META-* rules verified
     - Reference: `skills/validators/servicespec-compliance-rules.md`
     - Any META-* failure = BLOCKED
   - Decision must be **APPROVED** or **BLOCKED**
   - **NO CONDITIONAL APPROVAL ALLOWED**
   - **NO DEFERRALS ALLOWED**
   - Any unmet IVS requirement = BLOCKED
   - Any META-* failure = BLOCKED

3. **Deployment**
   - Monitor CI/CD pipeline
   - Verify deployment success
   - Check health endpoints

4. **Post-Deployment Verification**
   - Verify production functionality
   - Check observability (logs, metrics)
   - Verify ServiceSpec endpoint returns new capability

### Output: Release Package

- Git commit SHA
- Production Guardian report (**APPROVED only** - BLOCKED stops the process)
- Deployment verification

---

## Phase 4: COMPLETION

### Purpose

Finalize documentation, update platform conventions, and obtain user sign-off.

### Documentation Updates (MANDATORY)

#### PLATFORM_CONVENTIONS.md Evaluation

| Trigger | Section to Update |
|---------|-------------------|
| New entity ID prefix | Section 1.8 (Entity IDs) |
| New API endpoint pattern | Section 1.3 (URL Paths) |
| New permission pattern | Section 4.2 (Permission Patterns) |
| New state machine pattern | Section 7 (State Machines) |
| ServiceSpec extension | Section 8 (ServiceSpec) |

#### PLATFORM_ENTITY_MODEL.md Evaluation (REQUIRED)

| Trigger | Section | Action |
|---------|---------|--------|
| E1: New domain entity | 2. Entity Hierarchy | Add to tree |
| E2: New entity ID prefix | 2. Entity Hierarchy | Document prefix |
| E3: Modified entity relationship | 3. ERD Diagrams | Update diagram |
| E5: New service domain | 4. Service Ontologies | Add section |
| E9: Resolved architecture issue | 8. Issue Registry | Mark RESOLVED |

### Step 4.1: Create DOCUMENTATION_CHECKLIST.md (MANDATORY)

Create `features/{feature}/DOCUMENTATION_CHECKLIST.md` using template:

```
methodology templates/feature/DOCUMENTATION_CHECKLIST_TEMPLATE.md
```

**Checklist Requirements:**
- All 14 PLATFORM_CONVENTIONS.md triggers evaluated
- All 6 /docs folder triggers evaluated
- Post-deployment observability verified
- Feature index updated
- Every "not_applicable" has justification

### Step 4.2: Invoke Completion Validator (MANDATORY)

> **CRITICAL:** Before requesting user sign-off, invoke the Completion Validator agent.
>
> **Reference:** `skills/completion-validator/SKILL.md`

```python
Task(
    subagent_type="general-purpose",
    prompt="""
    ## Completion Validation Review

    Feature: {feature_name}
    Feature Path: features/{feature}/

    ## Your Task

    Perform a complete Completion Validation review following
    skills/completion-validator/SKILL.md

    1. Evaluate all 14 PLATFORM_CONVENTIONS.md triggers
    2. Evaluate all 6 /docs folder triggers
    3. Verify post-deployment observability
    4. Check feature index update
    5. Verify DOCUMENTATION_CHECKLIST.md

    Produce the full report. Decision: PASSED or BLOCKED.
    """,
    description="Completion Validator Review"
)
```

**Validation Decision:**

| Result | Action |
|--------|--------|
| **PASSED** | Proceed to User Sign-off |
| **BLOCKED** | Fix ALL issues, then re-validate |

**Store Report:**
```
features/{feature}/reviews/completion-validator-{YYYY-MM-DDTHHMMSSZ}.md
```

### User Sign-off Presentation

Present ALL artifacts together for user review:

```
Feature {Feature Name} - Complete Review
=========================================

VISION DOCUMENTS:
✓ PR_FAQ.md - Press release and FAQ
✓ USER_GUIDE.md - User documentation

TECHNICAL DESIGN:
✓ DESIGN.md - Architecture and components
✓ IVS.md - Implementation verification spec

ONTOLOGY:
✓ ONTOLOGY.jsonld - LLM-discoverable specification

TESTS:
✓ TEST_SCENARIOS.md - Test specifications
✓ All tests passing

CODE:
✓ {X} files added, {Y} files modified
✓ All pre-commit checks passing

QUALITY:
✓ Production Guardian: APPROVED
✓ Report: features/{feature}/reviews/production-guardian-{YYYY-MM-DDTHHMMSSZ}.md

DOCUMENTATION:
✓ Platform conventions updated: {Yes/No}
✓ Entity model updated: {Yes/No}
✓ /docs updated: {Yes/No}

=========================================
Please review all artifacts and confirm sign-off.
=========================================
```

### Output: Completion Report

- Feature status: complete
- All deliverables listed
- Documentation updates documented
- User sign-off recorded

---

## Mandatory Artifacts Checklist

Every feature MUST have these artifacts in `features/{feature}/`:

| Artifact | Phase | Mandatory | Notes |
|----------|-------|-----------|-------|
| **MARKET_EVIDENCE.md** | DESIGN (Step 1.0) | **YES** | Created FIRST - validates problem exists |
| PR_FAQ.md | DESIGN | YES | References MARKET_EVIDENCE.md |
| USER_GUIDE.md | DESIGN | YES | All classifications |
| TEST_SCENARIOS.md | DESIGN | YES | All classifications |
| DESIGN.md | DESIGN | YES | All classifications |
| IVS.md | DESIGN | YES | All classifications |
| **ONTOLOGY.jsonld** | DESIGN | **YES** | All classifications |
| TRACEABILITY.jsonld | DESIGN | YES | All classifications |
| **SOLUTION_SUMMARY.md** | DESIGN | **YES** | Executive dashboard - all classifications |
| **SERVICE_SPECIFICATION.md** | DESIGN | **YES** | **Service classification only** |
| **SERVICE_SPECIFICATION_EXTENSION.md** | DESIGN | **YES** | **Extension classification only** |
| PLAN.md | IMPLEMENTATION | YES | All classifications |
| TASKS.md | IMPLEMENTATION | YES | All classifications |
| CHANGELOG.md | IMPLEMENTATION | YES | All classifications |
| reviews/design-validator-{YYYY-MM-DDTHHMMSSZ}.md | DESIGN | YES | All classifications |
| reviews/production-guardian-{YYYY-MM-DDTHHMMSSZ}.md | RELEASE | YES | All classifications |
| **DOCUMENTATION_CHECKLIST.md** | COMPLETION | **YES** | All classifications - 20 triggers evaluated |
| reviews/completion-validator-{YYYY-MM-DDTHHMMSSZ}.md | COMPLETION | YES | All classifications |
| LIFECYCLE_STATE.json | All | YES | All classifications |

### ServiceSpec Artifact Requirements by Classification

| Classification | Required ServiceSpec Artifact |
|----------------|------------------------------|
| **Service** | `SERVICE_SPECIFICATION.md` - Full service contract |
| **ServiceSpec Extension** | `SERVICE_SPECIFICATION_EXTENSION.md` - Extension contract |
| **Service Enhancement** | None (update existing service's spec, document in DESIGN.md) |
| **Infrastructure** | None (no user-facing API contract) |

---

## NO DEFERRAL POLICY (STRICT)

> **CRITICAL: NO DEFERRALS ALLOWED. EVER.**

Everything planned in DESIGN must be completed in IMPLEMENTATION.
Everything in IVS.md must be verified before RELEASE.
There is NO MVP vs future scope distinction.

### What This Means

1. **All IVS requirements are BLOCKING**
   - SEC-* (Security) - BLOCKING
   - OBS-* (Observability) - BLOCKING
   - REL-* (Reliability) - BLOCKING

2. **Production Guardian decisions**
   - APPROVED - Deployment can proceed
   - BLOCKED - Deployment MUST NOT proceed
   - ~~CONDITIONAL~~ - **NOT ALLOWED**

3. **If work cannot be completed**
   - Do NOT proceed to next phase
   - Do NOT mark as "deferred"
   - Complete the work or redesign the scope in DESIGN phase
   - Phase cannot complete with incomplete work

4. **TASKS.md completion requirements**
   - Must be 100% complete
   - All tests must pass
   - All IVS requirements must be verified
   - No items marked as "deferred" or "future work"

### Why No Deferrals?

- Deferrals accumulate into technical debt
- "We'll fix it later" becomes "we never fixed it"
- Production issues from incomplete work damage user trust
- Quality gates lose meaning if they can be bypassed
- Features should be complete or not released

---

## State Management

### LIFECYCLE_STATE.json

Each feature has a state file:

**Location:** `features/{feature-name}/LIFECYCLE_STATE.json`

```json
{
  "feature_name": "rate-limiting",
  "classification": "servicespec_extension",
  "current_phase": "implementation",
  "phases": {
    "classification": { "status": "complete", "...": "..." },
    "design": { "status": "complete", "...": "..." },
    "implementation": { "status": "in_progress", "...": "..." },
    "release": { "status": "pending" },
    "completion": { "status": "pending" }
  },
  "notes": [],
  "blockers": []
}
```

### State Transitions

```
pending → in_progress → complete
                     ↘ blocked (requires resolution before continuing)
```

**Rules:**
1. Only ONE phase can be `in_progress` at a time
2. Phase cannot start until previous phase is `complete`
3. **NO `deferred` status exists** - work must be completed
4. `blocked` status requires documenting blocker and resolution

---

## Integration with Other Skills

| Phase | Skills Invoked | Purpose |
|-------|----------------|---------|
| CLASSIFICATION | (internal classification logic) | Determine ServiceSpec relationship |
| DESIGN | test-scenarios (internal) | Derive tests from User Guide |
| DESIGN → GATE 1 | **design-validator** | Validate against conventions & architecture |
| IMPLEMENTATION | backend-development, pre-commit-checks | TDD implementation |
| RELEASE | production-guardian (STRICT MODE) | Pre-deployment quality gate |
| COMPLETION → GATE 4 | **completion-validator** | Documentation & observability verification |

### Design Validator Integration

Before requesting GATE 1 (Design Approval), the Design Validator agent MUST be invoked:

```python
# Invoke Design Validator before GATE 1
Task(
    subagent_type="design-validator",
    prompt=f"""
    ## Feature Under Review
    Feature: {feature_name}
    Feature Path: features/{feature_name}/

    ## Reference Documents (Read First)
    1. features/PLATFORM_CONVENTIONS.md
    2. architecture/PLATFORM_ENTITY_MODEL.md
    3. architecture/ARCHITECTURE.md

    ## Design Artifacts to Validate
    - features/{feature_name}/PR_FAQ.md
    - features/{feature_name}/USER_GUIDE.md
    - features/{feature_name}/TEST_SCENARIOS.md
    - features/{feature_name}/DESIGN.md
    - features/{feature_name}/IVS.md
    - features/{feature_name}/ONTOLOGY.jsonld
    - features/{feature_name}/TRACEABILITY.jsonld
    - features/{feature_name}/SOLUTION_SUMMARY.md

    ## Your Task
    Perform a complete Design Validation review.
    Validate against all three reference documents.
    Produce the full report in the specified format.
    All violations are BLOCKING.
    """,
    description="Design Validator Review"
)
```

**Decision Handling:**
- **PASSED** → Proceed to GATE 1 (User Approval)
- **BLOCKED** → Fix ALL issues, then re-run Design Validator
- Report stored at: `features/{feature}/reviews/design-validator-{YYYY-MM-DDTHHMMSSZ}.md`

See `skills/design-validator/SKILL.md` for full agent specification.

---

## Non-Negotiable Rules

1. **No phase skipping** - Every phase must complete before the next starts
2. **Classification FIRST** - Must classify before design
3. **ONTOLOGY.jsonld MANDATORY** - Every feature must have ontology
4. **ServiceSpec integration required** - Features must be discoverable via ServiceSpec
5. **Entity Model Analysis required** - PLATFORM_ENTITY_MODEL.md must be read during DESIGN
6. **Entity Model Updates required** - PLATFORM_ENTITY_MODEL.md must be updated during COMPLETION
7. **Organization optionality verified** - B2C/B2B compatibility must be checked
8. **NO DEFERRALS** - Everything planned must be completed
9. **Production Guardian APPROVED only** - Not CONDITIONAL, must be APPROVED or BLOCKED
10. **Completion Validator PASSED only** - Documentation and observability must be verified
11. **Single user approval at COMPLETION** - User reviews complete package together
12. **State must be persisted** - LIFECYCLE_STATE.json updated at every transition
13. **Contracts must validate** - Input/output must match JSON schemas
14. **META-* compliance required** - All 60 ServiceSpec metadata rules must pass (see `skills/validators/servicespec-compliance-rules.md`)

---

## Quick Reference

### Starting a New Feature

```
/feature-lifecycle "Build rate limiting for API request throttling"
```

### Checking Feature Status

```
Read features/{name}/LIFECYCLE_STATE.json
```

### Classification Quick Reference

| If the feature... | Then it's a... | ServiceSpec Action |
|-------------------|----------------|-------------------|
| Has new entities | Service | Create new ServiceSpec |
| Applies to all operations | Extension | Update SERVICE_SPECIFICATION.md |
| Adds operations to existing service | Enhancement | Update existing ServiceSpec |
| Is pure infrastructure | Infrastructure | No ServiceSpec changes |

---

## Files in This Skill

```
skills/feature-lifecycle/
├── SKILL.md                          # This file
├── COMPLETION_PROTOCOL.md            # Quick checklist
└── schema/
    ├── lifecycle-state.json
    ├── contracts/
    │   ├── feature-request.json
    │   ├── classification-result.json
    │   ├── design-package.json
    │   ├── implementation-package.json
    │   ├── release-package.json
    │   └── completion-report.json
    ├── gates/
    │   └── user-signoff.json         # Only gate requiring user approval
    └── artifacts/
        ├── pr-faq.json
        ├── user-guide.json
        ├── test-scenarios.json
        ├── design.json
        ├── ivs.json
        ├── ontology.json             # MANDATORY
        ├── traceability.json
        ├── plan.json
        ├── tasks.json
        └── changelog.json
```
