# faithful-generation-harness run journal

- run_id: 01KT419R8MQBQ6BNZPXDSKZBHZ
- workflow: dna:workflow:01KT3GM8ZF8PC7RJSGSE5JE7QQ (faithful-generation-harness)
- instance dir: /Users/iain/Documents/repos/plugins/plugins/sulis-brain/instances/faithful-generation-harness
- trigger fired: operator-invokes-generation (manual) — dna:trigger:01KT3GM8ZFWBJP98QFPN24B7QJ
- generation-goal: produce a bound claim→source table for a GitHub Actions Platform Contract (n=1 dogfood of platform-contract-standard)
- started: 2026-06-02
- resolved: true

## Closed manifest (the ONLY citable input set)

| variable_id | meaning | value (verbatim where quoted) |
|---|---|---|
| src-reusable-workflow-location | GitHub docs: reusing-workflows; where reusable workflows must live; retrieved 2026-06-02 | "As with other workflow files, you locate reusable workflows in the `.github/workflows` directory of a repository. Subdirectories of the `workflows` directory are not supported." (URL: https://docs.github.com/en/actions/sharing-automations/reusing-workflows) |
| src-bot-token-no-trigger | GitHub docs: trigger-a-workflow; GITHUB_TOKEN downstream trigger behaviour; retrieved 2026-06-02 | "When you use the repository's `GITHUB_TOKEN` to perform tasks, events triggered by the `GITHUB_TOKEN` will not create a new workflow run, with the following exceptions:" (exceptions: workflow_dispatch and repository_dispatch) (URL: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow) |
| src-branch-restriction-org | GitHub docs: about-protected-branches; the ONLY plan/availability sentence groundable as of 2026-06-02; retrieved 2026-06-02 | "You can enable branch restrictions in public repositories owned by a GitHub Free organization and in all repositories owned by an organization using GitHub Team or GitHub Enterprise Cloud." (URL: https://docs.github.com/en/.../about-protected-branches) |
| probe-rule1 | confirmed real-world probe for rule 1 | v0.87.0 release failed: reusable workflow placed in plugins/sulis/templates/workflows/ not .github/workflows/; GitHub could not resolve via `uses:` (issue #137) |
| probe-rule2 | confirmed real-world probe for rule 2 | release tag pushed with GITHUB_TOKEN did NOT trigger downstream release-publish workflow; ran `gh release create v1.132.0` manually |
| probe-rule3-op | operational observation (NOT a docs source) | #52 unprotected-repo detection on a private free-plan repo |

Manifest is CLOSED: nothing outside these entries may be cited. No "see attached", no implicit external source.

## Step walk (OODA spiral)

### Step 1 — observe-manifest [mixed] — completed
- Structural check: 3 docs entries + 3 probe entries; each has variable_id+meaning+value; ids unique; non-empty; closed.
- No structural/closure fault. NOTE: rule-3 goal-relative gap (no docs source for "private free-plan repo cannot enforce branch protection") is NOT Observe's to catch — deferred to decide-commit-bindings per DR-029 W1.
- Postcondition: PASS. Transition: observe-manifest -> orient-select-relevant.

### Step 2 — orient-select-relevant [mixed] — completed
- relevant-subset: ALL of {src-reusable-workflow-location, src-bot-token-no-trigger, src-branch-restriction-org, probe-rule1, probe-rule2, probe-rule3-op}. The goal (claim→source table for rules 1-3) bears on every entry.
- MECE: no redundant coverage. src-branch-restriction-org covers ORG branch restrictions only — it does NOT cover the private free-plan claim rule 3 actually makes; noted for binding.
- Postcondition: PASS. Transition: orient-select-relevant -> decide-commit-bindings.

### Step 3 — decide-commit-bindings [probabilistic] — completed (THE LOAD-BEARING ARTIFACT)
Claims enumerated and bound:

- CLAIM rule-1 (reusable-workflow-location): reusable workflows must live in `.github/workflows`; subdirectories unsupported.
  - BINDING: variable_id = src-reusable-workflow-location. justification: verbatim quote directly states both the location requirement and the subdirectory exclusion. Probe probe-rule1 corroborates (issue #137). load_bearing: true. BOUND.
- CLAIM rule-2 (bot-token-no-downstream-trigger): events triggered by GITHUB_TOKEN will not create a NEW workflow run (except workflow_dispatch / repository_dispatch).
  - BINDING: variable_id = src-bot-token-no-trigger. justification: verbatim quote states exactly this, including the "new workflow run" qualifier and the two exceptions. Probe probe-rule2 corroborates (v1.132.0 manual release). load_bearing: true. BOUND.
- CLAIM rule-3 (branch-protection-on-private-free-plan): "branch protection on a private free-plan repo cannot be enforced."
  - GAP. No manifest variable supports THIS claim. src-branch-restriction-org speaks to ORG-owned repos and which plans enable branch RESTRICTIONS — it does NOT state that a private free-plan repo cannot enforce branch protection. Binding it would be a FALSE CITATION (variable does not support the span).
  - load-bearing-claim-test (DR-029 W4): rule 3 is declared NOT load-bearing for this contract (operator: "NOT load-bearing for this contract; probe deferred"). Limb (a) fails: not demanded by the goal as a contract-binding rule. => non-load-bearing => REDUCIBLE.
  - Resolution: record rule 3 as an honest INFERENCE (operational, from #52 via probe-rule3-op), inferred:true, NO source. Probe deferred: id=paid-private-repo-for-branch-protection-probe.

- binding-table: bindings=[rule-1, rule-2]; gaps=[{claim: rule-3, reason: no docs source supports the private-free-plan claim; the only related verbatim is org-scoped and does not cover it, load_bearing: false}]
- load-bearing-claims = {rule-1, rule-2}; both bound. goal-reducible = true (only gap is non-load-bearing).
- binding-validity: every bound variable_id exists in manifest. PASS.
- ROUTING (reduce-vs-escalate-rule): every load-bearing claim bound AND all gaps reducible => REDUCE+proceed.
- Postcondition: PASS. Transition: decide-commit-bindings -> act-generate-from-bindings.

### Step 4 — act-generate-from-bindings [probabilistic] — completed
- Expanded ONLY committed bindings into the claim→source table rows for rule 1 and rule 2 (each row carries its variable_id citation = source URL + retrieval date + verbatim quote).
- rule 3 emitted as an UNATTRIBUTED span (inference row): inferred:true, NO source, carrying the operational origin (#52) + deferred-probe id. NOT cited to any manifest variable.
- No judged-claim dispatch needed (rules 1-2 are verbatim-quoted facts, not interpretive assertions; rule 3 is flagged inference, not stated-as-sourced).
- Postcondition: PASS. Transition: act-generate-from-bindings -> self-critique-grounding.

### Step 5 — self-critique-grounding [mixed] — completed (FALSIFICATION GATE)
Substantive per-span re-read (NOT rubber-stamp):
- rule-1 span vs src-reusable-workflow-location value: span asserts ".github/workflows required, subdirectories unsupported". Variable value verbatim: "...you locate reusable workflows in the `.github/workflows` directory of a repository. Subdirectories of the `workflows` directory are not supported." SUPPORTED — span is a direct paraphrase, no drift, no added detail. GROUNDED.
- rule-2 span vs src-bot-token-no-trigger value: ABLATION + MEANING-CHECK on the "*new* workflow run" qualifier. Variable value verbatim: "...events triggered by the `GITHUB_TOKEN` will not create a new workflow run, with the following exceptions:". Span preserves "new workflow run" (NOT "any workflow run" / "no workflow run") and preserves the exceptions (workflow_dispatch, repository_dispatch). Dropping the word "new" would over-generalise (GITHUB_TOKEN CAN still run the SAME workflow / other triggers) — qualifier confirmed PRESERVED. GROUNDED.
- rule-3 inference span: carries NO citation. Re-checked: it is in unattributed/inference set, explicitly inferred:true. REFUSED to bind it to src-branch-restriction-org (which is org-scoped and does not support the private-free-plan claim) — fabricated-provenance refusal upheld. Correctly UNATTRIBUTED, not falsely cited.
- binding-validity: true. false-citation-detected: false. grounding-theatre check: per-span rationales quote the specific variable VALUE (above) — substantive, not templated.
- revision-count: 0. No cycle-back needed.

VERDICT: All LOAD-BEARING claims (rule 1, rule 2) are bound + grounded with no false citation; the one gap (rule 3) is honestly flagged unattributed/inference, not falsely cited.
=> terminal:partial-unattributed (honest partial provenance — content is sound; rule 3 carries no fabricated source).
residual-unattributed: rule-3 (branch-protection-on-private-free-plan) — no docs source as of 2026-06-02; recorded as inference; probe deferred (paid-private-repo-for-branch-protection-probe).

## Terminal
- final-verdict: partial-unattributed
- All three rules emitted; rules 1-2 source-bound + grounded; rule 3 honest inference (no source).
- LifecycleRun persisted: .brain/instances/product-development/lifecyclerun/01KT419R8MQBQ6BNZPXDSKZBHZ.jsonld

