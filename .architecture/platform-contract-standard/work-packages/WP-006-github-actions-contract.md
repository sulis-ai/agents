---
id: WP-006
title: Produce the GitHub Actions Platform Contract (run harness, ground 3 rules)
status: pending
change_id: "01KT3X2M0JHFN583DKKV77W83C"
kind: methodology
primitive: create
group: EXPAND
sequence_id: WP-006
dependsOn: [WP-002, WP-003]
blocks: [WP-007, WP-008]
platform: github-actions
touch-class: read-only
estimated_token_cost:
  input: 6k
  output: 5k
tdd_section: "Form §component 5 (line 81); Proof §3 the n=1 dogfood (lines 177-191); FR-009; UC-005; A-2, A-3, A-4"
adrs: [ADR-004, ADR-005]
verification:
  adapter: methodology
  artifact: tests/methodology/test_github_actions_contract.py::test_contract_conformance
---

## Context

Produces the **n=1 dogfood instance**: the GitHub Actions Platform Contract at
`plugins/sulis/references/platform-contracts/github-actions.md`. **This
contract is itself the proof the discipline works.** It is produced by *running
the harness* (the glue authored in WP-003) and grounding three rules against
re-retrieved live GitHub-docs URLs, conforming to the schema defined in WP-001.

**Dogfooding this change's own new field.** This WP touches a third-party
platform (GitHub), so it carries `platform: github-actions, touch-class:
read-only` in its own frontmatter — the first use of the field WP-005 makes
`plan-work` emit. `read-only` is correct: authoring the contract *reads*
GitHub docs and runs read-only probes; it does not write to or deploy through
GitHub.

**TDD reference:** Form component 5 (line 81) names this file as the dogfood
instance. Proof leg 3 (lines 177-191) defines the three rules, their
grounding, their probes, and the assertions they become. The MUST at lines
188-191: the contract MUST NOT ship with any rule uncited, nor with a
load-bearing rule unprobed-and-not-justifiably-deferred; **the three URLs and
quotes MUST be re-retrieved at authoring — the handoff is not the source.**

**Why this depends on WP-002 + WP-003 (load-bearing).** WP-002 creates the
directory the contract lands in + the INDEX it adds a row to. WP-003 authors
the harness-invocation glue this WP *executes* to produce the contract. This
WP **must not start before both land** — it runs the harness and conforms to
the schema (TDD Decomposition signal lines 331-335). It does **not** depend on
WP-001 directly because WP-002 and WP-003 both already depend on WP-001
(transitive).

**Why EXPAND-Create, not SUBSTITUTE-Wrap.** We author an instance the harness
*produces*; we dispatch the harness, we do not wrap it (TDD lines 99-104;
change-primitives "Ports & Adapters vs Wrappers").

**Pre-Work Prior-Art Check:** no `github-actions.md` contract exists. The
three rules trace to the triggering reusable-workflow incident (issue #137).

## Contract

### Files created / modified

- `plugins/sulis/references/platform-contracts/github-actions.md` — NEW (the
  contract; conforms to the WP-001 claim-entry schema).
- `plugins/sulis/references/platform-contracts/INDEX.md` — MODIFY (replace the
  "none yet" placeholder row with the github-actions row + freshness column).

### The three grounded rules (Proof leg 3 — TDD lines 182-186)

Each becomes a claim entry conforming to the schema. **The URLs + quotes MUST
be re-retrieved live at authoring** (not copied from the handoff):

| Rule | Grounding | Probe | `probe-result` |
|---|---|---|---|
| **Reusable-workflow-location** — reusable workflows MUST live in `.github/workflows/`; `uses:` resolves only there. | real `docs.github.com` URL, re-retrieved + quoted + dated. | scratch repo: workflow in `.github/workflows/` resolves via `uses:`; same file in a subdir fails. | `confirmed` (+ `probe-evidence`) |
| **Bot-token-no-downstream-trigger** — events from the default `GITHUB_TOKEN` do not trigger a new workflow run. | real `docs.github.com` URL (automatic-token-authentication). | scratch repo: a push made with `GITHUB_TOKEN` does not trigger the `on: push` workflow. The meaning-check guards the "*new*" qualifier (MUC-002). | `confirmed` (+ `probe-evidence`) |
| **Branch-protection-on-free-plan** — branch protection on private repos requires a paid plan. | real `docs.github.com` URL (about-protected-branches). | **deferred** — needs a paid private repo. | `deferred:paid-private-repo-for-branch-protection-probe` |

### Front matter (the contract's own)

- `harness-run: <LifecycleRun.run_id>` — the provenance P-PLAT checks (A-8 /
  NFR-007). A hand-authored substitute with no run-ref is rejected.
- `platform: github-actions`, contract metadata, oldest `retrieval-date`.

### Production method (FR-009 / ADR-004)

Produced by dispatching the faithful-generation-harness via
`/sulis-brain:execute-workflow` (through the WP-003 glue) against the GitHub
docs as the closed manifest. The committed binding table becomes the three
claim entries; any span outside a binding is flagged `inferred: true`.

> **The repeatable probe pipeline is deferred** —
> `deferred:scratch-github-actions-probe-repo`. This WP runs the
> reusable-workflow + bot-token probes **manually once** and records the
> evidence in the contract; the automated/repeatable pipeline is the
> follow-on need.

## Definition of Done

### Red — Failing test written first

- [ ] `tests/methodology/test_github_actions_contract.py::test_contract_conformance`
  (authored in WP-007; this WP's Red writes the assertion stub) asserts the
  contract satisfies every claim-entry invariant:
  - all three rules present;
  - `inferred:false` ⇒ source+quote+retrieval-date (A-1);
  - `load_bearing:true` ⇒ probe + probe-result (A-6);
  - `probe-result:confirmed` ⇒ non-empty `probe-evidence`;
  - front matter `harness-run:` non-empty (A-8).
- [ ] Initial run FAILS (the contract does not exist yet).

### Green — Implementation makes the test pass

- [ ] Run the harness through the WP-003 glue against GitHub docs.
- [ ] **Re-retrieve** the three docs URLs live; capture verbatim quotes +
  retrieval dates (do not copy from the handoff).
- [ ] Author `github-actions.md` with the three claim entries + the
  `harness-run:` front-matter reference.
- [ ] Run the reusable-workflow + bot-token probes once against a scratch repo;
  record `probe-result: confirmed` + `probe-evidence`.
- [ ] Defer the branch-protection probe with the canonical need id.
- [ ] Add the github-actions row to `platform-contracts/INDEX.md`.
- [ ] Red-phase conformance test passes.

### Blue — Refactor + polish

- [ ] Each rule carries a plain-language summary at FK Grade ≤ 10 (NFR-003).
- [ ] Every `source` URL resolves (the authoring-time link check — OAQ-2).
- [ ] No claim asserted as fact without a citation; inferences flagged
  `inferred: true` with no fabricated source (A-4).

## Sequence

- **Sequence ID:** WP-006
- **dependsOn:** WP-002 (storage dir + INDEX), WP-003 (the harness-invocation
  glue this WP executes). Transitively depends on WP-001 via both.
- **blocks:** WP-007 (conformance test reads this contract), WP-008 (the
  dogfood acceptance turns these three rules into real assertions).
- **Parallelisable with:** WP-005 (disjoint file surface).

## Estimated Token Cost

- **Input:** ~6k (re-retrieving + reading three GitHub docs pages + the schema
  + ADR-004 + ADR-005).
- **Output:** ~5k (the contract + INDEX row + probe evidence records).
- **Total:** ~11k.

## Notes

- **Load-bearing dogfood.** This is one of the two pieces that prove the
  discipline (the other is the harness-binding in WP-003). If the harness
  cannot be dispatched (sibling repo unresolvable), this WP emits a BLOCKER per
  ADR-004 — it does **not** hand-author the contract.
- **The handoff names *where*; the harness *grounds*.** The HANDOFF_TO_SEA may
  point at the docs pages, but the URLs + quotes + dates MUST be re-retrieved
  at authoring (UC-005 MUST). The handoff is not the source.
- This WP carries the new `platform:` / `touch-class:` frontmatter field
  (dogfood of WP-005's emission) — `touch-class: read-only`.

## Verification Plan (per-WP)

- **Adapter:** `methodology` — for the conformance assertion: **Shape 1
  (concrete)** — `tests/methodology/test_github_actions_contract.py::test_contract_conformance`.
- For the *repeatable probe pipeline*: **Shape 2 (deferred)** —
  `deferred:scratch-github-actions-probe-repo` (manual one-shot run recorded
  now). Branch-protection probe: **Shape 2 (deferred)** —
  `deferred:paid-private-repo-for-branch-protection-probe`.
- **Observable:** the first contract artifact exists; its reusable-workflow
  rule is cited to a resolving `docs.github.com` URL and probed `confirmed`.
- **Resilience:** the probe is a one-shot read-only exercise, no production hot
  path — no timeout/retry/CB primitive applies.
