# ADR-003 — Quick vs full why-rooting is one orchestrator, two entry depths

> Change: CH-01KT60 · Status: accepted · Pillar: Form
> Relates: FR-02 (opportunity-first, two intensities), FR-03 (requirement sourced from opportunity)

## Decision

The capture orchestrator (`_brain_capture`) exposes **one** rooting
function with a `why_intensity` parameter — `quick` or `full` — that
controls **how the Opportunity is populated**, not whether it exists. Both
intensities walk why-then-what in one sitting and produce the same shape of
output (a backing chain + an Opportunity + an optional draft Requirement).
The only difference is who fills the Opportunity's `job_statement`:

| Intensity | Who shapes the why | Opportunity lands at |
|---|---|---|
| `quick` | the orchestrator, from the founder's one-line why | `state: hypothesis` |
| `full` | the opportunity-analyst agent (FR-11, ADR-004) | `state: validated` or `defined` |

`quick` is the in-conversation default: the founder drops an idea, gives a
one-line why, the orchestrator emits a `hypothesis` Opportunity and a `draft`
Requirement sourced from it, all in the same call. `full` hands the why to
the analyst agent *first*, then captures the what against the matured
Opportunity.

## Why

FR-02 is emphatic that the why is **mandatory and same-sitting** — "an idea
cannot be captured as a bare requirement with no why," and "either way the
what is captured in the same pass." The two intensities exist so the
discipline doesn't become friction: a mid-conversation idea shouldn't force
a full facilitation, but a real opportunity shouldn't be hollowed out by a
one-line prompt (the SRD's scope-decision rationale).

Modelling this as **one function, two depths** (rather than two separate
capture paths) keeps the invariant in one place: *every* path emits the
Opportunity before the Requirement, and the Requirement's `source` is
*always* the Opportunity's id. The branch is about who authors
`job_statement`, not about whether rooting happens. This is the boring
choice — a single code path with a strategy parameter beats two parallel
paths that must each independently enforce the same rule.

## Alternatives considered

- **Two separate skills (`/sulis:capture` and `/sulis:capture-full`)
  (rejected).** Doubles the surface, duplicates the chain-bootstrap and
  requirement-emission logic, and invites drift where one path enforces the
  why-first rule and the other doesn't. Rejected: duplication of the
  load-bearing invariant.

- **Quick = skip the Opportunity, Full = create it (rejected — violates
  FR-02).** This is the exact failure FR-02 forbids: a bare requirement with
  no why. The Opportunity is mandatory at both intensities; quick just
  populates it thinly. Rejected: breaks the spine principle.

- **Always run the full analyst (rejected — friction).** Forces a
  facilitation conversation for every mid-chat idea. The founder asked for a
  lightweight door (FR-01). Rejected: too heavy for the common case.

- **Branch in the skill prose, not the orchestrator (rejected).** Putting
  the why-first invariant in markdown instructions means it's enforced by
  the agent reading carefully, not by code. The orchestrator is the gate:
  it refuses to emit a Requirement whose `source` doesn't resolve to an
  Opportunity it just wrote. Rejected: invariants belong in code (boring-code
  / explicit-over-inferred).

## Consequences

- `_brain_capture.capture_idea(...)` signature carries `why_intensity:
  Literal["quick","full"]`, `why: str` (the one-liner, quick path),
  `what: str | None` (the requirement statement; None ⇒ Opportunity stands
  alone as hypothesis per FR-03's tail clause), and the resolved
  `opportunity_id` (full path, when the analyst already produced one — see
  ADR-004).
- The **rejection path** is explicit: if `why_intensity == "quick"` and
  `why` is empty/blank, the orchestrator returns `{"ok": false, "error":
  "an idea needs a why before it can be captured"}` and emits nothing
  (FR-02 enforcement, NFR-01 envelope). The skill renders this in plain
  English.
- `quick` Opportunity `job_statement` is the founder's one-line why, cleaned
  to a single line (mirroring `_opportunity_emission`'s flatten). `state:
  hypothesis`. `full` Opportunity is whatever the analyst emitted (ADR-004),
  read back by id.
- The draft Requirement is always emitted via the existing
  `_requirement_emission` shape but **single-idea**, not from-SRD (ADR-005),
  with `source` = the Opportunity id (real, never synthetic).
