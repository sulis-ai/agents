# Handoff to SEA — Platform Contract Standard

**Change:** `platform-contract-standard` · primitive: `create`
**Spec folder:** `.specifications/platform-contract-standard/`
**Cross-links:** GitHub issue #137 (the need) · #138 (verification-by-design, the
sibling that consumes the contract's constraints)

---

## What this change ships (scope)

1. **The standard** — `plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md`.
2. **The design-stage gate** — wired into `/sulis:specify` and
   `/sulis:draft-architecture`, enforced mechanically by a new rubric phase.
3. **The first contract** — `plugins/sulis/references/platform-contracts/github-actions.md`,
   produced as the n=1 dogfood by running the faithful-generation-harness.

Out of scope: contracts for platforms other than GitHub Actions; the
`auto-back-merge` redesign itself; automated staleness re-probing.

---

## Design hints

### Where the standard lives
`plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md`. Author it to
**mirror the shape** of its three siblings (read them first):
- `plugins/sulis/references/standards/CONTRACT_FIRST_STANDARD.md` (Data contract —
  note the CF-01..CF-10 requirement structure and the "Relationship to existing
  standards" section).
- `plugins/sulis/references/standards/UX_VISUAL_DESIGN_STANDARD.md` (Visual contract
  — note especially how it is a **hard design-before-build gate**, per #45; the
  Platform Contract mirrors that gate posture).
- The **ServiceSpec** — referenced by the decompose rubric's Phase 7 ("the Lovable
  Test"); `architecture/SERVICE_SPECIFICATION.md` is the reference shape that
  `CONTRACT_FIRST_STANDARD.md` CF-10 points to.

The standard's "Relationship to existing standards" section MUST name all three and
state the distinguishing axis: the Platform Contract is the seam **we do not
control** (FR-016).

### Where contracts live
`plugins/sulis/references/platform-contracts/<platform>.md` — the directory does not
exist yet; create it. Version-controlled, reviewable, reused across changes (FR-010,
FR-011). **Open Question 1 (yours to resolve):** the indexing mechanism for reuse —
a manifest file, a naming convention, or the rubric scanning the directory.

### How the harness is invoked from the design phase
The Platform Contract MUST be produced by running the **faithful-generation-harness**
at `/Users/iain/Documents/repos/plugins/plugins/sulis-brain/instances/faithful-generation-harness/`
(FR-003). The mapping of harness steps to the contract:

| Harness step | Contract production role |
|---|---|
| `observe-manifest` | The platform's **official docs** are the closed manifest; each entry `{variable_id, meaning, value}` = `{claim-topic, what-the-doc-says, verbatim-quote+URL}`. |
| `orient-select-relevant` | Select the doc sections bearing on this integration's needs. |
| `decide-commit-bindings` | The **claim→source binding table** — the load-bearing artifact. An ungrounded load-bearing claim fires `manifest-insufficient` → refusal. |
| `act-generate-from-bindings` | Generate the contract; every claim carries its citation inline; inferences flagged unattributed. |
| `self-critique-grounding` | Re-read each claim against its source's **meaning** (catches MUC-002 drift + false citation). |

The contract artifact records a **harness-run reference** so the rubric P-PLAT can
reject a hand-authored substitute (MUC-007).

### The contract artifact shape (FR-004)
Each claim is a structured entry:
```yaml
- claim: "<one statement about the platform>"
  source: "<official-doc URL>"
  retrieval-date: "<ISO-8601>"
  quote: "<verbatim from the source>"
  inferred: false          # true ⇒ no source/quote; a flagged inference (ours, not the platform's)
  load_bearing: true       # the integration design depends on this
  probe: "<the sandbox exercise, if load-bearing>"
  probe-result: "confirmed | refuted | deferred:<canonical-need-id>"
```

### The GitHub Actions contract's first content (UC-005, FR-009)
Three rules, each grounded in a **real GitHub docs page** (retrieve + quote + stamp
the date at authoring time; URLs below are the canonical doc locations — confirm
they resolve and capture the exact quote):

1. **Reusable-workflow location** *(load-bearing → probe).* Reusable workflows must
   reside in `.github/workflows/`; a `uses:` reference resolves only there. This is
   the rule the triggering incident violated.
   Source: `https://docs.github.com/en/actions/sharing-automations/reusing-workflows`
   ("Reusing workflows" — Access section / "must be stored in the
   `.github/workflows` directory"). **Probe:** scratch repo — reusable workflow in
   `.github/workflows/` resolves via `uses:`; same file in a subdir fails.

2. **Bot-token-doesn't-trigger-downstream-workflows** *(load-bearing → probe).*
   Events triggered by the default `GITHUB_TOKEN` (or actions running as
   `github-actions[bot]`) do not trigger a new workflow run — preventing recursive
   runs. Directly relevant to any auto-merge/auto-push design.
   Source: `https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication`
   ("Using the GITHUB_TOKEN in a workflow" — "events triggered by the GITHUB_TOKEN
   ... will not create a new workflow run"). **Probe:** scratch repo — a push made
   with `GITHUB_TOKEN` does not trigger the `on: push` workflow.

3. **Branch-protection-on-free-plan** *(constraint → cite; probe deferred).* Branch
   protection rules / rulesets on **private** repositories require a paid plan;
   public repositories get them free.
   Source: `https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches`
   (plan-availability note). **Probe deferred** — needs a paid private repo
   (canonical need: `paid-private-repo-for-branch-protection-probe`).

> All three URLs and quotes MUST be re-retrieved and verbatim-captured at authoring
> time — do not trust this handoff as the source. The handoff *names where to
> ground*; the harness *does the grounding*.

### The decompose-rubric new-phase wiring (FR-015)
Add **Phase P-PLAT** to `plugins/sulis/references/decompose-validation-rubric.md`,
sibling to **Phase 7 (ServiceSpec)** and **Phase 9 (P-VER)**. It fails a cross-kind
/ integration WP set that touches a **gated** third party (write/deploy, per FR-014)
without a referenced Platform Contract; emits an explicit "Platform Contract
required at `plugins/sulis/references/platform-contracts/<platform>.md`" instruction;
collapses the overall verdict to GAPS_FOUND. Include a **grandfather sub-phase**
mirroring P-VER's `verification_required_from:` merge-date constant (NFR-005).

### The Verification-Plan feed (FR-012, #138)
Each contract constraint maps to a test assertion or a named post-ship observable in
the consuming change's `## Verification Plan` per-integration subsection, with the
integration classified `existing` / `deferred` / `out-of-scope` per the ADR-007
adapter table in `VERIFICATION_QUESTIONS.md`.

---

## Open questions for SEA (surfaced in SRD, yours to resolve)

1. **Storage + indexing** of contracts for cross-change reuse (FR-010).
2. **Freshness detection** threshold + manual-flag UX (FR-013); automated re-probe
   is explicitly Out of Scope (canonical need: `platform-contract-staleness-reprobe`).
3. **Gate scope** — confirm FR-014's proposed default (hard-gate write/deploy;
   soft-recommend read-only).
4. **Probe mechanism per platform class** (FR-008) — design the GitHub Actions probe
   concretely (scratch repo; canonical need: `scratch-github-actions-probe-repo`);
   other platform classes deferred.

---

## Deferred infrastructure needs (for the slice-end review to aggregate)

- `scratch-github-actions-probe-repo` — throwaway repo + scratch credentials to run
  the reusable-workflow and bot-token probes against real GitHub.
- `paid-private-repo-for-branch-protection-probe` — to fully probe the
  branch-protection constraint.
- `platform-contract-staleness-reprobe` — automated staleness detection (Out of
  Scope this change; flag if a second design surfaces the same need).

---

## Artifact reading order for SEA

1. `GLOSSARY.md` — the locked vocabulary, incl. the four-contracts disambiguation.
2. `PRIMITIVE_TREE.jsonld` — the structural inventory (existing-impl leaves =
   harness + rubric, which you *extend* not *build*).
3. `SRD.md` — the six use cases, FR-001..016, and the `## Verification Plan`.
4. `MISUSE_CASES.md` — the seven misuse cases (the failure class this exists to
   prevent) + the pre-mortem.
5. `diagrams/` — gate flow, harness sequence, claim lifecycle.
6. `NFR.md` — the measurable targets.

**Next command:** `/sulis:draft-architecture .specifications/platform-contract-standard/`
