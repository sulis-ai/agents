---
id: PLATFORM_CONTRACT_STANDARD
version: 0.1.0
status: active
severity-convention: see "Severity convention" below (per repo CLAUDE.md)
---

# Platform Contract Standard — The Contract With the Platform We Don't Control

> **Sulis-local v0.1.0 (2026-06-02).** The design-time **contract with a
> third-party platform** — a faithful capture of how a platform we do **not**
> control actually behaves at the seam our integration depends on. It is the
> fourth member of the design-stage contract family, alongside the data
> contract (`CONTRACT_FIRST_STANDARD.md`), the visual contract
> (`UX_VISUAL_DESIGN_STANDARD.md`), and the service contract
> (`architecture/SERVICE_SPECIFICATION.md`). Where those three capture
> decisions **we** make, the Platform Contract captures a reality **the
> platform** imposes — so its discipline is *faithful grounding*, not design.

<!-- summary -->
When a change integrates a third-party platform (GitHub Actions, Stripe, an
AWS service), the design phase produces a **Platform Contract**: a durable,
reviewable capture of the platform constraints the integration depends on.
Each constraint is a **claim entry** — a single statement bound to an official
documentation source, quoted verbatim, dated, with inferences honestly
flagged and load-bearing claims empirically probed. The contract is **produced
by running the faithful-generation-harness** (not hand-authored), so every
claim is grounded by construction or the harness refuses. The gate **fires
hard** for write/deploy integrations and **soft-recommends** for read-only
ones. Contracts live in `plugins/sulis/references/platform-contracts/` and are
**reused, not regenerated** — a retrieval-date stamp surfaces claims older
than 180 days for re-grounding. The whole point: a non-platform-expert can
click every citation and check it.
<!-- detail -->

## Severity convention

`MUST` — non-negotiable; violations block the change. `SHOULD` — default;
deviation needs a one-line rationale. `MAY` — judgement.

## The model — the seam we don't control

A Platform Contract is a **faithful capture of a third-party platform's
behaviour at a seam we do not control**. That last clause is the whole
distinction. Our own code, our own API, our own UI — we decide how those
behave, and the data / visual / service contracts record those decisions. A
third-party platform decides how *it* behaves; we can only observe, ground,
and probe. So a Platform Contract is not a design artifact we author from
intent — it is an evidence artifact we **derive from the platform's own
documentation and from probing the platform's real behaviour**.

> **The triggering incident (#137).** A reusable GitHub Actions workflow was
> placed where the integration design assumed it would resolve. GitHub
> Actions only resolves `uses:` references to reusable workflows under
> `.github/workflows/`. The assumption was never grounded against GitHub's
> documentation, so the flaw surfaced at the first real release — a
> half-applied production deploy. A Platform Contract for GitHub Actions, with
> the reusable-workflow-location rule cited to GitHub's docs and probed in a
> scratch repo, would have caught it at design time. The verification-by-design
> sibling (#138) is what consumes a contract's constraints downstream.

## Relationship to existing standards (FR-016) · MUST

The Platform Contract is the fourth design-stage contract. The family:

| | Data contract | Visual contract | Service contract | **Platform contract (this)** |
|---|---|---|---|---|
| Standard | `CONTRACT_FIRST_STANDARD.md` | `UX_VISUAL_DESIGN_STANDARD.md` | `architecture/SERVICE_SPECIFICATION.md` | this one |
| Between | producer ↔ consumer (machines) | product ↔ user (human) | a service ↔ its callers | **us ↔ a platform we don't control** |
| Captures | a decision we make | a decision we make | a decision we make | **a reality the platform imposes** |
| Discipline | agree the schema first | agree the design first | declare the service first | **ground every claim faithfully** |

> **The distinguishing axis (MUST).** The first three contracts record
> decisions **we** are free to make and revise. The Platform Contract records
> facts **the platform** has already decided — so it cannot be "designed", only
> faithfully captured. Change the data contract and the system changes; get the
> Platform Contract wrong and the system breaks against a reality that does not
> care what we wrote. That is why grounding, not intent, is the discipline.

This standard **references** rather than restates: the faithful-generation
-harness's grounding theory (its five steps, its failure modes, its terminal
verdicts) is pointed at, not re-derived; P-VER's grandfather mechanism and
verdict semantics are cited, not copied.

---

## The claim-entry schema (FR-004) · MUST

Each platform constraint in a Platform Contract is a **structured claim entry**.
This is the canonical identifier every downstream artifact conforms to — the
storage convention (ADR-002), the conformance check (the `contract` adapter),
the GitHub Actions instance, and the P-PLAT rubric phase all point **here** for
the schema definition. It is defined **once**, in this standard:

```yaml
- claim: "<one statement about the platform's behaviour or constraint>"
  source: "<official-doc URL>"            # required iff inferred:false
  retrieval-date: "<ISO-8601>"            # required iff inferred:false
  quote: "<verbatim span from the source>" # required iff inferred:false
  inferred: false                          # true ⇒ a flagged inference (ours, not the platform's): no source/quote/retrieval-date
  load_bearing: true                       # the integration design depends on this claim
  probe: "<the sandbox exercise, if load_bearing>"
  probe-result: "confirmed | refuted | deferred:<canonical-need-id>"
  probe-evidence: "<reference to the artifact proving the exercise ran>"  # required iff probe-result:confirmed
```

**Conformance invariants** (the `contract` adapter checks these):

- `inferred: false` ⇒ non-empty `source` + `quote` + `retrieval-date`.
- `inferred: true` ⇒ **no** `source` (no fabricated citation).
- `load_bearing: true` ⇒ `probe` + `probe-result` present (or
  `probe-result: deferred:<id>`).
- `probe-result: confirmed` ⇒ non-empty `probe-evidence`.

> **Why `quote`, not just `source` (NFR-003).** A real URL proves the source
> *exists*; it does not prove the source *supports the claim*. The verbatim
> `quote` is what makes the difference reviewer-checkable — a non-expert can
> open the URL, find the quoted span, and confirm the claim says what the
> source says. "Source exists vs source supports the claim" is the gap the
> quote field closes (GLOSSARY).

---

## The requirements

The eight requirements below are one-to-one with the Armor controls A-1..A-8
(TDD Armor pillar) — each closes a named misuse case (MUC) and a non-functional
requirement (NFR). Each carries a **plain-language summary** a non-platform
-expert can read.

### PC-01 — No uncited factual claim · MUST

> **Plain language:** every fact about the platform must link to where the
> platform's own docs say it.

A claim with `inferred: false` MUST carry a non-empty `source`, `quote`, and
`retrieval-date`. A factual claim with no citation is not allowed to ship.
*(Closes MUC-001 / NFR-001. Enforced by the `contract` adapter + P-PLAT.
Schema invariant above.)*

### PC-02 — Refusal on an ungrounded load-bearing claim · MUST

> **Plain language:** if a make-or-break claim can't be grounded, the tool
> stops and says so — it never guesses.

When a load-bearing claim cannot be bound to a source, the harness fires
`binding-table-incomplete-or-invalid` and reaches the terminal verdict
`terminal-manifest-insufficient` — a **refusal**. The claim is recorded as a
flagged assumption requiring a probe; it is **never** asserted as fact.
*(Closes MUC-001 / FR-006. Enforced by the harness step `decide-commit-bindings`;
see ADR-004.)*

### PC-03 — Meaning-check, not shape-check · MUST

> **Plain language:** we re-read each claim against what the source actually
> means, not just whether a link is present.

Each claim MUST be re-read against the **meaning** of its source, not merely
the presence of a citation. The verbatim `quote` field is what makes a drift
between claim and source visible to a reviewer.
*(Closes MUC-002 / NFR-003, FR-007. Enforced by the harness step
`self-critique-grounding` + the human reviewer.)*

### PC-04 — Honest inference · MUST

> **Plain language:** anything we worked out ourselves is labelled as ours —
> never dressed up as a platform fact.

Every span that is not backed by a committed source binding MUST be flagged
`inferred: true` and MUST carry **no** `source` (an inference with a fabricated
citation is the failure this closes).
*(Closes MUC-006 / NFR-002. Enforced by the harness step
`act-generate-from-bindings` + the `contract` adapter.)*

### PC-05 — Freshness · MUST

> **Plain language:** every claim is dated, and old claims get flagged for a
> fresh look before we lean on them again.

Every claim MUST carry a `retrieval-date`. On the reuse path, claims older than
the **180-day** staleness threshold MUST be surfaced for re-grounding. A stale
claim MUST NOT be reused silently behind a valid-looking citation.
*(Closes MUC-003 / NFR-006. Enforced by the date stamp + the reuse-path
staleness flag; see ADR-003. Automated re-probe deferred —
`platform-contract-staleness-reprobe`.)*

### PC-06 — Probe integrity · MUST

> **Plain language:** "I checked it" only counts if you can show the proof you
> checked it.

A claim with `probe-result: confirmed` MUST carry a non-empty `probe-evidence`
reference. A bare `confirmed` with no evidence artifact is **rejected**.
*(Closes MUC-005 / NFR-004. Enforced by the conformance invariant + the probe
-recipe section; see ADR-005.)*

### PC-07 — Gate, not prose-only · MUST

> **Plain language:** a check you can edit away in a paragraph isn't a real
> check — the gate runs mechanically.

A gated third-party touch with no referenced contract MUST fail the
mechanical rubric phase **P-PLAT** regardless of any prose edits. The prose
gate in the design skills is the friendly early ask; P-PLAT is the enforcement
leg that cannot be talked around.
*(Closes MUC-004 / NFR-005. Enforced by P-PLAT — the
`decompose-validation-rubric.md` phase authored in WP-004; see ADR-006.)*

### PC-08 — Harness provenance · MUST

> **Plain language:** every contract records the run that produced it, so a
> hand-written fake can't pass as the real thing.

A Platform Contract MUST carry a **harness-run reference** (the `run_id` of the
`execute-workflow` dispatch) in its front matter. A hand-authored substitute
with no run reference is **rejected**.
*(Closes MUC-007 / NFR-007. Enforced by the run-reference front-matter field +
the P-PLAT provenance check; see ADR-004.)*

---

## Harness-invocation discipline (FR-003) · MUST

A Platform Contract is **produced by running the faithful-generation-harness**,
dispatched through the brain `execute-workflow` engine
(`/sulis-brain:execute-workflow`), against the platform's official documentation
as the closed manifest. It is **not hand-authored**. The harness's committed
claim→source binding table **is** the contract body: each binding becomes one
claim entry; spans outside any binding are flagged `inferred: true`; an
ungrounded load-bearing claim drives a refusal (PC-02).

The step→artifact mapping (which harness step produces which part of the
contract) is **defined in ADR-004** and is not restated here — respect-don't
-restate. The reason for binding the contract body to the harness rather than
cite-as-you-go is also in ADR-004: cite-as-you-go improves grounding but does
not give audit-grade attribution, because its citations are post-hoc narration,
not a causal mechanism.

> **Cross-repo boundary (load-bearing) · MUST.** The harness instance lives in a
> **sibling repo**
> (`plugins/sulis-brain/instances/faithful-generation-harness/`), **not** in this
> change's checkout. It is an `existing` dependency: the architect dispatches the
> harness where it lives; this standard references it and does not vendor or copy
> it. If the harness instance is **not resolvable** at design time, the gate
> emits a **BLOCKER** naming the missing dependency — it MUST NOT fall back to
> hand-authoring (which would re-open MUC-007). See ADR-004 / OAQ-1.

---

## Probe recipes (FR-008) · MUST (for load-bearing claims)

A claim with `load_bearing: true` MUST be **probed** — empirically confirming
"the doc says X *and* the platform does X" — or carry a justified deferral.
Each Platform Contract carries a `## Probe recipes` section: per platform
class, a written-down recipe naming (1) the **probe target** (e.g. a scratch
repo), (2) the **exercise** (the minimal steps that make the platform
demonstrate the behaviour), and (3) the **evidence shape** (the artifact that
proves the exercise ran). A claim's `probe-result` is
`confirmed | refuted | deferred:<canonical-need-id>`, and MUST carry
`probe-evidence` when `confirmed` (PC-06). The probe-recipe mechanism, and the
deferral of heavy/repeatable probe automation, are defined in ADR-005.

---

## Gate posture (FR-014) · MUST

The design-stage Platform Contract gate fires by **touch class**:

| Touch class | Gate | Behaviour |
|---|---|---|
| **write / deploy** | **hard** | Design is **blocked** from proceeding until a Platform Contract for the platform exists. |
| **read-only** | **soft** | The gate **recommends** a lightweight Platform Contract but does not block. |

> **Plain language:** if a change writes to or deploys through someone else's
> platform, design stops until the platform's behaviour is captured and
> checked. If it only reads, the gate suggests a contract but lets the work
> continue.

**Override path (per ADR-001).** The boundary is a default, not a law. A change
author or the founder MAY **escalate a read-only touch to hard-gated** when the
read informs a write/deploy decision — recorded as a one-line note in the
change's SRD/TDD; no ADR required. **De-escalating a write/deploy touch to
soft is NOT permitted by author discretion** — it requires a new ADR
superseding ADR-001, because the write/deploy class is exactly where a
fabricated assumption is most expensive (the triggering incident was a
deploy-path touch).

---

## Storage and reuse (ADR-002) · MUST

- **Standard:** `plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md`
  (this file).
- **Contracts:** `plugins/sulis/references/platform-contracts/<platform>.md` —
  one file per platform, where `<platform>` is a **lowercase, hyphenated slug**
  (`github-actions`, `stripe`, `aws-s3`). Version-controlled and durable across
  changes.
- **Index:** `plugins/sulis/references/platform-contracts/INDEX.md` — a derived
  view (`{platform, contract-path, claims-count, oldest-retrieval-date,
  last-harness-run}`), regenerated from the directory, never hand-maintained as
  the primary record.

The **file's existence** at `platform-contracts/<platform>.md` is the
authoritative "is this platform covered?" signal — a single `test -f`-shaped
lookup the gate and P-PLAT use. `INDEX.md` is a generated convenience for human
review and the freshness sweep, **not** a second source of truth.

> **Plain language:** each platform gets one durable file; if the file exists,
> the platform is covered. The index is a generated summary you can read, not a
> thing you edit by hand.

---

## Freshness (ADR-003) · MUST

Every claim carries a `retrieval-date` (ISO-8601). On reuse, the gate compares
each reused claim's `retrieval-date` against the **180-day** staleness
threshold — a single **named constant** in this standard so a calibration pass
can tune it without touching the gate logic — and surfaces claims past it:
*"this contract has N claims older than 180 days; re-ground before relying on
them."* The surfacing is a **manual flag**; the gate does **not** auto-re-probe.
Automated re-probe is deferred (`platform-contract-staleness-reprobe`).

---

## Tiers / how this standard is used

| Phase | Who | Application |
|---|---|---|
| **Design** | engineering-architect (`draft-architecture`) | Detects a gated third-party touch; runs the harness via `execute-workflow`; lands the bound-claim table as the contract at `platform-contracts/<platform>.md`. |
| **Reuse** | any later change touching the same platform | **Reuses** the existing contract (FR-011) — zero new full harness runs; only re-grounds claims the freshness flag surfaces. Reuse, not regeneration. |
| **Decomposition** | `/sulis:plan-work` + the P-PLAT rubric phase | A gated platform touch with no contract file fails P-PLAT → GAPS_FOUND, with an FE-readable remediation naming the exact file to produce. |

A contract is produced **once per platform** when the first change needs it,
then reused. Contracts are **durable and shared**, never per-change throwaways.

> **Honest status (v0.1.0):** this standard defines the discipline, the schema,
> the gate posture, and the harness binding. The mechanical pieces ship as
> sibling work packages of this change: the storage directory + index
> (WP-002), the design-skill gate wiring + harness glue (WP-003), the P-PLAT
> rubric phase (WP-004), the `plan-work` `platform:` / `touch-class:` field
> (WP-005), and the first worked instance — the GitHub Actions contract
> (WP-006). Until those land, the gate is cited by hand.

---

## Provenance

- **The need (#137).** The triggering incident: a reusable GitHub Actions
  workflow placed where the integration assumed it would resolve, against
  GitHub Actions' real reusable-workflow-location constraint. It surfaced at the
  first real release as a half-applied deploy. This standard exists to catch
  that class at design time.
- **The downstream sibling (#138).** Verification-by-design consumes a Platform
  Contract's grounded constraints as real assertions.
- **The mechanism (referenced, not restated).** The
  **faithful-generation-harness** (`plugins/sulis-brain/instances/
  faithful-generation-harness/`, sibling repo) — its grounding discipline,
  failure modes, and terminal verdicts. This standard references it; it does
  not re-derive the faithful-by-construction theory.
- **The family (referenced).** `CONTRACT_FIRST_STANDARD.md` (data),
  `UX_VISUAL_DESIGN_STANDARD.md` (visual),
  `architecture/SERVICE_SPECIFICATION.md` (service) — the three sibling
  contracts whose shape this standard mirrors and whose relationship axis it
  states.
- **Decisions.** ADR-001 (gate boundary), ADR-002 (storage + index), ADR-003
  (freshness), ADR-004 (harness-invocation shape), ADR-005 (probe mechanism),
  ADR-006 (P-PLAT rubric placement).

---

## Version history

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-06-02 | Initial sulis-local definition. The fourth design-stage contract standard. Defines the canonical claim-entry schema (FR-004) + four conformance invariants; eight requirements PC-01..PC-08 mapped to Armor controls A-1..A-8; harness-invocation discipline (ADR-004); probe recipes (ADR-005); gate posture write/deploy-hard, read-only-soft (ADR-001); storage + derived index (ADR-002); freshness via 180-day named constant (ADR-003). Mirrors the CONTRACT_FIRST / UX_VISUAL / ServiceSpec sibling shape; states the distinguishing axis (a faithful capture, not a design decision). MUST-tier across the board (a contract that looks sound while being unsound is the failure class); the requirements carry 90-day calibration on the staleness threshold per ADR-003. |
