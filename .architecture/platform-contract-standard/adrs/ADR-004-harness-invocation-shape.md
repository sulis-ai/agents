---
id: ADR-004
title: Harness-invocation shape — the architect runs the faithful-generation-harness via execute-workflow and lands the bound-claim table as the contract body
status: accepted
date: 2026-06-02
change: platform-contract-standard
relates-to: [FR-003, FR-006, FR-007, NFR-007, UC-004, UC-005, MUC-007]
---

# ADR-004 — Harness-invocation shape

## Decision

A Platform Contract is produced by the **engineering-architect agent running the
faithful-generation-harness through the brain `execute-workflow` engine**
(`/sulis-brain:execute-workflow`), against the platform's official documentation
as the closed manifest. The harness's committed **claim→source binding table**
**is** the contract body: each binding becomes one claim entry; the harness's
`act-generate-from-bindings` step emits the inline-cited spans; flagged
inferences (spans outside any binding) become `inferred: true` entries.

The contract artifact records a **harness-run reference** (the
`LifecycleRun.run_id` of the dispatch) in its front matter. This reference is the
provenance proof the P-PLAT rubric checks (NFR-007 / MUC-007) — a hand-authored
contract has no run reference and is rejected.

## The step→artifact mapping (locked)

| Harness step | Contract production role |
|---|---|
| `observe-manifest` | The platform's **official docs** are the closed manifest; each manifest entry `{variable_id, meaning, value}` = `{claim-topic, what-the-doc-says, verbatim-quote + URL}`. |
| `orient-select-relevant` | Select the doc sections bearing on this integration's needs. |
| `decide-commit-bindings` | The **claim→source binding table** — the load-bearing artifact. An ungrounded load-bearing claim fires `binding-table-incomplete-or-invalid` → the harness terminal verdict `terminal-manifest-insufficient` → refusal (FR-006). |
| `act-generate-from-bindings` | Generate the contract; every claim carries its citation inline; spans outside a binding flagged `inferred: true` (never falsely cited). |
| `self-critique-grounding` | Re-read each claim against its source's **meaning** (catches `false-citation` + `ungrounded-span` → MUC-002 / MUC-006). |

## Cross-repo dependency (load-bearing)

The harness instance lives in a **sibling repo**
(`plugins/sulis-brain/instances/faithful-generation-harness/`), *not* in this
change's checkout. The standard records this as a **`existing` dependency**: the
architect dispatches the harness where it lives; this change consumes it, does
not build it. The Verification Plan classifies the harness integration `existing`
accordingly. If the harness instance is not resolvable at design time, the gate
emits a BLOCKER naming the missing dependency rather than falling back to
hand-authoring (which would be MUC-007).

## Why

- **Binding-table-as-contract-body is faithful by construction.** The harness's
  whole design property (arXiv 2301.13379, cited in the instance) is that a span
  is causally downstream of its committed binding — remove the binding, the span
  vanishes. Making the binding table *be* the contract inherits that property:
  every claim is auditable to its source by construction, which is exactly
  NFR-001/002/003. Any other shape (e.g. generate prose, then back-fill
  citations) reintroduces the post-hoc-narration failure the harness exists to
  prevent.
- **The run reference is the mechanical anti-MUC-007 control.** Provenance you can
  *check* (a run_id the rubric verifies) beats provenance you assert. This is the
  difference between "the standard says use the harness" (convention) and "the
  rubric rejects a contract with no run reference" (enforcement).
- **`execute-workflow` is the established dispatch path (CP-01).** The marketplace
  already runs brain Workflows this way (critical-thinking, research-synthesis).
  Inventing a bespoke harness-runner would be novelty against an existing
  convention.

## Alternatives considered

- **The architect hand-authors the contract, citing as it goes ("cite-as-you-go").**
  Rejected — this is precisely the failure mode the harness's own provenance
  research rejected: cite-as-you-go improves grounding but does **not** give
  audit-grade attribution, because citations are post-hoc narration not causal
  mechanism. It also reopens every MUC the harness closes (MUC-001/002/006/007).
- **A thin custom script that scrapes docs and emits claim entries.** Rejected:
  duplicates the harness's grounding discipline badly (no meaning-check, no
  refusal path) and creates a second generation mechanism to maintain. The
  harness already exists and is mandated (FR-003).
- **Embed a copy of the harness in this repo.** Rejected: violates
  single-source-of-truth — the harness is owned by the brain plugin and evolves
  there. Cross-repo dispatch with an `existing`-classified dependency is the
  correct boundary; a vendored copy drifts.
