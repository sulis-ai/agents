# SRD — Platform Contract Standard

**Change:** `platform-contract-standard` · primitive: `create`
**Date:** 2026-06-02
**Status:** draft v1
**Scope:** the standard + the design-stage gate + the first GitHub Actions contract (the n=1 dogfood)
**Mechanism (mandated):** the Platform Contract is produced by running the
**faithful-generation-harness** brain Workflow — not by ad-hoc authored prose.
**Dogfood:** this change produces the GitHub Actions Platform Contract as its n=1 worked instance, and ships with a populated `## Verification Plan` section.

---

## Summary

When we integrate with a third party — GitHub Actions, Stripe, AWS, a payment
processor — we are building against a contract we do **not** control. The other
three design-stage contracts cover the seams we *do* control: the **Data
contract** (backend↔frontend), the **Visual contract** (product↔user), and the
**ServiceSpec** (service↔agent/SDK). The **Platform Contract** is the fourth:
the seam with the third-party platform.

The standard mandates that before any change integrates a third-party platform,
the design phase produces a **Platform Contract** — a reviewable, version-
controlled artifact in which **every claim about the platform's behaviour carries
its source citation inline** (official-doc URL + retrieval date + verbatim quote),
every inference is **explicitly flagged as unattributed**, and any claim that
cannot be grounded in official documentation triggers a **refusal** rather than a
fabrication. Load-bearing claims get a **probe** — a real sandbox exercise
confirming the doc says X *and* the platform actually does X.

The contract is produced by running the **faithful-generation-harness**: the
platform's official documentation is the closed manifest, each constraint a
`{claim, source, quote}` entry; the harness commits a claim→source binding table,
generates the contract by expanding only committed bindings, and re-reads each
claim against its source's *meaning* before passing. This is the gate that would
have caught the triggering incident.

**The triggering incident.** The `auto-back-merge-on-release` change designed a
GitHub Actions reusable workflow placed in a plugin subdirectory
(`plugins/sulis/templates/workflows/`), called via `uses: ./plugins/...`. GitHub
Actions **requires** reusable workflows to live in `.github/workflows/`. The
design was invalid from the start, passed every structural test, and only failed
at the first real release — a half-applied production release requiring emergency
recovery. Root cause: the claim "a reusable workflow can live in a plugin subdir"
was a **fabrication about GitHub's contract with no source binding**, and no gate
refused it.

---

## Why this is now

We have three sibling contracts for the seams we control. We have zero discipline
for the seam we don't — and that is the seam where a fabricated assumption is most
expensive, because the platform will not bend to our mistake. The reusable-workflow
incident is the proof: structural tests are blind to a false claim about an
external contract. A gate that demands *source-bound* platform claims, and
*refuses* ungrounded ones, is the missing control.

GitHub issue #137 captures the founder framing — verbatim:

> "Whenever we're working with a third party, how do we conform to their
> specification, their contract. We need to come outside-in, ensuring we're
> almost expert-level on that platform. Much like we have contracts that we build
> for the UI / Data / API, we need contracts for the platforms we're integrating
> with, that need to be grounded in a deep verifiable analysis that is reviewable
> and a critical part of the process."

This change is the design-side counterpart to verification-by-design (#138): a
Platform Contract's constraints feed the Verification Plan — each becomes a test
assertion or a named post-ship observable.

---

## Stakeholders

- **Founder (Iain)** — greenlights integration changes; reads Platform Contracts
  in plain English; the contract must be reviewable by a non-platform-expert.
- **requirements-analyst agent** — surfaces the need for a Platform Contract
  during `/sulis:specify` when a change names a third-party platform.
- **engineering-architect agent** — runs the faithful-generation-harness during
  `/sulis:draft-architecture` to produce or reuse the Platform Contract; binds its
  constraints into the TDD and the Verification Plan.
- **faithful-generation-harness** — the mandated generation mechanism; its
  five-step OODA-grounding discipline produces the contract.
- **decompose-validation-rubric (P-PLAT, new phase)** — fails a cross-kind /
  integration WP set that touches a third party without a Platform Contract.
- **Future integration changes** — reuse durable Platform Contracts that accrue
  in `plugins/sulis/references/platform-contracts/`.
- **Grandfathered integrations** — everything shipped before this standard merges
  continues to pass without a retroactive Platform Contract; only new third-party
  touches are gated.

---

## Glossary anchor

Terms used below are defined precisely in [GLOSSARY.md](GLOSSARY.md): Platform
Contract, bound claim, source citation, flagged inference, probe / ablation,
`manifest-insufficient`, grounded vs. assumed. The Platform Contract is
distinguished there from the Data / Visual / Service contracts.

---

## Use Cases

### UC-001 — A change integrates a new third-party platform → the design phase requires a Platform Contract before proceeding (the gate)

**Actor:** Founder (via engineering-architect agent)
**Trigger:** A change's requirements name a third-party platform the marketplace
does not yet have a Platform Contract for, and the change *writes to or deploys
through* that platform (see Open Question 3 / FR-014 for the read-only carve-out).
**Preconditions:** The Platform Contract Standard exists at
`plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md`. The design
phase (`/sulis:draft-architecture`) has been wired to detect third-party touches.

**Main flow:**
1. The change's SRD/TDD names the platform (e.g. "GitHub Actions").
2. The design phase checks `plugins/sulis/references/platform-contracts/` for an
   existing contract for that platform.
3. None exists → the design phase **blocks** and requires a Platform Contract to
   be produced before proceeding (the hard gate — mirrors the Visual contract gate
   per #45).
4. The architect runs the faithful-generation-harness (UC-004 / FR-003) against
   the platform's official documentation.
5. The harness produces the contract artifact; it is written to
   `plugins/sulis/references/platform-contracts/<platform>.md`.
6. The design proceeds; the TDD references the contract's constraints.

**Postconditions:** A version-controlled Platform Contract exists for the platform;
the integration design is grounded in it.

**Negative requirements (MUST NOT):**
- MUST NOT let an integration design proceed past the design phase without a
  Platform Contract for a gated third-party touch (see MUC-002).
- MUST NOT treat a structural-test pass as a substitute for the contract (the
  reusable-workflow incident — structural tests were green on an invalid design).

---

### UC-002 — An existing Platform Contract is reused by a later change touching the same platform (contracts are durable)

**Actor:** Founder (via engineering-architect agent)
**Trigger:** A later change integrates a platform that already has a contract.
**Preconditions:** `plugins/sulis/references/platform-contracts/<platform>.md`
exists from a prior change.

**Main flow:**
1. The design phase finds the existing contract for the platform.
2. It checks the contract's **freshness** (every claim's retrieval date; see
   NFR-006 / Open Question 2) — if a claim is older than the staleness threshold
   the contract flags it for re-grounding (mechanism deferred — see Out of Scope).
3. The change reuses the contract's constraints without regenerating it.
4. If the new change relies on a platform behaviour the contract does **not** yet
   cover, only the *new* claims are added via a harness run (incremental, not full
   regeneration).

**Postconditions:** The contract accrues coverage across changes; it is not
regenerated per change.

**Alternate flow A — contract is stale:** A retrieval date exceeds the threshold →
the affected claims are flagged; the architect re-probes / re-grounds them before
reuse (see UC-004).

**Negative requirements (MUST NOT):**
- MUST NOT regenerate a durable contract from scratch per change (waste + drift).
- MUST NOT silently reuse a stale claim past the freshness threshold without
  flagging it (see MUC-003).

---

### UC-003 — A platform claim can't be grounded in official docs → the harness refuses → the contract records it as an explicit assumption requiring a probe

**Actor:** engineering-architect agent (running the harness)
**Trigger:** During harness `decide-commit-bindings`, a claim the contract needs
to make has no supporting entry in the platform's official-documentation manifest.
**Preconditions:** The harness is running; the manifest is the platform's official
docs.

**Main flow:**
1. The architect enumerates the claims the contract will make.
2. For one claim, no official-doc source supports it.
3. The harness applies the load-bearing-claim test: is this claim demanded by the
   generation goal?
4. If load-bearing and ungrounded → the harness fires `manifest-insufficient`
   (the `binding-table-incomplete-or-invalid` failure mode) and **refuses** to
   assert the behaviour as documented fact.
5. The architect records the claim in the contract as an **explicit assumption**
   (`inferred: true`, no false citation) **requiring a probe** (UC-004) before it
   can be relied upon.
6. The contract proceeds for the grounded claims; the assumption is visibly flagged.

**Postconditions:** No ungrounded claim is asserted as documented fact; the gap is
visible, not silent.

**This is the gate that would have caught the triggering incident.** "A reusable
workflow can live in a plugin subdir" had no official-doc source. The harness
would have refused it rather than letting it pass as fact.

**Negative requirements (MUST NOT):**
- MUST NOT assert undocumented platform behaviour as fact (see MUC-001).
- MUST NOT silently promote an inference to documented-fact (see MUC-006).

---

### UC-004 — A load-bearing claim gets a probe (real sandbox exercise) → the probe result is recorded in the contract

**Actor:** engineering-architect agent
**Trigger:** A claim is classified load-bearing (the integration design depends on
it being true), OR a claim was recorded as an assumption (UC-003) and must be
confirmed before reliance.
**Preconditions:** A probe mechanism exists for the platform class (Open Question 4
flags that the per-platform probe mechanism — sandbox repo / scratch credentials /
dry-run — is to be designed by SEA).

**Main flow:**
1. The architect identifies the claim as load-bearing.
2. The architect designs a probe: a real, minimal sandbox exercise that confirms
   both "doc says X" and "platform actually does X".
3. The probe is run (e.g. for GitHub Actions: a scratch repo with a reusable
   workflow placed in `.github/workflows/`, called via `uses:`, observed to
   resolve; and the same placed in a subdir, observed to fail).
4. The probe result (`probe-result: confirmed | refuted`, with evidence) is
   recorded against the claim in the contract.

**Postconditions:** Load-bearing claims carry empirical confirmation, not only a
citation. A doc-says-X claim refuted by the probe is escalated (the doc was wrong
or our reading was wrong).

**Negative requirements (MUST NOT):**
- MUST NOT record a probe as run if it was not actually executed (see MUC-005 —
  a faked probe is the integrity failure of the probe mechanism itself).
- MUST NOT treat a plausible-by-shape claim as grounded without the meaning-check
  (the harness `self-critique-grounding` re-read; see MUC-002 meaning-drift).

---

### UC-005 — The GitHub Actions Platform Contract (the n=1 dogfood) captures the load-bearing rules

**Actor:** engineering-architect agent (this change)
**Trigger:** This change produces the first Platform Contract as its dogfood.
**Preconditions:** The harness and the standard exist.

**Main flow:**
1. The architect runs the harness against GitHub Actions' official documentation.
2. The contract captures, at minimum, these three grounded rules — each with an
   official-doc citation and (for the load-bearing ones) a probe:
   - **Reusable-workflow location:** reusable workflows MUST reside in
     `.github/workflows/`; the `uses:` reference resolves only there. *(Source:
     docs.github.com — Reusing workflows. The rule the triggering incident
     violated. Load-bearing → probed.)*
   - **Bot-token-doesn't-trigger-downstream-workflows:** events triggered by the
     default `GITHUB_TOKEN` (or a `github-actions[bot]` action) do **not** trigger
     a new workflow run — preventing recursive runs. *(Source: docs.github.com —
     Triggering a workflow / "events that won't trigger workflows". Load-bearing
     for any auto-merge / auto-push design → probed.)*
   - **Branch-protection-on-free-plan:** branch protection rules / rulesets on
     **private** repositories require a paid plan; public repos get them free.
     *(Source: docs.github.com — About protected branches / plan availability.
     Constraint, not a runtime behaviour → cited; probe optional.)*
3. The contract is written to
   `plugins/sulis/references/platform-contracts/github-actions.md`.

**Postconditions:** The marketplace has its first durable Platform Contract; the
`auto-back-merge` redesign (separate follow-on) has a grounded contract to build
against.

**Negative requirements (MUST NOT):**
- MUST NOT ship the GitHub Actions contract with any of the three rules uncited
  or unprobed where the rule is load-bearing.

---

### UC-006 — A Platform Contract feeds the Verification Plan (#138)

**Actor:** engineering-architect agent
**Trigger:** A change with a Platform Contract reaches the Verification Plan step
of design.
**Preconditions:** A Platform Contract exists; the verification-by-design
methodology (`VERIFICATION_QUESTIONS.md`) is active.

**Main flow:**
1. The architect reads each constraint in the Platform Contract.
2. Each constraint is mapped to **either** a test assertion (the change's tests
   assert the platform behaves per the contract) **or** a named post-ship
   observable (a signal watched after deploy when the behaviour can't be tested
   pre-ship).
3. These land in the change's `## Verification Plan` per-integration subsection,
   with the integration classified `existing` / `deferred` / `out-of-scope` per
   the ADR-007 adapter table.

**Postconditions:** The Platform Contract is not a dead document — its constraints
become live verification obligations. A probe-refuted or unverifiable constraint
surfaces as a deferred infrastructure need (Open Question 4).

**Negative requirements (MUST NOT):**
- MUST NOT leave a load-bearing platform constraint with neither a test assertion
  nor a named post-ship observable.

---

## Functional Requirements

Each FR carries an acceptance criterion testable enough to write a test or a
rubric check against.

- **FR-001 — The standard exists.** A new reference standard
  `plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md` is authored,
  defining the discipline, the contract artifact shape, the gate, and the harness
  binding. *Acceptance:* the file exists, declares severity conventions, and cites
  the three sibling standards. Mirrors the shape of `CONTRACT_FIRST_STANDARD.md`
  and `UX_VISUAL_DESIGN_STANDARD.md`.

- **FR-002 — The design-stage gate.** `/sulis:specify` and
  `/sulis:draft-architecture` are wired so that a change touching a gated
  third-party platform (FR-014) requires a Platform Contract before design
  proceeds. *Acceptance:* a design dispatch that names a gated, uncovered platform
  blocks with an explicit "Platform Contract required" instruction; a design that
  names a covered platform proceeds.

- **FR-003 — The harness-invocation requirement.** A Platform Contract MUST be
  produced by running the faithful-generation-harness (the platform's official
  docs as the closed manifest), NOT by ad-hoc authored prose. *Acceptance:* the
  standard names the harness as the required mechanism; the contract artifact
  records that it was harness-produced (a harness-run reference).

- **FR-004 — The contract artifact shape.** Every claim in a Platform Contract is
  a structured entry: `{claim, source, quote, retrieval-date, inferred?, probe?,
  probe-result?}`. *Acceptance:* the standard specifies this schema; the GitHub
  Actions contract conforms; a claim with `inferred: false` MUST carry a non-empty
  `source` + `quote` + `retrieval-date`; a claim with `inferred: true` MUST NOT
  carry a fabricated source.

- **FR-005 — Inline citation, flagged inference.** Every grounded claim carries
  its source citation inline; every connective / inferred span is explicitly
  flagged as unattributed and never falsely cited. *Acceptance:* the contract has
  zero spans that carry a citation to a source that does not support them (the
  harness `false-citation` failure mode); inferred spans are visibly marked.

- **FR-006 — The refusal behaviour.** When a load-bearing claim cannot be grounded
  in official docs, the harness fires `manifest-insufficient` and the claim is
  recorded as an explicit assumption requiring a probe — never asserted as fact.
  *Acceptance:* a harness run with an ungrounded load-bearing claim produces a
  refusal + an assumption entry, not a fabricated citation. This is the control
  that catches the reusable-workflow class of defect.

- **FR-007 — Meaning-check (not shape-check).** Each claim is re-read against its
  source's *meaning*, not its value-shape, before the contract passes (the harness
  `self-critique-grounding` step). *Acceptance:* a claim that is plausible-by-shape
  but means something different from its source is caught and corrected/flagged.

- **FR-008 — Load-bearing claims get a probe.** Claims the integration design
  depends on carry a probe: a real sandbox exercise confirming doc-says-X AND
  platform-does-X, with `probe-result` recorded. *Acceptance:* every claim marked
  load-bearing has a `probe` + `probe-result` field populated (or an explicit,
  justified deferral with a canonical need identifier per Open Question 4).

- **FR-009 — The GitHub Actions contract is the first instance.** The n=1 dogfood
  produces `plugins/sulis/references/platform-contracts/github-actions.md`
  capturing the three rules in UC-005, each grounded with a real GitHub-docs URL
  and retrieval date, the load-bearing ones probed. *Acceptance:* the file exists
  and conforms to FR-004/005/008; the reusable-workflow-location rule is present,
  cited, and probed.

- **FR-010 — Durable storage location.** Platform Contracts live in
  `plugins/sulis/references/platform-contracts/<platform>.md` — reviewable,
  version-controlled, reused across changes. *Acceptance:* the directory exists;
  the GitHub Actions contract is committed there; the standard names this location
  as canonical.

- **FR-011 — Reuse, not regeneration.** A later change touching a covered platform
  reuses the existing contract; only new uncovered claims trigger an incremental
  harness run. *Acceptance:* the standard specifies the reuse path; the gate
  (FR-002) treats a covered platform as satisfied (subject to freshness, FR-013).

- **FR-012 — The Verification-Plan feed.** Each Platform Contract constraint maps
  to a test assertion or a named post-ship observable in the consuming change's
  `## Verification Plan`. *Acceptance:* the standard specifies this mapping; a
  change with a Platform Contract carries, per load-bearing constraint, either an
  assertion or an observable in its Verification Plan.

- **FR-013 — Freshness via retrieval date.** Every claim carries a retrieval date;
  the contract surfaces claims older than a staleness threshold for re-grounding.
  *Acceptance:* claims carry `retrieval-date`; a reuse path checks it. *(The
  automated re-probe mechanism is deferred — see Out of Scope. This FR ships the
  date + the manual flag, not the automation.)*

- **FR-014 — Gate trigger scope.** The gate fires for third-party touches that
  **write to or deploy through** the platform. Read-only API calls are flagged as
  a SHOULD (a lightweight contract is encouraged) but are not hard-gated. *(This
  resolves Open Question 3 as a proposed default; the standard authoring confirms
  it.)* *Acceptance:* the gate logic distinguishes write/deploy touches (hard gate)
  from read-only touches (soft recommendation).

- **FR-015 — The decompose-rubric check (P-PLAT, new phase).** A new rubric phase,
  sibling to Phase 7 (ServiceSpec) and Phase 9 (P-VER), fails a cross-kind /
  integration WP set that touches a gated third party without a referenced Platform
  Contract. *Acceptance:* `decompose-validation-rubric.md` gains a phase that, on a
  WP set touching a gated platform with no contract reference, emits a FAIL with an
  explicit "Platform Contract required at `plugins/sulis/references/platform-
  contracts/<platform>.md`" instruction; collapses the overall verdict to
  GAPS_FOUND.

- **FR-016 — Distinct from the sibling contracts.** The standard cross-references
  and distinguishes the Platform Contract from the Data contract
  (`CONTRACT_FIRST_STANDARD.md`), the Visual contract
  (`UX_VISUAL_DESIGN_STANDARD.md`), and the ServiceSpec
  (`architecture/SERVICE_SPECIFICATION.md`, referenced by the rubric Phase 7).
  *Acceptance:* the standard's "Relationship to existing standards" section names
  all three and states the distinguishing axis (the seam we don't control).

---

## Non-Functional Requirements

Full detail in [NFR.md](NFR.md). Summarised here:

- **NFR-001 (Source-bound).** Every non-inferred claim cites an official source
  with a retrieval date. Measurable: zero uncited factual claims in any contract.
- **NFR-002 (Honest inference).** Inferences are flagged, never stated as fact.
  Measurable: every inferred span carries `inferred: true`; zero false citations.
- **NFR-003 (Reviewable by a non-platform-expert).** A reviewer who is not a
  platform expert can check every claim by following its citation. Measurable:
  every claim's source URL resolves; the quote is locatable at the source.
- **NFR-004 (Load-bearing claims probed).** Every load-bearing claim carries a
  probe result. Measurable: zero load-bearing claims without `probe-result`
  (or a justified deferral).
- **NFR-005 (Backward compatibility / grandfathering).** Existing integrations are
  grandfathered; only new third-party touches are gated. Measurable: a change whose
  `started_at` precedes the standard's merge passes without a contract.
- **NFR-006 (Durable + reused, with freshness).** Contracts persist and are reused,
  not regenerated; each claim's retrieval date enables staleness detection.
  Measurable: a second change touching the same platform produces zero new full
  harness runs; reused claims past threshold are flagged.

---

## Negative Requirements (cross-cutting)

These hold across all use cases and are the spine of the misuse cases
([MISUSE_CASES.md](MISUSE_CASES.md)):

- **NR-1 — MUST NOT assert undocumented platform behaviour as fact.** (MUC-001)
- **NR-2 — MUST NOT let an integration design proceed without a contract for a
  gated third-party touch.** (MUC-002, MUC-004)
- **NR-3 — MUST NOT treat a plausible-by-shape claim as grounded without the
  meaning-check.** (MUC-002 meaning-drift)
- **NR-4 — MUST NOT reuse a stale claim past the freshness threshold without
  flagging it.** (MUC-003)
- **NR-5 — MUST NOT record a probe as run when it was not actually executed.**
  (MUC-005)
- **NR-6 — MUST NOT silently promote an inference to documented fact.** (MUC-006)
- **NR-7 — MUST NOT substitute a hand-waved doc for a harness run.** (MUC-007)

---

## Diagrams

- [Use-case diagram](diagrams/use-cases.md) — actors and the six use cases.
- [Process flow — the design-stage gate + harness run](diagrams/process-flows.md)
- [Sequence — harness producing a Platform Contract](diagrams/sequence-diagrams.md)
- [State — a claim's lifecycle (ungrounded → grounded → probed → stale)](diagrams/state-diagrams.md)

---

## Open Questions (surfaced, not resolved)

1. **Storage + indexing.** `plugins/sulis/references/platform-contracts/<platform>.md`
   is proposed (FR-010). How are contracts *indexed* for cross-change reuse — a
   manifest file, a naming convention, the rubric scanning the directory? (SEA to
   resolve.)
2. **Freshness detection.** Retrieval-date + periodic re-probe is the proposed
   shape (FR-013). The *automated* re-probe is deferred (Out of Scope); the
   threshold value and the manual-flag UX are open.
3. **Gate scope.** FR-014 proposes: hard-gate write/deploy touches, soft-recommend
   read-only. Confirm at standard-authoring time.
4. **Probe mechanism per platform class.** Sandbox repo / scratch credentials /
   dry-run mode — how a probe is actually executed differs per platform. SEA to
   design the GitHub Actions probe concretely (scratch repo); other classes deferred.

---

## Out of Scope

- Platform Contracts for platforms **other than GitHub Actions** (per-integration,
  later).
- The `auto-back-merge` redesign itself (separate follow-on; this change gives it
  the GitHub Actions contract to build against).
- **Automated staleness re-probing** — the need is flagged (FR-013, Open Q2); the
  automation mechanism is deferred.

---

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->
## Verification Plan

> Populated per the verification-by-design methodology. This change's `kind:` is
> **methodology** (it ships a standard + a gate + a rubric phase + the first
> instance), with a **documentation** secondary adapter (the GitHub Actions
> contract is a cited document) and a **contract** secondary adapter (the contract
> artifact has a conformance shape). Canonical question set cited above; not
> inlined.

### What user-observable behaviour are we verifying?

After this change ships, a founder starting a change that integrates a third-party
platform sees the design phase **stop** and ask for a Platform Contract before it
will continue — and the produced contract is one where every claim about the
platform links to an official GitHub/AWS/Stripe doc page they can click and check
themselves. Concretely: a design that names "GitHub Actions" and tries to place a
reusable workflow in the wrong directory is **refused at design time** with a
citation showing the rule, instead of failing at the first real release. The first
visible artifact is `github-actions.md` in the platform-contracts directory, whose
reusable-workflow-location rule is cited and probed.

### Verification environment(s)

- **Local / CI (structural):** the standard file exists; the GitHub Actions
  contract conforms to the `{claim, source, quote, inferred?, probe?, probe-result?}`
  shape; the rubric P-PLAT phase is present and fails a no-contract integration WP
  set. These run as rubric checks + a structural test in CI.
- **Local (harness behavioural):** a harness dispatch against a small fixture
  manifest with one ungrounded load-bearing claim produces a refusal +
  assumption entry (FR-006) — run locally where the harness executes.
- **Probe (real GitHub):** the reusable-workflow-location probe runs against a real
  scratch GitHub repo (see per-integration below) — this is the dogfood probe, run
  once during this change, recorded in the contract.

### Bootstrap-from-zero case

A fresh clone needs: the faithful-generation-harness instance (already in the
plugins repo — a dependency, see per-integration); the three sibling standards
(already shipped); and, for the real probe, **scratch GitHub credentials + a
throwaway repo** (NOT shipped — flagged as a deferred infrastructure need below).
The structural and harness-behavioural verification need nothing beyond the repo.
The real-GitHub probe is the one piece that needs un-shipped infrastructure.

### Per-integration verification strategy

| Integration | Boundary | Approach | Classification |
|---|---|---|---|
| **faithful-generation-harness** (brain Workflow, plugins repo) | Workflow dispatch / instance files | **real** — run the harness against a fixture manifest; assert refusal on ungrounded load-bearing claim (FR-006) and binding-table production (FR-004) | `existing` (the instance is authored; this change consumes it) |
| **GitHub Actions** (the platform the n=1 contract describes) | Official docs (manifest source) + a scratch repo (probe target) | docs: **real** read with retrieval date; probe: **real** scratch-repo exercise for reusable-workflow location; bot-token + branch-protection rules **cited** (probe deferred for branch-protection — needs a paid private repo) | `deferred` — probe infra is the deferred need below |
| **decompose-validation-rubric** (internal, P-PLAT phase) | Rubric prose + the WP-set scan | **real** — structural test: a synthetic integration WP set with no contract reference triggers P-PLAT FAIL → GAPS_FOUND | `existing` |

### Per-kind verification adapter

**Primary adapter — `methodology`:** Structural assertions + an integration test
where a fresh design dispatch (a change naming a gated platform) produces the gate
behaviour (block when uncovered; proceed when covered) and the produced contract
carries the new shape. Concrete artifact (Shape 1): a rubric-level test asserting
P-PLAT fails a no-contract integration WP set, plus a harness-dispatch test
asserting the refusal-on-ungrounded-load-bearing-claim path.

**Secondary adapter — `documentation`:** Link-resolution check (every source URL in
`github-actions.md` resolves) + freshness-of-cited-sources check (retrieval dates
present and within threshold) + readability (the contract is reviewable by a
non-platform-expert, FK target met).

**Secondary adapter — `contract`:** Contract-conformance check on the artifact
shape — every claim entry has the required fields; `inferred: false` ⇒ source +
quote + retrieval-date present; `inferred: true` ⇒ no fabricated source;
load-bearing ⇒ probe + probe-result present (or justified deferral).

### Infrastructure needs surfaced (deferred)

- **`scratch-github-actions-probe-repo`** — a throwaway GitHub repository +
  scratch credentials in CI/local to run real reusable-workflow-location and
  bot-token probes against live GitHub. Needed to fully satisfy FR-008 for the
  GitHub Actions contract's load-bearing rules. This change runs the
  reusable-workflow probe manually once and records the result; the *repeatable
  automated* probe pipeline is the deferred follow-on.
- **`paid-private-repo-for-branch-protection-probe`** — branch-protection-on-free-
  plan is a *constraint* (plan availability), citeable but only fully probeable
  with a paid private repo. Probe deferred; claim ships cited.
- **`platform-contract-staleness-reprobe`** — the automated re-probe that detects a
  platform changed since retrieval (Open Q2 / FR-013). Explicitly Out of Scope for
  this change; flagged so the slice-end review can aggregate it if a second design
  surfaces the same need.
