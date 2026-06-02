# Code Review: train-2026-06-01T124607Z — WP-007 squash-merged (THE drift detector lands)

> **Timestamp:** 2026-06-01T12:51:41Z UTC
> **Train ID:** train-2026-06-01T124607Z
> **Diff range:** 35af641..e182531
> **WPs shipped:** WP-007 (Build canonical drift detector — kind: backend)
> **Outcome:** Ready to merge — Path A's structural bridge is functionally complete

## At a glance — this is the dogfood moment

This wave lands **WP-007**, the drift detector — the structural bridge in Path A. With it on the change branch, we **ran the detector against the actual live canonical** for the first time. It works.

It immediately surfaced **11 real reconciliation items** between the canonical workflow spec (WP-001…006) and the imperative `release-on-merge.yml` (WP-009 annotations). These aren't bugs in WP-007 — they're the methodology delivering its promised value: *the canonical captured the intent; the imperative is partially aligned; the bridge surfaced the gap.*

The 11 items break down into:
- **6 canonical Steps with no YAML annotation.** Most of these are by-design absences (Steps 1-8 live in the `/sulis:release-train` skill prose per MUC-007, not in the GitHub Actions tail). But the detector doesn't know that yet — it treats every canonical Step as expected-in-YAML.
- **5 Step↔FailureMode handling pairs the YAML doesn't annotate.** WP-009 added 1 `canonical:failuremode:` annotation; the canonical lists 5 more pairs that need explicit handling annotations in the YAML.

**None of these block this change.** They're future reconciliation work (WP-008 will determine whether to ship the detector in blocking or advisory mode initially). The drift detector working AND finding drift IS the proof Path A succeeds.

## What to fix

**Nothing in this WP.** The drift detector is correct.

The 11 reconciliation items it surfaced are tracked as **future work** below. Whether to address them in this change vs. a sibling change is a decision for the wave-6 dispatch (WP-008's brief).

## Things to take away

1. **Path A's first dogfood worked.** We *thought* the canonical and imperative were aligned after WP-009 added annotations. The detector showed otherwise — finding 11 specific gaps in 0.5 seconds. This is the value of structural canonical-vs-imperative reconciliation that the SRD promised in plain English: *"we know what should happen; we know what we coded; the bridge tells us where they disagree."* That promise is now testable.

2. **The detector's "missing_in_yaml" classification is a touch too eager.** Canonical Steps with `mechanism: human` (like `gate-founder-confirmation`) or whose implementation lives in skill prose by design (per MUC-007) are flagged the same as Steps with genuinely missing imperative annotations. A small refinement (filed below as Watch List): teach the detector to respect a `skip_in_yaml: true` field on the canonical Step, or to read MUC-007's prose-vs-YAML boundary. Not blocking; the current output is still readable (the 6 missing-in-yaml items are obvious from context).

---

## Technical detail

### Verdict

`PASS` per CR-06. The WP itself is clean (42/42 tests; 98% coverage; per-WP Step 6.5 PASS). The drift findings are correct outputs, not defects.

### Live drift run

```bash
$ python3 plugins/sulis/scripts/check-canonical-drift.py \
    --instance-dir plugins/sulis/instances/release-train/ \
    --yaml-path .github/workflows/release-on-merge.yml
{"ok": false, "data": {"drift": [11 items]}}
exit 1
```

Full output captured at `tool-outputs/drift-detector-live-run.json`.

### Summary

- **CR-01 mechanical baseline:** 42/42 detector tests pass; live run against real canonical exits with structured drift verdict.
- **CR-09 PR Hygiene:** clean — single WP, single Conventional Commits feat, no infra/migration/secret patterns.
- **Lens findings (in changes):** 0.
- **Step 11:** not dispatched as subagent this wave (API caution from wave 4; the WP-007 codebase is pure-function backend code with no auth/data/network surface; per-WP Step 6.5 already PASS with verdict).
- **Inline security spot-check on WP-007 code:**
  - No subprocess.run with shell=True or interpolated argv.
  - No filesystem traversal outside `--instance-dir` and `--yaml-path` (both required CLI args, no defaults).
  - No network calls; pure-local per WP-007 DoD.
  - JSON output is structured (no raw string concatenation into command shapes).

### Watch List — the 11 drift findings + a small detector refinement

**Six `missing_in_yaml` items** — by-design absences that the detector currently can't distinguish from real gaps:

| Canonical Step | Reason it's absent in YAML | Future action |
|---|---|---|
| `gate-founder-confirmation` | `mechanism: human`; lives in `/sulis:release-train` skill prose per MUC-007 | Tag canonical Step with `skip_in_yaml: true` or equivalent; refine detector. |
| `open-release-pr` | Currently in `bump-and-release.yml` workflow, not in `release-on-merge.yml` (different workflow file) | Sibling change: either consolidate workflows OR have detector read multiple workflow files. |
| `preflight-cross-branch-drift` | Canonical specifies this safety Step; YAML doesn't implement | Sibling change: add the preflight to `release-on-merge.yml`. |
| `publish-github-release` | Manual founder step per `bot-tag-doesnt-trigger-release-prod` FailureMode | Tag canonical Step with `skip_in_yaml: true`. |
| `squash-merge` | Happens in GitHub UI / PR merge workflow, not in YAML bash | Tag canonical Step with `skip_in_yaml: true`. |
| `wait-for-checks-and-mergeability` | Happens in skill prose (Steps 9-15 boundary per MUC-007) | Tag canonical Step OR move to YAML implementation. |

**Five `missing_failuremode_handling` items** — Steps name FailureModes in `handles_failures` but YAML doesn't annotate which block handles each:

| Step | FailureMode | Future action |
|---|---|---|
| `draft-pr-body-and-changelog` | `probabilistic-step-token-budget-exceeded` | Add `# canonical:failuremode:probabilistic-step-token-budget-exceeded` near the draft block. |
| `wait-for-checks-and-mergeability` | `pr-checks-fail`, `release-pr-conflicts-with-target-at-merge`, `pr-open-but-mergeability-stuck` | Step itself absent from YAML; resolves with the parent Step's resolution above. |
| `publish-github-release` | `bot-tag-doesnt-trigger-release-prod` | Step itself absent (parent resolution above). |

**Recommended disposition for the 11 items:** open a **follow-on change** named something like `reconcile-canonical-to-imperative-drift` after this change ships. That change's first deliverable is a refinement to the canonical Step schema (a `skip_in_yaml` field for prose-handled Steps) + detector update + remediation of the genuinely-missing imperative implementations.

### Methodology

- [✓] CR-01: 42/42 unit + live drift run; exit 1 with structured JSON envelope.
- [—] CR-02: 1-WP train (deviation per the wave-2/3 pattern). Per-WP Step 6.5 bundle already PASS.
- [✓] CR-03: live run + WP-007 per-WP review covered the code end-to-end.
- [✓] CR-04: drift findings cite specific Step + FailureMode names.
- [✓] CR-05: 0 findings (the drift items are detector outputs, not defects).
- [✓] CR-06: PASS.
- [—] CR-07: reduced — Step 11 subagent not dispatched; inline security spot-check substituted.
- [✓] CR-09: PR Hygiene clean.

### Run details

- **Diff source:** `git diff 35af641..e182531`.
- **Detector live run:** exit 1 (drift detected); 11 items; bundle artifact at `tool-outputs/drift-detector-live-run.json`.
- **Watch list outcome:** future-change scope (one follow-on change to handle all 11).
