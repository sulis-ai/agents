# Misuse Cases — Platform Contract Standard

The Platform Contract exists to prevent fabricated or drifted claims about a
third-party platform from passing a gate. The misuse cases are therefore the ways
a contract could *look* sound while being unsound — the failure class the
triggering incident belongs to. Each maps to a negative requirement (`NR-n` in
SRD.md) and to a harness failure mode where one applies.

| Field key |
|---|
| **Abusive actor** — who (or what) produces the failure (rarely malicious; usually an agent or author taking the cheap path) |
| **Targets** — the use cases / assets attacked |
| **Misuse flow** — how it proceeds |
| **System response (REQUIRED)** — the negative requirement the system MUST enforce |

---

## MUC-001 — Contract with uncited claims (fabricated platform behaviour)

- **Abusive actor:** an authoring agent under time pressure, or a model
  hallucinating plausible platform behaviour.
- **Targets:** UC-003, UC-005; NR-1. The integrity of every downstream design that
  trusts the contract.
- **Misuse flow:** the contract asserts "GitHub Actions does X" with no source.
  It reads as authoritative. A design builds on X. X is false (the
  reusable-workflow incident, exactly).
- **System response (REQUIRED):** the harness MUST NOT bind a claim to a
  non-existent source; an ungrounded load-bearing claim MUST fire
  `manifest-insufficient` and be recorded as a flagged assumption requiring a
  probe — never asserted as documented fact. The rubric MUST reject a contract
  containing a `inferred: false` claim with an empty `source`/`quote`.
- **Related harness failure mode:** `binding-table-incomplete-or-invalid`.
- **Related NFR:** NFR-001 (source-bound), NFR-002 (honest inference).

---

## MUC-002 — Contract that paraphrases the docs wrongly (meaning-drift)

- **Abusive actor:** an authoring agent that cites a real source but states a
  claim the source does not actually support (plausible by shape, wrong by
  meaning).
- **Targets:** UC-003, UC-004; NR-3. Worse than MUC-001 because the citation lends
  false authority.
- **Misuse flow:** the contract cites a real GitHub docs page, but the paraphrase
  shifts meaning ("`GITHUB_TOKEN` events never trigger any workflow" vs. the actual
  "do not trigger a *new* workflow run of the same kind"). A reviewer checking the
  URL exists sees a real link and trusts it.
- **System response (REQUIRED):** the harness `self-critique-grounding` step MUST
  re-read each claim against its source's **meaning** (not value-shape) and flag
  the drift; the system MUST NOT treat a plausible-by-shape claim as grounded
  without the meaning-check. The verbatim quote field (FR-004) MUST be present so a
  reviewer compares the claim against the quote, not just the URL.
- **Related harness failure mode:** `ungrounded-span`, `false-citation`.
- **Related NFR:** NFR-003 (reviewable — the quote makes drift checkable).

---

## MUC-003 — Stale contract (platform changed since retrieval)

- **Abusive actor:** time (no malice) — the platform changed its behaviour after
  the contract's claims were retrieved.
- **Targets:** UC-002; NR-4. Any later change reusing the contract.
- **Misuse flow:** a contract written months ago is reused. GitHub changed the
  behaviour (e.g. a new default). The reused claim is now false but carries an old,
  valid-looking citation.
- **System response (REQUIRED):** every claim MUST carry a `retrieval-date`; the
  reuse path MUST surface claims older than the staleness threshold for
  re-grounding; the system MUST NOT silently reuse a stale claim past threshold.
  (Automated re-probe is deferred — the date + manual flag ship now per FR-013.)
- **Related NFR:** NFR-006 (durable + reused, with freshness).

---

## MUC-004 — Gate bypassed via skill-prose edit

- **Abusive actor:** an author who edits the design skill prose to skip the
  Platform Contract check (to "move faster").
- **Targets:** UC-001; NR-2. The gate itself.
- **Misuse flow:** the design-phase gate (FR-002) is wired in skill prose; an edit
  removes or weakens it; an integration design proceeds with no contract; the
  reusable-workflow class of defect returns.
- **System response (REQUIRED):** the gate MUST be enforced by the
  **decompose-validation-rubric (P-PLAT, FR-015)** as a mechanical phase — not only
  by skill prose — so that a WP set touching a gated third party without a
  referenced contract fails the rubric regardless of prose edits. Defence in depth:
  prose asks; the rubric enforces.
- **Related NFR:** NFR-005 (the gate is the backward-compat boundary — new touches
  gated, old grandfathered).

---

## MUC-005 — A "probe" that's faked rather than really run

- **Abusive actor:** an authoring agent that records `probe-result: confirmed`
  without executing the sandbox exercise.
- **Targets:** UC-004; NR-5. The probe mechanism's integrity — the empirical leg of
  a load-bearing claim.
- **Misuse flow:** a load-bearing claim is marked probed-and-confirmed, but no real
  exercise ran. The claim looks doubly grounded (cited + probed) while being only
  asserted.
- **System response (REQUIRED):** a probe-result MUST carry evidence the exercise
  actually ran (a scratch-repo run reference, a captured output, a log) — the
  system MUST NOT accept a bare `confirmed` without evidence. The probe mechanism
  (SEA, Open Q4) MUST produce a verifiable artifact. The grounding-check theatre
  failure mode is the harness analogue.
- **Related harness failure mode:** `grounding-check-theatre`.
- **Related NFR:** NFR-004 (load-bearing claims probed — with evidence).

---

## MUC-006 — An inference silently promoted to documented-fact

- **Abusive actor:** an authoring agent that drops the `inferred: true` flag so a
  connective inference reads as a cited fact.
- **Targets:** UC-003; NR-6. The honest-inference boundary.
- **Misuse flow:** the contract contains a reasonable inference ("therefore the
  auto-merge should use a PAT not `GITHUB_TOKEN`"). The flag is dropped; it reads as
  a documented platform rule rather than our reasoning.
- **System response (REQUIRED):** the harness `act-generate-from-bindings` step MUST
  flag every span not expanded from a committed binding as unattributed; the system
  MUST NOT present an inferred span as documented fact. Inferences are legitimate —
  they MUST just be visibly labelled as ours, not the platform's.
- **Related harness failure mode:** `false-citation` (the worst failure: false
  provenance).
- **Related NFR:** NFR-002 (honest inference).

---

## MUC-007 — The harness skipped, a hand-waved doc substituted

- **Abusive actor:** an author who writes a Platform Contract by hand "because it's
  faster" and skips the faithful-generation-harness.
- **Targets:** UC-005, FR-003; NR-7. The mandated mechanism.
- **Misuse flow:** a hand-authored contract has no binding table, no committed
  claim→source bindings, no `self-critique-grounding` re-read. It may contain all
  the MUC-001/002/006 defects with none of the controls that catch them.
- **System response (REQUIRED):** the standard MUST require the contract be
  harness-produced (FR-003); the contract artifact MUST record a harness-run
  reference; the rubric P-PLAT check MUST reject a contract with no harness-run
  provenance. A hand-waved doc is not a Platform Contract.
- **Related NFR:** NFR-001..004 (the harness is how all four are mechanically
  enforced rather than convention-only).

---

## Pre-mortem

> Assume the Platform Contract Standard has been live for six months and has just
> failed badly. The top-3 most likely reasons:

1. **A contract drifted stale and no one noticed (MUC-003).** The biggest live
   risk, because freshness automation is deferred. Mitigation shipped: retrieval
   dates + manual flag. Residual: needs the deferred
   `platform-contract-staleness-reprobe` follow-on. → flagged as deferred
   infrastructure need in the Verification Plan.
2. **A probe was deferred-then-forgotten for a load-bearing claim, and the
   un-probed claim was wrong (MUC-005-adjacent).** The branch-protection probe is
   already deferred (needs a paid private repo). Mitigation: load-bearing claims
   without a probe-result MUST carry a justified deferral with a canonical need
   identifier, so the gap is tracked, not silent.
3. **The gate was correct but too narrow — a read-only integration that turned out
   to write caused an incident (Open Q3 / FR-014).** Mitigation: FR-014's
   write/deploy-vs-read-only split is a *proposed default* surfaced for confirmation
   at standard-authoring, not a silent decision — so the boundary is reviewed
   explicitly.
