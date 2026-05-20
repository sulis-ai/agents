# SEA: Senior Engineering Architect Plugin for Claude Code

A Claude Code plugin that converts requirements into hardened technical
designs, audits brownfield code for primitive gaps, and decomposes
architectures into atomic Work Packages an execution agent can implement
without drift.

SEA is the technical counterpart to [SRD](../srd/) — where SRD handles
**What** and **Why**, SEA handles **How**, **Hardening**, and **Work
Decomposition**.

---

## Why This Exists

Most AI coding agents act like junior developers: they write code that
passes the next test. SEA is opinionated in the opposite direction. It
plays the Staff Engineer role — designing the system before code is
written, naming the trade-offs explicitly, and breaking work into pieces
small enough that an execution agent can implement each piece correctly
without holding the whole design in its head.

The output is "boring code": explicit, type-safe, free of magic and
hidden state. The kind of code a future maintainer can read top-to-bottom
and predict.

---

## Quick Start

```bash
# Install the plugin
/plugin marketplace add sulis-ai/agents
/plugin install sea@sulis-ai-agents

# Start an architect session
claude --agent sea:engineering-architect --dangerously-skip-permissions
```

### Commands

| Command | What It Does |
|---------|-------------|
| `claude --agent sea:engineering-architect` | Start the architect as the primary agent |
| `/sea:blueprint` | Greenfield — synthesise a `TDD.md` and ADRs from an existing SRD |
| `/sea:codebase-audit` | Brownfield — read source, identify primitive gaps, draft Hardening Deltas |
| `/sea:harden` | Brownfield — implement accepted Hardening Deltas through the Red-Green-Blue cycle |
| `/sea:decompose` | Break a TDD into atomic Work Packages with dependency graph and token-cost estimates |
| `/sea:verify` | Run five-perspective completeness check; produce `COMPLETENESS_REPORT.md` |
| `/code-review <PR\|branch\|range>` | PR-scoped review — runs architecture, security, and quality lenses in parallel; produces one merged report under `.architecture/{project}/code-reviews/` plus draft Hardening Deltas. Advisory only (no PR comments, no status checks, no auto-blocking). |

---

## How It Works

### The MECE-3 Architecture Framework

Every component SEA designs or audits goes through three Mutually Exclusive
and Collectively Exhaustive pillars:

1. **Form — Structural Integrity.** Hexagonal architecture. Dependencies
   point inward. Modules expose contracts, not implementations.

2. **Armor — Operational Hardening.** Every external call has a timeout,
   retry, and circuit breaker. Secrets are fetched, never embedded.
   Inter-service traffic is encrypted and authenticated. Every operation
   emits a trace, a log, and a metric.

3. **Proof — Verification Protocol.** Every port has a contract test.
   Integration tests use real adapters (testcontainers, not mocks). Every
   resiliency primitive has a chaos test.

A design that satisfies one pillar but ignores another is incomplete. SEA
flags the gap.

### Dual-Mode Operation

| Mode | Trigger | Workflow |
|---|---|---|
| **Greenfield** | SRD exists, codebase doesn't | `/sea:blueprint` → `/sea:decompose` → hand off to execution agent |
| **Brownfield** | Codebase exists, hardening needed | `/sea:codebase-audit` → review deltas → `/sea:harden` → `/sea:verify` |

### Red-Green-Blue

Every Work Package follows a three-stage cycle:

| Stage | What happens |
|---|---|
| **Red** | Write failing tests — including hardening assertions (timeouts, circuit-breaker behaviour, OpenTelemetry spans, authz checks). Hardening lives in Red, not after Green. |
| **Green** | Boring code makes the tests pass. Explicit types. No hidden state. No metaprogramming. |
| **Blue** | Refactor with all tests still green. Extract shared primitives. Remove duplication. Mandatory, not optional. |

See [`references/red-green-blue.md`](references/red-green-blue.md) for full detail.

---

## What It Produces

For greenfield work, SEA writes to `.architecture/{project}/` parallel to
SRD's `.specifications/{project}/`:

```
.architecture/{project}/
├── ARCH.yaml                       # metadata, status, link to source SPEC
├── TDD.md                          # Technical Design Document (Form/Armor/Proof)
├── adrs/
│   ├── ADR-001-{slug}.md           # one decision per file
│   └── ...
├── hardening-deltas/               # brownfield only
│   ├── INDEX.md
│   └── HD-001-{slug}.md
├── work-packages/
│   ├── INDEX.md                    # dependency graph + sequence
│   └── WP-001-{slug}.md            # atomic Red-Green-Blue WPs
└── COMPLETENESS_REPORT.md
```

### Work Package shape

Each WP is atomic — an execution agent can pick one up and implement it
without reading any other WP. Fields:

- **Context** — which TDD section / architecture component
- **Contract** — public interfaces, types, ports
- **Definition of Done** — three checklists for Red, Green, Blue
- **Sequence ID** with `dependsOn` graph — prevents merge conflicts
- **Estimated Token Cost** — `input: ~Nk / output: ~Nk` for orchestrator routing

### Hardening Delta shape

For brownfield work, each delta describes one gap and one fix:

- **Gap type** — which MECE-3 violation (circuit-breaker, secrets, contract-test, etc.)
- **Context** — file path, line, why this is a gap
- **Change** — ADDED / MODIFIED / REMOVED (OpenSpec-style)
- **Verification** — the failing characterisation test that proves the gap exists
- **Rationale** — why this approach, what alternatives were rejected

---

## Where SEA Fits in the Spec-Driven Pipeline

The SEA pipeline composes with the broader Sulis fleet:

```
sulis-security                 SEA                              SRD
(security-reviewer)            (engineering-architect)          (requirements-analyst)
─────────────────              ─────────────────                ─────────────────
25-primitive viability    ←→   MECE-3 architecture        ←→    What & Why
.security/{project}/           .architecture/{project}/         .specifications/{project}/
viability-report.md            TDD + ADRs + WPs + HDs           SRD + NFR + diagrams
```

- **`sulis-security`** runs the broader audit (5 categories, OODA spiral).
  Its Critical and Concern findings convert into SEA Hardening Deltas via
  `/sea:harden`. SEA's `codebase-audit` focuses on Form/Armor/Proof against
  the design; `sulis-security` covers a wider surface (code quality, supply
  chain, infrastructure) and runs without a TDD.
- **`srd`** produces the specification SEA builds the architecture from.
- **Execution agents** (Claude Code, GSD) implement SEA's Work Packages.

```
SRD                  SEA                   Execution Agent
(srd:requirements-   (sea:engineering-     (claude code, gsd, ...)
 analyst)             architect)
─────────────────    ─────────────────     ──────────────────
What & Why     →     How & Hardening   →   Implementation
Functional reqs      Hardened TDD          Code + tests
NFRs                 ADRs                  Green CI
Primitive tree       Work Packages         Merged PR
```

SRD produces the specification. SEA consumes it and produces the
architecture + Work Packages. An execution agent (Claude Code itself,
GSD, or a human engineering team) picks up Work Packages one at a time
and implements them through the Red-Green-Blue cycle.

### Integration with SRD outputs

SEA parses these SRD artifacts directly:

- `SRD.md` → drives the Form pillar (entities, operations, business rules)
  and per-use-case Negative Requirements
- `NFR.md` → drives the Armor pillar and pattern selection
- `MISUSE_CASES.md` (SRD v1.11.0+) → seeds Armor primitives; each MUC's
  System Response becomes one or more Hardening Deltas or TDD Armor entries.
  See `references/hardening-deltas.md` for the MUC → delta translation
  pattern (with worked example).
- `PRIMITIVE_TREE.jsonld` → component inventory for the TDD
- `GLOSSARY.md` (SRD v1.11.0+) → locked vocabulary; SEA uses preferred terms
  exactly in the TDD, ADRs, and Work Packages
- `diagrams/` → integration design (sequence, process, data-flow)
- `EXPLORATION_JOURNAL.md` `## Deferred to SEA` section (SRD v1.11.0+) →
  architecture content SRD parked mid-session; treated as additional user
  design intent
- `HANDOFF_TO_SEA.md` (SRD v1.11.0+, only present in Early Handover path) →
  the sole upstream context when SRD bailed out because the user arrived
  with predominantly technical input; read first, then ask for any missing
  business intent before producing artifacts

If `.specifications/{project}/` doesn't exist, SEA blocks and refers the
user to `srd:requirements-analyst`. It does not invent requirements.

---

## Who It's For

**Engineering teams using AI-assisted development.** When you have a
specification and need a hardened technical design, plus atomic Work
Packages that won't drift when handed to an execution agent.

**Brownfield audits.** When you have a working codebase that needs to
become production-grade — timeouts, circuit breakers, observability,
secrets management, contract tests. SEA produces a delta-driven path
from where you are to where you need to be, one focused change at a time.

**Spec-driven development practitioners.** SEA slots between SRD (or any
SRD-equivalent) and execution-layer tools (Claude Code Plan mode, GSD,
Spec Kit). It bridges "we know what to build" and "we're building it".

---

## Installation

### From marketplace

```bash
/plugin marketplace add sulis-ai/agents
/plugin install sea@sulis-ai-agents
```

### From local clone

```bash
claude --plugin-dir ./plugins/sea
```

---

## Usage

### Starting a session

```bash
claude --agent sea:engineering-architect --dangerously-skip-permissions
```

The agent runs as your primary conversational partner — direct
conversation, full context window. The `--agent` flag is the right
invocation for the multi-turn design sessions this plugin is built for.

To make it the default for a project, add to `.claude/settings.json`:

```json
{
  "agent": "sea:engineering-architect"
}
```

### Standalone skill invocation

Each skill can be run independently outside of an architect session:

```bash
/sea:blueprint .specifications/payments-service
/sea:codebase-audit
/sea:decompose
/sea:harden HD-003
/sea:verify
```

---

## References

The plugin loads these standards. They are authoritative for the decisions
SEA makes.

| File | Purpose |
|---|---|
| [`references/mece-3-architecture.md`](references/mece-3-architecture.md) | The three pillars — Form, Armor, Proof |
| [`references/red-green-blue.md`](references/red-green-blue.md) | The Work Package execution cycle |
| [`references/boring-code.md`](references/boring-code.md) | The Green-stage code standard |
| [`references/hardening-deltas.md`](references/hardening-deltas.md) | The brownfield delta format (OpenSpec-style) |
| [`references/architecture-patterns.md`](references/architecture-patterns.md) | Catalogue of vetted architecture patterns |

---

## License

MIT
