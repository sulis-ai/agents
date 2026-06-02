# Scenario authoring source — the open delta

> **Status:** draft / founder-review. **This is a thin delta on an existing
> checkpoint, not a fresh design.** The Scenario entity model is already
> decided in `.architecture/testable-state-done/scenario-entity.md` (#65 mint).
> This doc covers ONLY the piece that checkpoint explicitly deferred (its
> line 106): *the journey-as-Workflow emission, once an n=2 authoring pattern
> exists.* Read the checkpoint first; everything below sits on top of it.
>
> **Confirmed with sulis-brain (2026-06-02)** + verified against the committed
> schemas (Step 1.2.0, Workflow 1.1.0, Scenario 1.0.0, foundation Tool).

## What is already decided (do NOT re-litigate — see the checkpoint)

- `Scenario` **composes** a foundation `Workflow`, which composes IDEF0 `Step`s.
  Zero schema change. (`scenario-entity.md` "Compose, not specialise")
- A `Workflow` is a verification journey **iff** a `Scenario.journey` references
  it; discriminated by `for_process: "verification"` + `type: "review"` (no new
  `Workflow.type` member). (checkpoint "Discriminator")
- Edges: `verifies → Requirement[]`, `exercises → Design`, `journey → Workflow`.
- The asserts are `Step.preconditions`/`postconditions`; inputs/needs are
  `Step.input_artifacts` (with `deferred:<need>` for a missing credential). The
  CI-runnable / manual-tester / founder-legible triple falls out of
  `Step.mechanism` + `agent_instructions` + `mechanism_detail`.

## Tool invocation is modelled, not annotated (the founder's point)

A journey step invokes a **typed `Tool`**, not a free-text driver:

- `Step.tool_ref → Tool` (foundation entity).
- `Tool.implementation_kind` ∈ `{mcp_server, subprocess, python_import,
  http_call, claude_code_tool, skill_invocation, workflow_dispatch}` — **this
  enum IS the invocation contract** (how the step is actually executed), with
  `inputs_schema_ref` / `outputs_schema_ref` typing the call.
- `_scenario_runtime.driver_for_step` already dispatches on exactly this enum.

So the earlier sketch's `(driver: http_call POST /pay)` was an ad-hoc render of
`Step.tool_ref → Tool{ implementation_kind: http_call, inputs_schema_ref: … }`.
Authoring a journey therefore **references Tools** — and tool invocation is a
first-class, typed part of the journey graph. Where a needed Tool entity
doesn't exist yet, it is authored alongside (a Tool is a foundation entity with
its own emitter need) — NOT inlined as prose.

## SIPOC is a reading lens, not a primitive (brain correction)

There is no SIPOC schema. IDEF0/ICOM is the per-Step primitive
(`input_artifacts`=I, `controls`=C, `output_artifacts`=O,
`mechanism`/`tool_ref`=M). SIPOC's Suppliers/Customers are *emergent*:
Inputs = `initial_steps.input_artifacts`; Outputs/Customers =
`terminal_steps.output_artifacts`; Process = the Workflow. Do not author a
SIPOC layer; author the Workflow + Steps and read SIPOC off the graph.

## The authored form (follow the canonical exemplar)

The brain's recommended pattern is **`plugins/sulis/instances/discover-project/
steps.jsonld`** (9 real IDEF0 Steps) + `release-train/steps.jsonld` — NOT a new
markdown mini-language. A verification journey is authored as the same shape:

- a `Workflow` envelope (`for_process: "verification"`, `type: "review"`,
  `steps`/`initial_steps`/`terminal_steps`/`transitions`),
- one IDEF0 `Step` per journey beat, each with `tool_ref` → a typed `Tool`,
  `preconditions`/`postconditions` (the asserts), `input_artifacts` (the needs),
  `mechanism` (deterministic|human|mixed — the CI/manual/founder triple),
- a `Scenario` that `verifies` real Requirement refs, `exercises` a Design ref,
  and points `journey` at the **real** emitted Workflow ULID (no synthetic
  placeholder — Workflow/Step are fully modelled).

> Per-Step note: `Step` sets `unevaluatedProperties: false`; carry per-step
> "phase" inside `mechanism_detail`, mirroring the exemplars, so it validates.

## The genuinely-open work (what to build)

1. **Founder-facing authoring intake.** The `steps.jsonld` shape is the storage
   form, not what a non-technical founder writes. Decide the intake surface that
   *produces* it — most likely `/sulis:specify` drafting the journey from the
   SRD's acceptance criteria, founder-refined — so the founder describes the
   test in plain steps and the Workflow+Steps+Tool refs are generated.
2. **The emitter is a small GRAPH emit, not one entity.** Emitting a Scenario
   means emitting Scenario + its Workflow + its Steps + resolving/creating the
   referenced Tools. `add-entity-emitter Scenario` scaffolds the Scenario slice;
   the Workflow/Step/Tool emitters are the dependency (Tool especially — tool
   invocation can't be a real ref until Tools emit).
3. **Bundle-from-graph.** Point the testable-state engine at the emitted graph
   instead of hand-built bundle JSON (the loop-close the runner anticipates).

## Open question for the founder

- **Intake surface:** is the verification journey authored inside
  `/sulis:specify` (drafted from acceptance criteria, founder-refined), or a
  separate step after design? (Lean: inside specify — a Scenario `verifies`
  Requirements, so it belongs with the requirements conversation.)
