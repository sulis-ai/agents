---
id: ADR-003
title: Tool minting fidelity — fully populate primaries; stub the rest under Path A
status: accepted
date: 2026-06-01
deciders: [iain]
---

## Context

The release-train Workflow references ~17 Tools (per SRD FR-005):
`gh-pr-create`, `gh-pr-checks-watch`, `gh-pr-mergeability`,
`gh-pr-merge`, `gh-release-create`, `git-tag`, `git-push-tag`,
`git-commit`, `git-compare-branch-versions`, `update-version-file`,
`prepend-changelog`, `_changeset.read_changesets`,
`_changeset.compare_version_files`, `_changeset.cumulative_tier`,
`_changeset.next_version`, `_changeset.summarise`,
`sulis-emit-release`.

Under Path A (ADR-001), Tools are **documentation entities** — they
describe what the imperative bash does, formalising the contract.
They are NOT invoked at runtime by the imperative path. The three
uses of Tool instances under Path A:

1. Drift detector validates each Step's `tool_ref` resolves to a real
   Tool instance + (optionally) checks Tool inputs/outputs schema
   against the YAML's actual call shape.
2. Dry-run preview reads Tools when the LLM walks the canonical via
   `execute-workflow`.
3. Path C (future deterministic runner) would call them directly.

The question: at what fidelity do we author each Tool?

- **Stub all** — minimal fields per Tool (id, name, for_domain, kind,
  inputs_schema_ref + outputs_schema_ref both pointing at a `none://`
  placeholder, implementation_kind, version, state). 1-2 lines each.
- **Fully populate all** — every Tool gets a complete JSON Schema for
  inputs + outputs, populated `implementation_detail`, full
  error_catalogue. ~30-50 lines per Tool × 17 = ~700 lines.
- **Hybrid — fully populate primaries; stub rest.** The ~5 Tools
  load-bearing for the release-train get full schemas + details; the
  rest are stubbed.

Lessons that bear on the call: **L13 — don't abstract on n=1.** We
have one consumer (the marketplace itself). Over-investing in Tool
detail before n=2 evidence is the canonical anti-pattern.

## Decision

**Hybrid — fully populate primary Tools; stub the rest.**

**Primary Tools (~5, fully populated with inputs/outputs schemas +
implementation_detail + error_catalogue):**

- `_changeset.cumulative_tier` — the version-math entry point; behaviour
  is type-critical (input: list of changeset dicts; output: enum tier).
  Tested by the drift detector's input/output schema checks.
- `_changeset.next_version` — same; semver math.
- `gh-pr-create` — the most-used GitHub seam.
- `git-tag` + `git-push-tag` — the version-bump artifact.
- `gh-release-create` — the release-artifact publish.

**Stubbed Tools (~12, minimal fields with `state: draft`):**

All other Tools — they're real (the imperative bash uses them) but
their formal contracts are deferred until Path C or until a drift-
detector check surfaces a specific need.

Stub shape:

```jsonld
{
  "id": "dna:tool:01XXXX...",
  "name": "git-commit",
  "for_domain": "dna:tenant:01JA0AAA...",
  "kind": "side-effect",
  "inputs_schema_ref": "none://stub-pending-path-c",
  "outputs_schema_ref": "none://stub-pending-path-c",
  "implementation_kind": "subprocess",
  "implementation_detail": "{\"command\": \"git\", \"args\": [\"commit\"], \"env_keys\": []}",
  "version": "0.0.1",
  "state": "draft",
  "sys_status": "active"
}
```

The drift detector treats `state: draft` Tools as schema-validation-
exempt — it still asserts every Step's `tool_ref` resolves, but it
doesn't validate the YAML's actual call shape against the Tool's
input/output schemas.

## Options Considered

- **Hybrid — primaries fully populated, rest stubbed (CHOSEN).** Best
  cost/value: the Tools that benefit most from schema validation get
  it; the rest are recorded as references without over-investment.
  Each stub is a hook for future enrichment when Path C lands or a
  specific drift case demands it.
- **Stub all** — rejected. The drift detector loses validation surface
  on the primaries — exactly the Tools where wrong inputs would cause
  silent release-bumping bugs. The `_changeset.next_version` Tool in
  particular needs schema validation; if its inputs change shape, the
  imperative path will produce wrong versions silently.
- **Fully populate all** — rejected per L13 (n=1; ~700 lines of Tool
  authoring for marginal v1 value). Future Tool consumers (env-init,
  deploy) will pull through what they need; we'll lift Tool detail at
  that point.

## Consequences

- **Positive:** Discipline matches the value. Primary Tools get
  formal contracts that the drift detector enforces. Stubbed Tools
  document the surface without over-investment. L13 honoured.
- **Negative:** Two-class Tool catalogue (primary vs stub) requires
  the drift detector to distinguish (via `state` field). Adds one
  conditional in the drift-matcher. Risk that "primary" creeps
  (operator promotes stubs to primary opportunistically without
  measuring need). Mitigated by: any promotion requires a code-path
  drift detector check be added, which makes the cost visible.
- **Neutral:** Path C's future runner can consume both primary +
  stub Tools the same way (it dispatches by `implementation_detail`
  regardless of how complete the schemas are; full schemas just give
  it more validation surface).
