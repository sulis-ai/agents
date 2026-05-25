# Engineering Principles Standard

<!-- summary -->
Three active engineering principles (EP-02, EP-03, EP-07) that govern how software is
designed and built. Nine further principles are staged for future introduction — see
roadmap/ROLLOUT_PLAN.md. Active principles apply to all work automatically.
<!-- /summary -->

> **Version:** 1.0.0
> **Status:** Active

---

## Provenance

These principles encode practitioner knowledge accumulated through production software
delivery, drawing on: SOLID and Clean Code (Martin, 2008), Test-Driven Development
(Beck, 2002), and hexagonal architecture (Cockburn, 2005).

This is practitioner knowledge, not peer-reviewed research.

---

## Boundary Definition

This standard contains **universal engineering principles only**. Content belongs here if
and only if it passes the **ProjectX test**: replacing every project name, file path, and
technology-specific example with a fictional "ProjectX" equivalent requires zero semantic
changes to the principle statement.

Content that fails the ProjectX test belongs in the project's architecture file, not here.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification. |

---

## Active Principles

### EP-02: Quality is Paramount

**Severity:** MUST

All known issues introduced by the current work are resolved before moving on. Pre-existing
issues discovered during the work are captured and planned — they do not block the current
PR. Every change follows the RED → GREEN → REFACTOR cycle. The REFACTOR step is mandatory
— it is where duplication is removed and shared primitives are extracted. Never mock what
you can implement — prefer real in-memory adapters over mocks for all internal services.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Write a failing test before implementation (RED). Make the test pass with the simplest correct code (GREEN). Refactor for clarity, naming, and duplication removal with all tests still passing (REFACTOR). Before any commit: all tests pass, no linting errors, no known issues deferred. **Testing architecture:** prefer in-memory adapters (real code, in-memory backend) over mocks. Mocks hide bugs; adapters validate behaviour. Only mock truly external services (third-party APIs, LLMs) where an in-memory adapter is impractical. |
| **Anti-Pattern** | Writing implementation first and tests after. Deferring known issues with "we'll fix it later." Committing with failing tests or linting errors. **Treating the REFACTOR step as optional** — this is where shared primitives are identified and extracted; skipping it is how duplication accumulates. Mocking infrastructure that could be replaced with an in-memory adapter. |
| **How to verify** | All tests pass and linter is clean before every commit. Review that the REFACTOR step actually happened — duplication was removed, shared primitives were extracted, naming was improved. No known issues were deferred. In-memory adapters were used instead of mocks for internal services. |

---

### EP-03: Reuse First

**Severity:** MUST

Exhaust migration and refactoring opportunities before building new. Before creating a new
component, verify that no existing component can be extended or adapted. When a second
consumer of a pattern appears, extract the shared primitive immediately.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Before building something new, search the codebase for existing components that serve the same or similar purpose. Ask: does this component already exist? Can an existing one be extended? If two or more components implement the same pattern, behaviour, or data structure — stop and extract a shared primitive before continuing. This extraction happens in the same PR, not as a follow-up. This applies equally to infrastructure services: when a shared execution primitive exists (workflow engine, state machine, event dispatcher), use it. Build caller-side adapters to conform to the primitive's contract rather than reimplementing its capability. |
| **The Refactoring Trigger** | The threshold for extraction is **two consumers**. When you are building something and realise an existing component already does the same thing differently, that is the signal. Do not build a third copy — extract the shared version now. The extraction is part of the current work, not a separate ticket. |
| **Anti-Pattern** | Building a new utility when an existing one covers 90% of the need. Ignoring existing components because "it's faster to write from scratch." Accumulating near-duplicate implementations across modules. Deferring extraction to a "refactoring sprint" that never happens. Building a standalone workflow engine when a shared one exists, because integrating with it requires upfront adapter work. |
| **How to verify** | Before creating any new component, confirm existing components were searched. No near-duplicate implementations were introduced. When duplication was identified, extraction happened in the same PR. |

---

### EP-07: SOLID and Clean Code

**Severity:** MUST

Follow SOLID principles. Code should be readable, well-named, and free of duplication.

**The Boy Scout Rule:** Leave every file better than you found it. When you touch a file,
you are responsible for improving what's already there — scoped to that file, not the
whole codebase.

**Mechanical vs structural changes:**

- **Mechanical changes** (renames, dead code removal, import cleanup, fixing typos) are
  safe transformations. Do them. They don't require a characterisation test.
- **Structural changes** (extracting functions, splitting classes, changing interfaces,
  rewriting conditionals) change how code is organised. Follow Fowler's refactoring
  discipline: write a characterisation test first, confirm it passes, refactor, confirm
  it still passes. Refactoring without a characterisation test is not refactoring — it's
  editing and hoping.

When you're in a file, look for:

- **Unclear names.** If a variable is called `data` or `tmp` or `result`, rename it
  to say what it actually holds.
- **Duplicated logic.** If the function you're editing contains logic that also
  exists elsewhere, extract the shared version now.
- **Overcomplicated conditionals.** If a condition is hard to read, break it
  into a named predicate.
- **Dead code.** If you see unused imports, commented-out blocks, or unreachable
  branches, delete them.
- **Structural problems.** If a function does three things, split it. If a class has
  multiple responsibilities, separate them.

**Scoping boundary:** If an improvement requires changes beyond the file you're working
in, capture it and plan it separately. Do not let a Boy Scout improvement cascade into
an unbounded refactoring PR.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | **S**ingle Responsibility — one reason to change. **O**pen/Closed — open for extension, closed for modification. **L**iskov Substitution — subtypes must be substitutable. **I**nterface Segregation — many specific interfaces over one general. **D**ependency Inversion — depend on abstractions, not concretions. Use clear, descriptive names. Keep functions small (5–15 lines ideal). Eliminate duplication (DRY). Comments explain "why", not "what." Type hints on all signatures. |
| **Anti-Pattern** | God classes with multiple responsibilities. Inheritance hierarchies that violate substitutability. Vague names (`data`, `manager`, `helper`). Large functions that do many things. Missing type annotations. Touching a file and ignoring existing problems because "that's not what this PR is about." |
| **How to verify** | Linter and type checker pass. Code follows SOLID principles, names are clear and descriptive, no duplication remains. Files touched in the PR are cleaner than they were before. |

---
