# TDD — Platform Contract Standard

> **Change:** `platform-contract-standard` · primitive: `create`
> **Date:** 2026-06-02 · **Status:** designed
> **Sourced from:** `.specifications/platform-contract-standard/` (SRD v1, NFR, MISUSE_CASES, GLOSSARY, PRIMITIVE_TREE, HANDOFF_TO_SEA)
> **Tier:** L (see [SIZING.md](SIZING.md)) — low end of L (Form references two sibling templates; Proof references the SRD's authored Verification Plan)
> **Cross-references:** GitHub issue #137 (the need) · #138 (verification-by-design — the sibling that consumes this contract's constraints)
> **`kind:`** `methodology` (primary) · `documentation` + `contract` (secondary adapters)

This change creates the **fourth design-stage contract** — the Platform Contract,
for the seam with a third-party platform we do **not** control. It mirrors the
three siblings (Data, Visual, ServiceSpec) in shape and gate posture, extends two
existing components (the faithful-generation-harness and the
decompose-validation-rubric), and ships its own n=1 worked instance (the GitHub
Actions contract) as proof the discipline works.

---

## Canonical Identifiers (P8)

The change introduces three identifier conventions. They are locked here so
`/sulis:plan-work` and downstream artifacts use them without re-deciding.

### Contract-artifact claim-entry schema

Each claim in a Platform Contract is a structured entry. The schema (FR-004):

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

Conformance invariants (the `contract` adapter checks these):
- `inferred: false` ⇒ non-empty `source` + `quote` + `retrieval-date`.
- `inferred: true` ⇒ **no** `source` (no fabricated citation).
- `load_bearing: true` ⇒ `probe` + `probe-result` present (or `probe-result: deferred:<id>`).
- `probe-result: confirmed` ⇒ non-empty `probe-evidence`.

### Storage path convention

- Standard: `plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md`
- Contracts: `plugins/sulis/references/platform-contracts/<platform>.md` (`<platform>` = lowercase-hyphenated slug)
- Index: `plugins/sulis/references/platform-contracts/INDEX.md` (derived view — ADR-002)

### Rubric phase id

- **`P-PLAT`** — the new decompose-validation-rubric phase, appended as **Phase 10**
  after P-VER (Phase 9). Cited by name (`P-PLAT`), not by position. (ADR-006)

### Canonical deferred-need identifiers

These follow the `{noun}-{noun}-{vendor-or-scope}` recipe so the slice-end review
aggregates them across changes:
- `scratch-github-actions-probe-repo` — repeatable automated GitHub Actions probe pipeline.
- `paid-private-repo-for-branch-protection-probe` — branch-protection probe target.
- `platform-contract-staleness-reprobe` — automated staleness re-probe (ADR-003).

---

## Form — Structural Integrity

The change is methodology authoring: the "components" are documents, skill-prose
wiring, and one rubric phase. The Form discipline here is **dependency direction
among artifacts** and **respect-don't-restate** against the existing standards.

### Component inventory

| # | Component | Path | Move | Primitive | Notes |
|---|---|---|---|---|---|
| 1 | **The standard** | `plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md` | new | EXPAND-Create | Mirrors `CONTRACT_FIRST_STANDARD.md` / `UX_VISUAL_DESIGN_STANDARD.md` shape: severity convention, model, relationship-to-siblings, numbered requirements (`PC-NN`), tiers, how-used, provenance, version history. |
| 2 | **Contract artifact shape + storage + INDEX** | `plugins/sulis/references/platform-contracts/` (dir + `INDEX.md`) | new | EXPAND-Create | The claim-entry schema (above) is *defined in* the standard; the directory + derived INDEX are the durable store (ADR-002). |
| 3 | **Design-phase gate wiring** | `plugins/sulis/skills/specify/SKILL.md`, `plugins/sulis/skills/draft-architecture/SKILL.md` | modify | REINFORCE-Gate | Prose detects a gated third-party touch and asks for a Platform Contract. Defence-in-depth front leg; the rubric is the enforcement leg. |
| 4 | **Harness-invocation glue** | within the standard + `draft-architecture/SKILL.md` | new | EXPAND-Create | How the design phase runs the faithful-generation-harness via `execute-workflow` and lands the bound-claim table as the contract body (ADR-004). |
| 5 | **GitHub Actions contract (n=1)** | `plugins/sulis/references/platform-contracts/github-actions.md` | new | EXPAND-Create | The dogfood instance; produced by running the harness, three rules grounded. |
| 6 | **P-PLAT rubric check** | `plugins/sulis/references/decompose-validation-rubric.md` | modify | REINFORCE-Gate | New Phase 10, mirrors P-VER (ADR-006). |

### Dependency direction (the contract's "ports")

The artifact dependency graph points **inward to the standard** — the standard
defines the schema and the discipline; everything else conforms to it:

```
PLATFORM_CONTRACT_STANDARD.md  (defines: schema, gate posture, harness binding, relationship-to-siblings)
        ▲                ▲                    ▲
        │ conforms-to    │ enforces           │ produces-an-instance-of
   github-actions.md   P-PLAT (rubric)   harness-invocation glue
        │                                      │
        │ consumes (existing dep)              │ dispatches (existing dep)
   faithful-generation-harness  ◄──────────────┘   (sibling repo — ADR-004)
```

- The **harness** and the **rubric** are `existing-impl` leaves (PRIMITIVE_TREE):
  this change **extends** them, does not build them. Implementing the GitHub
  Actions contract by *running* the harness is **EXPAND-Create** (we author an
  instance the harness produces), **not** SUBSTITUTE-Wrap — we are not wrapping
  the harness, we are dispatching it. (See change-primitives "Ports & Adapters vs
  Wrappers".)
- **Relationship-to-siblings (FR-016, MUST):** the standard's "Relationship to
  existing standards" section names the Data contract
  (`CONTRACT_FIRST_STANDARD.md`), the Visual contract
  (`UX_VISUAL_DESIGN_STANDARD.md`), and the ServiceSpec
  (`architecture/SERVICE_SPECIFICATION.md`) and states the distinguishing axis:
  **the Platform Contract is the seam we do not control**, so it is a *faithful
  capture* of the platform's reality, not our design decision (GLOSSARY four-contracts table).

### Respect-don't-restate

- The standard **references** the harness's grounding discipline (the five steps,
  the failure modes, the terminal verdicts) by pointing at the instance — it does
  not re-derive the faithful-by-construction theory.
- P-PLAT **references** P-VER's grandfather mechanism and verdict semantics rather
  than restating them; it cites the P-VER ADRs the rubric already links.
- The contract-artifact schema is defined **once** (in the standard); the GitHub
  Actions contract and the conformance check both point at it.

---

## Armor — Operational Hardening

For a methodology change, "Armor" is **gate integrity** — the controls that stop a
contract from *looking* sound while being unsound. Each MUC system-response maps to
exactly one mechanical control. This table is the spine of the P-PLAT failure-mode
table and the conformance adapter.

| # | Control (the hardening primitive) | Closes | Mechanism | Enforced by |
|---|---|---|---|---|
| A-1 | **No uncited factual claim.** `inferred:false` ⇒ source+quote+retrieval-date non-empty. | MUC-001 / NFR-001 | Conformance schema invariant. | `contract` adapter + P-PLAT |
| A-2 | **Refusal on ungrounded load-bearing claim.** Harness fires `binding-table-incomplete-or-invalid` → `terminal-manifest-insufficient`; claim recorded as flagged assumption requiring a probe, never asserted as fact. | MUC-001 / FR-006 | Harness step `decide-commit-bindings`. | harness (existing) |
| A-3 | **Meaning-check, not shape-check.** Each claim re-read against its source's *meaning*; the verbatim `quote` field makes drift reviewer-checkable. | MUC-002 / NFR-003 | Harness step `self-critique-grounding` (`false-citation`, `ungrounded-span`). | harness (existing) + reviewer |
| A-4 | **Honest inference.** Every span outside a committed binding flagged `inferred:true`; never falsely cited. | MUC-006 / NFR-002 | Harness step `act-generate-from-bindings`. | harness (existing) + `contract` adapter |
| A-5 | **Freshness.** Every claim carries `retrieval-date`; reuse surfaces claims past 180 days; never silently reuse a stale claim. | MUC-003 / NFR-006 | Date stamp + reuse-path staleness flag (ADR-003). Automated re-probe deferred. | gate (specify/draft-arch) + manual flag |
| A-6 | **Probe integrity.** `probe-result:confirmed` ⇒ non-empty `probe-evidence`; a bare `confirmed` rejected. | MUC-005 / NFR-004 | Conformance invariant + probe-recipe section (ADR-005). | `contract` adapter + P-PLAT |
| A-7 | **Gate not prose-only.** A gated third-party touch with no referenced contract fails P-PLAT regardless of prose edits. | MUC-004 / NFR-005 | Mechanical rubric phase (ADR-006), defence-in-depth with prose. | P-PLAT |
| A-8 | **Harness provenance.** Contract carries a harness-run reference; a hand-authored substitute (no run ref) is rejected. | MUC-007 / NFR-007 | Run-reference front-matter field + P-PLAT provenance check. | P-PLAT |

### Reviewability (NFR-003) — the founder-facing Armor

A non-platform-expert can check every claim by following its citation:
- Every `source` URL **resolves** (the `documentation` adapter's link-resolution check).
- Every `quote` is **locatable** at its source (the verbatim string makes drift visible).
- Each rule carries a **plain-language summary** at Flesch-Kincaid Grade ≤ 10 (NFR-003).
This is why the standard mandates the `quote` field, not just the URL: a real URL is
necessary but not sufficient (GLOSSARY "source exists vs source supports the claim").

---

## Proof — Verification Protocol

The SRD already authored a six-subsection Verification Plan; this section
**concretises** it (the full concretion is in `## Verification Plan` below). The
proof strategy has three legs:

### 1. Structural / conformance tests (CI)

| Test | Asserts | Adapter |
|---|---|---|
| `test_standard_exists` | `PLATFORM_CONTRACT_STANDARD.md` exists, declares severity conventions, cites the three siblings (FR-001, FR-016). | methodology |
| `test_contract_conformance` | `github-actions.md` satisfies every claim-entry invariant (A-1, A-4, A-6 above). | contract |
| `test_source_urls_resolve` | Every `source` URL in `github-actions.md` resolves (NFR-003). | documentation |
| `test_pplat_fails_no_contract` | A synthetic integration WP set naming a gated platform with no contract reference triggers P-PLAT FAIL → GAPS_FOUND (FR-015). | methodology |
| `test_pplat_grandfathers` | A change with `started_at` before the merge date passes P-PLAT without a contract (NFR-005). | methodology |

### 2. Harness behavioural test (local)

`test_harness_refuses_ungrounded_load_bearing` — a harness dispatch against a small
fixture manifest containing one ungrounded load-bearing claim produces a refusal
(`terminal-manifest-insufficient`) + a flagged-assumption entry, **not** a fabricated
citation (FR-006 / A-2). This is the control that catches the reusable-workflow class.

### 3. The n=1 dogfood (the load-bearing proof)

**The GitHub Actions contract is itself the proof the discipline works.** Its three
grounded rules become real assertions:

| Rule | Grounding | Probe | Becomes the assertion |
|---|---|---|---|
| **Reusable-workflow location** — reusable workflows MUST live in `.github/workflows/`; `uses:` resolves only there. | real GitHub-docs URL, re-retrieved + quoted + dated at authoring (per harness discipline — the handoff *names where*, the harness *grounds*). | **scratch repo:** workflow in `.github/workflows/` resolves via `uses:`; same file in a subdir fails. | `test_reusable_workflow_rule_cited_to_real_github_url` — the rule's `source` is a real `docs.github.com` URL that resolves, and `probe-result: confirmed` with evidence. |
| **Bot-token-no-downstream-trigger** — events from the default `GITHUB_TOKEN` do not trigger a new workflow run. | real GitHub-docs URL (automatic-token-authentication page). | **scratch repo:** a push made with `GITHUB_TOKEN` does not trigger the `on: push` workflow. | claim cited + probed; meaning-check guards MUC-002 drift (the "*new*" qualifier). |
| **Branch-protection-on-free-plan** — branch protection on private repos requires a paid plan. | real GitHub-docs URL (about-protected-branches). | **deferred** — needs a paid private repo. | claim cited; `probe-result: deferred:paid-private-repo-for-branch-protection-probe`. |

> **MUST (UC-005):** the GitHub Actions contract MUST NOT ship with any of the three
> rules uncited, nor with a load-bearing rule unprobed-and-not-justifiably-deferred.
> The three URLs and quotes MUST be re-retrieved at authoring — the handoff is not the
> source.

---

## Open Architecture Questions

The SRD's four open questions are resolved in ADRs (ADR-002 storage/index, ADR-003
freshness, ADR-001 gate scope, ADR-005 probe mechanism). Residual questions surfaced
during design:

| # | Question | Disposition |
|---|---|---|
| OAQ-1 | The harness lives in a **sibling repo** not in this change's checkout. Does the gate need that repo resolvable at design time? | **Resolved in ADR-004:** classify the harness integration `existing`; if unresolvable, the gate emits a BLOCKER (do not fall back to hand-authoring). No founder input needed. |
| OAQ-2 | Should the `documentation` link-resolution check be a hard CI gate (network-dependent, flaky) or a soft advisory? | **Recommend soft advisory in CI, hard at authoring time.** Network checks in CI are flaky and GitHub docs URLs are stable-ish; a hard CI gate would fail builds on transient network/redirect issues unrelated to the change. The authoring-time check (run once when the contract is produced) is the real gate. Recorded as a SHOULD in the standard. |
| OAQ-3 | The 180-day staleness threshold (ADR-003) is a first guess. | **Calibration item.** Named constant; the rubric's existing 90-day calibration window applies. No founder input needed now. |
| OAQ-4 | P-PLAT needs to detect "this WP set touches a gated third party." What is the detection signal — a WP frontmatter field, a platform-name scan, or an explicit `platform:` declaration? | **Recommend an explicit `platform:` + `touch-class: write\|deploy\|read` field on the integration WP**, set by `/sulis:plan-work`. Scanning prose for platform names is brittle (MUC-004-adjacent). This is a `plan-work` concern — flagged for the decomposition step, not blocking the TDD. |

None of these requires founder input; all are convention-shaped technical choices
taken per CP-01 and journal-recorded. OAQ-4 is the one to carry into `/sulis:plan-work`.

---

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->
## Verification Plan

> This change's `kind:` is **methodology** (it ships a standard + a gate + a rubric
> phase + the first instance), with **documentation** and **contract** secondary
> adapters. Canonical question set cited above; not inlined. This section
> concretises the SRD's Verification Plan into TDD-level test artifacts.

### What user-observable behaviour are we verifying?

A founder starting a change that integrates a third-party platform sees the design
phase **stop** and ask for a Platform Contract before continuing — and the produced
contract is one where every claim links to an official doc page they can click and
check. Concretely: a design that names "GitHub Actions" and tries to place a reusable
workflow in the wrong directory is **refused at design time** with a citation showing
the rule, instead of failing at the first real release. The first visible artifact is
`github-actions.md`, whose reusable-workflow-location rule is cited and probed.

### Verification environment(s)

- **CI (structural):** the five structural/conformance tests above run as
  rubric checks + pytest-style structural tests. Artifacts:
  `tests/methodology/test_platform_contract_standard.py`,
  `tests/methodology/test_pplat_rubric.py`.
- **Local (harness behavioural):** the harness-refusal test runs where the harness
  executes (sibling brain repo / `execute-workflow`). Fixture manifest at
  `tests/methodology/fixtures/ungrounded-manifest.jsonld`.
- **Probe (real GitHub):** the reusable-workflow + bot-token probes run once against
  a real scratch GitHub repo during this change; results recorded in the contract.

### Bootstrap-from-zero case

A fresh clone at the merge SHA can run the **structural** and **harness-behavioural**
verification with nothing beyond the repo + the sibling brain plugin (the harness is
an `existing` dependency). The **real-GitHub probe** is the one piece needing
un-shipped infrastructure (scratch credentials + a throwaway repo) — flagged deferred
below. The bootstrap test (`test_contract_conformance` + `test_pplat_fails_no_contract`)
must pass on a clean clone.

### Per-integration verification strategy

| Integration | Boundary | Approach | Classification | TDD concretion (artifact + shape) |
|---|---|---|---|---|
| **faithful-generation-harness** (brain Workflow, sibling repo) | `execute-workflow` dispatch / instance files | **real** — run against a fixture manifest; assert refusal on ungrounded load-bearing claim (FR-006) + binding-table production (FR-004). | `existing` — instance authored; this change consumes it (ADR-004). | `tests/methodology/test_harness_refusal.py`; fixture `tests/methodology/fixtures/ungrounded-manifest.jsonld`. **Seam:** the `execute-workflow` engine boundary — no internal mocking. **Shape 1 — concrete.** |
| **GitHub Actions** (the platform the n=1 contract describes) | Official docs (manifest source) + a scratch repo (probe target) | docs: **real** read with retrieval date; reusable-workflow + bot-token probes: **real** scratch-repo exercise; branch-protection: **cited**, probe deferred (paid private repo). | `deferred` — probe infra is the deferred need below. | reusable-workflow + bot-token: **Shape 2 — deferred** `deferred:scratch-github-actions-probe-repo` for the *repeatable* pipeline (manual run recorded now); branch-protection: `deferred:paid-private-repo-for-branch-protection-probe`. Resilience: the probe is a one-shot exercise, no HTTP-call resilience primitive applies (no production hot path). |
| **decompose-validation-rubric** (internal, P-PLAT phase) | Rubric prose + the WP-set scan | **real** — structural test: a synthetic integration WP set with no contract reference triggers P-PLAT FAIL → GAPS_FOUND; a grandfathered change passes. | `existing` — extended, not built. | `tests/methodology/test_pplat_rubric.py`. **Shape 1 — concrete.** Fixtures: `tests/methodology/fixtures/wp-set-no-contract/`, `tests/methodology/fixtures/wp-set-grandfathered/`. |

### Per-kind verification adapter

**Primary — `methodology`:** structural assertions + an integration test where a
fresh design dispatch naming a gated platform produces the gate behaviour (block when
uncovered; proceed when covered) and the produced contract carries the schema.
Concrete artifact (Shape 1): the P-PLAT rubric test + the harness-refusal test above.

**Secondary — `documentation`:** link-resolution check (every `source` URL in
`github-actions.md` resolves) + freshness check (retrieval-dates present, within 180
days) + readability (plain-language rule summaries at FK Grade ≤ 10). Per OAQ-2,
hard at authoring time, SHOULD-advisory in CI.

**Secondary — `contract`:** conformance check on the claim-entry schema — every claim
has the required fields; `inferred:false` ⇒ source+quote+retrieval-date;
`inferred:true` ⇒ no fabricated source; `load_bearing:true` ⇒ probe+probe-result (or
justified deferral); `probe-result:confirmed` ⇒ non-empty `probe-evidence`.

### Infrastructure needs surfaced (deferred)

- **`scratch-github-actions-probe-repo`** — a throwaway repo + scratch credentials to
  run the reusable-workflow + bot-token probes repeatably/automatically. This change
  runs them **manually once** and records the evidence; the repeatable pipeline is the
  follow-on.
- **`paid-private-repo-for-branch-protection-probe`** — to fully probe the
  branch-protection constraint. Probe deferred; the claim ships cited.
- **`platform-contract-staleness-reprobe`** — the automated re-probe (ADR-003 / Open
  Q2). Explicitly out of scope; flagged so the slice-end review aggregates it if a
  second design surfaces the same need.

---

## Sizing Report

> Cross-references [SIZING.md](SIZING.md).

- **Tier:** L computed (sFPC 13 → M; ASR 22 → L; take higher). Confirmed L (autonomous
  run; founder-resolved scope confirms non-trivial: standard + gate + first contract +
  rubric phase).
- **TDD length vs target:** within the tier-L target (~250–400 lines); sits at the low
  end because Form references two sibling templates and Proof references the SRD's
  authored Verification Plan rather than restating either.
- **ADRs:** 6 produced vs 6 named by the founder. Each is a genuine cross-component or
  technology-lock decision (gate boundary, storage, freshness, harness binding, probe,
  rubric placement) — none is quota-filling. Within tier-L maximum.
- **Authoritative sources referenced (not restated):** the harness instance (grounding
  discipline + failure modes + terminal verdicts), P-VER (grandfather mechanism +
  verdict semantics), the two sibling standards (shape + relationship axis), the GLOSSARY
  four-contracts table.
- **Sections that referenced rather than restated:** Form (sibling-standard shape,
  harness theory), Armor (harness failure modes), Proof (SRD Verification Plan).
- **Circuit breakers triggered:** none. TDD is within 1.5× the tier target; ADR count
  is at the named maximum, all justified.

---

## Decomposition signal (for `/sulis:plan-work`)

Estimated **6–9 WPs**. The shared-file collision risk (the discover-project lesson) is
real here — three WPs touch shared files: the gate wiring touches two skill files; the
P-PLAT WP touches the rubric; the harness-glue touches the standard + draft-architecture.

| WP signal | Touches | Depends on |
|---|---|---|
| The standard doc | `PLATFORM_CONTRACT_STANDARD.md` (new) | — (foundational; defines the schema everything conforms to) |
| Contract-artifact shape + storage + INDEX | `platform-contracts/` dir + `INDEX.md` (new) | standard WP |
| specify + draft-architecture gate wiring | two skill files (modify) | standard WP |
| Harness-invocation glue | standard + draft-architecture (modify) | standard WP, gate-wiring WP (shared file: draft-architecture) |
| **GitHub Actions contract** (run harness, ground 3 rules) | `github-actions.md` (new) | **contract-shape WP + harness-glue WP** (load-bearing dependency) |
| P-PLAT rubric check | `decompose-validation-rubric.md` (modify) | standard WP |
| Tests + dogfood acceptance | `tests/methodology/` (new) | all above |

**Load-bearing:** the harness-binding (ADR-004) and the grounded GitHub Actions
contract are the two pieces that prove the discipline. The GitHub Actions contract WP
**must not** start before the contract-shape WP and the harness-glue WP land — it
*runs the harness* and *conforms to the schema*. Carry **OAQ-4** (the `platform:` /
`touch-class:` WP frontmatter field) into `plan-work` so P-PLAT has a detection signal.
