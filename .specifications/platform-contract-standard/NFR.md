# Non-Functional Requirements — Platform Contract Standard

Every NFR is measurable. The Platform Contract's whole value is that its
qualities (grounded, honest, reviewable, probed) are *checkable*, not asserted.

## NFR-001 — Source-bound

**Requirement:** Every non-inferred claim in a Platform Contract cites an official
source with a retrieval date and a verbatim quote.
**Measurable target:** Zero claim entries with `inferred: false` and an empty
`source`, `quote`, or `retrieval-date`. Checked by the `contract` conformance
adapter and rubric P-PLAT.
**Relates to:** FR-004, FR-005; MUC-001.

## NFR-002 — Honest inference

**Requirement:** Inferences and connective text are flagged, never stated as
documented platform fact.
**Measurable target:** Every span not expanded from a committed binding carries
`inferred: true` / unattributed flag; zero false citations (a citation to a source
that does not support the span). Checked by the harness
`self-critique-grounding` `false-citation-detected` output.
**Relates to:** FR-005; MUC-006.

## NFR-003 — Reviewable by a non-platform-expert

**Requirement:** A reviewer who is not an expert on the platform can verify every
claim by following its citation to the source and comparing against the verbatim
quote.
**Measurable target:** 100% of claim source URLs resolve; each quote is locatable
at its source; the contract's prose meets the founder-facing readability baseline
(Flesch-Kincaid Grade Level ≤ 10 for the plain-language summary of each rule).
Checked by the `documentation` adapter (link-resolution + readability).
**Relates to:** FR-004; the founder framing ("reviewable and a critical part of
the process").

## NFR-004 — Load-bearing claims probed

**Requirement:** Every claim the integration design depends on carries an empirical
probe result with evidence the exercise ran.
**Measurable target:** Zero load-bearing claims without a populated `probe-result`,
**unless** carrying an explicit, justified deferral with a canonical need
identifier. A bare `probe-result: confirmed` without evidence is rejected.
**Relates to:** FR-008; MUC-005.

## NFR-005 — Backward compatibility (grandfathering)

**Requirement:** Existing integrations are grandfathered; only new third-party
touches are gated.
**Measurable target:** A change whose `started_at` in `.changes/{slug}.yaml`
precedes the standard's merge date passes design and the rubric P-PLAT phase
without a Platform Contract. A change whose `started_at` postdates the merge and
touches a gated platform is gated regardless of which files it edits. (Mirrors the
ADR-006 grandfather mechanism used by P-VER.)
**Relates to:** FR-002, FR-015.

## NFR-006 — Durable and reused (with freshness)

**Requirement:** Platform Contracts persist and are reused across changes, not
regenerated per change; each claim's retrieval date enables staleness detection.
**Measurable target:** A second change touching a covered platform produces zero
new *full* harness runs (only incremental runs for genuinely new uncovered
claims); reused claims past the staleness threshold are flagged before reuse.
**Relates to:** FR-010, FR-011, FR-013; MUC-003.

## NFR-007 — Mechanism integrity (harness-produced)

**Requirement:** A Platform Contract is produced by the faithful-generation-harness,
recorded as such; a hand-authored substitute is not a Platform Contract.
**Measurable target:** Every Platform Contract carries a harness-run reference; the
rubric P-PLAT rejects a contract with no harness provenance.
**Relates to:** FR-003; MUC-007.

## NFR-008 — Gate scope correctness

**Requirement:** The gate fires for write/deploy third-party touches (hard) and
recommends a lightweight contract for read-only touches (soft) — and the boundary
is reviewed explicitly, not decided silently.
**Measurable target:** The gate logic distinguishes the two touch classes; the
write/deploy-vs-read-only default is surfaced for confirmation at standard-authoring
(not buried). Pre-mortem reason 3.
**Relates to:** FR-014; Open Question 3.
