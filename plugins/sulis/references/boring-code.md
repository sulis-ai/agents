# Boring Code Standard

<!-- summary -->
SEA produces "boring code": explicit, type-safe, readable, and free of magic.
A senior engineer should be able to read the code top-to-bottom and predict
its behaviour without running it, without consulting external documentation,
and without holding hidden state in their head. Boring code is the Green
standard in the [[red-green-blue]] cycle. Cleverness is rejected; explicitness
is preferred even when it is more verbose.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period

---

## Provenance

Synthesises three traditions:
- **Explicit-is-better-than-implicit** (PEP 20, The Zen of Python, Peters 2004)
- **Principle of Least Astonishment** (folk theorem; explicit in Geoffrey James,
  The Tao of Programming, 1987)
- **Locality of behaviour** (Carson Gross, htmx essays; Sandi Metz, POODR 2012)

This is practitioner knowledge, not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification in the TDD or PR. |

---

## Principles

### BC-01: Types are declared at every public boundary

**Severity:** MUST

Every function, method, or class exposed across a module boundary has explicit
type annotations on parameters and return type. Type inference is permitted
for local variables only.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | `export function createOrder(input: CreateOrderInput): Result<Order, OrderError>` — full annotations. Inside the function, `const total = lines.reduce(...)` is fine. |
| **Anti-Pattern** | Exported functions with inferred return types. `any` or `unknown` used to bypass type errors. `as` casts that the compiler cannot verify. |
| **How to verify** | Strict mode in the type checker (`strict: true` in TypeScript, `mypy --strict`). Lint rule requiring explicit return types on exported functions. |

### BC-02: No hidden state

**Severity:** MUST

State that affects behaviour is passed explicitly. Module-level mutable
variables, global singletons, ambient context, and "service locators" are
banned. Dependencies arrive via constructor or parameter — not via
`getInstance()` or `import { db }`.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | A function's inputs are its parameters. A class's inputs are its constructor arguments. The composition root (the outermost wiring) is the only place where dependencies are resolved. |
| **Anti-Pattern** | A module-level `let currentUser = null` mutated by request handlers. A singleton `Logger.getInstance()` called from deep inside business logic. AsyncLocalStorage used as a hidden parameter to avoid explicit threading. |
| **How to verify** | Code search for module-level `let` or `var`. Code search for `getInstance(`, `Singleton`, `globalThis.`. Architecture test asserting only the composition root resolves dependencies. |

### BC-03: No metaprogramming, reflection, or runtime code generation

**Severity:** SHOULD

Code does what it says. No proxies that intercept method calls. No decorators
that mutate class semantics at load time. No `eval`, `Function()`, or
runtime AST manipulation. No "magic strings" that map to behaviour by
convention.

Exceptions: framework-provided decorators (NestJS `@Controller`, Spring
`@Component`) that are visible at the boundary. The boundary is documented
in the TDD.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Prefer explicit configuration over convention-over-configuration. Prefer a function call over a decorator. Prefer a switch statement over a registry of strings. |
| **Anti-Pattern** | A Proxy that intercepts every property access. A decorator that rewrites the method body. `eval(userInput)`. A "plugin system" that loads code by string name without a registered type. |
| **How to verify** | Code search for `Proxy(`, `Reflect.`, `eval(`, `new Function(`. Each occurrence is justified in the TDD. |

### BC-04: Errors are values, not surprise jumps

**Severity:** SHOULD

Predictable failures are returned as values (`Result<T, E>`, tagged unions,
sum types). Exceptions are reserved for truly exceptional cases — programmer
errors and unrecoverable conditions. Callers can see from the type signature
which errors a function can produce.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | `function parseDate(input: string): Result<Date, ParseError>` makes the failure mode visible. A caller cannot ignore it without dealing with the `E` arm. |
| **Anti-Pattern** | A function that "might throw" with no indication in the signature. A 200-line try/catch that swallows every error type. Re-throwing a generic `Error` that loses the original type. |
| **How to verify** | Public functions document their error types in the signature. Lint rule discouraging untyped throws. |

### BC-05: One way to do each thing

**Severity:** SHOULD

If there are three ways to create an order, there are three places to update
when the rules change, and two of them will be missed. Pick one canonical
path per operation and route every caller through it.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Use the application service. Don't construct entities directly in tests except inside test factories. Don't have parallel "v1" and "v2" code paths long-term. |
| **Anti-Pattern** | Three constructors for `Order`, each doing something subtly different. A `createOrderLegacy()` that's still called from one place. Helper functions that duplicate logic in the service. |
| **How to verify** | Code search for `Legacy`, `Old`, `V1`, `V2` suffixes. Each one is either deleted or has a documented removal date. |

### BC-06: Locality of behaviour

**Severity:** SHOULD

To understand what a piece of code does, a reader should be able to find the
relevant logic close to where it is invoked. Indirection that hides behaviour
behind a chain of files is a cost; pay it only when the indirection serves
a clear purpose (testability boundary, swap point, polymorphic dispatch).

| Attribute | Detail |
|-----------|--------|
| **In Practice** | A handler that processes an order can be read top-to-bottom and the logic is visible. Database calls are abstracted (one indirection through the repository port — purposeful), but not every utility function is in its own file in its own folder. |
| **Anti-Pattern** | "Lasagne code" — twelve layers of helpers, each calling one other helper. A 200-file feature where the actual logic is spread across 40 single-function modules. |
| **How to verify** | Read the entry point. If understanding the behaviour requires opening more than 4-5 files for a simple operation, the indirection budget has been exceeded. |

---

## Anti-Patterns SEA Rejects

A non-exhaustive list of patterns SEA flags during `/sea:blueprint` review and
`/sea:codebase-audit`:

| Pattern | Why it's rejected |
|---|---|
| Mutable module-level state | Hidden — violates BC-02 |
| Singletons accessed via `getInstance()` | Hidden dependency — violates BC-02 |
| AsyncLocalStorage as a hidden parameter | Hidden state crossing boundaries — violates BC-02 |
| Decorators that rewrite method bodies | Magic — violates BC-03 |
| Proxies for "ergonomic" property access | Magic — violates BC-03 |
| `eval` or `Function()` with non-literal input | Security + magic — violates BC-03 |
| Untyped `throw` in public APIs | Hidden control flow — violates BC-04 |
| `any` or `as unknown as X` casts | Bypassing type safety — violates BC-01 |
| Parallel legacy + new code paths long-term | Multiple sources of truth — violates BC-05 |
| Deep file hierarchies for trivial helpers | Hides behaviour — violates BC-06 |

---

## Gotchas

- **"Boring" is not the same as "verbose".** A short, obvious implementation is
  more boring than a long, clever one. Boring rewards reading, not typing.
- **Frameworks force trade-offs.** Some frameworks require decorators or
  proxies. Use them — but document the boundary in the TDD and don't extend
  the magic past it.
- **Inference is fine inside functions.** BC-01 applies to public boundaries.
  Don't fight the type checker on local variables.
- **Boring code can still be elegant.** Elegance through directness, not
  through cleverness.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-12 | Initial standard. Six principles codifying SEA's "boring code" Green standard. |
