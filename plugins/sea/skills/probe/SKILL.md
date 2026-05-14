---
name: probe
description: >
  Deep structural analysis of a brownfield codebase. Uses programmatic
  tools (ast-grep, lizard, scc) to extract a deterministic capability
  inventory, extension point catalogue, reusable abstraction catalogue,
  coupling/hotspot map, convention inventory, and wrapper-rot detection.
  Produces `.architecture/{project}/CODE_INTELLIGENCE.md` so blueprint /
  decompose / harden / verify can make informed extend / reuse / refactor /
  create decisions per `references/change-primitives.md`.
user_invocable: true
---

# Code Intelligence Probe

When invoked, perform deterministic structural analysis of the project and
produce `.architecture/{project}/CODE_INTELLIGENCE.md`. The artifact is
load-bearing for every downstream SEA skill — blueprint reads it to make
extend/reuse/refactor/create decisions; decompose reads it to assign WPs
to specific code regions; verify reads it to check primitive-classification
sanity.

**Hard tool requirement.** `/sea:probe` does not run without its toolchain.
Pre-flight checks `ast-grep`, `lizard`, and `scc`; if any is missing, runs
the installer (`scripts/install-probe-tools.sh`) with user confirmation.
There is no LLM-only fallback — at codebase scale, LLM-as-AST-walker has
unacceptable hallucination risk for analysis that downstream skills depend
on.

---

## Inputs You Read

| Source | Why |
|---|---|
| Project source tree | Primary input — ast-grep extracts symbols, lizard computes complexity, scc builds the import graph |
| `.context/{project}/INDEX.md` (if present) | Tells you which docs are authoritative — adjusts which conventions you should look for |
| `package.json` / `Cargo.toml` / `pyproject.toml` / `go.mod` / `pom.xml` | Detect language(s), framework hints |

If `.context/{project}/INDEX.md` does not exist on a non-trivial codebase,
recommend `/sulis-context:discover` first (same auto-suggest gate as
other SEA skills).

---

## Workflow

### Phase 0 — Tool Detection

Run `bash scripts/install-probe-tools.sh --check`. The script reports
required tools (ast-grep, lizard, scc) and optional tools (repomix).

Three outcomes:

**All required tools present** → proceed to Phase 1.

**Some required tools missing** → present the missing-tool list to the user:

> "Required tools are missing for `/sea:probe`:
> - ast-grep (tree-sitter-based AST queries)
> - lizard (cyclomatic complexity)
>
> These tools produce deterministic analysis that LLM reads cannot reliably
> replicate at codebase scale. They cannot be replaced by a fallback.
>
> Want me to install them now? I'll run `scripts/install-probe-tools.sh`.
> On macOS this uses Homebrew; on Debian/Ubuntu it uses pip + cargo/npm.
> No sudo required for user-scoped installs.
>
> Choices:
> 1. **Install now** — I run the installer
> 2. **Show me the commands** — I print install commands; you run them
> 3. **Stop** — abort the probe
>
> If installs fail (network, permissions, missing prerequisites), I'll
> stop — there is no LLM-only fallback."

If choice 1: invoke the installer via Bash. On success, re-check and
proceed to Phase 1. On failure, surface the errors and stop.

**Prerequisite missing (e.g. Homebrew on macOS)** → tell the user, link to
installer for the prerequisite, stop.

### Phase 1 — Deterministic Extraction

Each of the following runs as a separate Bash invocation. Capture outputs
into working memory; cite them by-source in the resulting
CODE_INTELLIGENCE.md so the user can audit.

**1.1 — Language and stack inference.** Use `scc .` to get file counts by
language, LOC totals, and complexity averages. Read manifests
(`package.json`, etc.) to identify frameworks. Record in INFRA section of
the output.

**1.2 — Capability inventory.** For each language present, run ast-grep
queries that extract:

- Public classes, interfaces, traits, abstract classes
- Exported functions and their signatures
- Type definitions (TypeScript types/interfaces; Python protocols; Go interfaces; etc.)

Example queries:

```bash
# TypeScript: every exported class/function
ast-grep --pattern 'export class $NAME { $$$ }' --lang ts src/
ast-grep --pattern 'export function $NAME($$$) { $$$ }' --lang ts src/
ast-grep --pattern 'export interface $NAME { $$$ }' --lang ts src/

# Python: every public class/function
ast-grep --pattern 'class $NAME($$$):' --lang python src/
ast-grep --pattern 'def $NAME($$$):' --lang python src/

# Go: every exported type/func
ast-grep --pattern 'type $NAME $$$' --lang go .
ast-grep --pattern 'func $NAME($$$) $$$' --lang go .
```

Each match → one entry in the Capability Inventory with `[deterministic:
ast-grep]` provenance.

**1.3 — Extension point catalogue.** ast-grep queries for known extension-
point patterns:

- Abstract classes / abstract methods
- Interfaces with multiple known implementations (cross-reference
  capability inventory for `implements X` or `: X` declarations)
- Factory functions returning a polymorphic type
- Registry / plugin patterns (`register(...)` calls with type-tag args)
- Hook patterns (function arrays, observer patterns)
- Dependency-injection containers (look for framework-specific markers:
  NestJS `@Injectable`, Spring `@Component`, Symfony service definitions)

**1.4 — Reusable abstraction catalogue.** For each utility module / shared
library file in the project, count consumers via `ast-grep` import-path
matching or `grep -r "from 'path/to/utility'"`. Modules with consumer-count
≥ 3 go in the Reusable Abstractions section.

**1.5 — Coupling / hotspot map.** Use scc + ast-grep to build the import
graph:

- For each module, count incoming imports (fan-in) and outgoing imports
  (fan-out)
- High fan-in (>10 consumers) → "this is touched by many — refactor carefully"
- High fan-out (imports >15 other modules) → "this knows too much — candidate
  for Decompose"
- Identify cycles (any cycle is a structural smell)

**1.6 — Complexity hotspots.** Run lizard:

```bash
lizard -l <language> --CCN 15 --length 80 -E sloc -E maxcc src/
```

Functions with CCN > 15 (cyclomatic complexity > 15) go in the Hotspots
section as Refactor candidates. Files with average CCN > 10 go on the
"module-level fragility" list.

**1.7 — Wrapper rot detection.** Pattern-match for suspicious wrapper
naming:

```bash
# Classes whose name suffix suggests wrapping
ast-grep --pattern 'class $NAME { $$$ }' --lang ts src/ | grep -E 'V2|V3|Facade|Wrapper|Adapter|Proxy|Compat'

# For each match, find its dependency target — does it depend on another
# internal module with a similar name minus the suffix?
```

When a wrapper-style class is found, examine its constructor / fields /
delegations: does it hold a reference to another internal class with a
related name (e.g. `OrderServiceV2` holding `OrderService`)? If yes,
flag as candidate wrapper rot. Output is a list of pairs:
`(wrapper, wrapped, depth)`.

Note: ports-and-adapters work is NOT wrapper rot. An `infrastructure/`
adapter implementing a domain `port` is the correct pattern. The probe
distinguishes by:
- Adapter implements an interface defined in `domain/` (or equivalent) → legitimate Create
- Wrapper depends on another internal class with a similar name and translates calls → candidate rot

**1.8 — Convention inventory.** Pattern observations:

- File-naming convention (`PascalCase.ts`? `kebab-case.ts`? `snake_case.py`?)
- Test-file convention (`.test.ts`? `_test.go`? `tests/test_*.py`?)
- Error-handling convention (Result types? exceptions? error returns?)
- Module-layout convention (per-feature folders? layered folders?)
- Naming for repository / service / adapter / use-case classes

These come from scc's file-tree analysis + ast-grep observations + LLM
reading of `CONTRIBUTING.md` (if present).

### Phase 2 — LLM Synthesis (Judgement)

After Phase 1 produces deterministic facts, LLM synthesises the
interpretive layer:

**2.1 — Module role classification.** For each module identified by
ast-grep, classify as: `domain | application | infrastructure | shared |
test | tooling | unknown`. Mark `[llm-inferred]` with confidence per entry.

**2.2 — Pattern recognition at system level.** From the assembled facts,
identify which architectural pattern(s) the codebase follows:
hexagonal/ports-and-adapters, MVC, CQRS, event-sourcing, layered, modular
monolith, microservices. Cite the structural evidence.

**2.3 — Wrapper-rot triage.** For each candidate from Phase 1.7, judge
whether it is:
- Genuine wrapper rot (escalate as anti-pattern to flag in CODE_INTELLIGENCE.md)
- Legitimate adapter for an external system (mis-detected; clear)
- In-progress Strangle (check for the strangled subject's planned-removal indicator)
- Branch-by-abstraction (legitimate transitional)

**2.4 — Recommendation pass.** For each detected smell or opportunity,
propose the appropriate primitive per `references/change-primitives.md`.
Examples: "high-CC function `processOrder` → REORGANISE-Decompose";
"three near-duplicate utilities → REORGANISE-Abstract"; "wrapper rot on
`OrderService` → REORGANISE-Refactor of underlying OR SUBSTITUTE-Replace
+ CONTRACT-Delete of wrappers". Recommendations are advisory; the user
or blueprint chooses whether to act.

### Phase 3 — Write CODE_INTELLIGENCE.md

Write to `.architecture/{project}/CODE_INTELLIGENCE.md` per the schema in
`references/code-intelligence-template.md`. Every section entry is marked
with provenance:

- `[deterministic: ast-grep]` — Phase 1 extraction
- `[deterministic: lizard]`
- `[deterministic: scc]`
- `[llm-inferred, confidence: low|medium|high]` — Phase 2 synthesis

### Phase 4 — Report

Brief summary to the user:

> "Probe complete. Wrote `.architecture/{project}/CODE_INTELLIGENCE.md`.
>
> Headline findings:
> - **{N} modules** across {language} stack
> - **{M} capabilities** catalogued (classes / functions / types)
> - **{K} extension points** identified
> - **{P} reusable abstractions** (modules with consumer-count ≥ 3)
> - **{Q} complexity hotspots** (functions with CCN > 15)
> - **{R} candidate wrapper-rot cases** to review
> - **{S} convention rules** detected
>
> System-level pattern: {hexagonal / MVC / CQRS / ...}
>
> Top recommendations for blueprint / decompose:
> 1. {recommendation 1}
> 2. {recommendation 2}
> 3. {recommendation 3}
>
> Refresh: run `/sea:probe` again when source mtimes are newer than this
> intelligence file's `Generated` timestamp (currently {date})."

---

## Refresh Policy

CODE_INTELLIGENCE.md is regenerated when:

- Source-file mtimes are newer than the file's `Generated` timestamp
- Downstream skills (blueprint, decompose, harden, verify) refuse to use
  intelligence > 30 days old
- The user invokes `/sea:probe` explicitly

Refresh is full re-run, not incremental — the deterministic phase is fast
enough (typically < 60 seconds on a 1000-file project) that incremental
refresh is not worth the complexity.

---

## How Other Skills Use CODE_INTELLIGENCE.md

**`/sea:blueprint`** — reads the Capability Inventory + Extension Points
before designing. Reuse decisions cite specific modules. Create decisions
for adapters cite specific ports. Refactor recommendations cite specific
hotspots.

**`/sea:decompose`** — reads everything. Each WP cites the specific code
region (`target:` field). Primitive assignments use the intelligence to
distinguish Create-an-adapter from Wrap-something-internal.

**`/sea:harden`** — reads Coupling/Hotspot Map to understand impact radius
of each delta. Reads Wrapper Rot list to escalate when proposing wraps.

**`/sea:codebase-audit`** — uses Capability Inventory as the structural
baseline against which to find pillar gaps. Findings cite specific
modules from the intelligence.

**`/sea:verify`** — reads Wrapper Rot list. P6 (Change-Primitive
Discipline) cross-references WP primitives against intelligence (e.g.
flag a WP that classifies as Wrap on a subject the intelligence
identifies as internal).

---

## Gotchas

- **Tool drift.** ast-grep and lizard update; queries that work today may
  drift. The skill pins major versions where possible and recommends
  re-running installer if `--check` reports version mismatches in future
  versions.
- **Generated code.** Honour `.gitignore` and the language's standard
  ignore conventions (`node_modules/`, `target/`, `vendor/`, `dist/`,
  `__pycache__/`, etc.). Don't include generated code in the inventory.
- **Multi-language projects.** Probe runs the language detection in scc
  first, then loops over each detected language for ast-grep/lizard. The
  output is unified into a single CODE_INTELLIGENCE.md but cites the
  language per entry.
- **Symbolic links and vendored code.** Follow symlinks only within the
  repo root. Skip vendored directories (`vendor/`, `third_party/`,
  language-specific ones).
- **Repomix is optional and selective.** Not run by default. Used only
  when the LLM synthesis phase needs to read substantial code (e.g. for
  pattern recognition on a small-to-medium codebase). On large codebases,
  selective ast-grep queries are preferred over a full Repomix pack.

---

## See Also

- `references/code-intelligence-template.md` — the CODE_INTELLIGENCE.md schema
- `references/change-primitives.md` — what the intelligence informs (primitive choice)
- `references/right-sizing.md` — how tier interacts with intelligence depth
- `scripts/install-probe-tools.sh` — the installer this skill calls
- `skills/blueprint/SKILL.md` — primary downstream consumer
- `skills/decompose/SKILL.md` — primary downstream consumer
- `skills/verify/SKILL.md` — enforces consistency with intelligence
