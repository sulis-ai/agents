# Contract-First Integration Standard

> **Sulis-local v0.1.0 (2026-05-26).** The opinionated doctrine for the
> **seam between a producer and a consumer** — most often a backend and a
> frontend, but also any tool↔caller pair. It sits between
> `WP_BACKEND_STANDARD.md` and `WP_FRONTEND_STANDARD.md`: each governs one
> side; this governs the **contract they meet at**. Enables two-speed /
> parallel development — both sides build at once against an agreed contract,
> then integrate.

<!-- summary -->
Cross-kind work (backend + frontend, or tool + caller) defines its
**contract before implementation**. The contract is a **schema layer**
(operations + types + **errors** + LLM-facing descriptions) that is
*transport-agnostic*; the transport (HTTP, MCP, subprocess, library) is a
separate, interchangeable axis. Producer and consumer then build **in
parallel** — both depending only on the contract — with the consumer running
against a **mock generated from the contract** (including error + empty
stubs). Integration swaps mock→real and runs a **contract-conformance
check**. Errors are part of the contract (three universal categories), which
is what makes the consumer's loading/error/empty states contractual rather
than guessed.
<!-- detail -->

## Severity convention

`MUST` — non-negotiable; violations block the change. `SHOULD` — default;
deviation needs a one-line rationale. `MAY` — judgement.

## The model (inlined essentials)

> Full treatment: the plugin-builder **Agent-Consumable SDK Specification
> v0.2.0** (see Provenance). The load-bearing pieces are inlined here so this
> standard stands alone.

**Two axes.** An interface has two independent primitives:

| Axis | Defines | This standard's name |
|------|---------|----------------------|
| **Schema** | What operations exist, their input/output types, their error categories, their descriptions | **the contract** |
| **Transport** | How operations are invoked + how errors/telemetry come back | the **binding** (HTTP / MCP-over-stdio / subprocess+JSON / library) |

The contract is defined once; the transport is chosen separately and is
interchangeable. The same contract can ship over HTTP for a web app and over
MCP for an agent.

**Three error categories** (MECE, transport-agnostic):

| Category | Meaning | Consumer recovery |
|----------|---------|-------------------|
| **Protocol** | The transport failed before the operation ran (network down, process not found, file locked). | Retry-with-backoff if the transport supports it, else escalate. |
| **Expected** | The operation ran and returned a deterministic failure (validation, not-found, conflict, business rule). | Adjust inputs or escalate; retrying unchanged repeats it. |
| **Internal** | The operation crashed unexpectedly (a bug). | Log + escalate; don't retry. |

Each transport maps its native vocabulary onto these three (HTTP statuses;
subprocess exit codes 0/1/2; JSON-RPC/MCP codes; language exceptions).

## Relationship to existing standards (reference, don't restate)

- `WP_BACKEND_STANDARD.md` — the **producer** side. WPB-06 (typed Result) is
  how a backend *emits* the contract's three error categories; WPB-11
  (OpenAPI-first) is how it expresses the schema.
- `WP_FRONTEND_STANDARD.md` (forthcoming) — the **consumer** side. Its
  "in-memory adapter first" *is* the contract mock; its loading/error/empty
  states consume the three error categories.
- `engineering-principles.md` **EP-11 (Service Contract Conformance)** — CF-06
  is its direct application: consumers conform to the contract; adapter logic
  lives caller-side.
- `WORK_PACKAGE_STANDARD.md` — this standard **amends its cross-kind
  decomposition**: cross-kind WPs depend on a contract WP and run in parallel
  (CF-05), rather than the consumer depending on the producer.
- The marketplace's own `wpx-*` / `sulis-change` / `sulis-route` tools are the
  **reference implementation of the subprocess+JSON binding** (exit 0/1/2 +
  `{ok:false,error}` JSON). Contract-first is already how our tooling works.

---

## The requirements

### CF-01 — Contract before implementation (for cross-kind work) · MUST

Any change that spans a producer and a consumer (backend + frontend; tool +
caller) **defines the contract first**, as a **design-time artifact** (SEA,
during `draft-architecture`). No producer or consumer code is written until
the contract is agreed.

> **Anti-pattern:** building the backend, then "designing" the frontend
> against whatever it happened to return; discovering the shape at
> integration time.

### CF-02 — The contract is the schema layer · MUST

The contract specifies: **operations** (named units), **input types**,
**output types**, **error categories** (CF-03), and **LLM-/developer-facing
descriptions**. It is **transport-agnostic**. Express it in the established
schema language for the chosen binding (per `convention-preference-standard.md`):
**OpenAPI 3.1** for HTTP; **JSON Schema** for MCP/subprocess; language-native
types for library.

> **Anti-pattern:** a contract that is just a list of URLs; types defined
> inline per endpoint instead of as named, reusable schemas.

### CF-03 — Errors are part of the contract · MUST

Every operation declares its failure modes mapped to the **three categories**
(Protocol / Expected / Internal), with domain errors extending them. This is
non-negotiable: it is what lets the consumer build real error and empty states
instead of guessing.

> **In practice:** the contract for `getOrder` declares it can return
> `NotFound` (Expected) and `ServerError` (Internal); the frontend renders a
> "not found" empty state and an error state *by contract*.
> **Anti-pattern:** a happy-path-only contract; errors as undocumented free
> strings discovered at runtime.

### CF-04 — Stubs include error + empty cases · MUST

Each operation carries **example request/response pairs as JSON** — and the
examples **MUST include error and empty cases**, not only the happy path.
These stubs feed the consumer's mock.

> **Anti-pattern:** rosy stubs only; the frontend looks finished against the
> mock, then breaks on the first real not-found or empty list.

### CF-05 — Parallel, not sequential · MUST (decomposition)

The producer WP(s) and consumer WP(s) **both depend only on the contract WP**
and run **in parallel**. The consumer builds against a **mock generated from
the contract** — Prism (HTTP), MSW (frontend-side), or recorded NDJSON
(streaming). Neither side waits for the other.

> **In practice:** `WP-contract` (the schema + stubs) → then `WP-backend` and
> `WP-frontend` fire as parallel executors, both `dependsOn: [WP-contract]`.
> **Anti-pattern:** `WP-frontend` `dependsOn: [WP-backend]` — the sequential
> coupling contract-first exists to remove.

### CF-06 — Consumer conforms; adapters live caller-side · MUST

The consumer codes against the contract's typed client, **never around it**
(EP-11). If the contract doesn't fit the consumer's need, **change the
contract** — a design decision, made once, visible to both sides — rather than
forking or hand-massaging responses in the consumer.

> **Anti-pattern:** the frontend reshaping/patching backend responses in an ad
> hoc layer because "the API is almost right"; caller-specific transformation
> leaking into the producer.

### CF-07 — Integration = swap mock→real + conformance check · MUST

A cross-kind change is **not done** until: (1) the mock is swapped for the
real producer, and (2) a **contract-conformance check** passes — the producer
validated against the schema (e.g. Schemathesis/Dredd/Pact), and the
consumer's expectations validated against real responses. This is "done means
wired" (WPB-09) **at the seam**.

> **Anti-pattern:** declaring done when both sides pass against the mock; no
> step that proves the real producer matches the contract the consumer built
> against.

### CF-08 — Explicit, conventional transport binding · SHOULD

Choose the transport per the established binding and map its native errors
onto the three categories: **HTTP/REST** (OpenAPI; statuses), **MCP-over-stdio**
(JSON Schema; the canonical agent-facing local transport), **subprocess +
JSON-on-stdout** (the wpx pattern; exit 0/1/2), **library** (in-process; no
ProtocolError). Don't invent a bespoke transport when a conventional one fits.

When the seam is an **MCP App** (an MCP server returning interactive UI to an AI
client), the binding is the `ui://` resource (`text/html;profile=mcp-app`) + the
**`ui/` JSON-RPC-over-`postMessage`** channel — the UI's actions are MCP tool
calls, so they are contract operations (CF-03 error categories apply). See
[`mcp-ui-surface-patterns.md`](../mcp-ui-surface-patterns.md) for the resource
scheme, CSP allowlist, and sandbox model.

### CF-09 — Streaming contracts use a structured event schema · SHOULD

For streaming operations, the contract is the **event schema** (the set of
event types and their shapes), the consumer receives a **typed stream + a
terminal result**, and the stubs are **recorded event sequences**. Never
scrape an unstructured stream.

> **In practice:** the cockpit's live chat contract is the `stream-json` event
> set (`system` / `assistant` delta / `result`); fixtures are recorded NDJSON;
> the frontend renders against fixtures while the real bridge is built.

### CF-10 — The contract carries operational + founder-facing semantics, not only schemas · SHOULD (MUST for founder-reviewed surfaces)

A schema-only contract (inputs, outputs, errors) is enough for two engineers
to integrate — but it is **unreviewable by the non-technical founder** who has
to greenlight the work, and thinner than a real service needs. So a contract
carries, **per operation**, beyond the schema:

- **auth / permissions** — does it require sign-in, and what permission or
  scope (e.g. `platform.platforms:create`);
- **audience** — who the operation is for (admin / operator vs founder /
  end-user);
- **a plain-language user guide** — what it does in one sentence, when to use
  it, prerequisites, and the natural **next steps** ("leads to");
- **error fixes** — for each error, not just code + message but the *cause*
  and the *fix* (what the user does vs what a developer does).

These are exactly the dimensions the platform's **ServiceSpec**
(`architecture/SERVICE_SPECIFICATION.md`) carries natively — it evolved
because the generic schema-contract was too thin for a real product (the
offspring outgrew this standard; #89). Treat the ServiceSpec as the reference
shape: where a project already produces ServiceSpecs, **that is the contract**;
elsewhere, enrich the contract with these fields. They are what make a contract
**founder-reviewable** (the cockpit contract-preview, #85, renders exactly
these) and what catches gaps — a missing `list` operation behind a list view,
an unflagged auth requirement — *before* anything is built on the contract.

**MUST for any contract a founder reviews** (a user-facing surface); SHOULD
elsewhere. The schema layer (CF-02) + three-category errors (CF-03) remain the
floor; CF-10 is the founder-facing + operational layer on top.

**Concrete deliverable (added 2026-05-30):** the design stage
(`/sulis:draft-architecture`) MUST produce a **ServiceSpec manifest** at
`.architecture/{project}/service-specs/{service-name}.servicespec.yaml`
for every service the design introduces or modifies. The manifest is the
machine-readable contract — operations, errors, entities, bindings,
permissions — that the platform's **service-registration apply pipeline
(SPEC-006)** reads to register the service. Format follows SPEC-006; the
fields above (auth / audience / user-guide / error fixes) live in that
manifest, not in separate prose. Entities are referenced by id from the
marketplace's vendored compiled schemas (`plugins/sulis/brain/compiled/`),
not re-declared. The **Lovable Test** is the completeness bar — an AI
agent must be able to build a working integration against the manifest
with no human docs. Slice 2 (decompose-validation rubric P7) will
mechanically enforce the bar; hold it by hand until then. This is the
third design-stage structured deliverable alongside the visual contract
(#45) and the data contract (#48).

---

## Tiers (scope the rigor to the case)

| Tier | When | What's required |
|------|------|-----------------|
| **Lightweight (internal seam)** | One app, one transport, often one language — e.g. the cockpit's localhost frontend↔backend | CF-01..07: contract (schema + three-category errors + stubs) + a mock + a conformance check. **No** multi-language parity, **no** codegen apparatus. |
| **Full SDK (published / agent-consumable)** | A tool shipped for agents or other teams; multi-language; MCP/HTTP | All of the above **plus** the full Agent-Consumable SDK Specification: Python↔TypeScript parity contract, per-transport bindings, generation pipeline, telemetry, auth. |

Most internal product seams (including the cockpit) are **lightweight**. Reach
for the full-SDK tier only when the contract is a *published product surface*.
Single-kind changes and `--prototype` changes are **exempt** — contract-first
is for genuine producer/consumer seams, not solo work.

---

## How this standard is used (design · implementation · integration)

| Phase | Who | Application |
|-------|-----|-------------|
| **Design** | engineering-architect (`draft-architecture`) | Produces the contract artifact (schema + three-category errors + stubs). Decomposes into a contract WP + parallel producer/consumer WPs (CF-05). |
| **Implementation** | executors (parallel) | Producer implements to the contract; consumer builds against the mock. Each follows its own WP_*_STANDARD. |
| **Integration** | the calling session / `review` | Swaps mock→real, runs the conformance check (CF-07), surfaces drift. |

> **Honest status (v0.1.0):** the doctrine is written; the **wiring** that makes
> `draft-architecture` emit a contract WP and `plan-work` build the parallel
> dependency graph automatically is follow-on work (the same per-kind/seam
> dispatch gap noted for the `kind` enum). Today it is cited explicitly.

---

## Provenance

Synthesised from two reviewed documents (2026-05-26):

- `ae/.claude/agents/api-designer.md` — REST/OpenAPI **API-design** conventions
  (the HTTP-transport view of a contract): resource modelling, status codes,
  cursor pagination, versioning, progressive disclosure. Mobile-/SDK-for-mobile
  scope excluded.
- plugin-builder **`agent-consumable-sdk-spec.md` v0.2.0** (external —
  `repos/plugins/plugins/plugin-builder/references/`) — the **two-axis model**,
  the **three-category error model**, the per-transport bindings (incl. the
  subprocess/wpx binding and MCP), the Python↔TS parity contract, streaming,
  and the generation pipeline. **Cited as the authoritative fuller treatment**
  for the full-SDK tier; its essentials are inlined above so this standard is
  self-contained within the sulis marketplace.

The marketplace's existing `wpx-*` / `sulis-change` / `sulis-route` tools are
the in-repo reference implementation of the subprocess+JSON transport binding.

---

## Version history

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-05-26 | Initial sulis-local definition. 9 requirements (CF-01..CF-09) on the two-axis + three-category-error backbone. Two tiers (lightweight internal seam / full published SDK). Sits between WP_BACKEND and WP_FRONTEND; amends WORK_PACKAGE_STANDARD cross-kind decomposition (parallel via contract dependency — to be reflected there). SHOULD-tier requirements (CF-08/09) carry 90-day calibration. |
