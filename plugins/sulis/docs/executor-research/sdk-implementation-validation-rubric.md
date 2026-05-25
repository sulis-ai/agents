# SDK Implementation Validation Rubric

**Version:** 0.2.0
**Date:** 2026-05-21
**Status:** Retrospective rubric — runnable by an agent to validate a newly
implemented SDK against the three governing specifications
**Audience:** Agents (or humans) validating an SDK implementation after it has
been built

---

## Purpose

When an agent (or a team) implements a new SDK following:

1. [`agent-consumable-sdk-spec.md`](agent-consumable-sdk-spec.md) — the
   universal SDK spec (v0.2.0)
2. [`agent-consumable-sdk-docs-spec.md`](agent-consumable-sdk-docs-spec.md) —
   the documentation companion (v0.1.0)
3. [`integration-change-review-prompt.md`](integration-change-review-prompt.md)
   — the CTS-driven review prompt (v0.1.0)

this rubric checks that the implementation actually complies. It runs
retrospectively — after the SDK is built — and produces a structured
report with pass/fail per check, blocking gaps surfaced, and concrete
remediations.

The rubric is itself CTS-grounded: every check is a falsifiable claim
(FR); confidence per check is recorded (CC); the rubric attempts to break
the SDK (AT) rather than confirm it works (anti-AP-05).

---

## How to use this rubric

The agent runs phases in order. Each phase has 5-15 checks. For every
check, the agent records: PASS / FAIL / N/A / UNVERIFIABLE, with
evidence (file path + line if applicable; concrete observation;
"couldn't determine" with reason).

A phase produces a phase verdict; the overall verdict combines phases.

### Input the agent needs before starting

| Input | Required | Description |
|---|---|---|
| **SDK location** | MUST | Path to the SDK source repo or generated packages |
| **Source-of-truth schema** | MUST | The schema file (OpenAPI, Smithy, Protobuf, …) the SDK was generated from |
| **Codegen configuration** | MUST | The codegen config file (if used) |
| **Generated Python client** | SHOULD | The Python package + tests |
| **Generated TypeScript client** | SHOULD | The TS package + tests |
| **MCP server (if applicable)** | MAY | The MCP server source + tools listing |
| **Docs site / docs source** | MUST | Where the documentation lives |
| **Release artifacts** | SHOULD | Tags, changelog, marketplace.json |

If any MUST input is missing, the agent halts the rubric and reports the
gap rather than guessing.

### Severity convention

| Severity | Meaning | Effect on overall verdict |
|----------|---------|---------------------------|
| **MUST** | Non-negotiable. Spec mandates this. | Any MUST failure → overall FAIL |
| **SHOULD** | Default. Spec recommends; deviation needs justification. | ≥3 SHOULD failures or any deviation without rationale → overall WARN |
| **MAY** | Optional. Spec lists as possible but not required. | No effect on verdict |

### Output the agent produces

A markdown report with the following structure:

```
# SDK Validation Report: {SDK Name}

## Verdict
PASS | WARN | FAIL

## Summary
- Total checks run: N
- PASS: N
- FAIL: N (M MUST, K SHOULD)
- N/A: N
- UNVERIFIABLE: N

## Phase-by-phase results
{table per phase with pass/fail counts}

## Blocking gaps (MUST failures)
{numbered list with check ID + remediation}

## Recommended improvements (SHOULD failures)
{numbered list}

## Unverifiable items
{explicit list of "couldn't determine" with reasons}

## Detailed findings per check
{check-by-check results — only failures and unverifiable surface here;
passes are aggregated in the summary}
```

---

## Methodology

How this rubric was derived (CTS application):

1. **MECE extraction (MECE).** Every MUST and SHOULD requirement from
   the three source specs was extracted and assigned to exactly one
   phase. No requirement appears in two phases. No requirement is
   missing.

2. **Primitive grounding (PG).** Each check is irreducible — it asks
   one question with a binary answer. Compound checks were split.

3. **Falsifiability (FR).** Every check has a fail mode stated
   explicitly. A check that can't fail isn't a check.

4. **Confidence calibration (CC).** Per-check evidence requirements are
   stated. Checks that depend on subjective judgement are labelled.

5. **Honest uncertainty (HU).** The UNVERIFIABLE state is first-class.
   The agent doesn't guess.

6. **Adversarial posture (AT).** The rubric tries to break the SDK —
   intentionally hunts for failure cases (e.g., "what happens on
   timeout?") rather than confirming success.

7. **Anti-patterns** (AP-01..AP-09) addressed:
   - AP-01 Cherry-picking: rubric requires evidence per check
   - AP-05 Confirmation search: phases include "try to break this"
     adversarial checks
   - AP-08 Authority assumption: rubric doesn't trust author claims;
     verifies against artifacts

---

# Rubric

The rubric runs in 12 phases. Phases 1-9 validate the SDK spec.
Phases 10-11 validate the docs spec and integration review.
Phase 12 applies CTS to the implementation overall.

## Phase 1 — Schema layer compliance

**Source:** SDK spec v0.2.0 Parts 1, 2

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **1.01** | MUST | Schema axis and transport axis are kept separate | Source-of-truth schema doesn't conflate transport mechanics with operation definitions | Inspect schema file; transport-specific config lives in codegen config or transport-binding doc, not in the schema |
| **1.02** | MUST | An explicit source-of-truth schema document exists | One file (OpenAPI / Smithy / Protobuf / JSON Schema / etc.) describes every operation | File exists at a discoverable path |
| **1.03** | MUST | Schema language is named and matches the transport | Schema language declared (e.g., "OpenAPI 3.1 for HTTP transport"); choice rationale documented | Codegen config or top of schema file states the choice |
| **1.04** | MUST | Every operation has a unique name | Two operations with the same name → fail | Grep operationIds (or equivalent) for duplicates |
| **1.05** | MUST | Every operation has a description | No empty descriptions | Inspect schema; flag empties |
| **1.06** | MUST | Every operation has an input type and an output type | Both present (even if input is empty `{}`) | Inspect schema |
| **1.07** | MUST | Required fields are explicitly declared | Schema's `required` lists are present where applicable | Inspect schema for omitted `required` arrays |
| **1.08** | SHOULD | Operation descriptions are written for an LLM audience | Lead with intent; list required inputs; name outcomes; mention failure modes; ≤200 words | Sample 3 random operation descriptions; rate against criteria |
| **1.09** | SHOULD | Discriminated unions use `discriminator` | Polymorphic shapes have tagged union pattern with `discriminator` field | Inspect schema for `oneOf` / `anyOf` without `discriminator` |
| **1.10** | SHOULD | Streaming operations are declared as such | If any operation streams, the schema declares it (e.g., via tag, custom extension, or `x-streaming: true`) | Inspect schema for streaming declarations |
| **1.11** | SHOULD | Pagination operations are declared as such | If any operation paginates, the schema declares it | Inspect schema for pagination declarations |
| **1.12** | SHOULD | Auth requirements are declared per operation | Each operation states which auth scheme(s) apply | Inspect schema for `security` or equivalent |
| **1.13** | MUST | Schema is versioned | Schema declares its own version (e.g., `info.version`) | Inspect schema |

---

## Phase 2 — Error model compliance

**Source:** SDK spec v0.2.0 Part 3

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **2.01** | MUST | Three universal categories implemented | `ProtocolError`, `ExpectedError`, `InternalError` exist as classes in both Python and TypeScript | Inspect SDK source for class definitions |
| **2.02** | MUST | Each error has a `category` field with one of three values | Field present; value is `protocol` / `expected` / `internal` | Inspect error class definitions; verify field |
| **2.03** | MUST | Each error has a `message` field | String field; populated on every error instance | Inspect error class definitions |
| **2.04** | MUST | Each error has a `transport_code` field | Field present; populated with the transport's native code (HTTP status, exit code, JSON-RPC error code, etc.) | Inspect class definition; test instantiation |
| **2.05** | MUST | Each error has a `correlation_id` field | Field present; populated with transport-appropriate correlation (e.g., `request-id` header for HTTP, PID + timestamp for subprocess) | Inspect class definition |
| **2.06** | MUST | Each error has a `body` field | Field present; contains the parsed error body | Inspect class definition |
| **2.07** | SHOULD | Each error has a `code` field for domain-specific codes | Field present; nullable | Inspect class definition |
| **2.08** | MUST | Canonical subclasses present per spec | `ConnectionError`, `TimeoutError`, `TransportError` under Protocol; `ValidationError`, `AuthenticationError`, `PermissionError`, `NotFoundError`, `ConflictError`, `RateLimitError`, `BusinessError` under Expected; `ServerError`, `UnexpectedError` under Internal | Inspect class hierarchy |
| **2.09** | MUST | Class names identical in Python and TypeScript | `RateLimitError` exists in both; no per-language renaming | Compare both packages' error exports |
| **2.10** | MUST | Transport-specific errors mapped onto the three categories | The transport binding doc shows the mapping (HTTP statuses → categories; exit codes → categories; etc.) | Inspect transport binding doc; verify the mapping is complete |
| **2.11** | SHOULD | Domain errors extend canonical subclasses | E.g., `IdempotencyKeyMismatchError` extends `ConflictError`, not stands alone | Inspect SDK for any error class that extends `Error` directly without going through the hierarchy |
| **2.12** | MUST | "Successful operation with bad outcome" is NOT raised as an exception | If the SDK has a notion of "operation ran but result is bad" (e.g., wpx blocker), it returns as a typed result, not an exception | Inspect SDK source for the pattern; verify no exception type called `BlockerError` / `FailureError` / etc. that means "operation completed successfully but with negative outcome" |

---

## Phase 3 — Transport binding compliance

**Source:** SDK spec v0.2.0 Part 4

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **3.01** | MUST | At least one transport binding chosen and documented | The implementation states which Part 4.x binding it uses | Transport binding doc; SDK README |
| **3.02** | MUST | Per-transport ProtocolError mapping documented | The doc shows what triggers `ProtocolError` for this transport | Transport binding doc; per-transport section |
| **3.03** | MUST | Per-transport ExpectedError mapping documented | Same | Same |
| **3.04** | MUST | Per-transport InternalError mapping documented | Same | Same |
| **3.05** | MUST | Retry policy is explicit | Doc states "retries enabled" or "retries disabled" with rationale | Inspect transport binding doc |
| **3.06** | MUST | Telemetry vehicle is named | Doc names the telemetry vehicle (headers / stderr / notifications / structured logging) | Same |
| **3.07** | MUST | Authentication scheme is chosen | Doc names how auth is conveyed (Bearer / API key / mTLS / process inheritance / etc.) | Same |
| **3.08** | SHOULD | Streaming approach documented (if applicable) | If any operation streams, the binding doc states how | Same |
| **3.09** | SHOULD | Pagination approach documented (if applicable) | If any operation paginates, the binding doc states how | Same |
| **3.10** | SHOULD | Idempotency mechanism documented | Whether the transport supports idempotency keys, and how | Same |
| **3.11** | MAY | Multiple transport bindings supported | SDK supports more than one transport (e.g., HTTP + MCP) | Inspect SDK for multi-transport code |

---

## Phase 4 — Python client compliance

**Source:** SDK spec v0.2.0 Parts 5, 6

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **4.01** | MUST | Generated Python client exists | Importable Python package | `pip install` + `import` succeeds |
| **4.01a** | MUST | Editable install succeeds in a clean venv | `pip install -e .` (or `-e .[test]` for dev) exits 0 in a fresh virtual environment; package then imports cleanly. Added in rubric v0.2.0 after a real bug (broken `license = { file = "..." }` relative path) was caught only by attempting an editable install in a peer SDK. | `python -m venv /tmp/probe && /tmp/probe/bin/pip install -e <sdk-path>` |
| **4.02** | MUST | Both sync and async clients exported | `MySDK` (sync) and `AsyncMySDK` (async) classes both available | Import test |
| **4.03** | MUST | Pydantic v2 used for JSON-wire response shapes | Response models are Pydantic v2 `BaseModel` subclasses | Inspect generated model files |
| **4.04** | MUST | Snake_case field names preserved from wire (when wire is JSON) | Generated models use `snake_case` field names matching the schema | Inspect 3 random response models |
| **4.05** | MUST | Method names are `snake_case` | Method signatures use `snake_case` | Inspect 3 random method signatures |
| **4.06** | MUST | Class names are `PascalCase` | Class definitions follow convention | Inspect class names |
| **4.07** | MUST | Keyword-only method arguments | All method args after a `*` in signature; no positional-only patterns | Inspect 3 method signatures for `*,` |
| **4.08** | SHOULD | Per-method overrides accepted | `extra_headers`, `extra_query`, `extra_body`, `timeout` available (transport-dependent) | Inspect method signatures for these params |
| **4.09** | SHOULD | Raw response access available | `.with_raw_response.method(...)` available where transport supports it | Inspect SDK for `.with_raw_response` property |
| **4.10** | MUST | Type stubs shipped | `py.typed` marker file present | File system check |
| **4.11** | SHOULD | HTTP client is `httpx` (when transport is HTTP) | Codebase uses `httpx`, not `requests` | Inspect imports |
| **4.12** | MUST | Tests exist for the generated client | At least one test file with assertions on the client behaviour | Inspect tests/ directory |

---

## Phase 5 — TypeScript client compliance

**Source:** SDK spec v0.2.0 Parts 5, 6

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **5.01** | MUST | Generated TypeScript client exists | Installable npm package | `npm install` + `import` succeeds |
| **5.01a** | MUST | Fresh-install succeeds (npm install + build in a clean checkout) | `npm install` + `npm run build` exit 0 against the package's pristine state (no node_modules / dist pre-existing). Added in rubric v0.2.0 as the TypeScript counterpart to 4.01a. | `rm -rf node_modules dist && npm install && npm run build` |
| **5.02** | MUST | Methods return Promises (async-only) | No sync method variants | Inspect TS method signatures |
| **5.03** | MUST | Generated `.d.ts` interfaces for response shapes | Type definitions present | Inspect type definitions |
| **5.04** | MUST | Snake_case field names preserved from wire (when wire is JSON) | Generated interfaces use `snake_case` field names | Inspect 3 random response interfaces |
| **5.05** | MUST | Method names are `camelCase` | Method signatures use `camelCase` | Inspect 3 random methods |
| **5.06** | MUST | Class names are `PascalCase` | Class definitions follow convention | Inspect class names |
| **5.07** | MUST | Resource tree shape identical to Python | `client.messages.create` exists in both languages | Compare resource trees |
| **5.08** | SHOULD | Per-method `options?` parameter accepted | Methods take an optional second arg `options?: RequestOptions` | Inspect method signatures |
| **5.09** | SHOULD | Raw response access available | `.withResponse()` available where transport supports it | Inspect SDK source |
| **5.10** | SHOULD | HTTP via native `fetch` (when transport is HTTP) | No `axios` or similar in dependencies | Inspect package.json |
| **5.11** | MUST | No unnecessary runtime dependencies | Package.json lists minimal deps; no kitchen-sink frameworks | Inspect package.json |
| **5.12** | MUST | Tests exist for the generated client | At least one test file with assertions | Inspect tests/ directory |

---

## Phase 6 — Python ↔ TypeScript parity

**Source:** SDK spec v0.2.0 Part 6

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **6.01** | MUST | Resource tree shape identical | `client.x.y.z()` works the same way in both languages | Compare resource trees |
| **6.02** | MUST | Error class names identical | `RateLimitError`, `ConflictError`, etc. spelled identically in both packages | Compare error exports |
| **6.03** | MUST | Error category enum values identical | The `category` field in both languages has the same string values | Inspect error class definitions |
| **6.04** | MUST | Field case identical for JSON-wire (`snake_case` in both) | TypeScript fields are NOT auto-camelCased when wire is JSON | Inspect 3 corresponding response shapes in both languages |
| **6.05** | SHOULD | Telemetry headers stamped consistently | Same telemetry payload regardless of language | Inspect outbound HTTP requests (or transport equivalent) |
| **6.06** | MUST | Method shapes parallel | A method available in Python is also available in TypeScript with the same input/output types | Spot-check 5 methods across both clients |

---

## Phase 7 — Authentication compliance

**Source:** SDK spec v0.2.0 Part 7

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **7.01** | MUST | Authentication scheme implemented per the transport | The chosen auth scheme (Bearer, API key, mTLS, …) is callable from the SDK | Inspect SDK for auth handling |
| **7.02** | MUST | Auth parameter at client construction | `client = SDK(api_key=...)` or equivalent | Inspect SDK constructor |
| **7.03** | SHOULD | Environment variable fallback | If no auth passed, SDK reads from a conventional env var | Inspect SDK for env-var lookup |
| **7.04** | SHOULD | Auth-related errors map cleanly | 401/403/etc. become `AuthenticationError` / `PermissionError` | Inspect error mapping |
| **7.05** | MUST | Auth secrets not logged | SDK doesn't write auth tokens to stdout/stderr/log files | Inspect logging output / search code for accidental log of credentials |

---

## Phase 8 — Streaming, batching, long-running ops (if applicable)

**Source:** SDK spec v0.2.0 Part 8

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **8.01** | MAY | Streaming primitives implemented | If any operation streams, the SDK exposes a stream object | Inspect SDK for stream classes |
| **8.02** | SHOULD | High-level streaming helper present | Beyond raw event iteration, a context-manager-friendly helper exists | Inspect SDK for `Stream` / `MessageStream` / equivalent |
| **8.03** | MAY | Batching support | If the API has batch endpoints, the SDK exposes them | Inspect SDK |
| **8.04** | MAY | Long-running operation handling | Polling / callback / progress-stream pattern implemented if applicable | Inspect SDK |
| **8.05** | SHOULD | Streaming uses transport-appropriate mechanism | HTTP=SSE; JSON-RPC/MCP=notifications; subprocess=NDJSON; etc. | Inspect implementation |

---

## Phase 9 — Telemetry compliance

**Source:** SDK spec v0.2.0 Part 10

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **9.01** | MUST | Correlation ID per operation | Every operation produces a correlation ID (server-provided or client-generated) | Inspect SDK; trace one operation |
| **9.02** | MUST | Outbound metadata stamped | Per-transport vehicle (HTTP headers / stderr line / structured field) carries client arch, lang, runtime, package version | Inspect outbound message of one operation |
| **9.03** | SHOULD | Inbound metadata captured | Per-transport vehicle carries server-side info; surfaced on errors | Inspect error.correlation_id and error.transport_code |
| **9.04** | SHOULD | Latency measurable | SDK exposes per-call latency (via hook, logging, or return value) | Inspect SDK for timing |
| **9.05** | SHOULD | Audit log produced | A log entry exists per operation (separate from full request logs) | Inspect log output |
| **9.06** | MUST | Errors surface correlation ID | `error.correlation_id` populated and queryable | Inspect error class instances |
| **9.07** | MUST | `retry-count` style metadata stamped on retries | When retries fire, the count is captured in outbound metadata | Test retry path; inspect outbound metadata |

---

## Phase 10 — Documentation compliance

**Source:** docs spec v0.1.0 all parts

### 10.A — Tutorials

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **10.A.01** | MUST | Getting-started tutorial per supported language | `tutorials/python/` and `tutorials/typescript/` (or equivalent) each have a working tutorial | Docs structure |
| **10.A.02** | MUST | Setup tutorial per supported transport | E.g., `tutorials/mcp/with-claude-desktop.md` if MCP is a transport | Docs structure |
| **10.A.03** | SHOULD | Tutorial length ≤15 min | Read-and-follow time | Estimate by length / 200 wpm read speed |
| **10.A.04** | MUST | Tutorial leads to working code | Final state of each tutorial is a runnable example | Try following one |
| **10.A.04a** | MUST | Tutorial actually executes end-to-end from a clean state | Following the tutorial VERBATIM, in a fresh environment (no insider context), produces the documented result without errors. Added in rubric v0.2.0 — the previous 10.A.04 was satisfied by "the snippet looks runnable" but didn't catch broken install commands or assumed-but-not-published packages. | Tutorial-execution transcript or recording |

### 10.B — How-to guides

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **10.B.01** | MUST | "How to handle errors" guide present | A how-to for the canonical error hierarchy with examples | Docs |
| **10.B.02** | MUST | "How to configure the client" guide present | Timeouts, retries, base URL covered | Docs |
| **10.B.03** | SHOULD | "How to authenticate" guide per transport+method | E.g., HTTP Bearer, HTTP OAuth, MCP setup | Docs |
| **10.B.04** | SHOULD | "How to access raw response" guide present | If raw access is supported | Docs |
| **10.B.05** | SHOULD | "How to handle pagination" guide (if applicable) | Iteration pattern shown | Docs |
| **10.B.06** | SHOULD | "How to handle streaming" guide (if applicable) | Per-language streaming example | Docs |
| **10.B.07** | SHOULD | "How to mock for testing" guide present | Pattern shown for testing code that calls the SDK | Docs |
| **10.B.08** | SHOULD | "How to use idempotency keys" guide (if supported) | Pattern shown | Docs |
| **10.B.09** | MUST | Every how-to ends in working code | Snippet at the end is copy-pasteable | Sample one |

### 10.C — Reference

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **10.C.01** | MUST | API reference auto-generated per language | Reference for Python (e.g., via pdoc/Sphinx) and TypeScript (e.g., via TypeDoc) | Inspect reference output |
| **10.C.02** | MUST | MCP tool reference present (if MCP is supported) | Each tool listed with name, description, input/output schemas | Inspect docs OR call `tools/list` |
| **10.C.03** | MUST | Configuration reference present | All client constructor params documented | Docs |
| **10.C.04** | MUST | Error reference present | All canonical + domain error classes documented | Docs |
| **10.C.05** | MUST | Type reference present | All schema types documented | Auto-generated typically |
| **10.C.06** | MUST | Transport binding reference per supported transport | One doc per transport per Part 4 of SDK spec | Docs |
| **10.C.07** | MUST | Reference is auto-generated (not hand-written) | Generated docs exist as part of the release pipeline | Inspect build configuration |

### 10.D — Explanations

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **10.D.01** | MUST | Mental model explanation present | A doc covering the schema/transport split (Part 1 of SDK spec) | Docs |
| **10.D.02** | MUST | Error categories explanation present | A doc covering the three categories | Docs |
| **10.D.03** | SHOULD | Retry strategy explanation present | When and why the SDK retries | Docs |
| **10.D.04** | SHOULD | Field case conventions explanation present | Why snake_case in TypeScript when wire is JSON | Docs |
| **10.D.05** | SHOULD | Async vs sync explanation (Python) | When to use which | Docs |
| **10.D.06** | SHOULD | Versioning policy explanation present | What counts as breaking, deprecation timeline | Docs |
| **10.D.07** | SHOULD | Known quirks / accepted compromises documented | Wart confessions, not silent ones | Docs |

### 10.E — Cross-cutting docs

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **10.E.01** | MUST | Migration notes per release | Each release has documented changes; breaking changes called out | docs/migrations/ |
| **10.E.02** | SHOULD | Troubleshooting section indexed by symptom | At least 3 entries | docs/troubleshooting/ |
| **10.E.03** | SHOULD | Cookbook with at least 2 end-to-end recipes | docs/recipes/ | Docs |
| **10.E.04** | MUST | CHANGELOG.md at repo root | Following Keep a Changelog convention | File exists |

### 10.F — Agent-consumable conventions

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **10.F.01** | MUST | Code blocks are copy-pasteable (full, with imports) | Every example includes imports and setup | Sample 3 random examples |
| **10.F.02** | MUST | Operation reference shows signature with types | Method docs include typed signatures, not just descriptions | Sample 3 reference pages |
| **10.F.03** | MUST | Failure modes documented per operation | Reference for each operation lists what can go wrong | Sample 3 reference pages |
| **10.F.04** | SHOULD | Version visible in every doc | Header on each doc states "Applies to v{X.Y.Z}" | Sample 3 docs |
| **10.F.05** | SHOULD | Examples cover failure cases | Not just happy-path snippets | Sample 3 how-tos |
| **10.F.06** | MUST | Plain-English summary at the top of each doc | First paragraph explains intent | Sample 3 docs |
| **10.F.07** | SHOULD | Docs site has search | Search box / search index | Visit docs site |

### 10.G — Generation discipline

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **10.G.01** | MUST | Reference docs auto-generated from schema | Not hand-written; not drifted | Inspect generation pipeline |
| **10.G.02** | MUST | Docs build is part of release pipeline | Each release publishes docs | CI configuration |
| **10.G.03** | SHOULD | Per-version docs maintained | Old versions still readable | Docs site |

---

## Phase 11 — Integration review compliance

**Source:** integration-change-review-prompt.md

This phase only applies when the SDK is **replacing or modifying** an
existing integration surface. For a brand-new SDK with no prior consumers,
mark all items N/A.

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **11.01** | MUST (if applicable) | Integration review performed | A review artifact exists | Review document or commit referencing the prompt |
| **11.02** | MUST (if applicable) | All affected integrations enumerated (Step 1 of prompt) | List of callers, consumers, shared-state, downstream, docs | Review document |
| **11.03** | MUST (if applicable) | Per-integration impact assessed (Step 2) | Each integration has a documented primitive impact | Review document |
| **11.04** | SHOULD (if applicable) | BI applied: supporting + counter-evidence (Step 3) | Both directions surfaced per integration | Review document |
| **11.05** | SHOULD (if applicable) | SI checked (Step 4) | Echo-chamber risk assessed | Review document |
| **11.06** | MUST (if applicable) | FR criteria stated per recommendation (Step 5) | Each recommendation has "what would change this" | Review document |
| **11.07** | MUST (if applicable) | CC tier per recommendation (Step 6) | VALIDATED / SUPPORTED / EMERGING / UNVALIDATED / CONTRADICTED labels | Review document |
| **11.08** | MUST (if applicable) | AT + HU applied (Step 7) | Failure cases named + uncertainties acknowledged | Review document |
| **11.09** | MUST (if applicable) | Recommended updates in SCQA shape (Step 8) | Per integration: Situation, Complication, Question, Answer | Review document |
| **11.10** | MUST (if applicable) | Anti-pattern self-check ran (Step 9) | All 9 anti-patterns reviewed | Review document |
| **11.11** | MUST (if applicable) | Structured impact report produced (Step 10) | Follows the prompt's output template | Review document |

---

## Phase 12 — CTS overall compliance

**Source:** Critical Thinking Standard applied to the SDK implementation itself

These are meta-checks: did the SDK author follow CTS in building the SDK,
not just claim compliance with the spec?

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **12.01** | MUST | Confidence tier disclosure present | Spec, docs, or release notes state confidence levels per major design choice | Inspect for CC table or per-claim labels |
| **12.02** | MUST | Adversarial Testing pass documented | An AT section exists (in the spec, docs, or PR description) — "where this could fail" | Inspect for AT section |
| **12.03** | MUST | Falsifiability criteria stated | "We will STOP / PIVOT / RE-EVALUATE if…" clauses exist | Inspect for FR section |
| **12.04** | SHOULD | Counter-evidence acknowledged | Documentation includes "what doesn't work" / known limitations | Inspect for HU or limitations section |
| **12.05** | SHOULD | Sources cited per design choice (and they're independent) | The SDK isn't single-vendor; multiple independent sources cited | Inspect spec sources |
| **12.06** | SHOULD | Outside-in reasoning evident | The SDK design starts from "what does an agent need?" not "what does framework X do?" | Inspect spec/README |
| **12.07** | MUST | Pre-mortem documented | "If this fails after 6 months, the most likely reasons are…" | Inspect for pre-mortem |
| **12.08** | SHOULD | Anti-pattern self-check ran | AP-01..AP-09 checked on the design itself | Inspect for AP self-check |
| **12.09** | SHOULD | Vocabulary coherence — package + repo names match what users will look for | A first-time user's natural-language question about the domain doesn't require the SDK or its docs to correct the user's terminology. E.g., if the repo is called `bids` but actually contains adapters, that's incoherent. Added in rubric v0.2.0 after a real user session where the SDK had to spend a full turn explaining "this isn't what the name implies." | Pose 2-3 natural questions a first-time user might ask; verify the docs don't have to redirect terminology |
| **12.10** | SHOULD | Internal-jargon prefixes documented or glossed | If the SDK wraps tools with cryptic-prefix names (e.g., `wpx-*`, `gcr-*`, `lt-*`), the SDK README or first reference doc explains what the prefix means in one sentence. New readers shouldn't have to guess. | Grep the docs for the prefix; verify at least one sentence-level explanation appears near the top of the README or a tutorial |

---

## Scoring

After all phases run:

### Overall verdict

| Verdict | Conditions |
|---|---|
| **PASS** | Zero MUST failures; ≤2 SHOULD failures (each with documented rationale) |
| **WARN** | Zero MUST failures; >2 SHOULD failures OR any SHOULD failure without rationale |
| **FAIL** | Any MUST failure |

### MUST failures are blocking

Every MUST failure must be either:
- Remediated before the SDK is considered compliant
- Explicitly accepted with a documented exception (rare; needs justification beyond convenience)

### SHOULD failures need rationale

A SHOULD that fails without documented rationale → WARN.
A SHOULD that fails with rationale ("we chose Y instead because…") → PASS.

### Unverifiable items

If >10% of checks land in UNVERIFIABLE, the rubric run itself is
insufficient — the agent re-runs with more inputs OR escalates the
gap (e.g., "I couldn't verify Phase 5 because the TypeScript package
isn't published yet").

---

## Worked example

Hypothetical run on a new SDK called `acme-sdk`:

```
# SDK Validation Report: acme-sdk

## Verdict
WARN

## Summary
- Total checks run: 124
- PASS: 109
- FAIL: 7 (0 MUST, 7 SHOULD)
- N/A: 6 (streaming/batching/long-running not applicable)
- UNVERIFIABLE: 2

## Phase-by-phase results
| Phase | PASS | FAIL | N/A | UV |
|---|---|---|---|---|
| 1 Schema layer | 11 | 2 | 0 | 0 |
| 2 Error model | 12 | 0 | 0 | 0 |
| 3 Transport bindings | 9 | 0 | 1 | 1 |
| 4 Python client | 12 | 0 | 0 | 0 |
| 5 TypeScript client | 11 | 1 | 0 | 0 |
| 6 Parity | 6 | 0 | 0 | 0 |
| 7 Authentication | 5 | 0 | 0 | 0 |
| 8 Streaming/batching | 0 | 0 | 5 | 0 |
| 9 Telemetry | 6 | 1 | 0 | 0 |
| 10 Documentation | 30 | 3 | 0 | 0 |
| 11 Integration review | 0 | 0 | 0 | 11 (N/A; no prior surface) |
| 12 CTS overall | 7 | 0 | 0 | 1 |

## Blocking gaps (MUST failures)
None.

## Recommended improvements (SHOULD failures)
1. **1.08 Operation descriptions for LLM audience** — 8 of 22 operation
   descriptions are 1-line summaries with no input/outcome detail.
   Remediation: Rewrite per the description-as-LLM-prompt rule.
2. **1.09 Discriminator on polymorphic types** — 3 oneOf schemas
   lack discriminators. Remediation: Add `discriminator` to each.
3. **5.10 Native fetch in TypeScript** — Package uses axios.
   Remediation: Swap to native fetch.
4. **9.05 Audit log per operation** — No separate audit log; relies
   on application-level logging. Remediation: Emit one structured
   log line per operation completion.
5. **10.B.07 "How to mock for testing" guide** — Missing. Remediation:
   Author a how-to with a working mock example for Python and TS.
6. **10.D.07 Known quirks documented** — No quirks doc. Remediation:
   Author an explanation doc.
7. **10.F.05 Examples covering failure cases** — Most how-tos show
   only success. Remediation: Add a failure-case example to each
   how-to.

## Unverifiable items
1. **3.11 Multi-transport support** — Only HTTP binding documented;
   couldn't determine if multi-transport is on the roadmap.
2. **12.08 Anti-pattern self-check** — No documented AP self-check
   found, but the spec quality suggests one was done informally.
   Recommend documenting.
```

---

## Anti-patterns when running this rubric

Things the agent should AVOID when applying the rubric:

| Anti-pattern | What it looks like | Correct approach |
|---|---|---|
| **Rubber-stamping** | Marking PASS without inspecting evidence | For every PASS, the agent records what artifact was inspected and what evidence supported the pass |
| **Cherry-picking** | Sampling only obvious-pass operations and skipping the rest | Sample at least 3 random items per "sample X" check; document which ones |
| **Confirmation search (AP-05)** | Looking only for evidence the SDK is compliant | Each phase includes adversarial probes — "where could this fail?" |
| **Authority assumption (AP-08)** | "The author says X is implemented" treated as evidence | Trust the artifact, not the claim. Inspect the code/doc/test, not the README assertion |
| **Premature rejection (AP-04)** | Marking FAIL when the SDK has a defensible deviation | If the spec says SHOULD and the SDK does Y with rationale, mark PASS-WITH-RATIONALE |
| **Volume conflation (AP-07)** | "Tests exist" without checking quality | "Tests exist AND ≥1 test per public method" |
| **Over-decomposition (AP-09)** | Splitting a check into 5 sub-checks that all converge on one decision | Keep checks at the level where they change the verdict |

---

## When to re-run the rubric

The rubric runs:

1. **On SDK first release** (the typical retrospective)
2. **On SDK major version bump** — to validate that v2 still complies
3. **Quarterly** — for SDKs in active calibration
4. **When a referenced spec is updated** — if the SDK spec, docs spec, or
   integration-review prompt updates, re-run to verify continued compliance
5. **When the integration-review prompt flags drift** — the integration
   review surfaces issues that prompt a fuller compliance check

---

## Calibration

This rubric is in calibration. Falsification criteria (FR):

- **STOP applying** if, after running on 3 SDKs, the rubric produces
  more false positives (PASS when there are real problems) than false
  negatives (FAIL when the SDK is fine). The rubric's failing in the
  wrong direction.
- **PIVOT** if a phase consistently produces UNVERIFIABLE results — the
  check criteria are too vague.
- **RE-EVALUATE** if a new convention emerges that supersedes any of
  the source specs (e.g., a published industry standard for agent SDKs).

---

## Sources

### Specs validated by this rubric
- [`agent-consumable-sdk-spec.md`](agent-consumable-sdk-spec.md) (v0.2.0)
- [`agent-consumable-sdk-docs-spec.md`](agent-consumable-sdk-docs-spec.md) (v0.1.0)
- [`integration-change-review-prompt.md`](integration-change-review-prompt.md) (v0.1.0)

### Methodology source
- [`platform/methodology/standards/CRITICAL_THINKING_STANDARD.md`](../../../../platform/methodology/standards/CRITICAL_THINKING_STANDARD.md)
  — all 13 principles + AP-01..AP-09 anti-patterns

### Related marketplace standards
- [`plugins/srd/references/convention-preference-standard.md`](../../../srd/references/convention-preference-standard.md) — CP-01
- [`plugins/sea/references/code-review-standard.md`](../../../sea/references/code-review-standard.md) — CR-01..CR-09 (related: per-PR review; this rubric is per-SDK retrospective)

---

## Version history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-21 | Initial rubric. 12 phases. ~124 checks. Severity convention (MUST/SHOULD/MAY). Output template. Worked example. Anti-patterns for the rubric run itself. Falsifiability criteria. |
| 0.2.0 | 2026-05-21 | Added 5 checks (4.01a editable install probe; 5.01a TS fresh-install probe; 10.A.04a tutorial-executes-from-clean-state; 12.09 vocabulary coherence; 12.10 internal-jargon prefixes glossed). Each surfaced from a real adapter-test session where a peer SDK (following the v0.1.0 rubric) passed validation but then broke for a first-time user: a broken relative `license = { file = ... }` path made `pip install -e .` fail (caught by 4.01a); tutorials assumed PyPI-published packages that hadn't shipped yet (caught by 10.A.04a); repo name implied one thing but contained another (caught by 12.09); cryptic prefix `wpx-*` / `gtr-*` etc. left readers guessing (caught by 12.10). |
